import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const page = readFileSync(
  new URL('../routes/smart-apply/+page.svelte', import.meta.url),
  'utf8',
);

describe('smart apply application status', () => {
  test('tracks new applications as "applying", not "applied"', () => {
    // Smart Apply generates the documents and creates the tracker entry,
    // but the user still has to actually submit the application themselves.
    expect(page).toContain("status: 'applying'");
    expect(page).not.toContain("status: 'applied'");
  });
});
