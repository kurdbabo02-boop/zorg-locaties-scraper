"""
Global settings and constants for the zorg-locaties scraper.
"""

import os

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
REQUEST_DELAY_MIN = 1.5   # seconds between requests (min)
REQUEST_DELAY_MAX = 4.0   # seconds between requests (max)
REQUEST_TIMEOUT   = 30    # seconds
MAX_RETRIES       = 3

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
OUTPUT_DIR  = os.path.join(DATA_DIR, "output")
DB_PATH     = os.path.join(DATA_DIR, "zorg_locaties.db")

# ---------------------------------------------------------------------------
# Scraper toggles (set to False to skip a scraper)
# ---------------------------------------------------------------------------
ENABLE_ZORGKAART   = True
ENABLE_SEARCH      = True
ENABLE_VEKTIS      = True
ENABLE_BELGIUM     = True

# DuckDuckGo search: results per query
SEARCH_MAX_RESULTS = 15

# How many search queries to run per region (keeps runtime manageable)
MAX_QUERIES_PER_REGION = 5
