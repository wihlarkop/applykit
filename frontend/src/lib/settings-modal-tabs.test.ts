import { describe, expect, test } from 'bun:test';

import {
  defaultSettingsTab,
  footerActionForTab,
  type ProviderSettingsTab,
} from './settings-modal-tabs';

describe('provider settings modal tabs', () => {
  test('connected remote providers open on credentials', () => {
    expect(defaultSettingsTab({ isExistingProvider: true, requiresCredential: true })).toBe(
      'credentials',
    );
  });

  test('new and local providers open on model', () => {
    expect(defaultSettingsTab({ isExistingProvider: false, requiresCredential: true })).toBe(
      'model',
    );
    expect(defaultSettingsTab({ isExistingProvider: true, requiresCredential: false })).toBe(
      'model',
    );
  });

  test('each tab has a clear footer action', () => {
    const cases: Array<[ProviderSettingsTab, string]> = [
      ['model', 'Save model changes'],
      ['credentials', 'Done'],
      ['routing', 'Save routing settings'],
    ];

    for (const [tab, label] of cases) {
      expect(footerActionForTab(tab)).toBe(label);
    }
  });
});
