"""
Data model for a care location.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional
import uuid
import json


@dataclass
class CareLocation:
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""

    # Address
    address: str = ""
    city: str = ""
    postal_code: str = ""
    province: str = ""
    country: str = ""           # "NL" or "BE"

    # Classification
    care_type: str = ""         # verpleeghuis, woonzorgcentrum, etc.
    specializations: List[str] = field(default_factory=list)
    is_small: bool = False
    is_emerging: bool = False
    size_indicator: str = ""    # klein / middelgroot / groot

    # Contact
    phone: str = ""
    email: str = ""
    website: str = ""

    # Meta
    description: str = ""
    founded_year: Optional[int] = None
    num_beds: Optional[int] = None
    rating: Optional[float] = None

    # Source tracking
    source: str = ""            # which scraper found it
    source_url: str = ""        # URL where found
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Raw backup
    raw_data: str = ""          # JSON blob of original scraped data

    def to_dict(self) -> dict:
        d = asdict(self)
        d["specializations"] = json.dumps(d["specializations"])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CareLocation":
        d = d.copy()
        specs = d.get("specializations", "[]")
        if isinstance(specs, str):
            try:
                d["specializations"] = json.loads(specs)
            except Exception:
                d["specializations"] = []
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def dedup_key(self) -> str:
        """Normalised key used to detect duplicates."""
        name = self.name.lower().strip()
        city = self.city.lower().strip()
        postal = self.postal_code.replace(" ", "").upper()
        return f"{name}|{city}|{postal}"

    def __repr__(self):
        return f"<CareLocation '{self.name}' in {self.city}, {self.country}>"
