import type {
  CoverLetterRequest,
  CoverLetterResponse,
  GenerateCvResponse,
  PdfRequest,
  ProfileData,
  StatusResponse,
  OnboardingStatusResponse,
  GeneratedCVEntry,
  GeneratedCVListResponse,
  GeneratedCoverLetterEntry,
  GeneratedCoverLetterListResponse,
  ProfileListResponse,
  CreateProfileRequest,
  GenerateCvRequest,
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

// CV history
export const getCvHistory = (profileId?: number) =>
  request<GeneratedCVListResponse>(`/history/cv${profileId != null ? `?profile_id=${profileId}` : ''}`);

export const getCvHistoryEntry = (id: number) =>
  request<GeneratedCVEntry>(`/history/cv/${id}`);

export const deleteCvHistoryEntry = (id: number) =>
  request<void>(`/history/cv/${id}`, { method: 'DELETE' });

// Cover letter history
export const getCoverLetterHistory = (profileId?: number) =>
  request<GeneratedCoverLetterListResponse>(`/history/cover-letter${profileId != null ? `?profile_id=${profileId}` : ''}`);

export const getCoverLetterHistoryEntry = (id: number) =>
  request<GeneratedCoverLetterEntry>(`/history/cover-letter/${id}`);

export const deleteCoverLetterHistoryEntry = (id: number) =>
  request<void>(`/history/cover-letter/${id}`, { method: 'DELETE' });
