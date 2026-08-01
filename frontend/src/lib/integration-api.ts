import type { TestConnectionResponse } from '$lib/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export async function testConfiguredIntegration(
  providerId: string,
): Promise<TestConnectionResponse> {
  const response = await fetch(
    `${BASE_URL}/settings/integrations/${encodeURIComponent(providerId)}/test`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    },
  );

  if (!response.ok) {
    throw new Error('Configured integration test request failed.');
  }

  return response.json() as Promise<TestConnectionResponse>;
}
