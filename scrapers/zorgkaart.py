"""
Scraper for Zorgkaart Nederland (zorgkaart.nl).

Zorgkaart is the largest public database of Dutch healthcare providers.
We target the categories most relevant to elderly and dementia care.
"""

import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from models import CareLocation
from scrapers.base import BaseScraper
from utils.classify import detect_care_type, detect_specializations, is_small, is_emerging, size_indicator

logger = logging.getLogger(__name__)

BASE_URL = "https://www.zorgkaart.nl"

# Category slugs on zorgkaart.nl that are relevant to elderly/dementia care
CATEGORIES = [
    ("verpleging-en-verzorging", "verpleeghuis"),
    ("dementie", "dementie_centrum"),
    ("ouderengeneeskunde", "ouderengeneeskunde"),
    ("thuiszorg", "thuiszorg"),
    ("dagopvang-ouderen", "dagopvang"),
]


class ZorgkaartScraper(BaseScraper):
    name = "zorgkaart_nl"

    def scrape(self) -> List[CareLocation]:
        locations = []
        for slug, care_hint in CATEGORIES:
            try:
                page_locs = self._scrape_category(slug, care_hint)
                logger.info("[zorgkaart] %s -> %d locaties", slug, len(page_locs))
                locations.extend(page_locs)
            except Exception as e:
                logger.warning("[zorgkaart] Fout bij categorie %s: %s", slug, e)
        return locations

    def _scrape_category(self, slug: str, care_hint: str) -> List[CareLocation]:
        """Scrape all pages of a category."""
        locations = []
        page = 1
        while True:
            url = f"{BASE_URL}/zorg/{slug}?pagina={page}"
            try:
                soup = self.get_soup(url)
            except Exception as e:
                logger.warning("[zorgkaart] Kon pagina niet laden: %s (%s)", url, e)
                break

            items = self._parse_listing(soup)
            if not items:
                break

            for item in items:
                loc = self._build_location(item, care_hint)
                if loc:
                    locations.append(loc)

            # Check if there is a next page
            next_btn = soup.find("a", attrs={"aria-label": re.compile(r"volgende", re.I)})
            if not next_btn:
                # Also try a generic next link
                next_btn = soup.find("a", string=re.compile(r"volgende", re.I))
            if not next_btn:
                break

            page += 1
            if page > 50:  # safety cap
                break

        return locations

    def _parse_listing(self, soup: BeautifulSoup) -> list:
        """Extract raw provider entries from a listing page."""
        # Zorgkaart uses article elements or list items for search results
        items = soup.find_all("article", class_=re.compile(r"zorgaanbieder|provider|result", re.I))
        if not items:
            items = soup.find_all("li", class_=re.compile(r"zorgaanbieder|result", re.I))
        if not items:
            # Fall back to any card-like div with a heading
            items = soup.find_all("div", class_=re.compile(r"card|result|item", re.I))
        return items

    def _build_location(self, item, care_hint: str) -> Optional[CareLocation]:
        try:
            name = self._extract_text(item, ["h2", "h3", "h4", ".name", ".title"])
            if not name:
                return None

            link_tag = item.find("a", href=True)
            source_url = urljoin(BASE_URL, link_tag["href"]) if link_tag else ""

            address  = self._extract_text(item, [".address", ".adres", "[itemprop='streetAddress']"])
            city     = self._extract_text(item, [".city", ".plaats", "[itemprop='addressLocality']"])
            postal   = self._extract_text(item, [".postal", ".postcode", "[itemprop='postalCode']"])
            phone    = self._extract_text(item, [".phone", ".telefoon", "[itemprop='telephone']"])
            rating_tag = item.find(class_=re.compile(r"rating|score|cijfer", re.I))
            rating = None
            if rating_tag:
                m = re.search(r"(\d+[.,]\d+)", rating_tag.get_text())
                if m:
                    rating = float(m.group(1).replace(",", "."))

            desc = self._extract_text(item, [".description", ".omschrijving", "p"])

            specs = detect_specializations(name, desc)
            # Always include if care_hint is dementia
            if care_hint == "dementie_centrum" and "dementie" not in specs:
                specs.append("dementie")
            if "ouderenzorg" not in specs:
                specs.append("ouderenzorg")

            return CareLocation(
                name=name,
                address=address,
                city=city,
                postal_code=postal,
                country="NL",
                care_type=care_hint,
                specializations=specs,
                phone=phone,
                source=self.name,
                source_url=source_url,
                rating=rating,
                description=desc,
                is_small=is_small(name, desc),
                is_emerging=is_emerging(name, desc),
                size_indicator=size_indicator(name=name, description=desc),
            )
        except Exception as e:
            logger.debug("[zorgkaart] Parse fout: %s", e)
            return None

    def _extract_text(self, soup, selectors: list) -> str:
        for sel in selectors:
            tag = soup.select_one(sel) if sel.startswith(".") or sel.startswith("[") else soup.find(sel)
            if tag:
                return tag.get_text(strip=True)
        return ""
