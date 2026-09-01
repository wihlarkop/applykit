import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const personalInfoTab = readFileSync(
  new URL('./components/profile/PersonalInfoTab.svelte', import.meta.url),
  'utf8',
);
const cvPreview = readFileSync(
  new URL('./components/CvPreview.svelte', import.meta.url),
  'utf8',
);

describe('multiple GitHub links', () => {
  test('the personal info editor supports adding/removing GitHub links', () => {
    expect(personalInfoTab).toContain('addGithub');
    expect(personalInfoTab).toContain('removeGithub');
    expect(personalInfoTab).toContain('{#each profile.github as _, i}');
  });

  test('the live CV preview renders every GitHub link', () => {
    expect(cvPreview).toContain('profile.github.filter(Boolean)');
  });
});
