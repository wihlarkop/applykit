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
  id?: number | null;
  label?: string;
  color?: string;
  icon?: string;
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

export interface ProfileListItem {
  id: number;
  label: string;
  color: string;
  icon: string;
  name: string;
  has_content: boolean;
  completeness: number;
}

export interface ProfileListResponse {
  items: ProfileListItem[];
}

export interface CreateProfileRequest {
  label: string;
  color: string;
  icon: string;
  clone_from_id?: number | null;
}

export interface GenerateCvRequest {
  profile_id: number;
  enhance?: boolean;
  job_description?: string | null;
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
  profile_id: number;
  job_description: string;
  company_name?: string | null;
  extra_context?: string;
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
  profile_snapshot: string;
  profile_id?: number | null;
  profile_label?: string | null;
  profile_color?: string | null;
  profile_icon?: string | null;
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
  profile_id?: number | null;
  profile_label?: string | null;
  profile_color?: string | null;
  profile_icon?: string | null;
}

export interface GeneratedCoverLetterListResponse {
  items: GeneratedCoverLetterEntry[];
}

// Settings
export interface SettingsResponse {
  model: string | null;
  api_key_configured: boolean;
  source: 'database' | 'env' | 'none';
}

export interface UpdateSettingsRequest {
  model: string;
  api_key: string;
}

export interface TestConnectionResponse {
  ok: boolean;
  message: string;
}

export interface ModelOption {
  value: string;
  label: string;
}

export interface ProviderInfo {
  id: string;
  label: string;
  models: ModelOption[];
  requires_api_key: boolean;
}

export interface ModelsResponse {
  providers: ProviderInfo[];
}
