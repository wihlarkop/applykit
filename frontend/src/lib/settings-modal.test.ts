import { describe, expect, test } from 'bun:test';

import {
  connectionTestMode,
  modalMode,
  modalTitle,
  primaryActionLabel,
  saveSettingsWithRefresh,
  type SettingsSaveResult,
} from '$lib/settings-modal';

describe('settings modal presentation', () => {
  test('distinguishes connect and edit flows', () => {
    expect(modalMode('', '', false)).toBe('connect');
    expect(modalMode('openai', '', false)).toBe('connect');
    expect(modalMode('openai', 'openai/gpt-5-mini', false)).toBe('edit');
    expect(modalMode('openai', '', true)).toBe('edit');
  });

  test('uses provider-specific titles', () => {
    expect(modalTitle('connect', 'OpenAI')).toBe('Connect OpenAI');
    expect(modalTitle('edit', 'OpenAI')).toBe('Edit OpenAI');
    expect(modalTitle('connect', '')).toBe('Connect AI provider');
  });

  test('keeps activation as the primary outcome unless already active', () => {
    expect(primaryActionLabel('connect', false)).toBe('Save & set active');
    expect(primaryActionLabel('edit', false)).toBe('Save & set active');
    expect(primaryActionLabel('edit', true)).toBe('Save changes');
  });
});

describe('connection testing mode', () => {
  test('uses a newly entered credential when present', () => {
    expect(
      connectionTestMode({
        requiresApiKey: true,
        apiKey: 'new-secret',
        canReuseStoredKey: true,
        providerId: 'openai',
      }),
    ).toBe('draft');
  });

  test('uses the saved backend credential when the edit field is empty', () => {
    expect(
      connectionTestMode({
        requiresApiKey: true,
        apiKey: '',
        canReuseStoredKey: true,
        providerId: 'openai',
      }),
    ).toBe('stored');
  });

  test('allows keyless providers and disables missing credentials', () => {
    expect(
      connectionTestMode({
        requiresApiKey: false,
        apiKey: '',
        canReuseStoredKey: false,
        providerId: 'ollama',
      }),
    ).toBe('draft');
    expect(
      connectionTestMode({
        requiresApiKey: true,
        apiKey: '',
        canReuseStoredKey: false,
        providerId: 'openai',
      }),
    ).toBe('disabled');
  });
});

describe('settings save refresh flow', () => {
  test('refreshes the parent after persistence succeeds', async () => {
    const calls: string[] = [];

    const result = await saveSettingsWithRefresh(
      async () => {
        calls.push('persist');
      },
      async () => {
        calls.push('refresh');
      },
    );

    expect(result).toEqual({ status: 'saved' } satisfies SettingsSaveResult);
    expect(calls).toEqual(['persist', 'refresh']);
  });

  test('does not refresh when persistence fails', async () => {
    const error = new Error('save failed');
    let refreshCalls = 0;

    const result = await saveSettingsWithRefresh(
      async () => {
        throw error;
      },
      async () => {
        refreshCalls += 1;
      },
    );

    expect(result).toEqual({ status: 'save_failed', error });
    expect(refreshCalls).toBe(0);
  });

  test('reports a refresh failure after persistence succeeds', async () => {
    const error = new Error('refresh failed');

    const result = await saveSettingsWithRefresh(
      async () => undefined,
      async () => {
        throw error;
      },
    );

    expect(result).toEqual({ status: 'refresh_failed', error });
  });
});
