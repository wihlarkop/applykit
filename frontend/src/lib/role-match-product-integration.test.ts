import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const config = readFileSync(new URL('../../svelte.config.js', import.meta.url), 'utf8');
const apiCompat = readFileSync(new URL('./api-compat.ts', import.meta.url), 'utf8');
const display = readFileSync(
  new URL('./components/RoleMatchFitAnalysisDisplay.svelte', import.meta.url),
  'utf8',
);

describe('role match product compatibility', () => {
  test('redirects existing imports through compatibility modules', () => {
    expect(config).toContain("'$lib/api': './src/lib/api-compat.ts'");
    expect(config).toContain(
      "'$lib/components/FitAnalysisDisplay.svelte': './src/lib/components/RoleMatchFitAnalysisDisplay.svelte'",
    );
  });

  test('replaces legacy fit analysis with role match analysis', () => {
    expect(apiCompat).toContain('analyzeRoleMatch');
    expect(apiCompat).toContain('role_match_analysis_id');
    expect(apiCompat).toContain('role_match_analysis: analysis');
    expect(apiCompat).not.toContain("request<FitAnalysisResponse>('/analyze/fit'");
  });

  test('uses verified cover letter generation when an analysis id exists', () => {
    expect(apiCompat).toContain("'/generate/cover-letter/role-match'");
    expect(apiCompat).toContain('legacyGenerateCoverLetterStream(data)');
    expect(apiCompat).toContain('delete payload.match_score');
    expect(apiCompat).toContain('delete payload.fit_context');
  });

  test('renders new and legacy analysis through one stable component import', () => {
    expect(display).toContain('<RoleMatchResult');
    expect(display).toContain('<RoleMatchReviewPanel');
    expect(display).toContain('<RoleMatchVersionCompare');
    expect(display).toContain('<LegacyFitAnalysisDisplay');
  });
});
