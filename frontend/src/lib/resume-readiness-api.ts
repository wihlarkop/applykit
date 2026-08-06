import { apiFetch } from './api-client';
import { parseApiError } from './api-error';
import type {
  CreateResumeReadinessRequest,
  ResumeReadinessListResponse,
  ResumeReadinessResponse,
} from './resume-readiness-types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function parseError(response: Response, fallback: string): Promise<never> {
  const payload: unknown = await response.json().catch(() => undefined);
  throw parseApiError(payload, fallback, response.status);
}

export async function createResumeReadinessAnalysis(
  request: CreateResumeReadinessRequest,
): Promise<ResumeReadinessResponse> {
  const response = await apiFetch(`${BASE_URL}/resume-readiness/analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    await parseError(response, 'Could not analyze this resume.');
  }
  return response.json() as Promise<ResumeReadinessResponse>;
}

export async function getResumeReadinessAnalysis(
  analysisId: number,
): Promise<ResumeReadinessResponse> {
  const response = await apiFetch(
    `${BASE_URL}/resume-readiness/analyses/${analysisId}`,
  );
  if (!response.ok) {
    await parseError(response, 'Could not load the Resume Readiness analysis.');
  }
  return response.json() as Promise<ResumeReadinessResponse>;
}

export async function getLatestResumeReadiness(
  generatedCvId: number,
): Promise<ResumeReadinessResponse | null> {
  const response = await apiFetch(
    `${BASE_URL}/generated-cvs/${generatedCvId}/resume-readiness/latest`,
  );
  if (response.status === 404) return null;
  if (!response.ok) {
    await parseError(response, 'Could not load the latest Resume Readiness analysis.');
  }
  return response.json() as Promise<ResumeReadinessResponse>;
}

export async function listResumeReadinessAnalyses(
  generatedCvId: number,
): Promise<ResumeReadinessListResponse> {
  const response = await apiFetch(
    `${BASE_URL}/generated-cvs/${generatedCvId}/resume-readiness`,
  );
  if (!response.ok) {
    await parseError(response, 'Could not load Resume Readiness history.');
  }
  return response.json() as Promise<ResumeReadinessListResponse>;
}
