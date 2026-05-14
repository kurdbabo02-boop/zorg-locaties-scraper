"""
Contact-verrijking: bezoekt de website van elke gevonden zorginstelling
en haalt het telefoonnummer en e-mailadres op.
"""

import re
import logging
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from models import CareLocation
from utils.http import get_session, polite_get

logger = logging.getLogger(__name__)

# ── Reguliere expressies ──────────────────────────────────────────────────────

# E-mail — NL/BE TLD's en generieke
EMAIL_RE = re.compile(
    r'\b[\w.+\-]+@[\w\-]+\.(?:nl|be|com|org|net|eu|info|care)\b',
    re.IGNORECASE,
)

# Telefoonnummers — NL (06/0xx) en BE (+31/+32/0032)
PHONE_RE = re.compile(
    r'(?:'
    r'\+31[\s.\-]?(?:\(0\))?[\s.\-]?\d{1,3}[\s.\-]?\d{6,8}'   # +31
    r'|0031[\s.\-]?\d{1,3}[\s.\-]?\d{6,8}'                      # 0031
    r'|\+32[\s.\-]?\d{1,2}[\s.\-]?\d{6,8}'                      # +32
    r'|0032[\s.\-]?\d{1,2}[\s.\-]?\d{6,8}'                      # 0032
    r'|0[1-9]\d[\s.\-]?\d{7}'                                    # NL vast: 0xx xxxxxxx
    r'|06[\s.\-]?\d{8}'                                          # NL mobiel
    r'|0[1-9][\s.\-]?\d{3}[\s.\-]?\d{4}'                       # NL kort
    r')',
    re.IGNORECASE,
)

# Domeinen/adressen die GEEN contact-emails zijn
NOREPLY_PATTERNS = [
    "noreply", "no-reply", "donotreply", "mailer", "bounce",
    "postmaster", "webmaster@", "info@example",
]

# Subpaden die een contactpagina kunnen zijn
CONTACT_PATHS = [
    "/contact", "/contactgegevens", "/contact-us", "/contacteer-ons",
    "/over-ons", "/about", "/reach-us", "/bereikbaarheid",
]


def _clean_phone(raw: str) -> str:
    """Normaliseer telefoonnummer naar leesbaar formaat."""
    digits = re.sub(r'[^\d+]', '', raw)
    return digits[:15]


def _is_valid_email(email: str) -> bool:
    return not any(p in email.lower() for p in NOREPLY_PATTERNS)


def _extract_from_html(html: str, base_url: str = "") -> dict:
    """Trek e-mail en telefoon uit HTML-tekst."""
    soup = BeautifulSoup(html, "html.parser")

    # Verwijder script/style bloat
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    emails = [e for e in EMAIL_RE.findall(text) if _is_valid_email(e)]
    phones = [_clean_phone(p) for p in PHONE_RE.findall(text)]

    # Prefereer mailto: links (meer betrouwbaar dan tekst)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            if email and _is_valid_email(email) and email not in emails:
                emails.insert(0, email)
        elif href.startswith("tel:"):
            phone = re.sub(r'[^\d+]', '', href[4:])
            if phone and phone not in phones:
                phones.insert(0, phone)

    return {
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
    }


def enrich_one(loc: CareLocation, session=None) -> CareLocation:
    """Bezoek de website van één locatie en vul ontbrekende contactgegevens in."""
    if session is None:
        session = get_session()

    url = loc.website or loc.source_url
    if not url or not url.startswith("http"):
        return loc

    already_complete = bool(loc.email) and bool(loc.phone)
    if already_complete:
        return loc

    tried_urls = set()

    def try_url(u: str):
        if u in tried_urls:
            return
        tried_urls.add(u)
        try:
            resp = polite_get(session, u, timeout=12)
            return _extract_from_html(resp.text, u)
        except Exception:
            return None

    # 1. Hoofdpagina
    data = try_url(url)
    if data:
        if not loc.email and data["email"]:
            loc.email = data["email"]
        if not loc.phone and data["phone"]:
            loc.phone = data["phone"]

    # 2. Als nog steeds incompleet → probeer /contact subpagina
    if not loc.email or not loc.phone:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        for path in CONTACT_PATHS:
            if loc.email and loc.phone:
                break
            data2 = try_url(base + path)
            if data2:
                if not loc.email and data2["email"]:
                    loc.email = data2["email"]
                if not loc.phone and data2["phone"]:
                    loc.phone = data2["phone"]

    return loc


def enrich_all(locations: List[CareLocation],
               progress_callback=None) -> List[CareLocation]:
    """
    Verrijk alle locaties met contactgegevens.
    progress_callback(i, total, name) wordt aangeroepen per locatie.
    """
    session = get_session()
    enriched = []
    total = len(locations)

    for i, loc in enumerate(locations):
        if progress_callback:
            progress_callback(i, total, loc.name)
        try:
            loc = enrich_one(loc, session)
        except Exception as e:
            logger.debug("Verrijking mislukt voor %s: %s", loc.name, e)
        enriched.append(loc)

    return enriched
