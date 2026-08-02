// snake_case identifiers in this file mirror the Python backend API contract — intentional.
import type {
    ApplicationEntry,
    ApplicationFilters,
    ApplicationListResponse,
    CoverLetterHistoryFilters,
    CoverLetterPdfRequest,
    CoverLetterRequest,
    CoverLetterResponse,
    CreateApplicationRequest,
    CreateProfileRequest,
    CvHistoryFilters,
    CvPdfRequest,
    FitAnalysisResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    IntegrationsResponse,
    LlmUsageFilters,
    LlmUsageListResponse,
    LlmUsageStats,
    ModelsResponse,
    OnboardingStatusResponse,
    PdfRequest,
    ProfileData,
    ProfileListResponse,
    ScrapeAnalyzeResponse,
    ScrapeJobResponse,
    SettingsResponse,
    StatusResponse,
    TestConnectionResponse,
    UpdateApplicationRequest,
    UpdateSettingsRequest,
} from './types';
import { apiFetch } from './api-client';
import { parseApiError } from './api-error';
import { buildQs } from './utils';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function throwApiError(res: Response, fallbackMessage: string): Promise<never> {
    const payload: unknown = await res.json().catch(() => undefined);
    throw parseApiError(payload, fallbackMessage, res.status);
}

async function request<T>(
    path: string,
    options: RequestInit = {},
    fetchFn: typeof fetch = fetch,
): Promise<T> {
    const headers = new Headers(options.headers);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const res = await apiFetch(`${BASE_URL}${path}`, { ...options, headers }, fetchFn);

    if (!res.ok) {
        await throwApiError(res, 'Something went wrong. Please try again.');
    }

    if (res.status === 204 || res.headers.get('content-length') === '0') {
        return undefined as T;
    }

    return res.json() as Promise<T>;
}

async function requestForm<T>(path: string, body: FormData): Promise<T> {
    const res = await apiFetch(`${BASE_URL}${path}`, { method: 'POST', body });
    if (!res.ok) {
        await throwApiError(res, 'Failed to import your CV. Please check the file and try again.');
    }
    return res.json() as Promise<T>;
}

async function requestBlob(path: string, options: RequestInit): Promise<Blob> {
    const res = await apiFetch(`${BASE_URL}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        await throwApiError(res, 'Failed to download. Please try again.');
    }
    return res.blob();
}

function requestStream(path: string, body: unknown): Promise<Response> {
    return apiFetch(`${BASE_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
}

export const listProfiles = (fetchFn?: typeof fetch) =>
    request<ProfileListResponse>('/profiles', {}, fetchFn);

export const createProfile = (data: CreateProfileRequest, fetchFn?: typeof fetch) =>
    request<ProfileData>('/profiles', { method: 'POST', body: JSON.stringify(data) }, fetchFn);

export const getProfile = (profileId: number, fetchFn?: typeof fetch) =>
    request<ProfileData>(`/profiles/${profileId}`, {}, fetchFn);

export const saveProfile = (profileId: number, data: ProfileData, fetchFn?: typeof fetch) =>
    request<ProfileData>(`/profiles/${profileId}`, { method: 'PUT', body: JSON.stringify(data) }, fetchFn);

export const deleteProfile = (profileId: number, fetchFn?: typeof fetch) =>
    request<void>(`/profiles/${profileId}`, { method: 'DELETE' }, fetchFn);

export const getOnboardingStatus = (fetchFn?: typeof fetch) =>
    request<OnboardingStatusResponse>('/onboarding', {}, fetchFn);

export const getStatus = (fetchFn?: typeof fetch) =>
    request<StatusResponse>('/status', {}, fetchFn);

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

export const generateCv = (data: GenerateCvRequest) =>
    request<GenerateCvResponse>('/generate/cv', { method: 'POST', body: JSON.stringify(data) });

export const generateCvPdf = (data: CvPdfRequest) =>
    requestBlob('/generate/cv/pdf', { method: 'POST', body: JSON.stringify(data) });

export const generateCvStream = (data: GenerateCvRequest): Promise<Response> =>
    requestStream('/generate/cv/stream', data);

export const generateCoverLetter = (data: CoverLetterRequest) =>
    request<CoverLetterResponse>('/generate/cover-letter', {
        method: 'POST',
        body: JSON.stringify(data),
    });

export const generateCoverLetterStream = (data: CoverLetterRequest): Promise<Response> =>
    requestStream('/generate/cover-letter', data);

export const generateCoverLetterPdf = (data: CoverLetterPdfRequest) =>
    requestBlob('/generate/cover-letter/pdf', { method: 'POST', body: JSON.stringify(data) });

export const generateBulletsStream = (
    profile_id: number,
    company: string,
    role: string,
    bullets: string[],
    mode: 'improve' | 'reorganize',
    extra_context?: string,
): Promise<Response> => requestStream('/generate/bullets', {
    profile_id,
    company,
    role,
    bullets,
    mode,
    extra_context,
});

export const generateSummaryStream = (
    profile_id: number,
    tone: string,
    extra_context?: string,
): Promise<Response> => requestStream('/generate/summary', { profile_id, tone, extra_context });

export const scrapeJob = (url: string) =>
    request<ScrapeJobResponse>('/scrape/job', { method: 'POST', body: JSON.stringify({ url }) });

export const scrapeAnalyze = (data: { url?: string; text?: string }) =>
    request<ScrapeAnalyzeResponse>('/scrape/analyze', { method: 'POST', body: JSON.stringify(data) });

export const parseJobDescription = (text: string) =>
    request<{
        company_name: string | null;
        role_title: string | null;
        location: string | null;
        salary: string | null;
    }>('/scrape/parse', { method: 'POST', body: JSON.stringify({ text }) });

export const analyzeFit = (profile_id: number, job_description: string) =>
    request<FitAnalysisResponse>('/analyze/fit', {
        method: 'POST',
        body: JSON.stringify({ profile_id, job_description }),
    });

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
    request<SettingsResponse>('/settings/activate', {
        method: 'PUT',
        body: JSON.stringify({ provider_id }),
    });

export const disconnectProvider = (provider_id: string) =>
    request<IntegrationsResponse>(`/settings/integrations/${provider_id}`, { method: 'DELETE' });

export const listApplications = (filters: ApplicationFilters = {}) =>
    request<ApplicationListResponse>(`/applications${buildQs(filters)}`);

export const createApplication = (data: CreateApplicationRequest) =>
    request<ApplicationEntry>('/applications', { method: 'POST', body: JSON.stringify(data) });

export const getApplication = (id: number) =>
    request<ApplicationEntry>(`/applications/${id}`);

export const updateApplication = (id: number, data: UpdateApplicationRequest) =>
    request<ApplicationEntry>(`/applications/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    });

export const deleteApplication = (id: number) =>
    request<{ deleted: number }>(`/applications/${id}`, { method: 'DELETE' });

export const getLlmUsage = (filters?: LlmUsageFilters) => {
    const params = filters ? buildQs(filters) : '';
    return request<LlmUsageListResponse>(`/usage${params}`);
};

export const getLlmUsageStats = () =>
    request<LlmUsageStats>('/usage/stats', { method: 'GET' });
