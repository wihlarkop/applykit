import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const page = readFileSync(
  new URL('../routes/cover-letter/+page.svelte', import.meta.url),
  'utf8',
);

describe('cover letter hybrid workflow', () => {
  test('starts with URL import and exposes accessible input modes', () => {
    expect(page).toContain("let inputTab = $state<'paste' | 'url'>('url');");
    expect(page).toContain("aria-pressed={inputTab === 'url'}");
    expect(page).toContain("aria-pressed={inputTab === 'paste'}");
    expect(page).toContain('Import job');
    expect(page).toContain('Extract details');
  });

  test('uses a balanced staged layout instead of an empty preview canvas', () => {
    expect(page).toContain('data-cover-letter-layout="hybrid"');
    expect(page).toContain('Add the job');
    expect(page).toContain('What happens next?');
    expect(page).toContain('Job details');
    expect(page).toContain('Change job');
  });

  test('separates fit review from writing and preview actions', () => {
    expect(page).toContain("let resultView = $state<'fit' | 'letter'>('fit');");
    expect(page).toContain('Writing preferences');
    expect(page).toContain('Generate without fit review');
    expect(page).toContain('Cover Letter');
    expect(page).toContain('Fit Review');
    expect(page).toContain('<CoverLetterPreview text={coverLetterText} />');
    expect(page).toContain('<FitAnalysisDisplay');
  });
});
