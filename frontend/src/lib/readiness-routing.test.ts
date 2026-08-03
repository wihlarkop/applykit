import { describe, expect, test } from 'bun:test';

import { resolveReadinessDestination } from './readiness-routing';
import type { ReadinessResponse } from './readiness-types';

const base: ReadinessResponse = {
  onboarding: { version: 1, seen: false, skipped: false, should_redirect: true },
  profile: {
    profile_id: 1,
    ready: false,
    completeness: 0,
    missing_requirements: ['name', 'email', 'experience_or_education', 'skills'],
    recommendations: [],
  },
  ai: {
    ready: false,
    status: 'not_configured',
    provider: null,
    model: null,
    tested_at: null,
    failure_category: null,
    message: 'Configure AI.',
    configuration_fingerprint: null,
  },
  applykit_ready: false,
  checklist_visible: true,
  checklist_fingerprint: 'f'.repeat(64),
};

describe('resolveReadinessDestination', () => {
  test('redirects only a fresh unseen installation to onboarding', () => {
    expect(resolveReadinessDestination(base, '/')).toBe('/onboarding');
  });

  test('does not redirect an existing installation that needs a retest', () => {
    const existing = {
      ...base,
      onboarding: { ...base.onboarding, seen: true, should_redirect: false },
      ai: { ...base.ai, status: 'retest_required' as const, provider: 'gemini' },
    };
    expect(resolveReadinessDestination(existing, '/')).toBeNull();
  });

  test('does not redirect after skip', () => {
    const skipped = {
      ...base,
      onboarding: { ...base.onboarding, seen: true, skipped: true, should_redirect: false },
    };
    expect(resolveReadinessDestination(skipped, '/generate')).toBeNull();
  });

  test('never redirects auth or setup routes', () => {
    for (const route of ['/login', '/setup', '/settings', '/settings/security', '/onboarding', '/profile', '/profiles', '/import']) {
      expect(resolveReadinessDestination(base, route)).toBeNull();
    }
  });
});
