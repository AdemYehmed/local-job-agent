import re
from jobspy import scrape_jobs

JOBSPY_LOCATION_MAP = {
    "tunisie": "Tunisia",
    "france": "France",
    "maroc": "Morocco",
    "algerie": "Algeria",
    "belgique": "Belgium",
    "monde": "Worldwide",
}

TIMELIMIT_TO_HOURS = {
    "jour": 24,
    "semaine": 168,
    "mois": 720,
    "annee": 8760,
    "tout": None,
}

EXPERIENCE_LEVEL_MAP = {
    "junior": "entry level",
    "intermediaire": "associate",
    "senior": "director",
    "tout": None,
}

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def search_via_jobspy(
    keywords: str,
    site: str,
    region_label: str = "monde",
    timelimit_label: str = "tout",
    experience_label: str = "tout",
    results_wanted: int = 8,
) -> list[dict]:
    location = JOBSPY_LOCATION_MAP.get(region_label.lower(), region_label)
    hours_old = TIMELIMIT_TO_HOURS.get(timelimit_label.lower())

    kwargs = {
        "site_name": [site],
        "search_term": keywords,
        "location": location,
        "results_wanted": results_wanted,
    }
    if hours_old:
        kwargs["hours_old"] = hours_old
    if site == "indeed":
        kwargs["country_indeed"] = location

    experience_value = EXPERIENCE_LEVEL_MAP.get(experience_label.lower())
    if experience_value and site == "linkedin":
        kwargs["linkedin_experience_level"] = experience_value

    try:
        jobs_df = scrape_jobs(**kwargs)
    except Exception as e:
        print(f"[DEBUG jobspy_search] kwargs={kwargs} -> erreur: {type(e).__name__}: {e}")
        return []

    if jobs_df is None or jobs_df.empty:
        return []

    def clean(value) -> str:
        s = str(value) if value is not None else ""
        return "" if s.lower() in ("nan", "none", "nat") else s

    offers = []
    for _, row in jobs_df.iterrows():
        location_str = clean(row.get("location"))

        skills = []
        raw_skills = row.get("skills")
        if raw_skills and clean(raw_skills):
            skills = [s.strip() for s in str(raw_skills).split(",") if s.strip()]
        job_type = clean(row.get("job_type"))
        if job_type:
            skills.append(job_type)

        emails = clean(row.get("emails"))
        if not emails:
            description = clean(row.get("description"))
            email_match = EMAIL_REGEX.search(description)
            emails = email_match.group(0) if email_match else ""
        elif "[" in emails:
            match = EMAIL_REGEX.search(emails)
            emails = match.group(0) if match else ""

        offers.append({
            "title": clean(row.get("title")),
            "company": clean(row.get("company")),
            "location": location_str,
            "skills_mentioned": skills,
            "contact_email": emails,
            "application_method": "email" if emails else "lien",
            "url": clean(row.get("job_url")),
            "date_hint": clean(row.get("date_posted")),
        })

    return offers
