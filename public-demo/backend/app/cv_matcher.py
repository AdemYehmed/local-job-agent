import re


# Keywords extracted from Adem's CV.
# Higher weight = stronger evidence of profile compatibility.
CV_KEYWORDS = {
    # Core embedded profile
    "embedded systems": 4,
    "embedded software": 4,
    "embedded c": 4,
    "c++": 4,
    "microcontrollers": 4,
    "stm32": 4,
    "esp32": 4,
    "raspberry pi": 3,
    "rtos": 4,
    "linux": 3,

    # Automotive
    "automotive": 4,
    "automotive embedded": 5,
    "can": 4,
    "can bus": 4,
    "can-tp": 5,
    "can tp": 5,
    "doip": 5,
    "uds": 5,
    "automotive diagnostics": 5,
    "vehicle diagnostics": 5,
    "socketcan": 5,

    # Communication / hardware
    "uart": 2,
    "spi": 2,
    "i2c": 2,
    "mqtt": 2,
    "wi-fi": 1,
    "pcb": 2,
    "pcb design": 3,

    # Software / tools
    "python": 1,
    "java": 1,
    "vhdl": 2,
    "cmake": 2,
    "gcc": 2,
    "git": 1,
    "qt": 2,
    "qt creator": 2,

    # Testing / validation
    "unit testing": 3,
    "unit tests": 3,
    "functional testing": 3,
    "software testing": 3,
    "google test": 3,
    "googletest": 3,
    "verification": 3,
    "validation": 3,

    # System engineering
    "system engineering": 3,
    "systems engineering": 3,
    "mbse": 4,
    "requirements": 3,
    "requirements engineering": 4,
    "traceability": 3,

    # AI / ML / computer vision
    "machine learning": 2,
    "artificial intelligence": 2,
    "ai": 1,
    "embedded ai": 3,
    "edge ai": 3,
    "tensorflow": 2,
    "keras": 2,
    "opencv": 2,
    "mediapipe": 2,
    "x-cube-ai": 3,
    "lstm": 2,
}


# Variants that should be treated as the same keyword.
NORMALIZATION = {
    "can tp": "can-tp",
    "can_tp": "can-tp",
    "can-tp": "can-tp",

    "google test": "google test",
    "googletest": "google test",

    "c / c++": "c++",
    "cpp": "c++",

    "stm 32": "stm32",
    "esp 32": "esp32",

    "mbse": "mbse",

    "doip": "doip",
    "uds": "uds",
}


def normalize_text(text: str) -> str:
    """
    Normalize job text so keyword matching is more reliable.
    """
    if not text:
        return ""

    text = text.lower()

    # Normalize common separators.
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def keyword_present(text: str, keyword: str) -> bool:
    """
    Check whether a keyword appears in the job text.

    Uses word boundaries for short/common keywords to avoid
    accidental matches inside unrelated words.
    """
    keyword = normalize_text(keyword)

    if not keyword:
        return False

    # Special handling for very short keywords.
    if keyword in {"c", "ai", "can", "qt", "git", "uds"}:
        pattern = rf"\b{re.escape(keyword)}\b"
        return re.search(pattern, text) is not None

    return keyword in text


def calculate_cv_match(job: dict) -> dict:
    """
    Calculate compatibility between a job and the CV.

    Returns:
        score: normalized score from 0 to 10
        raw_score: weighted keyword score
        matched_keywords: keywords found in the job
    """

    title = job.get("title", "") or ""
    description = job.get("description", "") or ""
    company = job.get("company", "") or ""

    # Title is useful because it usually identifies the actual role.
    title_text = normalize_text(title)

    # Description contains the detailed technical requirements.
    description_text = normalize_text(description)

    # We use title + description for matching.
    full_text = f"{title_text} {description_text}"

    matched = []
    raw_score = 0

    for keyword, weight in CV_KEYWORDS.items():

        # Check title and description.
        if keyword_present(full_text, keyword):

            canonical = NORMALIZATION.get(keyword, keyword)

            if canonical not in [x["keyword"] for x in matched]:
                matched.append({
                    "keyword": canonical,
                    "weight": weight,
                })

                raw_score += weight

    # Extra bonus if a strong keyword appears in the title.
    title_bonus = 0

    strong_title_keywords = {
        "embedded": 2,
        "automotive": 2,
        "c++": 2,
        "stm32": 2,
        "can": 2,
        "doip": 2,
        "uds": 2,
    }

    for keyword, bonus in strong_title_keywords.items():
        if keyword_present(title_text, keyword):
            title_bonus += bonus

    raw_score += title_bonus

    # Maximum practical score for normalization.
    # We don't want a job containing many weak keywords
    # to automatically become 10/10.
    max_score = 30

    score = min(10.0, (raw_score / max_score) * 10)

    # Round for clean Telegram output.
    score = round(score, 1)

    # Sort strongest matches first.
    matched.sort(
        key=lambda item: item["weight"],
        reverse=True
    )

    return {
        "score": score,
        "raw_score": raw_score,
        "matched_keywords": [x["keyword"] for x in matched],
    }

