"""
Search query templates for discovering small and emerging care institutions.
"""

# Base search queries (will be combined with region names)
BASE_QUERIES_NL = [
    "kleinschalig wonen dementie {region}",
    "kleine zorginstelling ouderenzorg {region}",
    "nieuw verpleeghuis {region}",
    "woonzorgcentrum dementie {region}",
    "kleinschalig verpleeghuis {region}",
    "24 uurs zorg ouderen {region}",
    "particuliere zorginstelling ouderenzorg {region}",
    "hospice ouderenzorg {region}",
    "kleinschalig groepswonen dementie {region}",
    "woonzorglocatie dementie 24 uur {region}",
]

BASE_QUERIES_BE = [
    "kleinschalig woonzorgcentrum {region}",
    "nieuwe erkende zorginstelling ouderen {region}",
    "dementie zorgverlening {region}",
    "woonzorgcentrum dementie {region}",
    "kleinschalig ouderenzorg {region}",
    "maison de repos dépendance Alzheimer {region}",
    "nouveau établissement soins personnes âgées {region}",
    "petite structure soins déments {region}",
]

# Direct queries without region (national scope)
NATIONAL_QUERIES_NL = [
    "opkomende kleinschalige zorginstellingen Nederland 2024",
    "nieuwe kleinschalige woonvormen dementie Nederland",
    "innovatieve zorglocaties ouderenzorg Nederland",
    "startende zorginstelling ouderen 2023 2024 Nederland",
    "kleinschalig wonen dementie erkende instelling",
    "site:zorgkaart.nl verpleeghuis dementie kleinschalig",
    "site:zorgkaart.nl woonzorgcentrum dementie klein",
]

NATIONAL_QUERIES_BE = [
    "nieuwe erkende woonzorgcentra Vlaanderen",
    "kleinschalig woonzorgcentrum dementie Belgie erkend",
    "maison de repos et de soins Alzheimer Belgique nouveau",
    "site:zorg-en-gezondheid.be woonzorgcentrum dementie",
    "opkomende zorginstellingen ouderen Belgie",
]

# Care type keywords (for classification and filtering)
# Alleen 24/7 woonzorgtypen — thuiszorg en dagopvang zijn uitgesloten
CARE_TYPE_KEYWORDS = {
    "verpleeghuis":       ["verpleeghuis", "nursing home", "verpleegafdeling"],
    "woonzorgcentrum":    ["woonzorgcentrum", "wzc", "woon-zorgcentrum"],
    "kleinschalig_wonen": ["kleinschalig wonen", "kleinschalige woonvorm", "groepswonen", "woongroep"],
    "hospice":            ["hospice", "palliatieve zorg"],
    "alzheimer_centrum":  ["alzheimer centrum", "geheugenkliniek"],
}

# Typen die NIET 24/7 zijn en gefilterd worden
EXCLUDED_CARE_TYPES = {"thuiszorg", "dagopvang", "dagverzorging"}

# Keywords that signal focus on elderly / dementia
ELDERLY_KEYWORDS = [
    "ouderenzorg", "ouderen", "elderly", "senioren", "seniorenzorg",
    "bejaarden", "bejaardenzorg", "65+", "verzorgingshuis",
]

DEMENTIA_KEYWORDS = [
    "dementie", "dementia", "alzheimer", "geheugenprobleem",
    "geheugenzorg", "cognitieve achteruitgang", "dementerende",
    "psychogeriatrie", "psychogeriatrisch",
]

# Keywords that signal a SMALL or EMERGING institution
SMALL_KEYWORDS = [
    "kleinschalig", "klein", "kleinere", "kleine",
    "intiem", "huiselijk", "woongroep", "kleinschalige woonvorm",
    "boutique", "particulier", "zelfstandig",
]

EMERGING_KEYWORDS = [
    "nieuw", "nieuwe", "opening", "geopend", "gestart", "opgestart",
    "2022", "2023", "2024", "2025", "innovatief", "innovatieve",
    "modern", "vernieuwd", "uitgebreid", "opgericht",
]
