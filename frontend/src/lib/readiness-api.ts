import { apiFetch } from '$lib/api-client';
import { parseApiError } from '$lib/api-error';
import type { ReadinessResponse } from '$lib/readiness-types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function requestReadiness(
  path: string,
  options: RequestInit = {},
  fetchFn: typeof fetch = fetch,
): Promise<ReadinessResponse> {
  const response = await apiFetch(
    `${BASE_URL}${path}`,
    {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
      },
    },
    fetchFn,
  );
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    throw parseApiError(payload, 'Could not load ApplyKit readiness.', response.status);
  }
  return response.json() as Promise<ReadinessResponse>;
}

export function getReadiness(
  profileId: number,
  fetchFn: typeof fetch = fetch,
): Promise<ReadinessResponse> {
  return requestReadiness(
    `/readiness?profile_id=${encodeURIComponent(profileId)}`,
    {},
    fetchFn,
  );
}

function mutateReadiness(
  path: string,
  profileId: number,
  fetchFn: typeof fetch = fetch,
): Promise<ReadinessResponse> {
  return requestReadiness(
    path,
    {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    },
    fetchFn,
  );
}

export const skipOnboarding = (profileId: number, fetchFn: typeof fetch = fetch) =>
  mutateReadiness('/readiness/onboarding/skip', profileId, fetchFn);

export const completeOnboarding = (profileId: number, fetchFn: typeof fetch = fetch) =>
  mutateReadiness('/readiness/onboarding/complete', profileId, fetchFn);

export const dismissReadinessChecklist = (
  profileId: number,
  fetchFn: typeof fetch = fetch,
) => mutateReadiness('/readiness/checklist/dismiss', profileId, fetchFn);
