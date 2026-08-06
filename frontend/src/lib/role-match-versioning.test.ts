import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const source = readFileSync(
  new URL('./components/role-match/RoleMatchVersionCompare.svelte', import.meta.url),
  'utf8',
);
const legacySource = readFileSync(
  new URL('./components/role-match/LegacyFitAnalysisNotice.svelte', import.meta.url),
  'utf8',
);

describe('role match versioning UI', () => {
  test('shows safe carry-forward states and restoration', () => {
    for (const phrase of [
      'Carried forward',
      'Needs review',
      'Not applicable',
      'Restore original analysis',
      'Your match increased from',
    ]) {
      expect(source).toContain(phrase);
    }
  });

  test('clearly labels old model-generated results', () => {
    expect(legacySource).toContain('Legacy AI fit score');
    expect(legacySource).toContain('before evidence-based scoring was introduced');
  });
});
