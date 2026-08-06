import { apiFetch } from './api-client';
import { parseApiError } from './api-error';
import type {
  AnalyzeRoleMatchRequest,
  ReanalyzeRoleMatchRequest,
  RoleMatchAnalysisResponse,
  RoleMatchComparisonResponse,
  RoleMatchOverridesRequest,
  RoleMatchVersionsResponse,
} from './role-match-types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function request<T>(
  path: string,
  options: RequestInit = {},
  fetchFn: typeof fetch = fetch,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await apiFetch(`${BASE_URL}${path}`, { ...options, headers }, fetchFn);
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    throw parseApiError(payload, 'Role match analysis could not be completed.', response.status);
  }
  return response.json() as Promise<T>;
}

export const analyzeRoleMatch = (
  data: AnalyzeRoleMatchRequest,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchAnalysisResponse>(
    '/analyze/role-match',
    { method: 'POST', body: JSON.stringify(data) },
    fetchFn,
  );

export const getRoleMatchAnalysis = (
  analysisId: number,
  fetchFn?: typeof fetch,
) => request<RoleMatchAnalysisResponse>(`/analyze/role-match/${analysisId}`, {}, fetchFn);

export const getRoleMatchVersions = (
  analysisId: number,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchVersionsResponse>(
    `/analyze/role-match/${analysisId}/versions`,
    {},
    fetchFn,
  );

export const compareRoleMatchVersions = (
  analysisId: number,
  otherAnalysisId: number,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchComparisonResponse>(
    `/analyze/role-match/${analysisId}/compare/${otherAnalysisId}`,
    {},
    fetchFn,
  );

export const reanalyzeRoleMatch = (
  analysisId: number,
  data: ReanalyzeRoleMatchRequest,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchAnalysisResponse>(
    `/analyze/role-match/${analysisId}/reanalyze`,
    { method: 'POST', body: JSON.stringify(data) },
    fetchFn,
  );

export const applyRoleMatchOverrides = (
  analysisId: number,
  data: RoleMatchOverridesRequest,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchAnalysisResponse>(
    `/analyze/role-match/${analysisId}/overrides`,
    { method: 'POST', body: JSON.stringify(data) },
    fetchFn,
  );

export const restoreRoleMatchOverride = (
  analysisId: number,
  overrideId: number,
  fetchFn?: typeof fetch,
) =>
  request<RoleMatchAnalysisResponse>(
    `/analyze/role-match/${analysisId}/overrides/${overrideId}`,
    { method: 'DELETE' },
    fetchFn,
  );
