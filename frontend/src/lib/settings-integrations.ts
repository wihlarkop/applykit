import type { CatalogProviderInfo } from '$lib/llm-catalog';
import type { IntegrationInfo } from '$lib/types';

export type IntegrationModelKind = 'catalog' | 'custom' | 'unavailable';

export interface IntegrationGroups {
  connected: IntegrationInfo[];
  available: IntegrationInfo[];
}

export interface SettingsOverview {
  active: IntegrationInfo | null;
  connectedCount: number;
  credentialCount: number;
}

export function isConfiguredIntegration(integration: IntegrationInfo): boolean {
  return (
    integration.api_key_configured ||
    (integration.id === 'ollama' && Boolean(integration.current_model))
  );
}

export function groupIntegrations(
  integrations: IntegrationInfo[],
): IntegrationGroups {
  const connected: IntegrationInfo[] = [];
  const available: IntegrationInfo[] = [];

  for (const integration of integrations) {
    if (isConfiguredIntegration(integration)) {
      connected.push(integration);
    } else {
      available.push(integration);
    }
  }

  connected.sort((left, right) => {
    if (left.is_active !== right.is_active) {
      return left.is_active ? -1 : 1;
    }
    return left.label.localeCompare(right.label);
  });

  return { connected, available };
}

export function integrationModelKind(
  integration: IntegrationInfo,
  providers: CatalogProviderInfo[],
): IntegrationModelKind | null {
  if (!integration.current_model) return null;

  const provider = providers.find((item) => item.id === integration.id);
  if (provider?.models.some((model) => model.value === integration.current_model)) {
    return 'catalog';
  }
  if (provider?.supports_custom_models) {
    return 'custom';
  }
  return 'unavailable';
}

export function settingsOverview(
  integrations: IntegrationInfo[],
): SettingsOverview {
  const connectedCount = integrations.filter(isConfiguredIntegration).length;
  const credentialCount = integrations.filter(
    (integration) => integration.api_key_configured,
  ).length;

  return {
    active: integrations.find((integration) => integration.is_active) ?? null,
    connectedCount,
    credentialCount,
  };
}
