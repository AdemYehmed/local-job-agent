import re
import unicodedata


# ============================================================
# CV MATCHER
# ============================================================

# Strongest areas for your profile
KEYWORDS = {

    # --------------------------------------------------------
    # EMBEDDED / ELECTRONICS
    # --------------------------------------------------------

    "embedded": 3.0,
    "embedded systems": 3.5,
    "embedded software": 3.5,
    "embedded linux": 4.0,
    "embedded engineer": 3.5,
    "embedded developer": 3.5,
    "embedded software engineer": 4.0,

    "firmware": 3.0,
    "firmware engineer": 3.5,

    "electronics": 2.5,
    "electronic": 2.5,
    "electronic engineering": 3.0,
    "electronics engineer": 3.0,

    "electronique": 2.5,
    "électronique": 2.5,

    "embarque": 3.0,
    "embarqué": 3.0,
    "embarquee": 3.0,
    "embarquée": 3.0,

    # Common typo / variation
    "embadded": 2.5,

    # --------------------------------------------------------
    # PROGRAMMING
    # --------------------------------------------------------

    "c++": 3.0,
    "cpp": 3.0,
    "c": 2.5,
    "python": 1.5,
    "java": 1.0,
    "vhdl": 1.5,

    # --------------------------------------------------------
    # MICROCONTROLLERS
    # --------------------------------------------------------

    "stm32": 3.0,
    "esp32": 2.5,
    "microcontroller": 3.0,
    "microcontrollers": 3.0,
    "mcu": 2.5,

    # --------------------------------------------------------
    # LINUX / SYSTEMS
    # --------------------------------------------------------

    "linux": 2.5,
    "embedded linux": 4.0,
    "linux embedded": 4.0,

    "rtos": 2.5,
    "real time operating system": 2.5,
    "real-time operating system": 2.5,

    # --------------------------------------------------------
    # AUTOMOTIVE
    # --------------------------------------------------------

    "automotive": 2.5,
    "automobile": 2.5,
    "automotive software": 3.0,

    "can": 2.5,
    "can bus": 3.0,
    "can-bus": 3.0,
    "can tp": 3.5,
    "can-tp": 3.5,

    "doip": 3.5,
    "doip protocol": 3.5,
    "uds": 3.0,
    "diagnostics": 2.5,
    "automotive diagnostics": 3.5,
    "socketcan": 3.0,

    # --------------------------------------------------------
    # COMMUNICATION
    # --------------------------------------------------------

    "uart": 1.5,
    "spi": 1.5,
    "i2c": 1.5,
    "mqtt": 1.5,
    "wifi": 1.0,
    "wi-fi": 1.0,

    # --------------------------------------------------------
    # SOFTWARE TOOLS
    # --------------------------------------------------------

    "git": 1.0,
    "cmake": 1.5,
    "gcc": 1.5,
    "qt": 1.0,
    "google test": 2.0,
    "unit testing": 2.0,
    "unit test": 2.0,
    "software testing": 2.0,
    "software validation": 2.0,
    "verification": 1.5,
    "validation": 1.5,

    # --------------------------------------------------------
    # SYSTEM ENGINEERING
    # --------------------------------------------------------

    "systems engineering": 2.0,
    "system engineering": 2.0,
    "mbse": 2.5,
    "requirements": 1.5,
    "requirements engineering": 2.5,
    "requirements management": 2.0,
    "traceability": 1.5,

    # --------------------------------------------------------
    # AI / ML
    # --------------------------------------------------------

    "artificial intelligence": 1.5,
    "ai": 1.0,
    "machine learning": 2.0,
    "deep learning": 1.5,
    "embedded ai": 3.0,
    "edge ai": 3.0,
    "edge computing": 2.0,

    "tensorflow": 1.5,
    "keras": 1.0,
    "opencv": 1.0,
    "mediaPipe": 1.0,
    "x-cube-ai": 2.0,
    "lstm": 1.0,

    # --------------------------------------------------------
    # HARDWARE
    # --------------------------------------------------------

    "pcb": 1.5,
    "pcb design": 2.0,
    "altium": 1.5,
    "hardware": 1.0,

    # --------------------------------------------------------
    # ROBOTICS
    # --------------------------------------------------------

    "robotics": 2.0,
    "robot": 1.5,
    "robotic": 1.5,
    "autonomous systems": 2.0,
    "autonomous": 1.0,
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize text so that:
      Électronique -> electronique
      Électronique -> electronique
      EMBEDDED -> embedded
      C++ remains c++
    """

    if not text:
        return ""

    text = str(text).lower()

    # Remove accents
    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    # Normalize separators
    text = text.replace(
        "-",
        "-"
    )

    text = text.replace(
        "–",
        "-"
    )

    text = text.replace(
        "—",
        "-"
    )

    # Keep letters, numbers, +, # and -
    text = re.sub(
        r"[^\w\s+#.-]",
        " ",
        text
    )

    # Collapse whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ALIASES
# ============================================================

ALIASES = {

    # Embedded
    "embedded": [
        "embedded",
        "embadded",
        "embarque",
        "embarquee",
    ],

    "embedded systems": [
        "embedded systems",
        "systemes embarques",
        "systemes embarque",
        "systèmes embarqués",
    ],

    "embedded software": [
        "embedded software",
        "logiciel embarque",
        "logiciels embarques",
    ],

    "embedded linux": [
        "embedded linux",
        "linux embedded",
        "linux embarque",
    ],

    # Electronics
    "electronics": [
        "electronics",
        "electronic",
        "electronique",
        "electronic engineering",
        "electronics engineering",
        "ingenieur electronique",
    ],

    # Automotive
    "automotive": [
        "automotive",
        "automobile",
        "automotive software",
    ],

    # CAN
    "can": [
        "can bus",
        "can-bus",
        "can",
    ],

    # CAN-TP
    "can-tp": [
        "can tp",
        "can-tp",
        "cantp",
    ],

    # DoIP
    "doip": [
        "doip",
        "doip protocol",
        "diagnostic over ip",
    ],

    # UDS
    "uds": [
        "uds",
        "unified diagnostic services",
    ],

    # Testing
    "unit testing": [
        "unit testing",
        "unit test",
        "software testing",
    ],

    # Systems engineering
    "systems engineering": [
        "systems engineering",
        "system engineering",
        "ingenierie systeme",
        "ingenierie des systemes",
    ],
}


# ============================================================
# TEXT MATCH
# ============================================================

def keyword_present(text, keyword):
    """
    Check whether keyword exists in normalized text.
    """

    keyword = normalize_text(keyword)

    if not keyword:
        return False

    # Special case C++
    if keyword == "c++":
        return bool(
            re.search(
                r"\bc\+\+\b",
                text
            )
        )

    # Special case C
    if keyword == "c":
        return bool(
            re.search(
                r"(?<![a-z])c(?![a-z])",
                text
            )
        )

    # Normal word / phrase matching
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(keyword)
        + r"(?![a-z0-9])"
    )

    return bool(
        re.search(
            pattern,
            text
        )
    )


# ============================================================
# CHECK ALIAS
# ============================================================

def alias_present(text, canonical_keyword):

    aliases = ALIASES.get(
        canonical_keyword,
        [canonical_keyword]
    )

    for alias in aliases:

        alias_normalized = normalize_text(
            alias
        )

        if keyword_present(
            text,
            alias_normalized
        ):
            return True

    return False


# ============================================================
# CV MATCH
# ============================================================

def calculate_cv_match(job):

    title = str(
        job.get("title") or ""
    )

    description = str(
        job.get("description") or ""
    )

    # IMPORTANT:
    # Search BOTH title and complete description.
    full_text = normalize_text(
        title + " " + description
    )

    normalized_title = normalize_text(
        title
    )

    matched_keywords = []

    raw_score = 0.0

    # ========================================================
    # KEYWORD MATCHING
    # ========================================================

    for keyword, weight in KEYWORDS.items():

        canonical = normalize_text(
            keyword
        )

        # Check aliases first
        if canonical in ALIASES:

            found = alias_present(
                full_text,
                canonical
            )

        else:

            found = keyword_present(
                full_text,
                canonical
            )

        if not found:
            continue

        # ----------------------------------------------------
        # Avoid duplicate semantic matches
        # ----------------------------------------------------

        matched_keywords.append(
            keyword
        )

        raw_score += weight

        # ----------------------------------------------------
        # TITLE BONUS
        # ----------------------------------------------------

        if (
            canonical in normalized_title
            or alias_present(
                normalized_title,
                canonical
            )
        ):

            raw_score += weight * 0.75

    # ========================================================
    # STRONG EMBEDDED TITLE BONUS
    # ========================================================

    strong_embedded_title = False

    embedded_title_terms = [
        "embedded",
        "embadded",
        "embarque",
        "embarquee",
        "firmware",
        "electronics",
        "electronique",
    ]

    for term in embedded_title_terms:

        if keyword_present(
            normalized_title,
            term
        ):

            strong_embedded_title = True
            break

    if strong_embedded_title:

        raw_score += 3.0

    # ========================================================
    # STRONG PROGRAMMING BONUS
    # ========================================================

    programming_terms = [
        "c++",
        "cpp",
        "c ",
        "python",
        "vhdl",
    ]

    programming_found = False

    for term in programming_terms:

        if keyword_present(
            normalized_title + " " + full_text,
            term
        ):

            programming_found = True
            break

    if programming_found:

        raw_score += 1.5

    # ========================================================
    # EMBEDDED + LINUX COMBINATION
    # ========================================================

    has_embedded = (
        alias_present(
            full_text,
            "embedded"
        )
        or alias_present(
            full_text,
            "embedded systems"
        )
        or alias_present(
            full_text,
            "embedded software"
        )
    )

    has_linux = keyword_present(
        full_text,
        "linux"
    )

    if has_embedded and has_linux:

        raw_score += 3.0

    # ========================================================
    # EMBEDDED + C/C++
    # ========================================================

    has_cpp = keyword_present(
        full_text,
        "c++"
    )

    has_c = keyword_present(
        full_text,
        "c"
    )

    if has_embedded and (
        has_cpp or has_c
    ):

        raw_score += 2.0

    # ========================================================
    # EMBEDDED + ELECTRONICS
    # ========================================================

    has_electronics = (
        alias_present(
            full_text,
            "electronics"
        )
    )

    if has_embedded and has_electronics:

        raw_score += 2.0

    # ========================================================
    # NORMALIZE SCORE TO 0-10
    # ========================================================

    # We don't want scores to become enormous.
    #
    # 10 = very strong CV match
    #
    score = min(
        10.0,
        raw_score / 3.0
    )

    score = round(
        score,
        1
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    matched_keywords = list(
        dict.fromkeys(
            matched_keywords
        )
    )

    return {
        "score": score,
        "matched_keywords": matched_keywords,
    }