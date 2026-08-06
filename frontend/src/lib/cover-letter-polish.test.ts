import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const layout = readFileSync(new URL('../routes/+layout.svelte', import.meta.url), 'utf8');
const page = readFileSync(
  new URL('../routes/cover-letter/+page.svelte', import.meta.url),
  'utf8',
);
const preview = readFileSync(
  new URL('./components/CoverLetterPreview.svelte', import.meta.url),
  'utf8',
);
const legacyFit = readFileSync(
  new URL('./components/FitAnalysisDisplay.svelte', import.meta.url),
  'utf8',
);

describe('cover letter visual polish', () => {
  test('uses a compact-balanced workspace with a larger result panel', () => {
    expect(layout).toContain("page.url.pathname === '/cover-letter'");
    expect(layout).toContain("'max-w-[80rem]'");
    expect(page).toContain('xl:grid-cols-[minmax(22rem,0.72fr)_minmax(0,1.28fr)]');
    expect(page).toContain('class="w-full space-y-6 pb-12"');
  });

  test('uses the role-match compatibility display without a nested card', () => {
    expect(page).toContain("RoleMatchFitAnalysisDisplay.svelte");
    expect(page).toContain('embedded={true}');
    expect(legacyFit).toContain("embedded = false");
    expect(legacyFit).toContain("embedded ? 'border-0 shadow-none'");
    expect(legacyFit).toContain('grid gap-4 2xl:grid-cols-2');
  });

  test('renders the generated letter at a focused document scale', () => {
    expect(page).toContain('max-w-[44rem]');
    expect(preview).toContain('text-[14px]');
    expect(preview).toContain('leading-6');
    expect(preview).toContain('max-w-[44rem]');
  });

  test('keeps one reanalysis action and gives long job fields enough room', () => {
    expect(page).toContain('onReanalyze={handleAnalyzeFit}');
    expect(page).not.toContain('>\n                Reanalyze\n              </Button>');
    expect(page.match(/class="space-y-1\.5 sm:col-span-2"/g)?.length).toBe(2);
    expect(page).toContain(
      'sm:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]',
    );
    expect(page).toContain('title={salary || undefined}');
    expect(page).toContain('class="text-xs tabular-nums"');
  });
});
