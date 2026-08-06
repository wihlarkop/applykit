import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const source = readFileSync(
  new URL('./components/role-match/RoleMatchReviewPanel.svelte', import.meta.url),
  'utf8',
);

describe('role match review UI', () => {
  test('supports the approved review corrections', () => {
    for (const phrase of [
      'Change requirement priority',
      'I don’t have this experience',
      'Not included in my profile',
      'Unlink this evidence',
      'Reason for this correction',
      'Save correction',
    ]) {
      expect(source).toContain(phrase);
    }
  });

  test('does not silently add analysis notes to the profile', () => {
    expect(source).toContain('This correction only changes this analysis');
    expect(source).toContain('Add this evidence to my profile separately');
  });
});
