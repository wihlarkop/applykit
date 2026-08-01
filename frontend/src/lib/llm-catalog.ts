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
  credential_url: string | null;
  models: CatalogModelOption[];
}

export interface CatalogModelFilters {
  statuses: ReadonlySet<ModelStatus>;
  freeTier: boolean;
  reasoning: boolean;
  structuredOutput: boolean;
}

export function credentialActionLabel(authType: ProviderAuthType): string {
  return authType === 'token' ? 'Get access token' : 'Get API key';
}

export function filterCatalogModels(
  models: readonly CatalogModelOption[],
  query: string,
  filters: CatalogModelFilters,
): CatalogModelOption[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();

  return models.filter((model) => {
    if (
      normalizedQuery &&
      !`${model.label} ${model.value}`.toLocaleLowerCase().includes(normalizedQuery)
    ) {
      return false;
    }

    if (filters.statuses.size > 0 && !filters.statuses.has(model.status)) {
      return false;
    }
    if (filters.freeTier && !model.free_tier) {
      return false;
    }
    if (filters.reasoning && !model.traits.includes('reasoning')) {
      return false;
    }
    if (filters.structuredOutput && !model.capabilities.includes('structured_output')) {
      return false;
    }

    return true;
  });
}
