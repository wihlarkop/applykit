import type {
  CreateProviderCredentialRequest,
  CredentialPolicyResponse,
  CredentialStrategy,
  ProviderCredentialInfo,
  ProviderCredentialsResponse,
  UpdateProviderCredentialRequest,
} from '$lib/provider-credential-types';
import type { TestConnectionResponse } from '$lib/types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = 'Credential request failed.';
    try {
      const payload = (await response.json()) as {
        detail?: string;
        error?: { message?: string };
      };
      message = payload.error?.message ?? payload.detail ?? message;
    } catch {
      // Keep the stable fallback instead of exposing an unreadable response body.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function providerPath(providerId: string): string {
  return `/settings/integrations/${encodeURIComponent(providerId)}`;
}

export async function testConfiguredIntegration(
  providerId: string,
): Promise<TestConnectionResponse> {
  return requestJson<TestConnectionResponse>(`${providerPath(providerId)}/test`, {
    method: 'POST',
  });
}

export async function getProviderCredentials(
  providerId: string,
): Promise<ProviderCredentialsResponse> {
  return requestJson<ProviderCredentialsResponse>(
    `${providerPath(providerId)}/credentials`,
  );
}

export async function addProviderCredential(
  providerId: string,
  request: CreateProviderCredentialRequest,
): Promise<ProviderCredentialInfo> {
  return requestJson<ProviderCredentialInfo>(
    `${providerPath(providerId)}/credentials`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );
}

export async function updateProviderCredential(
  providerId: string,
  credentialId: number,
  request: UpdateProviderCredentialRequest,
): Promise<ProviderCredentialInfo> {
  return requestJson<ProviderCredentialInfo>(
    `${providerPath(providerId)}/credentials/${credentialId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(request),
    },
  );
}

export async function activateProviderCredential(
  providerId: string,
  credentialId: number,
): Promise<ProviderCredentialInfo> {
  return requestJson<ProviderCredentialInfo>(
    `${providerPath(providerId)}/credentials/${credentialId}/activate`,
    { method: 'PUT' },
  );
}

export async function testProviderCredential(
  providerId: string,
  credentialId: number,
): Promise<TestConnectionResponse> {
  return requestJson<TestConnectionResponse>(
    `${providerPath(providerId)}/credentials/${credentialId}/test`,
    { method: 'POST' },
  );
}

export async function deleteProviderCredential(
  providerId: string,
  credentialId: number,
): Promise<ProviderCredentialsResponse> {
  return requestJson<ProviderCredentialsResponse>(
    `${providerPath(providerId)}/credentials/${credentialId}`,
    { method: 'DELETE' },
  );
}

export async function getCredentialPolicy(
  providerId: string,
): Promise<CredentialPolicyResponse> {
  return requestJson<CredentialPolicyResponse>(
    `${providerPath(providerId)}/credential-policy`,
  );
}

export async function updateCredentialPolicy(
  providerId: string,
  strategy: CredentialStrategy,
  maxAttempts: number,
): Promise<CredentialPolicyResponse> {
  return requestJson<CredentialPolicyResponse>(
    `${providerPath(providerId)}/credential-policy`,
    {
      method: 'PUT',
      body: JSON.stringify({
        strategy,
        max_attempts: maxAttempts,
      }),
    },
  );
}
