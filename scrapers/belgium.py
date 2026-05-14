"""
Belgian care facility scrapers.

Sources:
1. Zorg en Gezondheid (Flemish Agency) — erkende woonzorgcentra
   https://www.zorg-en-gezondheid.be/erkenningszoeker
2. AVIQ (Wallonia) — maisons de repos et de soins
   https://www.aviq.be/cms/sante/etablissements
3. Iriscare (Brussels)
   https://www.iriscare.brussels/
"""

import logging
import re
from typing import List

from models import CareLocation
from scrapers.base import BaseScraper
from utils.classify import detect_care_type, detect_specializations, is_small, is_emerging, size_indicator

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Zorg en Gezondheid (Flanders)
# ------------------------------------------------------------------
ZEG_SEARCH_URL = "https://www.zorg-en-gezondheid.be/erkenningszoeker"
ZEG_WZC_URL    = "https://www.zorg-en-gezondheid.be/erkende-woonzorgcentra"

# ------------------------------------------------------------------
# AVIQ (Wallonia)
# ------------------------------------------------------------------
AVIQ_URL = "https://www.aviq.be/cms/sante/etablissements/maisons-de-repos-et-de-soins"

# ------------------------------------------------------------------
# Iriscare (Brussels)
# ------------------------------------------------------------------
IRISCARE_URL = "https://www.iriscare.brussels/citoyen/maisons-de-repos/"


class BelgiumScraper(BaseScraper):
    name = "belgium"

    def scrape(self) -> List[CareLocation]:
        locations = []

        # --- Flanders: Zorg en Gezondheid ---
        try:
            fl = self._scrape_flanders()
            logger.info("[belgium/flanders] %d locaties", len(fl))
            locations.extend(fl)
        except Exception as e:
            logger.warning("[belgium/flanders] Fout: %s", e)

        # --- Wallonia: AVIQ ---
        try:
            wa = self._scrape_aviq()
            logger.info("[belgium/wallonie] %d locaties", len(wa))
            locations.extend(wa)
        except Exception as e:
            logger.warning("[belgium/wallonie] Fout: %s", e)

        # --- Brussels: Iriscare ---
        try:
            br = self._scrape_iriscare()
            logger.info("[belgium/brussel] %d locaties", len(br))
            locations.extend(br)
        except Exception as e:
            logger.warning("[belgium/brussel] Fout: %s", e)

        return locations

    # ---------------------------------------------------------------
    # Flanders
    # ---------------------------------------------------------------
    def _scrape_flanders(self) -> List[CareLocation]:
        locations = []
        page = 1
        while True:
            url = f"{ZEG_WZC_URL}?page={page}"
            try:
                soup = self.get_soup(url)
            except Exception:
                break

            rows = soup.select("table tr, .views-row, .result-item, article")
            if not rows:
                break

            found_on_page = 0
            for row in rows:
                loc = self._parse_flanders_row(row)
                if loc:
                    locations.append(loc)
                    found_on_page += 1

            if found_on_page == 0:
                break

            next_link = soup.find("a", string=re.compile(r"volgende|next", re.I))
            if not next_link:
                break
            page += 1
            if page > 30:
                break

        return locations

    def _parse_flanders_row(self, row) -> CareLocation | None:
        text = row.get_text(separator=" ", strip=True)
        if not text or len(text) < 10:
            return None

        # Try to find name (first heading or strong)
        name_tag = row.find(["h2", "h3", "h4", "strong", "b"])
        name = name_tag.get_text(strip=True) if name_tag else text[:80]
        if not name:
            return None

        link = row.find("a", href=True)
        url  = link["href"] if link else ZEG_WZC_URL
        if url and not url.startswith("http"):
            url = "https://www.zorg-en-gezondheid.be" + url

        # Address patterns: "Straatnaam 1, 9000 Gent"
        addr_match = re.search(r"([A-Z][^,\d]+\d+[^,]*),\s*(\d{4})\s+([A-Z][^\n,]+)", text)
        address = addr_match.group(1).strip() if addr_match else ""
        postal  = addr_match.group(2) if addr_match else ""
        city    = addr_match.group(3).strip() if addr_match else ""

        phone_match = re.search(r"(\+32|0\d)[0-9 .\-/]{8,}", text)
        phone = phone_match.group(0).strip() if phone_match else ""

        specs = detect_specializations(name, text)
        if not specs:
            specs = ["ouderenzorg"]

        return CareLocation(
            name=name,
            address=address,
            city=city,
            postal_code=postal,
            country="BE",
            care_type="woonzorgcentrum",
            specializations=specs,
            phone=phone,
            is_small=is_small(name, text),
            is_emerging=is_emerging(name, text),
            size_indicator=size_indicator(name=name, description=text),
            source=self.name + "_flanders",
            source_url=url,
        )

    # ---------------------------------------------------------------
    # Wallonia — AVIQ
    # ---------------------------------------------------------------
    def _scrape_aviq(self) -> List[CareLocation]:
        locations = []
        try:
            soup = self.get_soup(AVIQ_URL)
        except Exception as e:
            logger.warning("[aviq] Laden mislukt: %s", e)
            return []

        rows = soup.select("table tbody tr, .etablissement, .institution, article, .views-row")
        for row in rows:
            loc = self._parse_aviq_row(row)
            if loc:
                locations.append(loc)
        return locations

    def _parse_aviq_row(self, row) -> CareLocation | None:
        text = row.get_text(separator=" ", strip=True)
        if not text or len(text) < 10:
            return None

        cells = row.find_all(["td", "th"])
        name = cells[0].get_text(strip=True) if cells else text[:80]
        if not name or name.lower() in ("nom", "name", "instelling"):
            return None

        # Belgian postal code: 4-digit
        postal_match = re.search(r"\b(\d{4})\b", text)
        postal = postal_match.group(1) if postal_match else ""

        city_match = re.search(r"\b\d{4}\s+([A-Z][^\n,\d]{2,30})", text)
        city = city_match.group(1).strip() if city_match else (cells[2].get_text(strip=True) if len(cells) > 2 else "")

        phone_match = re.search(r"(\+32|0\d)[0-9 .\-/]{8,}", text)
        phone = phone_match.group(0).strip() if phone_match else ""

        return CareLocation(
            name=name,
            city=city,
            postal_code=postal,
            country="BE",
            care_type="maison_de_repos",
            specializations=["ouderenzorg"],
            phone=phone,
            is_small=is_small(name, text),
            is_emerging=is_emerging(name, text),
            size_indicator=size_indicator(name=name, description=text),
            source=self.name + "_wallonie",
            source_url=AVIQ_URL,
        )

    # ---------------------------------------------------------------
    # Brussels — Iriscare
    # ---------------------------------------------------------------
    def _scrape_iriscare(self) -> List[CareLocation]:
        locations = []
        try:
            soup = self.get_soup(IRISCARE_URL)
        except Exception as e:
            logger.warning("[iriscare] Laden mislukt: %s", e)
            return []

        rows = soup.select("table tbody tr, .etablissement, article, .views-row, li")
        for row in rows:
            text = row.get_text(separator=" ", strip=True)
            if len(text) < 15:
                continue
            name_tag = row.find(["h2", "h3", "strong", "b", "a"])
            name = name_tag.get_text(strip=True) if name_tag else text[:80]
            if not name:
                continue

            link = row.find("a", href=True)
            url  = link["href"] if link else IRISCARE_URL
            if url and not url.startswith("http"):
                url = "https://www.iriscare.brussels" + url

            phone_match = re.search(r"(\+32|0\d)[0-9 .\-/]{8,}", text)
            phone = phone_match.group(0).strip() if phone_match else ""

            postal_match = re.search(r"\b(1[0-9]{3})\b", text)  # Brussels postcodes 1000–1999
            postal = postal_match.group(1) if postal_match else ""

            specs = detect_specializations(name, text)
            if not specs:
                specs = ["ouderenzorg"]

            locations.append(CareLocation(
                name=name,
                postal_code=postal,
                city="Brussel",
                country="BE",
                care_type="maison_de_repos",
                specializations=specs,
                phone=phone,
                is_small=is_small(name, text),
                is_emerging=is_emerging(name, text),
                size_indicator=size_indicator(name=name, description=text),
                source=self.name + "_brussel",
                source_url=url,
            ))
        return locations
