import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const config = readFileSync(new URL('../../svelte.config.js', import.meta.url), 'utf8');
const historyTab = readFileSync(
  new URL('./components/history/RoleMatchFitAnalysisTab.svelte', import.meta.url),
  'utf8',
);
const historyCard = readFileSync(
  new URL('./components/history/RoleMatchClCard.svelte', import.meta.url),
  'utf8',
);
const trackerCard = readFileSync(
  new URL('./components/tracker/RoleMatchApplicationCard.svelte', import.meta.url),
  'utf8',
);

describe('role match history and tracker', () => {
  test('routes existing component imports to source-aware wrappers', () => {
    expect(config).toContain(
      "'$lib/components/history/FitAnalysisTab.svelte': './src/lib/components/history/RoleMatchFitAnalysisTab.svelte'",
    );
    expect(config).toContain(
      "'$lib/components/history/ClCard.svelte': './src/lib/components/history/RoleMatchClCard.svelte'",
    );
    expect(config).toContain(
      "'$lib/components/tracker/ApplicationCard.svelte': './src/lib/components/tracker/RoleMatchApplicationCard.svelte'",
    );
  });

  test('history detail renders evidence analysis and preserves legacy detail', () => {
    expect(historyTab).toContain('<RoleMatchResult');
    expect(historyTab).toContain('<LegacyFitAnalysisTab');
  });

  test('score cards label the metric source', () => {
    for (const source of [historyCard, trackerCard]) {
      expect(source).toContain('Evidence match');
      expect(source).toContain('Legacy score');
      expect(source).toContain('match_score_source');
    }
  });
});
