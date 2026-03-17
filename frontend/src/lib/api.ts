import type {
    CoverLetterRequest,
    CoverLetterResponse,
    CreateProfileRequest,
    FitAnalysisResponse,
    GenerateCvRequest,
    GenerateCvResponse,
    GeneratedCVEntry,
    GeneratedCVListResponse,
    GeneratedCoverLetterEntry,
    GeneratedCoverLetterListResponse,
    ModelsResponse,
    OnboardingStatusResponse,
    PdfRequest,
    ProfileData,
    ProfileListResponse,
    ScrapeJobResponse,
    SettingsResponse,
    StatusResponse,
    TestConnectionResponse,
    UpdateSettingsRequest,
} from './types';

const BASE_URL = 'http://localhost:8000/api';

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? 'Request failed');
  }

  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

// Profile
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

// Status
export const getStatus = () =>
  request<StatusResponse>('/status');

// Import CV
export const importCvFile = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return fetch(`${BASE_URL}/import/cv`, { method: 'POST', body: form }).then(
    async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail ?? 'Import failed');
      }
      return res.json() as Promise<ProfileData>;
    }
  );
};

export const importCvText = (text: string) => {
  const form = new FormData();
  form.append('text', text);
  return fetch(`${BASE_URL}/import/cv`, { method: 'POST', body: form }).then(
    async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail ?? 'Import failed');
      }
      return res.json() as Promise<ProfileData>;
    }
  );
};

// Generate CV
export const generateCv = (data: GenerateCvRequest) =>
  request<GenerateCvResponse>('/generate/cv', { method: 'POST', body: JSON.stringify(data) });

export const generateCvPdf = (data: PdfRequest) =>
  fetch(`${BASE_URL}/generate/cv/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail ?? 'PDF generation failed');
    }
    return res.blob();
  });

// Generate cover letter
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
  fetch(`${BASE_URL}/generate/cover-letter/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail ?? 'PDF generation failed');
    }
    return res.blob();
  });

// Scrape
export const scrapeJob = (url: string) =>
  request<ScrapeJobResponse>('/scrape/job', { method: 'POST', body: JSON.stringify({ url }) });

// Fit analysis
export const analyzeFit = (profile_id: number, job_description: string) =>
  request<FitAnalysisResponse>('/analyze/fit', {
    method: 'POST',
    body: JSON.stringify({ profile_id, job_description }),
  });

// CV history
export const getCvHistory = (filters: { profile_id?: number; sort?: string; limit?: number; offset?: number } = {}) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return request<GeneratedCVListResponse>(`/history/cv${qs ? `?${qs}` : ''}`);
};

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

// Cover letter history
export interface CoverLetterHistoryFilters {
  profile_id?: number;
  search?: string;
  match_min?: number;
  match_max?: number;
  status?: string;
  sort?: 'date_desc' | 'date_asc' | 'match_desc' | 'company_asc';
  limit?: number;
  offset?: number;
}

export const getCoverLetterHistory = (filters: CoverLetterHistoryFilters = {}) => {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return request<GeneratedCoverLetterListResponse>(`/history/cover-letter${qs ? `?${qs}` : ''}`);
};

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

// Settings
export const getSettings = () =>
  request<SettingsResponse>('/settings');

export const updateSettings = (data: UpdateSettingsRequest) =>
  request<SettingsResponse>('/settings', { method: 'PUT', body: JSON.stringify(data) });

export const testConnection = (data: UpdateSettingsRequest) =>
  request<TestConnectionResponse>('/settings/test', { method: 'POST', body: JSON.stringify(data) });

export const getModels = () =>
  request<ModelsResponse>('/settings/models');
