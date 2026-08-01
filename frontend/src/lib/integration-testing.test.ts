import { describe, expect, test } from 'bun:test';

import {
  connectedIntegrations,
  testConnectedIntegrations,
  type IntegrationTestState,
} from '$lib/integration-testing';
import type { IntegrationInfo } from '$lib/types';

const integrations: IntegrationInfo[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    is_active: true,
    api_key_configured: true,
    masked_api_key: 'sk••••••••key',
    current_model: 'openai/gpt-5-mini',
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    is_active: false,
    api_key_configured: false,
    masked_api_key: null,
    current_model: null,
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
    id: 'anthropic',
    label: 'Anthropic Claude',
    is_active: false,
    api_key_configured: true,
    masked_api_key: 'sk••••••••key',
    current_model: 'anthropic/claude-haiku-4-5-20251001',
  },
];

describe('connectedIntegrations', () => {
  test('includes configured API providers and Ollama with a selected model', () => {
    expect(connectedIntegrations(integrations).map((item) => item.id)).toEqual([
      'openai',
      'ollama',
      'anthropic',
    ]);
  });
});

describe('testConnectedIntegrations', () => {
  test('tests every connected provider and returns a summary', async () => {
    const states: Record<string, IntegrationTestState> = {};

    const summary = await testConnectedIntegrations(
      integrations,
      async (providerId) => ({
        ok: providerId !== 'anthropic',
        message: providerId === 'anthropic' ? 'Provider connection failed.' : 'Connection successful.',
      }),
      (providerId, state) => {
        states[providerId] = state;
      },
    );

    expect(summary).toEqual({ total: 3, passed: 2, failed: 1 });
    expect(states.openai.status).toBe('success');
    expect(states.ollama.status).toBe('success');
    expect(states.anthropic.status).toBe('failure');
    expect(states.gemini).toBeUndefined();
  });

  test('runs at most three provider tests concurrently', async () => {
    let active = 0;
    let peak = 0;
    const many = Array.from({ length: 7 }, (_, index): IntegrationInfo => ({
      id: `provider-${index}`,
      label: `Provider ${index}`,
      is_active: false,
      api_key_configured: true,
      masked_api_key: null,
      current_model: `provider-${index}/model`,
    }));

    await testConnectedIntegrations(
      many,
      async () => {
        active += 1;
        peak = Math.max(peak, active);
        await new Promise((resolve) => setTimeout(resolve, 5));
        active -= 1;
        return { ok: true, message: 'Connection successful.' };
      },
      () => undefined,
    );

    expect(peak).toBeLessThanOrEqual(3);
  });
});
