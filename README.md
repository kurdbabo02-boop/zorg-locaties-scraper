# 🏥 Zorg Locaties Scraper

Automatisch systeem dat kleinschalige en opkomende zorginstellingen vindt
in **Nederland** en **België**, met focus op **ouderenzorg** en **dementie**.

Geen API-sleutel nodig. Werkt lokaal op macOS.

---

## Wat doet het?

Het systeem scrapt meerdere bronnen tegelijkertijd:

| Scraper | Bron | Land |
|---------|------|------|
| `zorgkaart` | [Zorgkaart Nederland](https://www.zorgkaart.nl) — grootste NL-zorgdatabase | 🇳🇱 |
| `vektis` | [Vektis AGB-register](https://www.vektis.nl/intelligence/open-data) — open data CSV | 🇳🇱 |
| `search` | DuckDuckGo-zoekopdrachten (geen API-sleutel) | 🇳🇱 🇧🇪 |
| `belgium` | Zorg en Gezondheid (Vlaanderen), AVIQ (Wallonië), Iriscare (Brussel) | 🇧🇪 |

### Focus
- Kleinschalige instellingen (`--small`)
- Opkomende / nieuwe locaties (`--emerging`)
- Verpleeghuizen, woonzorgcentra, dagopvang, thuiszorg, kleinschalig wonen

### Output
- **SQLite-database** (`data/zorg_locaties.db`) — cumulatief, met deduplicatie
- **CSV** — direct te openen in Excel
- **JSON** — voor verdere verwerking
- **Excel** — opgemaakt met kleuren en filters

---

## Installatie (macOS)

```bash
# Clone de repo
git clone https://github.com/JOUW_USERNAME/zorg-locaties-scraper.git
cd zorg-locaties-scraper

# Eénmalige setup (installeert dependencies in een virtuele omgeving)
bash setup.sh
```

### Vereisten
- macOS 12+
- Python 3.10 of hoger

Geen Python? Installeer via:
```bash
brew install python@3.11
```

---

## Gebruik

Activeer de omgeving eerst:
```bash
source .venv/bin/activate
```

### Alles draaien
```bash
python main.py
```

### Specifieke scraper
```bash
python main.py --scrapers search          # alleen DuckDuckGo
python main.py --scrapers zorgkaart       # alleen Zorgkaart NL
python main.py --scrapers belgium         # alleen België
python main.py --scrapers zorgkaart search vektis  # meerdere
```

### Filters
```bash
python main.py --country NL              # alleen Nederland
python main.py --country BE              # alleen België
python main.py --small                   # alleen kleine instellingen
python main.py --emerging                # alleen opkomende instellingen
python main.py --small --emerging        # beiden
python main.py --city Amsterdam          # filter op stad
```

### Export
```bash
python main.py --export csv              # alleen CSV
python main.py --export excel            # alleen Excel
python main.py --export json             # alleen JSON
python main.py --export all              # alles (standaard)
```

### Automatisch draaien (elke 24 uur)
```bash
python main.py --schedule
```

### Alles samen
```bash
python main.py --country NL --small --emerging --export excel --verbose
```

---

## Projectstructuur

```
zorg-locaties-scraper/
├── main.py               # CLI-ingang
├── setup.sh              # macOS setup script
├── requirements.txt
│
├── config/
│   ├── settings.py       # globale instellingen
│   ├── regions.py        # provincies en steden NL/BE
│   └── queries.py        # zoekopdracht-templates
│
├── scrapers/
│   ├── base.py           # abstracte basisklasse
│   ├── zorgkaart.py      # Zorgkaart Nederland
│   ├── search.py         # DuckDuckGo (geen API-sleutel)
│   ├── vektis.py         # Vektis AGB open data
│   └── belgium.py        # Vlaamse, Waalse en Brusselse bronnen
│
├── models/
│   └── location.py       # CareLocation datamodel
│
├── storage/
│   ├── database.py       # SQLite opslag met deduplicatie
│   └── export.py         # CSV / JSON / Excel export
│
├── utils/
│   ├── http.py           # HTTP-helpers met rate-limiting
│   └── classify.py       # classificatie (klein, opkomend, type)
│
└── data/
    ├── zorg_locaties.db  # SQLite database (na eerste run)
    └── output/           # geëxporteerde bestanden
```

---

## Datavelden per locatie

| Veld | Beschrijving |
|------|-------------|
| `name` | Naam van de instelling |
| `address` | Straatnaam + huisnummer |
| `city` | Stad/gemeente |
| `postal_code` | Postcode |
| `province` | Provincie |
| `country` | NL of BE |
| `care_type` | verpleeghuis, woonzorgcentrum, etc. |
| `specializations` | dementie, ouderenzorg (JSON-lijst) |
| `is_small` | Klein of kleinschalig? (ja/nee) |
| `is_emerging` | Nieuw of opkomend? (ja/nee) |
| `size_indicator` | klein / middelgroot / groot |
| `phone` | Telefoonnummer |
| `email` | E-mailadres |
| `website` | Website-URL |
| `description` | Korte beschrijving |
| `rating` | Beoordeling (indien beschikbaar) |
| `source` | Welke scraper heeft dit gevonden |
| `source_url` | Bron-URL |
| `scraped_at` | Timestamp van het scrapen |

---

## Bronnen

### Nederland
- **Zorgkaart.nl** — [zorgkaart.nl](https://www.zorgkaart.nl)
- **Vektis AGB-register** — [vektis.nl/intelligence/open-data](https://www.vektis.nl/intelligence/open-data)

### België
- **Zorg en Gezondheid** (Vlaanderen) — [zorg-en-gezondheid.be](https://www.zorg-en-gezondheid.be)
- **AVIQ** (Wallonië) — [aviq.be](https://www.aviq.be)
- **Iriscare** (Brussel) — [iriscare.brussels](https://www.iriscare.brussels)

---

## Noten

- Het systeem respecteert de servers met ingebouwde pauzes tussen verzoeken (1–4 seconden).
- Deduplicatie voorkomt dubbele vermeldingen in de database.
- DuckDuckGo werkt zonder API-sleutel en heeft geen strikte rate-limits.
- Sommige websites kunnen hun HTML-structuur wijzigen; de scrapers zijn gebouwd om hier zo goed mogelijk mee om te gaan.
