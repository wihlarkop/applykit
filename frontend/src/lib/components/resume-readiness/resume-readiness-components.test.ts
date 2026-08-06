import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

describe('resume readiness components', () => {
  test('summary distinguishes failed and review states from score bands', () => {
    const source = readFileSync(
      'src/lib/components/resume-readiness/ReadinessSummary.svelte',
      'utf8',
    );
    expect(source).toContain("analysis.status === 'failed'");
    expect(source).toContain("analysis.status === 'needs_review'");
  });

  test('finding row exposes rule details accessibly', () => {
    const source = readFileSync(
      'src/lib/components/resume-readiness/ReadinessFindingRow.svelte',
      'utf8',
    );
    expect(source).toContain('aria-expanded');
    expect(source).toContain('finding.rule_id');
  });

  test('workspace retains the saved generated resume id', () => {
    const source = readFileSync(
      'src/lib/features/resume/ResumeWorkspace.svelte',
      'utf8',
    );
    expect(source).toContain('generatedCvId = result.id');
    expect(source).toContain('Check Resume Readiness');
  });

  test('workspace loads historical resumes from the backward-compatible query', () => {
    const workspace = readFileSync(
      'src/lib/features/resume/ResumeWorkspace.svelte',
      'utf8',
    );
    const card = readFileSync(
      'src/lib/components/history/CvCard.svelte',
      'utf8',
    );

    expect(workspace).toContain("searchParams.get('generated_cv_id')");
    expect(workspace).toContain('getCvHistoryEntry(requestedId)');
    expect(card).toContain('/resume?generated_cv_id={entry.id}');
  });
});
