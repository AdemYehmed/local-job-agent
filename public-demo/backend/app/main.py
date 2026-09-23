from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

import asyncio

from app.jobspy_search import search_via_jobspy
from app.alert_runner import (
    alert_loop,
    load_config as _alert_load_config,
    save_config as _alert_save_config,
    send_telegram_message,
)


app = FastAPI(title="FindJob — Recherche d'offres")


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def _start_background_alert():
    asyncio.create_task(alert_loop())


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class JobSearchRequest(BaseModel):
    keywords: str
    region: str = "monde"
    timelimit: str = "tout"
    experience: str = "tout"
    sources: List[str] = ["linkedin"]


class JobOffer(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    skills_mentioned: List[str] = []
    contact_email: str = ""
    application_method: str = "lien"
    url: str = ""
    date_hint: str = ""


class JobSearchResponse(BaseModel):
    offers: List[JobOffer]
    raw_count: int
    filtered_count: int


class AlertConfigRequest(BaseModel):
    keywords: str
    region: str = "monde"
    timelimit: str = "mois"
    experience: str = "tout"
    sources: List[str] = ["linkedin"]
    interval_hours: float = 1
    active: bool = True


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_SOURCES = {
    "linkedin",
    "indeed",
}


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "public-no-llm"
    }


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.get("/api/system-status")
async def system_status():

    return {
        "mode": {
            "ok": True,
            "label": "Mode démo public (sans LLM)",
            "hint": "",
        },

        "job_search": {
            "ok": True,
            "label": "Recherche d'offres (LinkedIn / Indeed)",
            "hint": "",
        },
    }


# ============================================================
# JOB SEARCH
# ============================================================

@app.post(
    "/api/search-jobs",
    response_model=JobSearchResponse
)
async def search_jobs(
    request: JobSearchRequest
):

    sources = [
        s
        for s in request.sources
        if s in ALLOWED_SOURCES
    ]

    if not sources:

        raise HTTPException(
            status_code=400,
            detail=(
                "Cette version publique ne supporte "
                "que les sources LinkedIn et Indeed "
                "(pas de LLM disponible)."
            ),
        )

    individual_keywords = [
        k.strip()
        for k in request.keywords.split("+")
        if k.strip()
    ]

    if not individual_keywords:

        individual_keywords = [
            request.keywords.strip()
        ]

    all_offers: List[JobOffer] = []

    total_raw = 0

    seen_urls = set()

    try:

        for source in sources:

            for kw in individual_keywords:

                jobspy_offers = search_via_jobspy(
                    keywords=kw,
                    site=source,
                    region_label=request.region,
                    timelimit_label=request.timelimit,
                    experience_label=request.experience,
                    results_wanted=15,
                )

                total_raw += len(
                    jobspy_offers
                )

                for item in jobspy_offers:

                    base_url = (
                        item.get("url", "")
                        .split("?")[0]
                    )

                    if not base_url:
                        continue

                    if base_url in seen_urls:
                        continue

                    seen_urls.add(
                        base_url
                    )

                    item["url"] = base_url

                    all_offers.append(
                        JobOffer(**item)
                    )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Erreur recherche offres: {str(e)}"
            ),
        )

    return JobSearchResponse(
        offers=all_offers,
        raw_count=total_raw,
        filtered_count=len(all_offers),
    )


# ============================================================
# ALERT CONFIGURATION
# ============================================================

@app.post("/api/alert-config")
async def set_alert_config(
    request: AlertConfigRequest
):

    config = request.model_dump()

    _alert_save_config(config)

    return {
        "status": "saved",
        "config": config,
    }


@app.get("/api/alert-config")
async def get_alert_config():

    config = _alert_load_config()

    return config or {}


# ============================================================
# ALERT STATUS
# ============================================================

@app.get("/api/alert-status")
async def get_alert_status():

    config = _alert_load_config()

    if not config:

        return {
            "active": False,
            "last_run": None,
            "last_new_count": 0,
        }

    return {
        "active": config.get(
            "active",
            False
        ),

        "keywords": config.get(
            "keywords",
            ""
        ),

        "region": config.get(
            "region",
            "monde"
        ),

        "sources": config.get(
            "sources",
            []
        ),

        "timelimit": config.get(
            "timelimit",
            "mois"
        ),

        "experience": config.get(
            "experience",
            "tout"
        ),

        "interval_hours": config.get(
            "interval_hours",
            1
        ),

        "last_run": config.get(
            "last_run"
        ),

        "last_new_count": config.get(
            "last_new_count",
            0
        ),
    }


# ============================================================
# TEST TELEGRAM
# ============================================================

@app.get("/api/test-telegram")
async def test_telegram():

    try:

        await send_telegram_message(
            "🧪 <b>Test Job Alert</b>\n\n"
            "✅ Telegram fonctionne correctement.\n"
            "🤖 Message envoyé depuis Render."
        )

        return {
            "success": True,
            "message": (
                "Telegram message sent successfully"
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }