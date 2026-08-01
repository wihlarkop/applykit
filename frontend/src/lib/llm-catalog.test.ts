import { describe, expect, test } from 'bun:test';

import {
  credentialActionLabel,
  customModelValidationError,
  filterCatalogModels,
  isCustomModel,
  type CatalogModelFilters,
  type CatalogModelOption,
} from '$lib/llm-catalog';

const models: CatalogModelOption[] = [
  {
    value: 'openai/gpt-5-mini',
    label: 'GPT-5 Mini',
    status: 'stable',
    capabilities: ['text', 'streaming', 'structured_output'],
    traits: ['fast', 'low_cost', 'reasoning'],
    free_tier: false,
  },
  {
    value: 'gemini/gemini-3-flash-preview',
    label: 'Gemini 3 Flash Preview',
    status: 'preview',
    capabilities: ['text', 'streaming', 'structured_output'],
    traits: ['fast', 'reasoning'],
    free_tier: true,
  },
  {
    value: 'ollama/llama3.2',
    label: 'Llama 3.2',
    status: 'stable',
    capabilities: ['text', 'streaming'],
    traits: ['local'],
    free_tier: false,
  },
];

const noFilters: CatalogModelFilters = {
  statuses: new Set(),
  freeTier: false,
  reasoning: false,
  structuredOutput: false,
};

describe('credentialActionLabel', () => {
  test('uses token-specific copy only for token providers', () => {
    expect(credentialActionLabel('token')).toBe('Get access token');
    expect(credentialActionLabel('api_key')).toBe('Get API key');
  });
});

describe('custom model helpers', () => {
  test('accepts provider-prefixed IDs and rejects invalid input', () => {
    expect(customModelValidationError('ollama', 'ollama/qwen3:14b')).toBeNull();
    expect(customModelValidationError('openrouter', 'openrouter/google/gemini-2.5-flash')).toBeNull();
    expect(customModelValidationError('openrouter', 'google/gemini')).toContain('openrouter/');
    expect(customModelValidationError('ollama', 'ollama/model with spaces')).toContain('spaces');
  });

  test('recognizes non-catalog selections only for supported providers', () => {
    expect(
      isCustomModel(
        { supports_custom_models: true, models },
        'ollama/qwen3:14b',
      ),
    ).toBe(true);
    expect(
      isCustomModel(
        { supports_custom_models: false, models },
        'openai/not-in-catalog',
      ),
    ).toBe(false);
    expect(
      isCustomModel(
        { supports_custom_models: true, models },
        'ollama/llama3.2',
      ),
    ).toBe(false);
  });
});

describe('filterCatalogModels', () => {
  test('searches case-insensitively by label and model ID', () => {
    expect(filterCatalogModels(models, 'gPt-5', noFilters).map((model) => model.value)).toEqual([
      'openai/gpt-5-mini',
    ]);
    expect(filterCatalogModels(models, 'gemini-3-flash', noFilters).map((model) => model.value)).toEqual([
      'gemini/gemini-3-flash-preview',
    ]);
  });

  test('combines status and metadata filters with AND semantics', () => {
    const filters: CatalogModelFilters = {
      statuses: new Set(['preview']),
      freeTier: true,
      reasoning: true,
      structuredOutput: true,
    };

    expect(filterCatalogModels(models, '', filters).map((model) => model.value)).toEqual([
      'gemini/gemini-3-flash-preview',
    ]);
  });

  test('supports multiple selected statuses with OR semantics', () => {
    const filters: CatalogModelFilters = {
      ...noFilters,
      statuses: new Set(['stable', 'preview']),
    };

    expect(filterCatalogModels(models, '', filters)).toHaveLength(3);
  });

  test('returns models in their existing catalog order', () => {
    expect(filterCatalogModels(models, '', noFilters).map((model) => model.label)).toEqual([
      'GPT-5 Mini',
      'Gemini 3 Flash Preview',
      'Llama 3.2',
    ]);
  });
});
