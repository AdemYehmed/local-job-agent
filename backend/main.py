from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.models import (
    ChatRequest, ChatResponse, ChatMessage,
    EmailGenerationRequest, EmailGenerationResponse,
    SendEmailRequest, SendEmailResponse,
    ProfileData, RHSearchRequest,
)
from app.llm_client import llm_client
from app.config import BACKEND_HOST, BACKEND_PORT, SYSTEM_PROMPT
from app.agent import decide_and_search, format_search_results, FINAL_SYSTEM_PROMPT_TEMPLATE
from app.email_generator import generate_application_email
from app.email_sender import send_application_email
from app.profile_extractor import extract_profile_from_cv
from app.job_search import search_jobs, search_rh
from pathlib import Path
import json

app = FastAPI(title="MiniLLM Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CV_STORAGE_PATH = Path(__file__).parent / "app" / "data" / "cv.pdf"
PROFILE_PATH = Path(__file__).parent / "app" / "data" / "profile.json"

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
        full_messages = with_system_prompt(request.messages)
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
            searched, results, query = await decide_and_search(request.messages)

            if searched:
                search_context = format_search_results(results)
                system_prompt = FINAL_SYSTEM_PROMPT_TEMPLATE.format(search_results=search_context)
            else:
                system_prompt = SYSTEM_PROMPT

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
        result = await generate_application_email(request.job_text)
        return EmailGenerationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur génération email: {str(e)}")

@app.post("/api/send-email", response_model=SendEmailResponse)
async def send_email(request: SendEmailRequest):
    try:
        result = send_application_email(request.to_email, request.subject, request.body)
        return SendEmailResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur envoi email: {str(e)}")

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

@app.get("/api/profile", response_model=ProfileData)
async def get_profile():
    if not PROFILE_PATH.exists():
        return ProfileData()
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ProfileData(**data)

@app.put("/api/profile", response_model=ProfileData)
async def update_profile(profile: ProfileData):
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
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

@app.get("/api/search-jobs")
async def api_search_jobs():
    try:
        results = search_jobs()
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche offres: {str(e)}")

@app.post("/api/search-rh")
async def api_search_rh(request: RHSearchRequest):
    try:
        results = search_rh(request.domain)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur recherche RH: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
