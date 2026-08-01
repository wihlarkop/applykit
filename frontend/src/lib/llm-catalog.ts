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
  supports_custom_models: boolean;
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

export function customModelValidationError(providerId: string, modelId: string): string | null {
  const normalized = modelId.trim();
  if (!normalized) return 'Enter a model ID.';
  if (normalized.length > 200) return 'Model ID must be at most 200 characters.';
  if (/\s/.test(normalized)) return 'Model ID cannot contain spaces or line breaks.';
  if (!normalized.startsWith(`${providerId}/`)) {
    return `Model ID must start with ${providerId}/.`;
  }
  if (normalized === `${providerId}/`) return 'Enter a model name after the provider prefix.';
  return null;
}

export function isCustomModel(
  provider: Pick<CatalogProviderInfo, 'supports_custom_models' | 'models'> | undefined,
  modelId: string,
): boolean {
  return Boolean(
    provider?.supports_custom_models &&
      modelId &&
      !provider.models.some((model) => model.value === modelId),
  );
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
