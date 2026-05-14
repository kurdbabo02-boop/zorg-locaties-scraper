"""
Vektis Open Data scraper.

Vektis (nl) publishes the AGB-register as open CSV downloads — no API key.
The AGB-register contains all contracted healthcare providers in the Netherlands,
including care homes, nursing homes, and home care organisations.

Download page: https://www.vektis.nl/intelligence/open-data
"""

import io
import logging
import zipfile
import re
from typing import List

import requests

from models import CareLocation
from scrapers.base import BaseScraper
from utils.classify import detect_care_type, detect_specializations, is_small, is_emerging, size_indicator

logger = logging.getLogger(__name__)

# AGB-register open data: zorg type 13 = Verpleging & Verzorging (V&V)
# Published as a yearly zip with CSV inside
AGB_BASE_URL = "https://www.vektis.nl/intelligence/open-data"

# Direct CSV download link pattern (Vektis uses a stable pattern)
# We try multiple known URLs; Vektis updates these occasionally
AGB_CSV_URLS = [
    "https://www.vektis.nl/uploads/Zorgaanbieder%20AGB%20register/agb-register-2024.zip",
    "https://www.vektis.nl/uploads/Zorgaanbieder%20AGB%20register/agb-register-2023.zip",
    # Also try direct CSV (some years published as plain CSV)
    "https://www.vektis.nl/uploads/Zorgaanbieder%20AGB%20register/agb-register.csv",
]

# V&V (Verpleging en Verzorging) is AGB zorgsoort code 13 or 08 (ouderenzorg)
VV_CODES = {"13", "08", "12"}   # 12 = GGZ (some dementia units)

# Keywords to filter V&V / dementia from the name column
VV_KEYWORDS = [
    "verpleeghuis", "verpleeg", "zorgcentrum", "woonzorg", "ouderen",
    "senioren", "dementie", "alzheimer", "verzorging", "thuiszorg",
    "kleinschalig", "groepswonen",
]


class VektisScraper(BaseScraper):
    name = "vektis_agb"

    def scrape(self) -> List[CareLocation]:
        logger.info("[vektis] AGB-register open data ophalen...")
        df_rows = self._try_download_agb()
        if df_rows is None:
            logger.warning("[vektis] Kon AGB-data niet downloaden, sla over.")
            return []

        locations = []
        for row in df_rows:
            loc = self._row_to_location(row)
            if loc:
                locations.append(loc)

        logger.info("[vektis] %d V&V locaties in AGB-register", len(locations))
        return locations

    # -------------------------------------------------------------------------
    def _try_download_agb(self):
        """Try each known URL; return parsed rows or None on failure."""
        for url in AGB_CSV_URLS:
            try:
                logger.debug("[vektis] Probeer %s", url)
                resp = self.session.get(url, timeout=60, stream=True)
                if resp.status_code != 200:
                    continue
                content = resp.content
                if url.endswith(".zip"):
                    rows = self._parse_zip(content)
                else:
                    rows = self._parse_csv_bytes(content)
                if rows:
                    return rows
            except Exception as e:
                logger.debug("[vektis] %s mislukt: %s", url, e)

        # Fallback: scrape the open data page for the current CSV link
        try:
            return self._scrape_page_for_csv()
        except Exception as e:
            logger.warning("[vektis] Pagina scrape mislukt: %s", e)
        return None

    def _scrape_page_for_csv(self):
        """Visit the open data page and find the latest AGB CSV link."""
        soup = self.get_soup(AGB_BASE_URL)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "agb" in href.lower() and (href.endswith(".zip") or href.endswith(".csv")):
                full_url = href if href.startswith("http") else f"https://www.vektis.nl{href}"
                resp = self.session.get(full_url, timeout=60)
                if resp.status_code == 200:
                    if full_url.endswith(".zip"):
                        return self._parse_zip(resp.content)
                    return self._parse_csv_bytes(resp.content)
        return None

    def _parse_zip(self, content: bytes):
        """Extract the first CSV from a zip archive."""
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            csv_files = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not csv_files:
                return None
            with z.open(csv_files[0]) as f:
                return self._parse_csv_bytes(f.read())

    def _parse_csv_bytes(self, content: bytes):
        """Parse CSV bytes into a list of dicts."""
        import csv

        # Try common encodings
        for enc in ("utf-8-sig", "latin-1", "cp1252"):
            try:
                text = content.decode(enc)
                reader = csv.DictReader(io.StringIO(text), delimiter=";")
                rows = list(reader)
                if rows:
                    return rows
            except Exception:
                continue
        return None

    def _row_to_location(self, row: dict) -> CareLocation | None:
        """Convert an AGB CSV row to a CareLocation, filtering for V&V."""
        # Normalise column names (Vektis uses various naming conventions)
        r = {k.lower().replace(" ", "_"): v for k, v in row.items()}

        name = r.get("naam_zorgaanbieder") or r.get("naam") or ""
        if not name:
            return None

        # Filter by zorgsoort code
        zorgsoort = r.get("zorgsoort_code") or r.get("agb_zorgsoort") or ""
        if zorgsoort and zorgsoort not in VV_CODES:
            # If we have a code that doesn't match, skip — unless name matches keyword
            if not any(kw in name.lower() for kw in VV_KEYWORDS):
                return None

        # If no code available, filter by name keywords
        if not zorgsoort:
            if not any(kw in name.lower() for kw in VV_KEYWORDS):
                return None

        address     = r.get("straatnaam", "") + " " + r.get("huisnummer", "")
        city        = r.get("plaatsnaam") or r.get("woonplaats") or ""
        postal      = r.get("postcode") or ""
        phone       = r.get("telefoonnummer") or r.get("telefoon") or ""
        agb_code    = r.get("agb_code") or r.get("zorgverlenerscode") or ""

        specs = detect_specializations(name)
        if not specs:
            specs = ["ouderenzorg"]

        return CareLocation(
            name=name.strip(),
            address=address.strip(),
            city=city.strip(),
            postal_code=postal.strip(),
            country="NL",
            care_type=detect_care_type(name),
            specializations=specs,
            phone=phone.strip(),
            is_small=is_small(name),
            is_emerging=is_emerging(name),
            size_indicator=size_indicator(name=name),
            source=self.name,
            source_url=f"https://www.vektis.nl/zorgaanbieders/{agb_code}" if agb_code else AGB_BASE_URL,
            raw_data=str(row),
        )
