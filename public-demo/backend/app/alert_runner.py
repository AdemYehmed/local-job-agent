import asyncio
import json
import os
import html
from datetime import datetime, timedelta

import httpx
import psycopg2

from app.jobspy_search import search_via_jobspy


# ============================================================
# CONFIGURATION
# ============================================================

CHECK_INTERVAL_SECONDS = 120  # Check every 2 minutes

DATABASE_URL = os.getenv("DATABASE_URL")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    """
    Create a PostgreSQL connection.
    DATABASE_URL should come from Render environment variables.
    """

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg2.connect(DATABASE_URL)


# ============================================================
# ALERT CONFIGURATION
# ============================================================

def load_config() -> dict | None:
    """
    Load the current alert configuration from PostgreSQL.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute(
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

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "keywords": row[0],
                "region": row[1],
                "sources": row[2],
                "timelimit": row[3],
                "experience": row[4],
                "interval_hours": float(row[5]),
                "active": row[6],
                "last_run": row[7].isoformat() if row[7] else None,
                "last_new_count": row[8] or 0,
            }

    finally:
        conn.close()


def save_config(config: dict) -> None:
    """
    Save/update the alert configuration in PostgreSQL.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                UPDATE alert_config
                SET
                    keywords = %s,
                    country = %s,
                    sources = %s::jsonb,
                    timelimit = %s,
                    experience = %s,
                    interval_hours = %s,
                    active = %s,
                    updated_at = NOW()
                WHERE id = 1
                """,
                (
                    config.get("keywords", ""),
                    config.get("region", "monde"),
                    json.dumps(
                        config.get(
                            "sources",
                            ["linkedin"]
                        )
                    ),
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
                )
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_alert_status(new_count: int) -> None:
    """
    Update the last execution information.
    """

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                UPDATE alert_config
                SET
                    last_run = NOW(),
                    last_new_count = %s,
                    updated_at = NOW()
                WHERE id = 1
                """,
                (new_count,)
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# JOB DATABASE
# ============================================================

def save_new_jobs(jobs: list[dict]) -> list[dict]:
    """
    Save jobs into PostgreSQL.

    Returns ONLY jobs that did not exist previously.

    The URL is used as the unique identifier.
    """

    new_jobs = []

    conn = get_db_connection()

    try:

        with conn.cursor() as cursor:

            for job in jobs:

                url = (job.get("url") or "").strip()

                if not url:
                    continue

                # ------------------------------------------------
                # Check if job already exists
                # ------------------------------------------------

                cursor.execute(
                    """
                    SELECT id
                    FROM jobs
                    WHERE url = %s
                    """,
                    (url,)
                )

                existing = cursor.fetchone()

                # ------------------------------------------------
                # OLD JOB
                # ------------------------------------------------

                if existing:

                    cursor.execute(
                        """
                        UPDATE jobs
                        SET
                            last_seen_at = NOW(),
                            title = COALESCE(%s, title),
                            company = COALESCE(%s, company),
                            location = COALESCE(%s, location),
                            description = COALESCE(%s, description)
                        WHERE url = %s
                        """,
                        (
                            job.get("title"),
                            job.get("company"),
                            job.get("location"),
                            job.get("description"),
                            url,
                        )
                    )

                # ------------------------------------------------
                # NEW JOB
                # ------------------------------------------------

                else:

                    cursor.execute(
                        """
                        INSERT INTO jobs (
                            url,
                            title,
                            company,
                            location,
                            description,
                            source,
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
                            NOW(),
                            NOW()
                        )
                        """,
                        (
                            url,
                            job.get("title", ""),
                            job.get("company", ""),
                            job.get("location", ""),
                            job.get("description", ""),
                            job.get("source", ""),
                        )
                    )

                    new_jobs.append(job)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return new_jobs


def get_total_jobs() -> int:
    """
    Return total number of jobs stored in PostgreSQL.
    """

    conn = get_db_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                """
            )

            result = cursor.fetchone()

            return result[0] if result else 0

    finally:
        conn.close()


# ============================================================
# TELEGRAM
# ============================================================

async def send_telegram_message(message: str) -> None:
    """
    Send a message through Telegram Bot API.
    """

    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not configured")
        return

    if not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID is not configured")
        return

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.post(
            telegram_url,
            json=payload
        )

        response.raise_for_status()


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_telegram_message(
    keywords: str,
    new_jobs: list[dict]
) -> str:
    """
    Build Telegram message containing only new jobs.
    """

    lines = [
        f"🔔 <b>{len(new_jobs)} nouvelle(s) offre(s)</b>",
        f"🔎 Recherche : <b>{html.escape(keywords)}</b>",
        ""
    ]

    for index, job in enumerate(new_jobs, start=1):

        title = html.escape(
            job.get("title", "Sans titre") or "Sans titre"
        )

        company = html.escape(
            job.get("company", "Entreprise inconnue")
            or "Entreprise inconnue"
        )

        location = html.escape(
            job.get("location", "Non précisé")
            or "Non précisé"
        )

        source = html.escape(
            job.get("source", "")
            or ""
        )

        url = job.get("url", "")

        lines.append(
            f"<b>{index}. 💼 {title}</b>\n"
            f"🏢 {company}\n"
            f"📍 {location}\n"
            f"🌐 {source}\n"
            f"🔗 {url}\n"
        )

    return "\n".join(lines)


# ============================================================
# RUN ONE SEARCH
# ============================================================

async def _run_one_check(config: dict) -> None:
    """
    Perform one complete job search.

    1. Search LinkedIn / Indeed
    2. Deduplicate jobs found during this run
    3. Compare jobs with PostgreSQL
    4. Save new jobs
    5. Send only new jobs to Telegram
    6. Save execution status
    """

    print("========================================")
    print("Starting job alert check")
    print("========================================")

    print(
        f"Keywords: {config.get('keywords')}"
    )

    print(
        f"Country: {config.get('region')}"
    )

    print(
        f"Sources: {config.get('sources')}"
    )

    all_offers = []

    # Prevent duplicates during the SAME search
    seen_this_run_keys = set()

    # ========================================================
    # SEARCH
    # ========================================================

    for source in config.get(
        "sources",
        ["linkedin"]
    ):

        if source not in (
            "linkedin",
            "indeed"
        ):
            continue

        keywords = [
            k.strip()
            for k in config.get(
                "keywords",
                ""
            ).split("+")
            if k.strip()
        ]

        for keyword in keywords:

            print(
                f"Searching {source}: {keyword}"
            )

            try:

                offers = search_via_jobspy(
                    keywords=keyword,
                    site=source,
                    region_label=config.get(
                        "region",
                        "monde"
                    ),
                    timelimit_label=config.get(
                        "timelimit",
                        "mois"
                    ),
                    experience_label=config.get(
                        "experience",
                        "tout"
                    ),
                    results_wanted=8,
                )

            except Exception as e:

                print(
                    f"Search error "
                    f"({source}, {keyword}): {e}"
                )

                continue

            if not offers:
                continue

            for job in offers:

                url = (
                    job.get("url") or ""
                ).strip()

                title = (
                    job.get("title") or ""
                ).strip().lower()

                company = (
                    job.get("company") or ""
                ).strip().lower()

                # ------------------------------------------------
                # Skip jobs without URL
                # ------------------------------------------------

                if not url:
                    continue

                # ------------------------------------------------
                # Deduplication during current run
                # ------------------------------------------------

                dedup_key = (
                    url
                    or f"{title}|{company}"
                )

                if dedup_key in seen_this_run_keys:
                    continue

                seen_this_run_keys.add(
                    dedup_key
                )

                job["source"] = source

                all_offers.append(job)

    print(
        f"Jobs found this run: "
        f"{len(all_offers)}"
    )

    # ========================================================
    # DATABASE
    # ========================================================

    if not all_offers:

        update_alert_status(0)

        print("No jobs found.")

        return

    try:

        new_jobs = save_new_jobs(
            all_offers
        )

    except Exception as e:

        print(
            f"Database error: {e}"
        )

        # Do NOT update last_run here.
        # This allows the system to retry
        # the search later.
        return

    print(
        f"New jobs: {len(new_jobs)}"
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    if new_jobs:

        message = build_telegram_message(
            config.get(
                "keywords",
                ""
            ),
            new_jobs
        )

        try:

            await send_telegram_message(
                message
            )

            print(
                "Telegram notification sent."
            )

        except Exception as e:

            print(
                f"Telegram error: {e}"
            )

    else:
        await send_telegram_message("no job now")

        print(
            "No new jobs. "
            "No Telegram message sent."
        )

    # ========================================================
    # STATUS
    # ========================================================

    update_alert_status(
        len(new_jobs)
    )

    print(
        f"Total jobs in database: "
        f"{get_total_jobs()}"
    )

    print("Job alert check finished.")


# ============================================================
# ALERT LOOP
# ============================================================

async def alert_loop():
    print("Job alert loop started.")

    while True:
        try:
            config = load_config()

            if not config.get("active"):
                await asyncio.sleep(120)
                continue

            interval_hours = float(config.get("interval_hours", 1))

            last_run = config.get("last_run")

            now = datetime.now()

            should_run = False

            if last_run is None:
                should_run = True
            else:
                if isinstance(last_run, str):
                    last_run = datetime.fromisoformat(last_run)

                # Handle timezone-aware PostgreSQL timestamps
                if last_run.tzinfo is not None:
                    now = datetime.now(last_run.tzinfo)

                elapsed_hours = (
                    now - last_run
                ).total_seconds() / 3600

                if elapsed_hours >= interval_hours:
                    should_run = True

            if should_run:
                print(
                    f"Running alert search "
                    f"(interval={interval_hours}h)"
                )

                await _run_one_check(config)

        except Exception as e:
            print(f"Alert loop error: {e}")

        # Check the database again in 2 minutes
        await asyncio.sleep(120)