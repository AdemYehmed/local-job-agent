import asyncio
import json
import os
import html
from datetime import datetime, timedelta

import httpx
import psycopg2

from app.jobspy_search import search_via_jobspy
from app.cv_matcher import calculate_cv_match


# ============================================================
# CONFIG
# ============================================================

CHECK_INTERVAL_SECONDS = 120

DATABASE_URL = os.getenv("DATABASE_URL")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CV_SCORE_THRESHOLD = 4.0


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg2.connect(DATABASE_URL)


# ============================================================
# TELEGRAM
# ============================================================

async def send_telegram_message(message: str) -> bool:
    """
    Send a message to Telegram.

    Returns:
        True  -> success
        False -> failure
    """

    if not TELEGRAM_BOT_TOKEN:
        print("Telegram error: TELEGRAM_BOT_TOKEN is missing")
        return False

    if not TELEGRAM_CHAT_ID:
        print("Telegram error: TELEGRAM_CHAT_ID is missing")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)

        if response.status_code == 200:
            print("Telegram message sent successfully.")
            return True

        print(
            f"Telegram error: HTTP {response.status_code} "
            f"{response.text}"
        )

        return False

    except Exception as e:
        print(f"Telegram exception: {e}")
        return False


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_telegram_message(keywords, new_jobs):
    """
    Build Telegram message containing only NEW relevant jobs.
    """

    lines = []

    lines.append("🚨 <b>New Job Alert</b>")
    lines.append("")
    lines.append(
        f"🔎 <b>Keywords:</b> {html.escape(str(keywords))}"
    )
    lines.append(
        f"📊 <b>New jobs:</b> {len(new_jobs)}"
    )
    lines.append("")

    for index, job in enumerate(new_jobs, start=1):

        title = html.escape(
            str(job.get("title") or "Unknown title")
        )

        company = html.escape(
            str(job.get("company") or "Unknown company")
        )

        location = html.escape(
            str(job.get("location") or "Unknown location")
        )

        source = html.escape(
            str(job.get("source") or "Unknown")
        )

        url = str(job.get("url") or "").strip()

        score = job.get("match_score")

        try:
            score_text = f"{float(score):.1f}/10"
        except Exception:
            score_text = "N/A"

        matched_keywords = job.get(
            "matched_keywords",
            []
        )

        if isinstance(matched_keywords, str):
            try:
                matched_keywords = json.loads(
                    matched_keywords
                )
            except Exception:
                matched_keywords = [matched_keywords]

        if matched_keywords:
            keywords_text = ", ".join(
                str(x) for x in matched_keywords
            )
        else:
            keywords_text = "None"

        lines.append(
            f"💼 <b>{index}. {title}</b>"
        )

        lines.append(
            f"🏢 {company}"
        )

        lines.append(
            f"📍 {location}"
        )

        lines.append(
            f"🌐 {source}"
        )

        lines.append(
            f"🎯 <b>CV Match:</b> {score_text}"
        )

        lines.append(
            f"🔑 <b>Matched:</b> "
            f"{html.escape(keywords_text)}"
        )

        if url:
            safe_url = html.escape(
                url,
                quote=True
            )

            lines.append(
                f'🔗 <a href="{safe_url}">View job</a>'
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# LOAD ALERT CONFIG
# ============================================================

def load_config():
    """
    Load alert configuration from PostgreSQL.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    keywords,
                    country,
                    sources,
                    timelimit,
                    experience,
                    interval_hours,
                    active,
                    last_run,
                    last_new_count
                FROM alert_config
                WHERE id = 1
                """
            )

            row = cur.fetchone()

            if not row:
                return {
                    "keywords": "",
                    "country": "monde",
                    "sources": ["linkedin"],
                    "timelimit": "mois",
                    "experience": "tout",
                    "interval_hours": 1,
                    "active": False,
                    "last_run": None,
                    "last_new_count": 0,
                }

            (
                keywords,
                country,
                sources,
                timelimit,
                experience,
                interval_hours,
                active,
                last_run,
                last_new_count,
            ) = row

            if isinstance(sources, str):
                try:
                    sources = json.loads(sources)
                except Exception:
                    sources = ["linkedin"]

            return {
                "keywords": keywords or "",
                "country": country or "monde",
                "sources": sources or ["linkedin"],
                "timelimit": timelimit or "mois",
                "experience": experience or "tout",
                "interval_hours": float(
                    interval_hours or 1
                ),
                "active": bool(active),
                "last_run": last_run,
                "last_new_count": int(
                    last_new_count or 0
                ),
            }

    finally:
        conn.close()


# ============================================================
# SAVE ALERT CONFIG
# ============================================================

def save_config(config):
    """
    Save alert configuration to PostgreSQL.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            sources = config.get(
                "sources",
                ["linkedin"]
            )

            cur.execute(
                """
                INSERT INTO alert_config (
                    id,
                    keywords,
                    country,
                    sources,
                    timelimit,
                    experience,
                    interval_hours,
                    active,
                    updated_at
                )
                VALUES (
                    1,
                    %s,
                    %s,
                    %s::jsonb,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
                ON CONFLICT (id)
                DO UPDATE SET
                    keywords = EXCLUDED.keywords,
                    country = EXCLUDED.country,
                    sources = EXCLUDED.sources,
                    timelimit = EXCLUDED.timelimit,
                    experience = EXCLUDED.experience,
                    interval_hours = EXCLUDED.interval_hours,
                    active = EXCLUDED.active,
                    updated_at = NOW()
                """,
                (
                    config.get("keywords", ""),
                    config.get("country", "monde"),
                    json.dumps(sources),
                    config.get("timelimit", "mois"),
                    config.get("experience", "tout"),
                    float(
                        config.get(
                            "interval_hours",
                            1
                        )
                    ),
                    bool(
                        config.get(
                            "active",
                            False
                        )
                    ),
                ),
            )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# UPDATE ALERT STATUS
# ============================================================

def update_alert_status(new_count):
    """
    Update last execution information.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE alert_config
                SET
                    last_run = NOW(),
                    last_new_count = %s,
                    updated_at = NOW()
                WHERE id = 1
                """,
                (int(new_count),),
            )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# SAVE JOBS
# ============================================================

def save_new_jobs(jobs):
    """
    Save relevant jobs into PostgreSQL.

    A job is considered NEW when its URL does not already exist.

    Existing jobs:
        last_seen_at is updated.

    New jobs:
        inserted and returned.

    Returns:
        list containing ONLY newly inserted jobs.
    """

    if not jobs:
        return []

    conn = get_db_connection()

    new_jobs = []

    try:
        with conn.cursor() as cur:

            for job in jobs:

                url = str(
                    job.get("url") or ""
                ).strip()

                if not url:
                    continue

                title = job.get(
                    "title",
                    ""
                )

                company = job.get(
                    "company",
                    ""
                )

                location = job.get(
                    "location",
                    ""
                )

                description = job.get(
                    "description",
                    ""
                )

                source = job.get(
                    "source",
                    ""
                )

                match_score = job.get(
                    "match_score"
                )

                matched_keywords = job.get(
                    "matched_keywords",
                    []
                )

                # ------------------------------------------------
                # Check if URL already exists
                # ------------------------------------------------

                cur.execute(
                    """
                    SELECT id
                    FROM jobs
                    WHERE url = %s
                    """,
                    (url,),
                )

                existing = cur.fetchone()

                if existing:

                    # Existing job:
                    # update last_seen_at and CV score.
                    cur.execute(
                        """
                        UPDATE jobs
                        SET
                            last_seen_at = NOW(),
                            match_score = %s,
                            matched_keywords = %s::jsonb
                        WHERE url = %s
                        """,
                        (
                            match_score,
                            json.dumps(
                                matched_keywords
                            ),
                            url,
                        ),
                    )

                    continue

                # ------------------------------------------------
                # New job
                # ------------------------------------------------

                cur.execute(
                    """
                    INSERT INTO jobs (
                        url,
                        title,
                        company,
                        location,
                        description,
                        source,
                        match_score,
                        matched_keywords,
                        first_seen_at,
                        last_seen_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s::jsonb,
                        NOW(),
                        NOW()
                    )
                    RETURNING id
                    """,
                    (
                        url,
                        title,
                        company,
                        location,
                        description,
                        source,
                        match_score,
                        json.dumps(
                            matched_keywords
                        ),
                    ),
                )

                inserted_id = cur.fetchone()[0]

                job["id"] = inserted_id

                new_jobs.append(job)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return new_jobs


# ============================================================
# TOTAL JOBS
# ============================================================

def get_total_jobs():
    """
    Return total number of jobs stored in DB.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                """
            )

            result = cur.fetchone()

            return int(result[0] or 0)

    finally:
        conn.close()


# ============================================================
# ONE ALERT CHECK
# ============================================================

async def _run_one_check(config):
    """
    Perform one complete alert cycle:

        1. Search jobs
        2. Deduplicate current search
        3. Calculate CV score
        4. Reject irrelevant jobs
        5. Save relevant jobs to PostgreSQL
        6. Detect genuinely new jobs
        7. Send only new jobs to Telegram
        8. Update status
    """

    keywords = str(
        config.get("keywords") or ""
    ).strip()

    country = config.get(
        "country",
        "monde"
    )

    sources = config.get(
        "sources",
        ["linkedin"]
    )

    timelimit = config.get(
        "timelimit",
        "mois"
    )

    experience = config.get(
        "experience",
        "tout"
    )

    if not keywords:
        print("Alert search skipped: no keywords.")
        return

    if not sources:
        sources = ["linkedin"]

    print("")
    print("=" * 70)
    print("STARTING JOB ALERT SEARCH")
    print("=" * 70)

    print(f"Keywords   : {keywords}")
    print(f"Country    : {country}")
    print(f"Sources    : {sources}")
    print(f"Timelimit  : {timelimit}")
    print(f"Experience : {experience}")
    print("=" * 70)

    # ========================================================
    # SEARCH
    # ========================================================

    all_offers = []

    for source in sources:

        try:

            print(
                f"Searching source: {source}"
            )

            offers = search_via_jobspy(
                keywords=keywords,
                country=country,
                sources=[source],
                timelimit=timelimit,
                experience=experience,
            )

            if not offers:
                print(
                    f"No jobs returned from {source}"
                )
                continue

            print(
                f"{len(offers)} jobs returned "
                f"from {source}"
            )

            for job in offers:

                if not isinstance(job, dict):
                    continue

                job["source"] = source

                all_offers.append(job)

        except Exception as e:

            print(
                f"Search error for {source}: {e}"
            )

    print("")
    print(
        f"Total raw jobs: {len(all_offers)}"
    )

    # ========================================================
    # DEDUPLICATE CURRENT SEARCH
    # ========================================================

    unique_jobs = []
    seen_urls = set()

    for job in all_offers:

        url = str(
            job.get("url") or ""
        ).strip()

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        unique_jobs.append(job)

    print(
        f"Unique jobs after URL deduplication: "
        f"{len(unique_jobs)}"
    )

    # ========================================================
    # CV MATCHING
    # ========================================================

    filtered_jobs = []

    print("")
    print("=" * 70)
    print("CV MATCHING")
    print("=" * 70)

    for job in unique_jobs:

        try:

            match = calculate_cv_match(job)

            score = float(
                match.get(
                    "score",
                    0
                )
            )

            matched_keywords = match.get(
                "matched_keywords",
                []
            )

            job["match_score"] = score

            job["matched_keywords"] = (
                matched_keywords
            )

            title = job.get(
                "title",
                ""
            )

            print(
                f"{title} "
                f"→ score={score:.1f}/10 "
                f"keywords={matched_keywords}"
            )

            # ------------------------------------------------
            # Threshold
            # ------------------------------------------------

            if score >= CV_SCORE_THRESHOLD:

                filtered_jobs.append(job)

                print(
                    "  ✅ ACCEPTED"
                )

            else:

                print(
                    "  ❌ REJECTED"
                )

        except Exception as e:

            print(
                f"CV matching error for "
                f"{job.get('title', '')}: {e}"
            )

    print("")
    print(
        f"Relevant jobs after CV filtering: "
        f"{len(filtered_jobs)}"
    )

    # ========================================================
    # SAVE TO DATABASE
    # ========================================================

    try:

        new_jobs = save_new_jobs(
            filtered_jobs
        )

    except Exception as e:

        print(
            f"Database save error: {e}"
        )

        return

    print("")
    print(
        f"New jobs inserted into DB: "
        f"{len(new_jobs)}"
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    if new_jobs:

        message = build_telegram_message(
            keywords,
            new_jobs
        )

        await send_telegram_message(
            message
        )

    else:

        # IMPORTANT:
        # Do NOT send Telegram message here.
        print(
            "No new jobs. "
            "No Telegram message sent."
        )

    # ========================================================
    # STATUS
    # ========================================================

    try:

        update_alert_status(
            len(new_jobs)
        )

    except Exception as e:

        print(
            f"Status update error: {e}"
        )

    # ========================================================
    # TOTAL DB JOBS
    # ========================================================

    try:

        total_jobs = get_total_jobs()

        print(
            f"Total relevant jobs in DB: "
            f"{total_jobs}"
        )

    except Exception as e:

        print(
            f"Could not get total job count: {e}"
        )

    print("=" * 70)
    print("JOB ALERT SEARCH FINISHED")
    print("=" * 70)
    print("")


# ============================================================
# BACKGROUND ALERT LOOP
# ============================================================

async def alert_loop():
    """
    Permanent background loop.

    It wakes every 120 seconds and checks PostgreSQL
    to determine whether another search is due.

    Example:

        interval_hours = 1
        -> approximately every 1 hour

        interval_hours = 0.5
        -> approximately every 30 minutes

        interval_hours = 2
        -> approximately every 2 hours
    """

    print(
        "Job alert loop started."
    )

    while True:

        try:

            config = load_config()

            # ==================================================
            # ALERT DISABLED
            # ==================================================

            if not config.get("active"):

                print(
                    "Alert system is inactive."
                )

                await asyncio.sleep(
                    CHECK_INTERVAL_SECONDS
                )

                continue

            # ==================================================
            # INTERVAL
            # ==================================================

            interval_hours = float(
                config.get(
                    "interval_hours",
                    1
                )
            )

            if interval_hours <= 0:

                interval_hours = 1

            # ==================================================
            # LAST RUN
            # ==================================================

            last_run = config.get(
                "last_run"
            )

            now = datetime.now()

            should_run = False

            # First run
            if last_run is None:

                should_run = True

            else:

                if isinstance(
                    last_run,
                    str
                ):

                    last_run = (
                        datetime.fromisoformat(
                            last_run
                        )
                    )

                # Handle timezone-aware DB timestamps
                if (
                    last_run.tzinfo
                    is not None
                ):

                    now = datetime.now(
                        last_run.tzinfo
                    )

                elapsed_hours = (
                    now - last_run
                ).total_seconds() / 3600

                if (
                    elapsed_hours
                    >= interval_hours
                ):

                    should_run = True

            # ==================================================
            # RUN SEARCH
            # ==================================================

            if should_run:

                print(
                    f"Running alert search "
                    f"(interval={interval_hours}h)"
                )

                await _run_one_check(
                    config
                )

            else:

                print(
                    "Alert search not due yet."
                )

        except Exception as e:

            print(
                f"Alert loop error: {e}"
            )

        # ======================================================
        # WAIT
        # ======================================================

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )