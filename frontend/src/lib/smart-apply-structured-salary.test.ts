import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const page = readFileSync(
  new URL('../routes/smart-apply/+page.svelte', import.meta.url),
  'utf8',
);

describe('Smart Apply structured salary', () => {
  test('keeps the posted salary text and adds extracted numeric values to the application', () => {
    expect(page).toContain("salary = analyzed.salary || ''");
    expect(page).toContain('minSalary = analyzed.min_salary');
    expect(page).toContain('maxSalary = analyzed.max_salary');
    expect(page).toContain('salary: salary || null');
    expect(page).toContain('min_salary: minSalary');
    expect(page).toContain('max_salary: maxSalary');
  });

  test('restores legacy text salary drafts while supporting editable structured fields', () => {
    expect(page).toContain("salary = restored.salary ?? ''");
    expect(page).toContain('id="salary"');
    expect(page).toContain('id="min-salary"');
    expect(page).toContain('id="max-salary"');
  });
});
