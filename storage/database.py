"""
SQLite storage for CareLocation objects.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from models import CareLocation
from config.settings import DB_PATH

logger = logging.getLogger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS locations (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    address      TEXT,
    city         TEXT,
    postal_code  TEXT,
    province     TEXT,
    country      TEXT,
    care_type    TEXT,
    specializations TEXT,   -- JSON array
    is_small     INTEGER,
    is_emerging  INTEGER,
    size_indicator TEXT,
    phone        TEXT,
    email        TEXT,
    website      TEXT,
    description  TEXT,
    founded_year INTEGER,
    num_beds     INTEGER,
    rating       REAL,
    source       TEXT,
    source_url   TEXT,
    scraped_at   TEXT,
    raw_data     TEXT,
    dedup_key    TEXT
);

CREATE INDEX IF NOT EXISTS idx_country  ON locations(country);
CREATE INDEX IF NOT EXISTS idx_city     ON locations(city);
CREATE INDEX IF NOT EXISTS idx_dedup    ON locations(dedup_key);
CREATE INDEX IF NOT EXISTS idx_source   ON locations(source);
"""


class Database:
    def __init__(self, path: str = DB_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(DDL)
        self.conn.commit()

    def upsert(self, loc: CareLocation) -> bool:
        """Insert loc; skip if dedup_key already exists. Returns True if inserted."""
        key = loc.dedup_key()
        existing = self.conn.execute(
            "SELECT id FROM locations WHERE dedup_key = ?", (key,)
        ).fetchone()
        if existing:
            return False

        d = loc.to_dict()
        d["dedup_key"] = key
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        self.conn.execute(
            f"INSERT INTO locations ({cols}) VALUES ({placeholders})",
            list(d.values()),
        )
        self.conn.commit()
        return True

    def upsert_many(self, locations: List[CareLocation]) -> int:
        """Bulk insert; returns number of new records added."""
        added = 0
        for loc in locations:
            if self.upsert(loc):
                added += 1
        logger.info("DB: %d nieuw toegevoegd van %d aangeboden", added, len(locations))
        return added

    def all(self, country: str = None, small_only: bool = False,
            emerging_only: bool = False) -> List[CareLocation]:
        sql = "SELECT * FROM locations WHERE 1=1"
        params = []
        if country:
            sql += " AND country = ?"
            params.append(country)
        if small_only:
            sql += " AND is_small = 1"
        if emerging_only:
            sql += " AND is_emerging = 1"
        sql += " ORDER BY country, city, name"

        rows = self.conn.execute(sql, params).fetchall()
        return [CareLocation.from_dict(dict(r)) for r in rows]

    def count(self) -> dict:
        """Return count statistics."""
        rows = self.conn.execute(
            "SELECT country, COUNT(*) as n FROM locations GROUP BY country"
        ).fetchall()
        totals = {r["country"]: r["n"] for r in rows}
        totals["total"] = sum(totals.values())
        return totals

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
