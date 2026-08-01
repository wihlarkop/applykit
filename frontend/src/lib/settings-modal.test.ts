import { describe, expect, test } from 'bun:test';

import {
  connectionTestMode,
  modalMode,
  modalTitle,
  primaryActionLabel,
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
