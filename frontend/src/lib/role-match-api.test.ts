import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('./role-match-api.ts', import.meta.url), 'utf8');

describe('role match API contract', () => {
  test('exposes all versioned analysis operations', () => {
    expect(source).toContain("'/analyze/role-match'");
    expect(source).toContain('`/analyze/role-match/${analysisId}`');
    expect(source).toContain('`/analyze/role-match/${analysisId}/versions`');
    expect(source).toContain('`/analyze/role-match/${analysisId}/compare/${otherAnalysisId}`');
    expect(source).toContain('`/analyze/role-match/${analysisId}/reanalyze`');
    expect(source).toContain('`/analyze/role-match/${analysisId}/overrides`');
    expect(source).toContain('`/analyze/role-match/${analysisId}/overrides/${overrideId}`');
  });

  test('uses POST for analysis and DELETE for restoration', () => {
    expect(source).toContain('export const analyzeRoleMatch');
    expect(source).toContain("method: 'POST'");
    expect(source).toContain('export const restoreRoleMatchOverride');
    expect(source).toContain("method: 'DELETE'");
  });
});
