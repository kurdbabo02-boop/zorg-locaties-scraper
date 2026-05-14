"""
Geographic regions for the Netherlands and Belgium.
"""

NL_PROVINCES = [
    "Noord-Holland", "Zuid-Holland", "Utrecht", "Noord-Brabant",
    "Gelderland", "Overijssel", "Friesland", "Groningen",
    "Drenthe", "Flevoland", "Zeeland", "Limburg",
]

NL_CITIES = [
    "Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Eindhoven",
    "Tilburg", "Groningen", "Almere", "Breda", "Nijmegen",
    "Enschede", "Arnhem", "Haarlem", "Haarlemmermeer", "Zaanstad",
    "Amersfoort", "Apeldoorn", "Zwolle", "Zoetermeer", "Leiden",
    "Maastricht", "Dordrecht", "Ede", "Westland", "Emmen",
    "Delft", "Venlo", "Alkmaar", "Leeuwarden", "Helmond",
    "Deventer", "Sittard-Geleen", "Amstelveen", "Hilversum",
]

BE_PROVINCES = [
    "Antwerpen", "Oost-Vlaanderen", "West-Vlaanderen",
    "Vlaams-Brabant", "Limburg",            # Flanders
    "Luik", "Henegouwen", "Namen", "Waals-Brabant", "Luxemburg",  # Wallonia
    "Brussel",                               # BHG
]

BE_CITIES = [
    "Antwerpen", "Gent", "Brussel", "Brugge", "Leuven",
    "Hasselt", "Luik", "Namen", "Mons", "Charleroi",
    "Kortrijk", "Mechelen", "Aalst", "La Louvière", "Genk",
    "Roeselare", "Mouscron", "Sint-Niklaas", "Tournai", "Beveren",
    "Dendermonde", "Beringen", "Oostende", "Turnhout", "Ieper",
]

ALL_NL_LOCATIONS = NL_PROVINCES + NL_CITIES
ALL_BE_LOCATIONS = BE_PROVINCES + BE_CITIES
