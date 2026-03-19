// snake_case identifiers in this file mirror the Python backend API contract — intentional.
import type {
    ApplicationEntry,
    ApplicationFilters,
    ApplicationListResponse,
    CoverLetterHistoryFilters,
    CoverLetterRequest,
    CoverLetterResponse,
    CreateApplicationRequest,
    CreateProfileRequest,
    CvHistoryFilters,
    FitAnalysisResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    IntegrationsResponse,
    ModelsResponse,
    OnboardingStatusResponse,
    PdfRequest,
    ProfileData,
    ProfileListResponse,
    ScrapeJobResponse,
    SettingsResponse,
    StatusResponse,
    TestConnectionResponse,
    UpdateApplicationRequest,
    UpdateSettingsRequest,
} from './types';
import { buildQs } from './utils';

// ---------------------------------------------------------------------------
// Base URL — override via VITE_API_BASE_URL env variable for non-localhost envs
// ---------------------------------------------------------------------------
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

// ---------------------------------------------------------------------------
// Core fetch helpers
// ---------------------------------------------------------------------------

/** JSON request/response for the vast majority of API calls. */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Something went wrong. Please try again.' }));
        throw new Error(err.detail ?? 'Something went wrong. Please try again.');
    }

    if (res.status === 204 || res.headers.get('content-length') === '0') {
        return undefined as T;
    }

    return res.json() as Promise<T>;
}

/** FormData upload — used for file and text CV imports. */
async function requestForm<T>(path: string, body: FormData): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, { method: 'POST', body });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to import your CV. Please check the file and try again.' }));
        throw new Error(err.detail ?? 'Failed to import your CV. Please check the file and try again.');
    }
    return res.json() as Promise<T>;
}

/** Blob download — used for PDF generation endpoints. */
async function requestBlob(path: string, options: RequestInit): Promise<Blob> {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to download. Please try again.' }));
        throw new Error(err.detail ?? 'Failed to download. Please try again.');
    }
    return res.blob();
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export const listProfiles = () =>
    request<ProfileListResponse>('/profiles');

export const createProfile = (data: CreateProfileRequest) =>
    request<ProfileData>('/profiles', { method: 'POST', body: JSON.stringify(data) });

export const getProfile = (profileId: number) =>
    request<ProfileData>(`/profiles/${profileId}`);

export const saveProfile = (profileId: number, data: ProfileData) =>
    request<ProfileData>(`/profiles/${profileId}`, { method: 'PUT', body: JSON.stringify(data) });

export const deleteProfile = (profileId: number) =>
    request<void>(`/profiles/${profileId}`, { method: 'DELETE' });

export const getOnboardingStatus = () =>
    request<OnboardingStatusResponse>('/onboarding');

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

export const getStatus = () =>
    request<StatusResponse>('/status');

// ---------------------------------------------------------------------------
// Import CV
// ---------------------------------------------------------------------------

export const importCvFile = (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requestForm<ProfileData>('/import/cv', form);
};

export const importCvText = (text: string) => {
    const form = new FormData();
    form.append('text', text);
    return requestForm<ProfileData>('/import/cv', form);
};

// ---------------------------------------------------------------------------
// Generate CV
// ---------------------------------------------------------------------------

export const generateCv = (data: GenerateCvRequest) =>
    request<GenerateCvResponse>('/generate/cv', { method: 'POST', body: JSON.stringify(data) });

export const generateCvPdf = (data: PdfRequest) =>
    requestBlob('/generate/cv/pdf', { method: 'POST', body: JSON.stringify(data) });

// ---------------------------------------------------------------------------
// Generate Cover Letter
// ---------------------------------------------------------------------------

export const generateCoverLetter = (data: CoverLetterRequest) =>
    request<CoverLetterResponse>('/generate/cover-letter', {
        method: 'POST',
        body: JSON.stringify(data),
    });

export const generateCoverLetterStream = (data: CoverLetterRequest): Promise<Response> =>
    fetch(`${BASE_URL}/generate/cover-letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });

export const generateCoverLetterPdf = (data: PdfRequest) =>
    requestBlob('/generate/cover-letter/pdf', { method: 'POST', body: JSON.stringify(data) });

// ---------------------------------------------------------------------------
// Generate Bullets / Summary (streaming endpoints)
// ---------------------------------------------------------------------------

export const generateBulletsStream = (
    profile_id: number,
    company: string,
    role: string,
    bullets: string[],
    mode: 'improve' | 'reorganize',
    extra_context?: string
): Promise<Response> =>
    fetch(`${BASE_URL}/generate/bullets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id, company, role, bullets, mode, extra_context }),
    });

export const generateSummaryStream = (profile_id: number, tone: string, extra_context?: string): Promise<Response> =>
    fetch(`${BASE_URL}/generate/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id, tone, extra_context }),
    });

// ---------------------------------------------------------------------------
// Scrape
// ---------------------------------------------------------------------------

export const scrapeJob = (url: string) =>
    request<ScrapeJobResponse>('/scrape/job', { method: 'POST', body: JSON.stringify({ url }) });

// ---------------------------------------------------------------------------
// Fit Analysis
// ---------------------------------------------------------------------------

export const analyzeFit = (profile_id: number, job_description: string) =>
    request<FitAnalysisResponse>('/analyze/fit', {
        method: 'POST',
        body: JSON.stringify({ profile_id, job_description }),
    });

// ---------------------------------------------------------------------------
// CV History
// ---------------------------------------------------------------------------

export const getCvHistory = (filters: CvHistoryFilters = {}) =>
    request<GeneratedCVListResponse>(`/history/cv${buildQs(filters)}`);

export const getCvHistoryEntry = (id: number) =>
    request<GeneratedCVEntry>(`/history/cv/${id}`);

export const deleteCvHistoryEntry = (id: number) =>
    request<void>(`/history/cv/${id}`, { method: 'DELETE' });

export const updateCvStatus = (id: number, status: string | null) =>
    request<GeneratedCVEntry>(`/history/cv/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    });

export const bulkDeleteCvs = (ids: number[]) =>
    request<{ deleted: number }>('/history/cv', {
        method: 'DELETE',
        body: JSON.stringify({ ids }),
    });

// ---------------------------------------------------------------------------
// Cover Letter History
// ---------------------------------------------------------------------------

export const getCoverLetterHistory = (filters: CoverLetterHistoryFilters = {}) =>
    request<GeneratedCoverLetterListResponse>(`/history/cover-letter${buildQs(filters)}`);

export const getCoverLetterHistoryEntry = (id: number) =>
    request<GeneratedCoverLetterEntry>(`/history/cover-letter/${id}`);

export const deleteCoverLetterHistoryEntry = (id: number) =>
    request<void>(`/history/cover-letter/${id}`, { method: 'DELETE' });

export const updateCoverLetterStatus = (id: number, status: string | null) =>
    request<GeneratedCoverLetterEntry>(`/history/cover-letter/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
    });

export const bulkDeleteCoverLetters = (ids: number[]) =>
    request<{ deleted: number }>('/history/cover-letter', {
        method: 'DELETE',
        body: JSON.stringify({ ids }),
    });

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export const getSettings = () =>
    request<SettingsResponse>('/settings');

export const updateSettings = (data: UpdateSettingsRequest) =>
    request<SettingsResponse>('/settings', { method: 'PUT', body: JSON.stringify(data) });

export const testConnection = (data: UpdateSettingsRequest) =>
    request<TestConnectionResponse>('/settings/test', { method: 'POST', body: JSON.stringify(data) });

export const getModels = () =>
    request<ModelsResponse>('/settings/models');

export const getIntegrations = () =>
    request<IntegrationsResponse>('/settings/integrations');

export const activateProvider = (provider_id: string) =>
    request<SettingsResponse>('/settings/activate', { method: 'PUT', body: JSON.stringify({ provider_id }) });

// ---------------------------------------------------------------------------
// Applications
// ---------------------------------------------------------------------------

export const listApplications = (filters: ApplicationFilters = {}) =>
    request<ApplicationListResponse>(`/applications${buildQs(filters)}`);

export const createApplication = (data: CreateApplicationRequest) =>
    request<ApplicationEntry>('/applications', { method: 'POST', body: JSON.stringify(data) });

export const getApplication = (id: number) =>
    request<ApplicationEntry>(`/applications/${id}`);

export const updateApplication = (id: number, data: UpdateApplicationRequest) =>
    request<ApplicationEntry>(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(data) });

export const deleteApplication = (id: number) =>
    request<{ deleted: number }>(`/applications/${id}`, { method: 'DELETE' });
