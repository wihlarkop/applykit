import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

describe('canonical route compatibility', () => {
  test('canonical and legacy resume routes share one workspace', () => {
    for (const path of [
      'src/routes/resume/+page.svelte',
      'src/routes/generate/+page.svelte',
    ]) {
      expect(readFileSync(path, 'utf8')).toContain('ResumeWorkspace');
    }
  });

  test.each([
    ['src/routes/documents/+page.svelte', "../history/+page.svelte"],
    ['src/routes/applications/+page.svelte', "../tracker/+page.svelte"],
  ])('%s preserves the existing workspace', (path, legacyImport) => {
    expect(readFileSync(path, 'utf8')).toContain(legacyImport);
  });
});
