import type { ModelOption, ProviderInfo } from '$lib/types';

export type ModelStatus = 'stable' | 'preview' | 'experimental';
export type ProviderAuthType = 'api_key' | 'token' | 'none';

export interface CatalogModelOption extends ModelOption {
  status: ModelStatus;
  capabilities: string[];
  traits: string[];
  free_tier: boolean;
}

export interface CatalogProviderInfo extends Omit<ProviderInfo, 'models'> {
  auth_type: ProviderAuthType;
  local: boolean;
  models: CatalogModelOption[];
}
