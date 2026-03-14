from datetime import datetime

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


class OnboardingStatusResponse(BaseModel):
    is_onboarded: bool


class StatusResponse(BaseModel):
    api_key_configured: bool
    provider: str | None


class GenerateCvResponse(BaseModel):
    enhanced: bool
    profile: ProfileData


class CoverLetterRequest(BaseModel):
    job_description: str
    company_name: str | None = None
    extra_context: str = ""


class CoverLetterResponse(BaseModel):
    cover_letter_text: str


class PdfRequest(BaseModel):
    html: str


class ATSEnhancement(BaseModel):
    summary: str
    work_experience: list[WorkExperience]


# --- History schemas ---

class GeneratedCVEntry(BaseModel):
    id: int
    created_at: datetime
    enhanced: bool
    profile_snapshot: str  # raw JSON — frontend parses if needed

    model_config = {"from_attributes": True}


class GeneratedCVListResponse(BaseModel):
    items: list[GeneratedCVEntry]


class GeneratedCoverLetterEntry(BaseModel):
    id: int
    created_at: datetime
    company_name: str | None
    job_description: str
    extra_context: str | None
    cover_letter_text: str

    model_config = {"from_attributes": True}


class GeneratedCoverLetterListResponse(BaseModel):
    items: list[GeneratedCoverLetterEntry]
