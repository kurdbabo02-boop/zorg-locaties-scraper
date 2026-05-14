#!/usr/bin/env python3
"""
Zorg Locaties Scraper — hoofdingang.

Gebruik:
  python main.py                        # alles draaien
  python main.py --scrapers zorgkaart   # alleen Zorgkaart
  python main.py --country NL           # alleen Nederland
  python main.py --small                # alleen kleine instellingen
  python main.py --emerging             # alleen opkomende instellingen
  python main.py --export csv           # exporteer naar CSV
  python main.py --schedule             # dagelijks draaien (24u interval)
"""

import argparse
import logging
import sys
import time
from typing import List

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from models import CareLocation
from storage import Database, export_all, to_csv, to_json, to_excel
from scrapers import ZorgkaartScraper, SearchScraper, VektisScraper, BelgiumScraper
from config.settings import ENABLE_ZORGKAART, ENABLE_SEARCH, ENABLE_VEKTIS, ENABLE_BELGIUM

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("data/scraper.log", encoding="utf-8"),
        ],
    )


def run_scrapers(args) -> List[CareLocation]:
    """Run all enabled scrapers and return combined results."""
    selected = args.scrapers if args.scrapers else ["all"]
    use_all  = "all" in selected

    scrapers_to_run = []
    if (use_all or "zorgkaart" in selected) and ENABLE_ZORGKAART:
        scrapers_to_run.append(("Zorgkaart Nederland", ZorgkaartScraper()))
    if (use_all or "search" in selected) and ENABLE_SEARCH:
        scrapers_to_run.append(("DuckDuckGo Zoeken", SearchScraper()))
    if (use_all or "vektis" in selected) and ENABLE_VEKTIS:
        scrapers_to_run.append(("Vektis AGB-register", VektisScraper()))
    if (use_all or "belgium" in selected) and ENABLE_BELGIUM:
        scrapers_to_run.append(("Belgie (Flanders/Wallonie/Brussel)", BelgiumScraper()))

    all_locations: List[CareLocation] = []

    for label, scraper in scrapers_to_run:
        console.rule(f"[bold cyan]{label}[/bold cyan]")
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Bezig met {label}...", total=None)
                results = scraper.scrape()
                progress.update(task, completed=True)

            console.print(f"  [green]✓[/green] {len(results)} locaties gevonden")
            all_locations.extend(results)
        except Exception as e:
            console.print(f"  [red]✗ Fout bij {label}: {e}[/red]")
            logging.exception("Scraper fout: %s", label)

    return all_locations


def apply_filters(locations: List[CareLocation], args) -> List[CareLocation]:
    """Apply command-line filters."""
    if args.country:
        locations = [l for l in locations if l.country.upper() == args.country.upper()]
    if args.small:
        locations = [l for l in locations if l.is_small]
    if args.emerging:
        locations = [l for l in locations if l.is_emerging]
    if args.city:
        locations = [l for l in locations if args.city.lower() in l.city.lower()]
    return locations


def save_to_db(locations: List[CareLocation]) -> int:
    with Database() as db:
        added = db.upsert_many(locations)
        stats = db.count()
    return added, stats


def do_export(locations: List[CareLocation], fmt: str):
    """Export to chosen format(s)."""
    if fmt == "all" or fmt is None:
        paths = export_all(locations)
        for f, path in paths.items():
            if path:
                console.print(f"  [green]✓[/green] {f.upper()}: {path}")
    elif fmt == "csv":
        console.print(f"  CSV: {to_csv(locations)}")
    elif fmt == "json":
        console.print(f"  JSON: {to_json(locations)}")
    elif fmt == "excel":
        p = to_excel(locations)
        if p:
            console.print(f"  Excel: {p}")


def print_summary(locations: List[CareLocation]):
    """Print a summary table of results."""
    if not locations:
        console.print("[yellow]Geen locaties gevonden.[/yellow]")
        return

    t = Table(title="Zorg Locaties Samenvatting", show_header=True, header_style="bold magenta")
    t.add_column("Land",     style="cyan",  no_wrap=True)
    t.add_column("Naam",     style="white")
    t.add_column("Stad",     style="green")
    t.add_column("Type",     style="yellow")
    t.add_column("Klein",    justify="center")
    t.add_column("Nieuw",    justify="center")
    t.add_column("Bron",     style="dim")

    # Show at most 50 rows in terminal
    for loc in locations[:50]:
        t.add_row(
            loc.country,
            loc.name[:45],
            loc.city[:25],
            loc.care_type[:20],
            "✓" if loc.is_small else "",
            "✓" if loc.is_emerging else "",
            loc.source[:20],
        )

    if len(locations) > 50:
        t.add_row("...", f"(+{len(locations)-50} meer)", "", "", "", "", "")

    console.print(t)
    console.print(f"\n[bold]Totaal:[/bold] {len(locations)} locaties")

    nl = sum(1 for l in locations if l.country == "NL")
    be = sum(1 for l in locations if l.country == "BE")
    sm = sum(1 for l in locations if l.is_small)
    em = sum(1 for l in locations if l.is_emerging)
    console.print(f"  Nederland: {nl} | België: {be} | Klein: {sm} | Opkomend: {em}")


def main():
    parser = argparse.ArgumentParser(
        description="Zorg Locaties Scraper — vindt zorginstellingen in NL en BE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scrapers", nargs="+",
        choices=["all", "zorgkaart", "search", "vektis", "belgium"],
        default=["all"],
        help="Welke scrapers te gebruiken (standaard: all)",
    )
    parser.add_argument("--country",  choices=["NL", "BE"],  help="Filter op land")
    parser.add_argument("--city",     type=str,               help="Filter op stad")
    parser.add_argument("--small",    action="store_true",    help="Alleen kleine instellingen")
    parser.add_argument("--emerging", action="store_true",    help="Alleen opkomende instellingen")
    parser.add_argument(
        "--export", choices=["csv", "json", "excel", "all"], default="all",
        help="Exportformat (standaard: all)",
    )
    parser.add_argument("--no-db",   action="store_true",    help="Niet opslaan in database")
    parser.add_argument("--verbose", action="store_true",    help="Uitgebreide logging")
    parser.add_argument(
        "--schedule", action="store_true",
        help="Draai automatisch elke 24 uur",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.schedule:
        try:
            import schedule as sched
            console.print("[bold]Scheduler gestart — draait elke 24 uur.[/bold]")
            console.print("Stop met Ctrl+C\n")

            def job():
                _run_once(args)

            job()  # run immediately first
            sched.every(24).hours.do(job)
            while True:
                sched.run_pending()
                time.sleep(60)
        except ImportError:
            console.print("[red]'schedule' pakket niet gevonden. Installeer met: pip install schedule[/red]")
            sys.exit(1)
    else:
        _run_once(args)


def _run_once(args):
    console.rule("[bold blue]Zorg Locaties Scraper[/bold blue]")
    console.print("Zoekt kleinschalige en opkomende zorginstellingen in NL en BE...\n")

    locations = run_scrapers(args)
    locations = apply_filters(locations, args)

    console.rule("[bold]Resultaten[/bold]")
    print_summary(locations)

    if not args.no_db and locations:
        added, stats = save_to_db(locations)
        console.print(f"\n[dim]Database: {added} nieuwe records toegevoegd | {stats}[/dim]")

    if locations:
        console.rule("[bold]Export[/bold]")
        do_export(locations, args.export)

    console.rule("[bold green]Klaar[/bold green]")


if __name__ == "__main__":
    main()
