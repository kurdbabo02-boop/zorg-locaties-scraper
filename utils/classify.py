"""
Helpers to classify a care location as small, emerging, and/or focused on
elderly care / dementia.
"""

from config.queries import (
    CARE_TYPE_KEYWORDS, ELDERLY_KEYWORDS, DEMENTIA_KEYWORDS,
    SMALL_KEYWORDS, EMERGING_KEYWORDS,
)


def _text(*fields) -> str:
    """Combine fields into one lowercase string for keyword matching."""
    return " ".join(str(f or "").lower() for f in fields)


def detect_care_type(name: str, description: str = "") -> str:
    text = _text(name, description)
    for care_type, keywords in CARE_TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return care_type
    return "overig"


def detect_specializations(name: str, description: str = "") -> list:
    text = _text(name, description)
    specs = []
    if any(kw in text for kw in ELDERLY_KEYWORDS):
        specs.append("ouderenzorg")
    if any(kw in text for kw in DEMENTIA_KEYWORDS):
        specs.append("dementie")
    return specs


def is_relevant(name: str, description: str = "") -> bool:
    """Returns True if the location is likely related to elderly/dementia care."""
    specs = detect_specializations(name, description)
    return bool(specs)


def is_small(name: str, description: str = "", num_beds: int = None) -> bool:
    text = _text(name, description)
    if any(kw in text for kw in SMALL_KEYWORDS):
        return True
    if num_beds is not None and num_beds <= 30:
        return True
    return False


def is_emerging(name: str, description: str = "", founded_year: int = None) -> bool:
    text = _text(name, description)
    if any(kw in text for kw in EMERGING_KEYWORDS):
        return True
    if founded_year is not None and founded_year >= 2018:
        return True
    return False


def size_indicator(num_beds: int = None, name: str = "", description: str = "") -> str:
    text = _text(name, description)
    if num_beds is not None:
        if num_beds <= 20:
            return "klein"
        elif num_beds <= 60:
            return "middelgroot"
        else:
            return "groot"
    if any(kw in text for kw in SMALL_KEYWORDS):
        return "klein"
    return "onbekend"
