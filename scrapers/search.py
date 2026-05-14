"""
Search-based discovery using DuckDuckGo (no API key required).

This is especially useful for finding small and emerging care institutions
that may not appear in official registries yet.
"""

import logging
import re
import random
from typing import List
from urllib.parse import urlparse

from duckduckgo_search import DDGS

from models import CareLocation
from scrapers.base import BaseScraper
from utils.classify import (
    detect_care_type, detect_specializations, is_small, is_emerging, size_indicator, is_relevant
)
from config.queries import (
    BASE_QUERIES_NL, BASE_QUERIES_BE,
    NATIONAL_QUERIES_NL, NATIONAL_QUERIES_BE,
)
from config.regions import NL_PROVINCES, NL_CITIES, BE_PROVINCES, BE_CITIES
from config.settings import SEARCH_MAX_RESULTS, MAX_QUERIES_PER_REGION

logger = logging.getLogger(__name__)


class SearchScraper(BaseScraper):
    name = "duckduckgo_search"

    def __init__(self, quick_mode: bool = False, max_queries: int = None,
                 region_override: List[str] = None):
        super().__init__()
        self.quick_mode      = quick_mode       # True = snelle modus (weinig queries)
        self.max_queries     = max_queries       # harde limiet op totaal aantal queries
        self.region_override = region_override  # specifieke regio's van de UI

    def scrape(self) -> List[CareLocation]:
        locations = []
        seen_urls: set = set()

        all_queries = self._build_queries()
        logger.info("[search] Totaal %d zoekopdrachten", len(all_queries))

        for i, (query, country) in enumerate(all_queries, 1):
            logger.info("[search] (%d/%d) '%s'", i, len(all_queries), query)
            try:
                results = self._ddg_search(query)
                for r in results:
                    url = r.get("href", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    loc = self._result_to_location(r, country, query)
                    if loc:
                        locations.append(loc)
            except Exception as e:
                logger.warning("[search] Fout bij '%s': %s", query, e)

        logger.info("[search] %d locaties gevonden via zoekopdrachten", len(locations))
        return locations

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _build_queries(self) -> List[tuple]:
        """Return list of (query_string, country) tuples."""
        queries = []

        if self.quick_mode:
            # Snelle modus: alleen nationale queries, geen per-regio loops
            for q in NATIONAL_QUERIES_NL[:5]:
                queries.append((q, "NL"))
            for q in NATIONAL_QUERIES_BE[:3]:
                queries.append((q, "BE"))
            # Als regio's zijn meegegeven, voeg een paar gerichte queries toe
            if self.region_override:
                for region in self.region_override[:3]:
                    queries.append((f"verpleeghuis dementie {region}", "NL"))
                    queries.append((f"woonzorgcentrum ouderenzorg {region}", "NL"))
        else:
            # Volledige modus
            for q in NATIONAL_QUERIES_NL:
                queries.append((q, "NL"))
            for q in NATIONAL_QUERIES_BE:
                queries.append((q, "BE"))

            if self.region_override:
                nl_regions = self.region_override
                be_regions = self.region_override
            else:
                nl_regions = random.sample(NL_PROVINCES, min(6, len(NL_PROVINCES))) + \
                             random.sample(NL_CITIES,    min(10, len(NL_CITIES)))
                be_regions = random.sample(BE_PROVINCES, min(4, len(BE_PROVINCES))) + \
                             random.sample(BE_CITIES,    min(8, len(BE_CITIES)))

            for region in nl_regions:
                templates = random.sample(BASE_QUERIES_NL, min(MAX_QUERIES_PER_REGION, len(BASE_QUERIES_NL)))
                for tpl in templates:
                    queries.append((tpl.format(region=region), "NL"))

            for region in be_regions:
                templates = random.sample(BASE_QUERIES_BE, min(MAX_QUERIES_PER_REGION, len(BASE_QUERIES_BE)))
                for tpl in templates:
                    queries.append((tpl.format(region=region), "BE"))

        # Harde limiet
        if self.max_queries:
            queries = queries[:self.max_queries]

        return queries

    def _ddg_search(self, query: str) -> list:
        """Run a DuckDuckGo text search and return result dicts."""
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_MAX_RESULTS, region="nl-nl"))
        return results

    def _result_to_location(self, result: dict, country: str, query: str) -> CareLocation | None:
        """Convert a DDG search result to a CareLocation."""
        title = result.get("title", "")
        body  = result.get("body", "")
        url   = result.get("href", "")

        if not title:
            return None

        # Filter: only include results that look like care institutions
        if not is_relevant(title, body, url):
            return None

        # Try to extract city from query context
        city = self._extract_city_from_query(query)

        specs = detect_specializations(title, body)
        care_type = detect_care_type(title, body)

        return CareLocation(
            name=title,
            description=body[:500],
            website=url,
            city=city,
            country=country,
            care_type=care_type,
            specializations=specs,
            is_small=is_small(title, body),
            is_emerging=is_emerging(title, body),
            size_indicator=size_indicator(name=title, description=body),
            source=self.name,
            source_url=url,
        )

    def _extract_city_from_query(self, query: str) -> str:
        """Best-effort city extraction from the query string."""
        from config.regions import ALL_NL_LOCATIONS, ALL_BE_LOCATIONS
        for loc in ALL_NL_LOCATIONS + ALL_BE_LOCATIONS:
            if loc.lower() in query.lower():
                return loc
        return ""
