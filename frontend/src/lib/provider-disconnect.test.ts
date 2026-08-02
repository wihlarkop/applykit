import { describe, expect, test } from 'bun:test';

import * as settingsIntegrations from '$lib/settings-integrations';
import type { IntegrationInfo } from '$lib/types';

const activeProvider: IntegrationInfo = {
  id: 'groq',
  label: 'Groq',
  is_active: true,
  api_key_configured: true,
  masked_api_key: 'gsk_••••••••',
  current_model: 'groq/openai/gpt-oss-20b',
};

const localProvider: IntegrationInfo = {
  id: 'ollama',
  label: 'Ollama',
  is_active: false,
  api_key_configured: false,
  masked_api_key: null,
  current_model: 'ollama/llama3.2',
};

describe('provider disconnect availability', () => {
  test('allows disconnecting active, credential-backed, and local providers', () => {
    const helper = (
      settingsIntegrations as typeof settingsIntegrations & {
        canDisconnectIntegration?: (integration: IntegrationInfo) => boolean;
      }
    ).canDisconnectIntegration;

    expect(typeof helper).toBe('function');
    if (!helper) return;

    expect(helper(activeProvider)).toBe(true);
    expect(helper({ ...activeProvider, is_active: false })).toBe(true);
    expect(helper(localProvider)).toBe(true);
  });

  test('does not offer disconnect for an unconfigured provider', () => {
    const helper = (
      settingsIntegrations as typeof settingsIntegrations & {
        canDisconnectIntegration?: (integration: IntegrationInfo) => boolean;
      }
    ).canDisconnectIntegration;

    expect(typeof helper).toBe('function');
    if (!helper) return;

    expect(
      helper({
        id: 'gemini',
        label: 'Google Gemini',
        is_active: false,
        api_key_configured: false,
        masked_api_key: null,
        current_model: null,
      }),
    ).toBe(false);
  });
});
