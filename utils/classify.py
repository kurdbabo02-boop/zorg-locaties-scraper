"""
Helpers to classify a care location as small, emerging, and/or focused on
elderly care / dementia.
"""

from config.queries import (
    CARE_TYPE_KEYWORDS, ELDERLY_KEYWORDS, DEMENTIA_KEYWORDS,
    SMALL_KEYWORDS, EMERGING_KEYWORDS,
)

# Domeinen en termen die vacature-sites of irrelevante resultaten aanduiden
VACATURE_DOMAINS = {
    "indeed.com", "linkedin.com", "jobbird.nl", "werk.nl", "nationale-vacaturebank.nl",
    "monsterboard.nl", "vacaturebank.nl", "intermediair.nl", "uitzendbureau",
    "werkzoekenden.nl", "carerix.com", "recruitnow.nl", "solliciteer",
    "mijncarriere.nl", "youngcapital.nl", "temper.nl", "werkenbij",
}

VACATURE_KEYWORDS = [
    "vacature", "vacatures", "werken bij", "solliciteren", "solliciteer",
    "baan", "medewerker gezocht", "stageplaats", "stageplek",
    "werving", "selectie", "recruiter", "jobboard", "werkenbij",
    "part-time functie", "fulltime functie", "uren per week",
    "functie-eisen", "wij zoeken", "ben jij", "jij bent",
]


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


def is_relevant(name: str, description: str = "", url: str = "") -> bool:
    """Returns True if the result is a genuine care institution (not a vacancy or irrelevant site)."""
    # Reject vacature domains
    if url:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(v in domain for v in VACATURE_DOMAINS):
            return False

    text = _text(name, description)

    # Reject if dominated by vacancy language
    vac_hits = sum(1 for kw in VACATURE_KEYWORDS if kw in text)
    if vac_hits >= 2:
        return False

    # Must mention elderly/dementia care
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
