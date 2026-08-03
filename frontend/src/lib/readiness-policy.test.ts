import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

function source(path: string): string {
  return readFileSync(new URL(path, import.meta.url), 'utf8');
}

const onboarding = source('../routes/onboarding/+page.svelte');
const dashboard = source('../routes/+page.svelte');
const layout = source('../routes/+layout.ts');
const generate = source('../routes/generate/+page.svelte');
const coverLetter = source('../routes/cover-letter/+page.svelte');
const smartApply = source('../routes/smart-apply/+page.svelte');

// This suite intentionally checks source-level UX and secret-boundary policy.
describe('readiness UX policy', () => {
  test('onboarding exposes the approved two-check flow without browser persistence', () => {
    for (const copy of [
      'Profile Ready',
      'AI Ready',
      'Skip for now',
      'Test connection',
      'Create your first CV',
      'Completeness is advisory',
      'Import CV',
      'Enter manually',
    ]) {
      expect(onboarding).toContain(copy);
    }
    expect(onboarding).not.toMatch(/\blocalStorage\b/);
    expect(onboarding).not.toMatch(/\bsessionStorage\b/);
    expect(onboarding).not.toContain('Complete setup first to unlock.');
    expect(onboarding).not.toMatch(/error\.message|String\(error\)/);
  });

  test('root routing never redirects an unconfigured AI provider to settings', () => {
    expect(layout).not.toContain("redirect(307, '/settings')");
    expect(layout).not.toContain('!isApiKeyConfigured');
  });

  test('dashboard renders the global checklist without navigation locks', () => {
    const checklist = source('./components/ReadinessChecklist.svelte');
    for (const copy of [
      'Finish setting up ApplyKit',
      'Profile Ready',
      'Test connection',
      'Fix AI settings',
      'ApplyKit Ready',
      'checklist_visible',
      'dismissReadinessChecklist',
    ]) {
      expect(checklist).toContain(copy);
    }
    expect(dashboard).toContain('<ReadinessChecklist {readiness} />');
    expect(dashboard).not.toContain('isRestricted');
    expect(dashboard).not.toContain('Complete setup first to unlock.');
    expect(dashboard).not.toContain('<Lock');
  });
  test('AI pages use focused readiness notices instead of onboarding locks', () => {
    for (const pageSource of [generate, coverLetter, smartApply]) {
      expect(pageSource).toContain('AiReadinessNotice');
      expect(pageSource).toContain('aiReady');
      expect(pageSource).not.toContain("goto('/settings')");
      expect(pageSource).not.toContain('isOnboarded');
      expect(pageSource).not.toContain('<Lock');
      expect(pageSource).not.toContain('> Locked');
    }
    expect(generate).toContain('bind:value={jobDescription}');
    expect(coverLetter).toContain('bind:value={jobDescription}');
    expect(smartApply).toContain('bind:value={jobUrl}');
  });

  test('readiness state does not capture only the initial prop value', () => {
    const checklist = source('./components/ReadinessChecklist.svelte');
    expect(checklist).not.toMatch(/\$state(?:<[^>]+>)?\(readiness\)/);
    for (const pageSource of [onboarding, generate, coverLetter, smartApply]) {
      expect(pageSource).not.toMatch(/\$state(?:<[^>]+>)?\(data\.readiness\)/);
    }
  });

  test('policy inputs remain tracked while later tasks migrate dashboard and AI pages', () => {
    expect(dashboard.length).toBeGreaterThan(0);
    expect(generate.length).toBeGreaterThan(0);
    expect(coverLetter.length).toBeGreaterThan(0);
    expect(smartApply.length).toBeGreaterThan(0);
  });
});
