from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, ChatResponse, ChatMessage, EmailGenerationRequest, EmailGenerationResponse
from app.llm_client import llm_client
from app.config import BACKEND_HOST, BACKEND_PORT, SYSTEM_PROMPT
from app.agent import decide_and_search, format_search_results, FINAL_SYSTEM_PROMPT_TEMPLATE
from app.user_context import build_profile_context
from app.email_generator import generate_application_email
from app.email_sender import send_application_email
from app.models import SendEmailRequest, SendEmailResponse
import json

app = FastAPI(title="MiniLLM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def with_system_prompt(messages: list[ChatMessage], prompt: str = SYSTEM_PROMPT) -> list[ChatMessage]:
    if messages and messages[0].role == "system":
        return messages
    return [ChatMessage(role="system", content=prompt)] + messages

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        base_prompt = SYSTEM_PROMPT
        if request.use_profile_context:
            base_prompt = base_prompt + build_profile_context()
        full_messages = with_system_prompt(request.messages, base_prompt)
        content = await llm_client.chat(
            messages=full_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return ChatResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur LLM: {str(e)}")

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            if request.force_search:
                searched, results, query = await decide_and_search(request.messages, force_search=True)
            else:
                searched, results, query = False, [], ""

            if searched:
                search_context = format_search_results(results)
                system_prompt = FINAL_SYSTEM_PROMPT_TEMPLATE.format(search_results=search_context)
            else:
                system_prompt = SYSTEM_PROMPT

            if request.use_profile_context:
                system_prompt = system_prompt + build_profile_context()

            full_messages = with_system_prompt(request.messages, system_prompt)

            async for token in llm_client.chat_stream(
                messages=full_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                payload = json.dumps({"token": token})
                yield f"data: {payload}\n\n"

            if searched:
                sources_payload = json.dumps({
                    "sources": [{"title": r["title"], "url": r["url"]} for r in results],
                    "query": query,
                })
                yield f"data: {sources_payload}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            error_payload = json.dumps({"error": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/generate-email", response_model=EmailGenerationResponse)
async def generate_email(request: EmailGenerationRequest):
    try:
        result = await generate_application_email(
            job_text=request.job_text,
            company_name=request.company_name,
            generic=request.generic,
        )
        return EmailGenerationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération email: {str(e)}")

@app.post("/api/send-email", response_model=SendEmailResponse)
async def send_email(request: SendEmailRequest):
    try:
        result = send_application_email(request.to_email, request.subject, request.body)
        return SendEmailResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur envoi email: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)

from fastapi import UploadFile, File
from pathlib import Path as _Path

CV_STORAGE_PATH = _Path(__file__).parent / "data" / "cv.pdf"

@app.post("/api/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")
    CV_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    with open(CV_STORAGE_PATH, "wb") as f:
        f.write(content)
    return {"status": "uploaded", "filename": file.filename, "size_bytes": len(content)}

@app.get("/api/cv-status")
async def cv_status():
    if CV_STORAGE_PATH.exists():
        size = CV_STORAGE_PATH.stat().st_size
        return {"has_cv": True, "size_bytes": size}
    return {"has_cv": False, "size_bytes": 0}

from app.models import ProfileData
from app.profile_extractor import extract_profile_from_cv
import json as _json

PROFILE_PATH = _Path(__file__).parent / "data" / "profile.json"

@app.get("/api/profile", response_model=ProfileData)
async def get_profile():
    if not PROFILE_PATH.exists():
        return ProfileData()
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        data = _json.load(f)
    return ProfileData(**data)

@app.put("/api/profile", response_model=ProfileData)
async def update_profile(profile: ProfileData):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        _json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
    return profile

@app.post("/api/extract-profile-from-cv", response_model=ProfileData)
async def extract_profile_endpoint():
    if not CV_STORAGE_PATH.exists():
        raise HTTPException(status_code=400, detail="Aucun CV uploadé. Uploade d'abord ton CV.")
    try:
        result = await extract_profile_from_cv()
        return ProfileData(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur extraction profil: {str(e)}")

from app.models import JobSearchRequest, JobSearchResponse, JobOffer
from app.job_search import search_jobs_by_source, enrich_with_full_text
from app.job_structurer import structure_job_results
from app.job_filters import is_listing_page, matches_region, clean_date_hint
from app.jobspy_search import search_via_jobspy
from app.job_store import load_stored_jobs, save_jobs, clear_jobs
from app.keyword_normalizer import normalize_keywords

@app.post("/api/search-jobs", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    try:
        individual_keywords = [k.strip() for k in request.keywords.split("+") if k.strip()]
        if not individual_keywords:
            individual_keywords = [request.keywords.strip()]

        all_offers = []
        total_raw = 0
        seen_offer_urls = set()

        for source in request.sources:
            if source in ("linkedin", "indeed"):
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
                        raw_url = item.get("url", "")
                        base_url = raw_url.split("?")[0]
                        if base_url in seen_offer_urls:
                            continue
                        seen_offer_urls.add(base_url)
                        item["url"] = base_url
                        item["score"] = get_score(base_url)
                        all_offers.append(JobOffer(**item))
                continue

            raw_results = []
            seen_raw_urls = set()
            for kw in individual_keywords:
                query_variants = await normalize_keywords(kw)
                for query in query_variants:
                    partial = search_jobs_by_source(
                        keywords=query,
                        source=source,
                        region_label=request.region,
                        timelimit_label=request.timelimit,
                        max_results=5,
                    )
                    for r in partial:
                        if r["url"] and r["url"] not in seen_raw_urls:
                            raw_results.append(r)
                            seen_raw_urls.add(r["url"])

            if source == "linkedin":
                raw_results = await enrich_with_full_text(raw_results, max_enriched=3)

            total_raw += len(raw_results)

            structured = await structure_job_results(raw_results, source=source)

            for item in structured:
                raw_url = item.get("url", "")
                base_url = raw_url.split("?")[0]
                if base_url in seen_offer_urls:
                    continue

                title = item.get("title", "")
                location = item.get("location", "")

                if is_listing_page(title):
                    continue
                if not matches_region(title, location, request.region):
                    continue

                company = item.get("company", "")
                if company and len(company.split()) > 4:
                    company = ""
                if company and company.lower().strip().startswith("company"):
                    company = ""
                site_names = ["linkedin", "indeed", "tanitjobs", "glassdoor", "jobted", "meteojob", "bluecoders"]
                if company and any(site in company.lower() for site in site_names):
                    company = ""
                bad_company_phrases = ["résentation", "presentation", "société recherche", "notre client"]
                if company and any(phrase in company.lower() for phrase in bad_company_phrases):
                    company = ""

                seen_offer_urls.add(base_url)
                all_offers.append(JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    skills_mentioned=item.get("skills_mentioned", []),
                    contact_email=item.get("contact_email", ""),
                    application_method=item.get("application_method", "lien"),
                    url=base_url,
                    date_hint=clean_date_hint(item.get("date_hint", "")),
                    score=get_score(base_url),
                ))

        offers_as_dicts = [o.model_dump() for o in all_offers]
        save_jobs(offers_as_dicts)

        return JobSearchResponse(
            offers=all_offers,
            raw_count=total_raw,
            filtered_count=len(all_offers),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche offres: {str(e)}")

@app.get("/api/stored-jobs")
async def get_stored_jobs():
    return {"offers": load_stored_jobs()}

@app.delete("/api/stored-jobs")
async def delete_stored_jobs():
    clear_jobs()
    return {"status": "cleared"}

from app.models import ScoreRequest, ScoreResponse
from app.job_scorer import score_job_offer
from app.job_scores import get_score, save_score
from app.job_store import update_offer_score, get_offer_score

@app.post("/api/score-job", response_model=ScoreResponse)
async def score_job(request: ScoreRequest):
    try:
        if request.job_url:
            cached = get_offer_score(request.job_url)
            if cached is None:
                cached = get_score(request.job_url)
            if cached is not None:
                return ScoreResponse(score=cached, matching_skills=[], missing_skills=[], recommendation="(score en cache)")

        result = await score_job_offer(request.job_text)

        if request.job_url:
            save_score(request.job_url, result["score"])
            update_offer_score(request.job_url, result["score"])

        return ScoreResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur calcul score: {str(e)}")

from app.models import CompanySearchRequest, CompanySearchResponse, CompanyResult
from app.company_finder import find_companies_by_domain
from fastapi.responses import StreamingResponse as _StreamingResponse
import csv as _csv
import io as _io

@app.post("/api/search-companies", response_model=CompanySearchResponse)
async def search_companies(request: CompanySearchRequest):
    try:
        results = find_companies_by_domain(request.domain_keywords, request.region)
        companies = [CompanyResult(**r) for r in results]
        return CompanySearchResponse(companies=companies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche entreprises: {str(e)}")

@app.post("/api/export-companies-csv")
async def export_companies_csv(request: CompanySearchRequest):
    try:
        results = find_companies_by_domain(request.domain_keywords, request.region)

        buffer = _io.StringIO()
        writer = _csv.writer(buffer)
        writer.writerow(["Entreprise", "Email contact RH", "URL source", "Extrait"])
        for r in results:
            writer.writerow([r["company"], r["email"], r["url"], r["source_snippet"]])

        buffer.seek(0)
        return _StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=entreprises.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur export CSV: {str(e)}")

from app.keyword_suggester import suggest_keywords_from_profile

@app.get("/api/suggest-keywords")
async def suggest_keywords():
    try:
        keywords = await suggest_keywords_from_profile()
        return {"keywords": keywords}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suggestion mots-clés: {str(e)}")

from app.system_status import get_system_status

@app.get("/api/system-status")
async def system_status():
    return await get_system_status()
