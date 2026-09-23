import asyncio
import json
import os
import html
from datetime import datetime

import httpx
import psycopg2

from app.jobspy_search import search_via_jobspy
from app.cv_matcher import calculate_cv_match


# ============================================================
# CONFIGURATION
# ============================================================

CHECK_INTERVAL_SECONDS = 120

DATABASE_URL = os.getenv("DATABASE_URL")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Minimum CV score required
CV_SCORE_THRESHOLD = 1.0


# ============================================================
# DATABASE
# ============================================================


async def health():
    print("i m not die")
    


def get_db_connection():
    """
    Connect to PostgreSQL / Supabase.
    """

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    return psycopg2.connect(
        DATABASE_URL
    )


# ============================================================
# TELEGRAM
# ============================================================

async def send_telegram_message(message: str):
    """
    Send a message to Telegram.

    Returns:
        True  -> message successfully sent
        False -> failed
    """

    if not TELEGRAM_BOT_TOKEN:
        print(
            "❌ Telegram error: "
            "TELEGRAM_BOT_TOKEN is missing"
        )
        return False

    if not TELEGRAM_CHAT_ID:
        print(
            "❌ Telegram error: "
            "TELEGRAM_CHAT_ID is missing"
        )
        return False

    telegram_url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:

        print(
            "📨 Sending Telegram notification..."
        )

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                telegram_url,
                json=payload
            )

        if response.status_code == 200:

            data = response.json()

            if data.get("ok") is True:

                print(
                    "✅ Telegram notification sent."
                )

                return True

            print(
                "❌ Telegram API returned "
                f"ok=false: {data}"
            )

            return False

        print(
            "❌ Telegram HTTP error: "
            f"{response.status_code}"
        )

        print(
            f"Telegram response: "
            f"{response.text}"
        )

        return False

    except Exception as e:

        print(
            f"❌ Telegram exception: {e}"
        )

        return False


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_telegram_message(
    keywords,
    new_jobs
):
    """
    Build Telegram message for new jobs.
    """

    lines = []

    lines.append(
        "🚨 <b>New Job Alert</b>"
    )

    lines.append("")

    lines.append(
        "🔎 <b>Search:</b> "
        f"{html.escape(str(keywords))}"
    )

    lines.append(
        "📊 <b>New relevant jobs:</b> "
        f"{len(new_jobs)}"
    )

    lines.append("")

    for index, job in enumerate(
        new_jobs,
        start=1
    ):

        title = html.escape(
            str(
                job.get("title")
                or "Unknown title"
            )
        )

        company = html.escape(
            str(
                job.get("company")
                or "Unknown company"
            )
        )

        location = html.escape(
            str(
                job.get("location")
                or "Unknown location"
            )
        )

        source = html.escape(
            str(
                job.get("source")
                or "Unknown"
            )
        )

        url = str(
            job.get("url")
            or ""
        ).strip()

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = job.get(
            "match_score"
        )

        try:

            score_text = (
                f"{float(score):.1f}/10"
            )

        except Exception:

            score_text = "N/A"

        # ----------------------------------------------------
        # MATCHED KEYWORDS
        # ----------------------------------------------------

        matched_keywords = job.get(
            "matched_keywords",
            []
        )

        if isinstance(
            matched_keywords,
            str
        ):

            try:

                matched_keywords = (
                    json.loads(
                        matched_keywords
                    )
                )

            except Exception:

                matched_keywords = [
                    matched_keywords
                ]

        if matched_keywords:

            keywords_text = ", ".join(
                str(keyword)
                for keyword
                in matched_keywords
            )

        else:

            keywords_text = "None"

        # ----------------------------------------------------
        # JOB
        # ----------------------------------------------------

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
            f"🎯 <b>CV Match:</b> "
            f"{score_text}"
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
                f'🔗 <a href="{safe_url}">'
                "View job"
                "</a>"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# LOAD CONFIG
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
                    "sources": [
                        "linkedin"
                    ],
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

            if isinstance(
                sources,
                str
            ):

                try:

                    sources = json.loads(
                        sources
                    )

                except Exception:

                    sources = [
                        "linkedin"
                    ]

            country_value = (
                country or "monde"
            )

            return {
                "keywords": (
                    keywords or ""
                ),

                # On expose la valeur sous les DEUX noms
                # ("country" et "region") pour rester compatible
                # avec main.py, qui lit parfois "region" au lieu
                # de "country" (ex: /api/alert-status).
                "country": country_value,
                "region": country_value,

                "sources": (
                    sources
                    or ["linkedin"]
                ),

                "timelimit": (
                    timelimit
                    or "mois"
                ),

                "experience": (
                    experience
                    or "tout"
                ),

                "interval_hours": float(
                    interval_hours
                    or 1
                ),

                "active": bool(
                    active
                ),

                "last_run": last_run,

                "last_new_count": int(
                    last_new_count
                    or 0
                ),
            }

    finally:

        conn.close()


# ============================================================
# SAVE CONFIG
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

            # BUGFIX:
            # main.py (AlertConfigRequest) envoie le champ sous le
            # nom "region", pas "country". Sans ce fallback,
            # config.get("country", "monde") ne trouvait jamais la
            # vraie valeur envoyée par l'utilisateur et retombait
            # toujours sur "monde" par défaut, silencieusement.
            country_value = (
                config.get("region")
                or config.get("country")
                or "monde"
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
                    interval_hours =
                        EXCLUDED.interval_hours,
                    active = EXCLUDED.active,
                    updated_at = NOW()
                """,
                (
                    config.get(
                        "keywords",
                        ""
                    ),

                    country_value,

                    json.dumps(
                        sources
                    ),

                    config.get(
                        "timelimit",
                        "mois"
                    ),

                    config.get(
                        "experience",
                        "tout"
                    ),

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

    finally:

        conn.close()


# ============================================================
# UPDATE STATUS
# ============================================================

def update_alert_status(
    new_count
):
    """
    Update last run information.
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
                (
                    int(new_count),
                )
            )

        conn.commit()

    finally:

        conn.close()


# ============================================================
# SAVE JOBS
# ============================================================

def save_new_jobs(jobs):
    """
    Save relevant jobs.

    URL is the unique identifier.

    Existing URL:
        update last_seen_at

    New URL:
        insert and return for Telegram.
    """

    if not jobs:
        return []

    conn = get_db_connection()

    new_jobs = []

    try:

        with conn.cursor() as cur:

            for job in jobs:

                url = str(
                    job.get("url")
                    or ""
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

                # ==================================================
                # CHECK URL
                # ==================================================

                cur.execute(
                    """
                    SELECT id
                    FROM jobs
                    WHERE url = %s
                    """,
                    (url,)
                )

                existing = cur.fetchone()

                # ==================================================
                # EXISTING JOB
                # ==================================================

                if existing:

                    cur.execute(
                        """
                        UPDATE jobs
                        SET
                            last_seen_at = NOW(),
                            match_score = %s,
                            matched_keywords =
                                %s::jsonb
                        WHERE url = %s
                        """,
                        (
                            match_score,

                            json.dumps(
                                matched_keywords
                            ),

                            url,
                        )
                    )

                    continue

                # ==================================================
                # NEW JOB
                # ==================================================

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
                    )
                )

                inserted_id = (
                    cur.fetchone()[0]
                )

                job["id"] = (
                    inserted_id
                )

                new_jobs.append(
                    job
                )

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

    conn = get_db_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                """
            )

            row = cur.fetchone()

            return int(
                row[0] or 0
            )

    finally:

        conn.close()


# ============================================================
# ONE ALERT CHECK
# ============================================================

async def _run_one_check(
    config
):
    """
    Complete pipeline:

        JobSpy
          ↓
        URL deduplication
          ↓
        CV matching
          ↓
        score >= 4
          ↓
        Supabase
          ↓
        NEW URL?
          ↓
        Telegram
    """

    keywords = str(
        config.get("keywords")
        or ""
    ).strip()

    # BUGFIX:
    # main.py (/api/search-jobs) split les mots-clés sur "+" et
    # fait une recherche PAR mot-clé ("embedded + linux" ->
    # ["embedded", "linux"]). Ici, la chaîne complète était
    # envoyée telle quelle à jobspy ("embedded + linux" avec le
    # "+" littéral), ce qui ne matchait aucune offre sur
    # LinkedIn/Indeed -> d'où le "No jobs returned" alors que
    # /api/search-jobs, lui, fonctionnait normalement.
    individual_keywords = [
        k.strip()
        for k in keywords.split("+")
        if k.strip()
    ]

    if not individual_keywords and keywords:

        individual_keywords = [
            keywords
        ]

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

        print(
            "Alert search skipped: "
            "no keywords."
        )

        return

    if not sources:

        sources = [
            "linkedin"
        ]

    # ========================================================
    # START
    # ========================================================

    print("")
    print("=" * 70)
    print("STARTING JOB ALERT SEARCH")
    print("=" * 70)

    print(
        f"Keywords   : {keywords}"
    )

    print(
        f"Country    : {country}"
    )

    print(
        f"Sources    : {sources}"
    )

    print(
        f"Timelimit  : {timelimit}"
    )

    print(
        f"Experience : {experience}"
    )

    print("=" * 70)

    # ========================================================
    # JOB SEARCH
    # ========================================================

    all_offers = []

    for source in sources:

        for kw in individual_keywords:

            try:

                print(
                    f"Searching source: "
                    f"{source} "
                    f"(keyword: {kw})"
                )

                # IMPORTANT:
                # Keep the OLD interface.
                offers = search_via_jobspy(
                    kw,
                    source,
                    country,
                    timelimit,
                    experience,
                    50
                )

                if not offers:

                    print(
                        f"No jobs returned "
                        f"from {source} "
                        f"for '{kw}'"
                    )

                    continue

                print(
                    f"{len(offers)} jobs "
                    f"returned from {source} "
                    f"for '{kw}'"
                )

                for job in offers:

                    if not isinstance(
                        job,
                        dict
                    ):
                        continue

                    job["source"] = (
                        source
                    )

                    all_offers.append(
                        job
                    )

            except Exception as e:

                print(
                    f"Search error for "
                    f"{source} "
                    f"(keyword: {kw}): {e}"
                )

    # ========================================================
    # RAW JOBS
    # ========================================================

    print(
        f"Total raw jobs: "
        f"{len(all_offers)}"
    )

    # ========================================================
    # CURRENT-SEARCH URL DEDUP
    # ========================================================

    unique_jobs = []

    seen_urls = set()

    for job in all_offers:

        url = str(
            job.get("url")
            or ""
        ).strip()

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        unique_jobs.append(
            job
        )

    print(
        "Unique jobs after URL "
        f"deduplication: "
        f"{len(unique_jobs)}"
    )

    # ========================================================
    # CV MATCHING
    # ========================================================

    print("")
    print("=" * 70)
    print("CV MATCHING")
    print("=" * 70)

    filtered_jobs = []

    for job in unique_jobs:

        try:

            match = calculate_cv_match(
                job
            )

            score = float(
                match.get(
                    "score",
                    0
                )
            )

            matched_keywords = (
                match.get(
                    "matched_keywords",
                    []
                )
            )

            job["match_score"] = (
                score
            )

            job["matched_keywords"] = (
                matched_keywords
            )

            print(
                f"{job.get('title', '')} "
                f"→ score={score:.1f}/10 "
                f"keywords="
                f"{matched_keywords}"
            )

            if (
                score
                >= CV_SCORE_THRESHOLD
            ):

                filtered_jobs.append(
                    job
                )

                print(
                    "  ✅ ACCEPTED"
                )

            else:

                print(
                    "  ❌ REJECTED"
                )

        except Exception as e:

            print(
                "CV matching error for "
                f"{job.get('title', '')}: "
                f"{e}"
            )

    print(
        "Relevant jobs after CV "
        f"filtering: "
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
            f"❌ Database save error: "
            f"{e}"
        )

        return

    print(
        "New jobs inserted into DB: "
        f"{len(new_jobs)}"
    )

    # ========================================================
    # TELEGRAM
    # ========================================================

    if new_jobs:

        print(
            f"📢 {len(new_jobs)} "
            "NEW jobs found!"
        )

        message = (
            build_telegram_message(
                keywords,
                new_jobs
            )
        )

        telegram_ok = (
            await send_telegram_message(
                message
            )
        )

        if telegram_ok:

            print(
                "✅ New jobs sent "
                "to Telegram."
            )

        else:

            print(
                "❌ Failed to send "
                "new jobs to Telegram."
            )

    else:

        print(
            "No new jobs. "
            "No Telegram message sent."
        )

    # ========================================================
    # UPDATE STATUS
    # ========================================================

    try:

        update_alert_status(
            len(new_jobs)
        )

    except Exception as e:

        print(
            f"Status update error: "
            f"{e}"
        )

    # ========================================================
    # TOTAL DATABASE JOBS
    # ========================================================

    try:

        total_jobs = get_total_jobs()

        print(
            "Total relevant jobs in DB: "
            f"{total_jobs}"
        )

    except Exception as e:

        print(
            "Could not get total "
            f"job count: {e}"
        )

    print("=" * 70)
    print(
        "JOB ALERT SEARCH FINISHED"
    )
    print("=" * 70)
    print("")


# ============================================================
# ALERT LOOP
# ============================================================

async def alert_loop():

    print(
        "Job alert loop started."
    )

    while True:

        try:

            config = load_config()

            # ==================================================
            # INACTIVE
            # ==================================================

            if not config.get(
                "active"
            ):

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
            # RUN
            # ==================================================

            if should_run:

                print(
                    "Running alert search "
                    f"(interval="
                    f"{interval_hours}h)"
                )

                await _run_one_check(
                    config
                )

            else:

                print(
                    "Alert search "
                    "not due yet."
                )

        except Exception as e:

            print(
                f"Alert loop error: "
                f"{e}"
            )

        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )