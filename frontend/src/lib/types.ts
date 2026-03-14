export interface WorkExperience {
  company: string;
  role: string;
  start_date: string;
  end_date?: string | null;
  bullets: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field: string;
  start_date: string;
  end_date?: string | null;
}

export interface Project {
  name: string;
  description: string;
  tech_stack: string[];
  link?: string | null;
}

export interface Certification {
  name: string;
  issuer: string;
  date: string;
}

export interface ProfileData {
  name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  linkedin?: string | null;
  github?: string | null;
  portfolio?: string | null;
  summary?: string | null;
  work_experience: WorkExperience[];
  education: Education[];
  skills: string[];
  projects: Project[];
  certifications: Certification[];
  updated_at?: string | null;
}

export interface ProfileResponse {
  profile: ProfileData | null;
}

export interface OnboardingStatusResponse {
  is_onboarded: boolean;
}

export interface StatusResponse {
  api_key_configured: boolean;
  provider: string | null;
}

export interface GenerateCvResponse {
  enhanced: boolean;
  profile: ProfileData;
}

export interface CoverLetterRequest {
  job_description: string;
  extra_context?: string;
  company_name?: string | null;
}

export interface CoverLetterResponse {
  cover_letter_text: string;
}

export interface PdfRequest {
  html: string;
}

export interface ApiError {
  detail: string;
  code?: string;
}

export interface GeneratedCVEntry {
  id: number;
  created_at: string;
  enhanced: boolean;
  profile_snapshot: string; // JSON string — parse with JSON.parse() when needed
}

export interface GeneratedCVListResponse {
  items: GeneratedCVEntry[];
}

export interface GeneratedCoverLetterEntry {
  id: number;
  created_at: string;
  company_name: string | null;
  job_description: string;
  extra_context: string | null;
  cover_letter_text: string;
}

export interface GeneratedCoverLetterListResponse {
  items: GeneratedCoverLetterEntry[];
}
