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
  test('widens only the cover letter workspace and gives the result panel more room', () => {
    expect(layout).toContain("page.url.pathname === '/cover-letter'");
    expect(layout).toContain("'max-w-[90rem]'");
    expect(page).toContain('xl:grid-cols-[minmax(22rem,0.7fr)_minmax(0,1.3fr)]');
    expect(page).toContain('class="w-full space-y-6 pb-12"');
  });

  test('uses the role-match compatibility display without a nested card', () => {
    expect(page).toContain("RoleMatchFitAnalysisDisplay.svelte");
    expect(page).toContain('embedded={true}');
    expect(legacyFit).toContain("embedded = false");
    expect(legacyFit).toContain("embedded ? 'border-0 shadow-none'");
    expect(legacyFit).toContain('grid gap-4 2xl:grid-cols-2');
  });

  test('renders the generated letter at comfortable document scale', () => {
    expect(page).toContain('max-w-4xl');
    expect(preview).toContain('text-[15px]');
    expect(preview).toContain('leading-7');
    expect(preview).toContain('max-w-[48rem]');
  });
});
