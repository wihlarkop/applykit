import { describe, expect, test } from 'bun:test';

import type { CatalogProviderInfo } from '$lib/llm-catalog';
import {
  groupIntegrations,
  integrationModelKind,
  settingsOverview,
} from '$lib/settings-integrations';
import type { IntegrationInfo } from '$lib/types';

const integrations: IntegrationInfo[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    is_active: true,
    api_key_configured: true,
    masked_api_key: 'sk-a••••••••z9',
    current_model: 'openai/gpt-5-mini',
  },
  {
    id: 'ollama',
    label: 'Ollama',
    is_active: false,
    api_key_configured: false,
    masked_api_key: null,
    current_model: 'ollama/qwen3:14b',
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    is_active: false,
    api_key_configured: false,
    masked_api_key: null,
    current_model: null,
  },
];

const providers: CatalogProviderInfo[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    auth_type: 'api_key',
    local: false,
    credential_url: 'https://platform.openai.com/api-keys',
    supports_custom_models: false,
    requires_api_key: true,
    models: [
      {
        value: 'openai/gpt-5-mini',
        label: 'GPT-5 Mini',
        status: 'stable',
        capabilities: ['text'],
        traits: ['fast'],
        free_tier: false,
      },
    ],
  },
  {
    id: 'ollama',
    label: 'Ollama',
    auth_type: 'none',
    local: true,
    credential_url: null,
    supports_custom_models: true,
    requires_api_key: false,
    models: [
      {
        value: 'ollama/llama3.2',
        label: 'Llama 3.2',
        status: 'stable',
        capabilities: ['text'],
        traits: ['local'],
        free_tier: false,
      },
    ],
  },
];

describe('groupIntegrations', () => {
  test('separates configured providers from providers that are available to connect', () => {
    const grouped = groupIntegrations(integrations);

    expect(grouped.connected.map((integration) => integration.id)).toEqual([
      'openai',
      'ollama',
    ]);
    expect(grouped.available.map((integration) => integration.id)).toEqual([
      'gemini',
    ]);
  });

  test('keeps the active provider first and sorts remaining connected providers by label', () => {
    const grouped = groupIntegrations([
      { ...integrations[1], label: 'Zulu Local' },
      { ...integrations[0], is_active: false, label: 'Alpha AI' },
      {
        ...integrations[0],
        id: 'anthropic',
        label: 'Anthropic Claude',
        is_active: true,
      },
    ]);

    expect(grouped.connected.map((integration) => integration.label)).toEqual([
      'Anthropic Claude',
      'Alpha AI',
      'Zulu Local',
    ]);
  });
});

describe('integrationModelKind', () => {
  test('distinguishes catalog, custom, unavailable, and missing models', () => {
    expect(integrationModelKind(integrations[0], providers)).toBe('catalog');
    expect(integrationModelKind(integrations[1], providers)).toBe('custom');
    expect(
      integrationModelKind(
        { ...integrations[0], current_model: 'openai/legacy-model' },
        providers,
      ),
    ).toBe('unavailable');
    expect(
      integrationModelKind(
        { ...integrations[0], current_model: null },
        providers,
      ),
    ).toBeNull();
  });
});

describe('settingsOverview', () => {
  test('returns the active integration and useful configuration counts', () => {
    const overview = settingsOverview(integrations);

    expect(overview.active?.id).toBe('openai');
    expect(overview.connectedCount).toBe(2);
    expect(overview.credentialCount).toBe(1);
  });
});
