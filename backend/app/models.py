from pydantic import BaseModel, field_validator
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    use_profile_context: bool = False
    force_search: bool = False

class ChatResponse(BaseModel):
    content: str

class EmailGenerationRequest(BaseModel):
    job_text: str = ""
    company_name: str = ""
    generic: bool = False

class EmailGenerationResponse(BaseModel):
    subject: str
    body: str
    candidate_email: str
    recipient_email: str = ""

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str

class SendEmailResponse(BaseModel):
    status: str
    to: str
    subject: str
    cv_attached: bool = False

class ProfileData(BaseModel):
    name: str = ""
    email: str = ""
    degree: str = ""
    graduation_year: Optional[str] = None
    skills: List[str] = []
    languages: dict = {}
    location: str = ""
    summary: str = ""

    @field_validator("graduation_year", mode="before")
    @classmethod
    def coerce_graduation_year(cls, v):
        if v is None:
            return None
        return str(v)

class RHSearchRequest(BaseModel):
    domain: str

class JobSearchRequest(BaseModel):
    keywords: str
    region: str = "monde"
    timelimit: str = "tout"
    experience: str = "tout"
    sources: List[str] = ["web"]

class JobOffer(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    skills_mentioned: List[str] = []
    contact_email: str = ""
    application_method: str = "lien"
    url: str = ""
    date_hint: str = ""
    score: Optional[int] = None

class JobSearchResponse(BaseModel):
    offers: List[JobOffer]
    raw_count: int
    filtered_count: int

class ScoreRequest(BaseModel):
    job_text: str
    job_url: str = ""

class ScoreResponse(BaseModel):
    score: int
    matching_skills: List[str] = []
    missing_skills: List[str] = []
    recommendation: str = ""

class CompanySearchRequest(BaseModel):
    domain_keywords: str
    region: str = "Tunisie"

class CompanyResult(BaseModel):
    company: str = ""
    url: str = ""
    email: str = ""
    source_snippet: str = ""

class CompanySearchResponse(BaseModel):
    companies: List[CompanyResult]
