import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const educationTab = readFileSync(
  new URL('./components/profile/EducationTab.svelte', import.meta.url),
  'utf8',
);
const cvPreview = readFileSync(
  new URL('./components/CvPreview.svelte', import.meta.url),
  'utf8',
);

describe('education accomplishments', () => {
  test('the education editor exposes an accomplishments field', () => {
    expect(educationTab).toContain('accomplishments: []');
    expect(educationTab).toContain('eduAccomplishmentsText');
    expect(educationTab).toContain('setEduAccomplishments');
  });

  test('the live CV preview renders education accomplishments', () => {
    expect(cvPreview).toContain('e.accomplishments');
  });
});
