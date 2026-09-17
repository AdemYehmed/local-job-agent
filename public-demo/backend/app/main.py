from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from app.jobspy_search import search_via_jobspy

app = FastAPI(title="FindJob — Recherche d'offres")

import asyncio
from app.alert_runner import alert_loop

@app.on_event("startup")
async def _start_background_alert():
    asyncio.create_task(alert_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


ALLOWED_SOURCES = {"linkedin", "indeed"}


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "public-no-llm"}


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


@app.post("/api/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    sources = [s for s in request.sources if s in ALLOWED_SOURCES]
    if not sources:
        raise HTTPException(
            status_code=400,
            detail="Cette version publique ne supporte que les sources LinkedIn et Indeed (pas de LLM disponible).",
        )

    individual_keywords = [k.strip() for k in request.keywords.split("+") if k.strip()]
    if not individual_keywords:
        individual_keywords = [request.keywords.strip()]

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
                    results_wanted=8,
                )
                total_raw += len(jobspy_offers)
                for item in jobspy_offers:
                    base_url = item.get("url", "").split("?")[0]
                    if not base_url or base_url in seen_urls:
                        continue
                    seen_urls.add(base_url)
                    item["url"] = base_url
                    all_offers.append(JobOffer(**item))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche offres: {str(e)}")

    return JobSearchResponse(
        offers=all_offers,
        raw_count=total_raw,
        filtered_count=len(all_offers),
    )


from app.alert_runner import load_config as _alert_load_config, save_config as _alert_save_config, load_status as _alert_load_status


class AlertConfigRequest(BaseModel):
    keywords: str
    region: str = "monde"
    timelimit: str = "mois"
    experience: str = "tout"
    sources: List[str] = ["linkedin"]
    interval_hours: float = 1
    email: str
    active: bool = True


@app.post("/api/alert-config")
async def set_alert_config(request: AlertConfigRequest):
    _alert_save_config(request.model_dump())
    return {"status": "saved"}


@app.get("/api/alert-config")
async def get_alert_config():
    config = _alert_load_config()
    return config or {}


@app.get("/api/alert-status")
async def get_alert_status():
    return _alert_load_status()


from app.smtp_test import test_smtp_connection

@app.get("/api/test-smtp")
async def test_smtp():
    return await test_smtp_connection()
