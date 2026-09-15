import re

# Mots-clés indiquant une page de LISTING générique, pas une offre individuelle
LISTING_PATTERNS = [
    r"\d[\d,\.]*\+?\s*(jobs|emplois|offres)",
    r"top\s+\d",
    r"jobs?\s+in\s+",
    r"emplois?\s+en\s+",
]

# Mots-clés associés à chaque région pour valider la cohérence géographique
REGION_KEYWORDS = {
    "tunisie": ["tunisie", "tunisia", "tunis", "sfax", "sousse", "bizerte", "ariana", "ben arous", "nabeul"],
    "france": ["france", "paris", "lyon", "marseille", "toulouse", "bordeaux", "lille", "nantes"],
    "maroc": ["maroc", "morocco", "rabat", "casablanca", "marrakech", "tanger"],
    "algerie": ["algerie", "algérie", "algeria", "alger", "oran"],
    "belgique": ["belgique", "belgium", "bruxelles", "brussels", "anvers", "antwerp", "liege", "liège", "gand", "gent"],
    "monde": [],  # pas de filtre si région = monde
}


def is_listing_page(title: str) -> bool:
    """Détecte si un titre ressemble à une page de listing générique plutôt qu'à une offre précise."""
    if not title:
        return False
    title_lower = title.lower()
    return any(re.search(pattern, title_lower) for pattern in LISTING_PATTERNS)


def matches_region(title: str, location: str, region_label: str) -> bool:
    """Vérifie que le titre ou la localisation mentionne bien la région demandée.
    Si aucune localisation n'est identifiée du tout, on laisse passer (plutôt que rejeter à tort)."""
    keywords = REGION_KEYWORDS.get(region_label.lower(), [])
    if not keywords:
        return True  # région "monde" ou inconnue : pas de filtre
    combined = f"{title} {location}".lower()
    if not location.strip():
        return True  # pas de localisation identifiée : on ne peut pas juger, on garde
    return any(kw in combined for kw in keywords)


def clean_date_hint(date_hint: str, max_len: int = 40) -> str:
    """Coupe les date_hint qui contiennent en fait une description entière au lieu d'une date."""
    if not date_hint:
        return ""
    cleaned = date_hint.strip()
    if len(cleaned) > max_len:
        return ""  # trop long pour être une vraie date, probablement une description mal placée
    return cleaned
