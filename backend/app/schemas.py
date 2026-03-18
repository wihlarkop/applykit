from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class WorkExperience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str | None = None
    bullets: list[str] = []


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    start_date: str
    end_date: str | None = None


class Project(BaseModel):
    name: str
    description: str
    tech_stack: list[str] = []
    link: str | None = None


class Certification(BaseModel):
    name: str
    issuer: str
    date: str


class ProfileData(BaseModel):
    id: int | None = None
    label: str = "Default"
    color: str = "#6366f1"
    icon: str = "💼"
    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    summary: str | None = None
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    skills: list[str] = []
    projects: list[Project] = []
    certifications: list[Certification] = []
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    profile: ProfileData | None


class ProfileListItem(BaseModel):
    id: int
    label: str
    color: str
    icon: str
    name: str
    has_content: bool = False
    completeness: int = 0


class ProfileListResponse(BaseModel):
    items: list[ProfileListItem]


class CreateProfileRequest(BaseModel):
    label: str
    color: str
    icon: str
    clone_from_id: int | None = None


class GenerateCvRequest(BaseModel):
    profile_id: int
    enhance: bool = True
    job_description: str | None = None
    application_id: int | None = None
    extra_context: str | None = None


class OnboardingStatusResponse(BaseModel):
    is_onboarded: bool


class StatusResponse(BaseModel):
    api_key_configured: bool
    provider: str | None


class GenerateCvResponse(BaseModel):
    enhanced: bool
    profile: ProfileData


class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
    tone: Literal["professional", "enthusiastic", "concise", "creative"] = "professional"
    job_url: str | None = None
    fit_context: str | None = None
    match_score: int | None = None          # from fit analysis — persisted to generated_cover_letter
    fit_analysis_json: str | None = None    # JSON string of FitAnalysisResponse — persisted to generated_cover_letter.fit_analysis
    application_id: int | None = None


class CoverLetterResponse(BaseModel):
    cover_letter_text: str


class PdfRequest(BaseModel):
    html: str


class ATSEnhancement(BaseModel):
    summary: str
    work_experience: list[WorkExperience]


class GenerateSummaryRequest(BaseModel):
    profile_id: int
    tone: Literal["professional", "enthusiastic", "concise", "creative"] = "professional"
    extra_context: str | None = None


class GenerateBulletsRequest(BaseModel):
    profile_id: int
    company: str
    role: str
    bullets: list[str]
    mode: Literal["improve", "reorganize"]
    extra_context: str | None = None


# --- History schemas ---


class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}


class GeneratedCVListResponse(BaseModel):
    items: list[GeneratedCVEntry]
    total: int


class GeneratedCoverLetterEntry(BaseModel):
    id: int
    created_at: datetime
    company_name: str | None
    job_description: str
    extra_context: str | None
    cover_letter_text: str
    tone: str
    job_url: str | None
    match_score: int | None
    fit_analysis: dict | None
    application_status: str | None
    application_id: int | None = None
    profile_id: int | None = None
    profile_label: str | None = None
    profile_color: str | None = None
    profile_icon: str | None = None

    model_config = {"from_attributes": True}


class GeneratedCoverLetterListResponse(BaseModel):
    items: list[GeneratedCoverLetterEntry]
    total: int


# --- Settings schemas ---


class SettingsResponse(BaseModel):
    model: str | None  # Full LiteLLM model string, e.g. "gemini/gemini-2.5-flash"
    api_key_configured: bool
    source: Literal["database", "env", "none"]


class UpdateSettingsRequest(BaseModel):
    model: str  # Full LiteLLM model string
    api_key: str
    activate: bool = True  # if False, saves the key but doesn't change the active model


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


class ModelOption(BaseModel):
    value: str
    label: str


class ProviderInfo(BaseModel):
    id: str
    label: str
    models: list[ModelOption]
    requires_api_key: bool


class ModelsResponse(BaseModel):
    providers: list[ProviderInfo]


class IntegrationInfo(BaseModel):
    id: str
    label: str
    is_active: bool
    api_key_configured: bool
    current_model: str | None


class IntegrationsResponse(BaseModel):
    integrations: list[IntegrationInfo]


class ActivateProviderRequest(BaseModel):
    provider_id: str


# --- Scraper schemas ---


class ScrapeJobRequest(BaseModel):
    url: str


class ScrapeJobResponse(BaseModel):
    job_description: str
    company_name: str | None
    source: Literal["greenhouse_api", "lever_api", "jina", "crawl4ai"]


# --- Fit analysis schemas ---


class FitAnalysisRequest(BaseModel):
    profile_id: int
    job_description: str


class FitAnalysisResponse(BaseModel):
    match_score: int
    pros: list[str]
    cons: list[str]
    missing_keywords: list[str]
    red_flags: list[str]
    suggested_emphasis: str
    interview_questions: list[str]


class UpdateStatusRequest(BaseModel):
    status: str | None  # None clears status back to null


class BulkDeleteRequest(BaseModel):
    ids: list[int]


# --- Application Tracker schemas ---


class ApplicationStatus(str, Enum):
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"


class CreateApplicationRequest(BaseModel):
    company_name: str
    role_title: str = ""
    status: ApplicationStatus = ApplicationStatus.applied
    job_url: str | None = None
    notes: str | None = None
    applied_date: date | None = None
    profile_id: int | None = None


class UpdateApplicationRequest(BaseModel):
    company_name: str | None = None
    role_title: str | None = None
    status: ApplicationStatus | None = None
    job_url: str | None = None
    notes: str | None = None
    applied_date: date | None = None


class ApplicationEntry(BaseModel):
    id: int
    company_name: str
    role_title: str
    status: ApplicationStatus
    job_url: str | None
    notes: str | None
    applied_date: date | None
    created_at: datetime
    profile_id: int | None
    profile_label: str | None
    profile_color: str | None
    profile_icon: str | None
    match_score: int | None
    linked_cover_letter_id: int | None
    linked_cv_id: int | None

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationEntry]
    total: int
