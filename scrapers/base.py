"""
Abstract base class for all scrapers.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

from bs4 import BeautifulSoup
from models import CareLocation
from utils.http import get_session, polite_get

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """All scrapers inherit from this. They must implement `scrape()`."""

    name: str = "base"

    def __init__(self):
        self.session = get_session()
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        resp = polite_get(self.session, url, **kwargs)
        return BeautifulSoup(resp.text, "html.parser")

    def get_text(self, url: str, **kwargs) -> str:
        resp = polite_get(self.session, url, **kwargs)
        return resp.text

    @abstractmethod
    def scrape(self) -> List[CareLocation]:
        """Run the scraper and return a list of CareLocation objects."""
        ...
