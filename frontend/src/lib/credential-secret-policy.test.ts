import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const settingsModal = readFileSync(
  new URL('./components/SettingsModal.svelte', import.meta.url),
  'utf8',
);
const credentialsPanel = readFileSync(
  new URL('./components/ProviderCredentialsPanel.svelte', import.meta.url),
  'utf8',
);

describe('credential secret policy', () => {
  test('credential components never use browser persistence or secret logging', () => {
    for (const source of [settingsModal, credentialsPanel]) {
      expect(source).not.toMatch(/\blocalStorage\b/);
      expect(source).not.toMatch(/\bsessionStorage\b/);
      expect(source).not.toMatch(
        /console\.(log|debug|info|warn|error)\([^)]*(apiKey|secret|credential)/i,
      );
    }
  });

  test('secret inputs use password-manager-safe attributes', () => {
    expect(settingsModal).toContain('autocomplete="new-password"');
    expect(credentialsPanel).toContain('autocomplete="new-password"');
  });

  test('components contain explicit secret reset paths', () => {
    expect(settingsModal).toContain("apiKey = ''");
    expect(credentialsPanel).toContain("newSecret = ''");
    expect(credentialsPanel).toContain("editValue = ''");
  });
});
