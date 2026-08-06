import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const coverLetterPage = readFileSync(
  new URL('../routes/cover-letter/+page.svelte', import.meta.url),
  'utf8',
);

describe('cover letter job input routing', () => {
  test('routes a pasted HTTP job URL through the URL importer instead of the AI text parser', () => {
    expect(coverLetterPage).toContain(
      'function extractHttpJobUrl(raw: string): string | null',
    );
    expect(coverLetterPage).toContain(
      'const pastedUrl = extractHttpJobUrl(jobDescription);',
    );
    expect(coverLetterPage).toContain('jobUrl = pastedUrl;');
    expect(coverLetterPage).toContain("inputTab = 'url';");
    expect(coverLetterPage).toContain('await handleImport();');
  });
});
