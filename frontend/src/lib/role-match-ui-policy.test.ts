import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const files = [
  './components/role-match/RoleMatchSummary.svelte',
  './components/role-match/RoleMatchInsights.svelte',
  './components/role-match/RoleMatchBreakdown.svelte',
  './components/role-match/AnalysisNeedsReview.svelte',
];
const source = files
  .map((path) => readFileSync(new URL(path, import.meta.url), 'utf8'))
  .join('\n');

describe('role match UI policy', () => {
  test('contains the approved information hierarchy', () => {
    for (const phrase of [
      'What makes you a good fit',
      'What may hold you back',
      'Your best next step',
      'See detailed breakdown',
      'How this assessment works',
      'Analysis needs review',
    ]) {
      expect(source).toContain(phrase);
    }
  });

  test('does not expose internal engine language in the main UI', () => {
    for (const forbidden of [
      'raw_score',
      'soft cap',
      'unsupported essential',
      'contradictory evidence',
      'AI Suggested Emphasis',
      'bg-gradient-to',
    ]) {
      expect(source).not.toContain(forbidden);
    }
  });
});
