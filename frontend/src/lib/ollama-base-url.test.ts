import { describe, expect, test } from 'bun:test';

import * as settingsModal from '$lib/settings-modal';

interface OllamaBaseUrlHelpers {
  normalizeOllamaBaseUrl?: (value: string) => string;
  ollamaBaseUrlError?: (value: string) => string | null;
}

const helpers = settingsModal as typeof settingsModal & OllamaBaseUrlHelpers;

describe('Ollama base URL', () => {
  test('normalizes surrounding whitespace and trailing slashes', () => {
    expect(typeof helpers.normalizeOllamaBaseUrl).toBe('function');
    if (!helpers.normalizeOllamaBaseUrl) return;

    expect(
      helpers.normalizeOllamaBaseUrl('  https://ollama.example.com///  '),
    ).toBe('https://ollama.example.com');
    expect(helpers.normalizeOllamaBaseUrl('http://localhost:11434/')).toBe(
      'http://localhost:11434',
    );
  });

  test('accepts HTTP and HTTPS endpoints', () => {
    expect(typeof helpers.ollamaBaseUrlError).toBe('function');
    if (!helpers.ollamaBaseUrlError) return;

    expect(helpers.ollamaBaseUrlError('http://localhost:11434')).toBeNull();
    expect(helpers.ollamaBaseUrlError('https://ollama.example.com')).toBeNull();
  });

  test('rejects missing schemes, unsupported schemes, and embedded credentials', () => {
    expect(typeof helpers.ollamaBaseUrlError).toBe('function');
    if (!helpers.ollamaBaseUrlError) return;

    expect(helpers.ollamaBaseUrlError('localhost:11434')).not.toBeNull();
    expect(helpers.ollamaBaseUrlError('ftp://ollama.example.com')).not.toBeNull();
    expect(
      helpers.ollamaBaseUrlError(
        'http://user:password@ollama.example.com:11434',
      ),
    ).not.toBeNull();
  });
});
