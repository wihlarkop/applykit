import type { IntegrationInfo } from '$lib/types';

export type CredentialStrategy = 'manual' | 'failover' | 'round_robin';

export interface CredentialIntegrationInfo extends IntegrationInfo {
  credential_count: number;
  active_credential_id: number | null;
  active_credential_label: string | null;
  credential_strategy: CredentialStrategy;
}

export interface ProviderCredentialInfo {
  id: number;
  provider_id: string;
  label: string;
  masked_secret: string;
  is_active: boolean;
  is_enabled: boolean;
  priority: number;
  health_status: string;
  cooldown_until: string | null;
  last_tested_at: string | null;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderCredentialsResponse {
  provider_id: string;
  credentials: ProviderCredentialInfo[];
  max_credentials: number;
}

export interface CredentialPolicyResponse {
  provider_id: string;
  strategy: CredentialStrategy;
  max_attempts: number;
}

export interface CreateProviderCredentialRequest {
  label: string;
  secret: string;
  activate?: boolean;
}

export interface UpdateProviderCredentialRequest {
  label?: string;
  secret?: string;
}
