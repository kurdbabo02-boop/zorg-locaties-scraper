"""
HTTP helpers: sessions with polite delays, retries, and rotating user-agents.
"""

import time
import random
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import (
    USER_AGENTS, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
    REQUEST_TIMEOUT, MAX_RETRIES
)

logger = logging.getLogger(__name__)


def get_session() -> requests.Session:
    """Return a requests Session with retry logic and a random User-Agent."""
    session = requests.Session()

    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return session


def polite_get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """GET with a random delay to avoid hammering servers."""
    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    logger.debug("Sleeping %.1fs before GET %s", delay, url)
    time.sleep(delay)

    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp
    except requests.exceptions.HTTPError as e:
        logger.warning("HTTP %s for %s", e.response.status_code, url)
        raise
    except requests.exceptions.RequestException as e:
        logger.warning("Request failed for %s: %s", url, e)
        raise
