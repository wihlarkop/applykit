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

  test('cancelling or changing providers clears the add-credential draft', () => {
    expect(credentialsPanel).toContain('function closeAddForm()');
    expect(credentialsPanel).toContain('function toggleAddForm()');
    expect(credentialsPanel).toContain('onclick={toggleAddForm}');
    expect(credentialsPanel).not.toContain('onclick={() => (addOpen = !addOpen)}');
    expect(credentialsPanel).toMatch(
      /async function loadData\(\)[\s\S]*?closeAddForm\(\);[\s\S]*?closeEditor\(\);/,
    );
  });
});
