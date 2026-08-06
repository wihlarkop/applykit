import { afterEach, describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';
import {
  analyzeFit,
  generateCoverLetterStream,
} from './api-compat';
import type { RoleMatchAnalysisResponse } from './role-match-types';
import type { CoverLetterRequest } from './types';

const config = readFileSync(new URL('../../svelte.config.js', import.meta.url), 'utf8');
const display = readFileSync(
  new URL('./components/RoleMatchFitAnalysisDisplay.svelte', import.meta.url),
  'utf8',
);
const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

function analysisFixture(): RoleMatchAnalysisResponse {
  return {
    id: 42,
    parent_analysis_id: null,
    created_at: '2026-08-06T06:00:00Z',
    state: 'success',
    score: 80,
    score_band: 'strong_evidence_match',
    confidence: 'high',
    eligibility: 'likely_eligible',
    show_authoritative_score: true,
    summary: {
      headline: 'Your profile is a strong match',
      description: 'Strong Python evidence.',
      strengths: [
        {
          title: 'Python backend capability',
          explanation: 'Supported by work evidence.',
        },
      ],
      concerns: [],
      next_step: 'Use the Python production example.',
    },
    category_breakdown: [],
    requirements: [],
    excluded_items: [],
    overrides: [],
    override_review_count: 0,
    rules_version: 'role-match-v1',
    prompt_version: 'role-match-extraction-v1',
    legacy: false,
    failure_code: null,
  };
}

function coverLetterRequest(): CoverLetterRequest {
  return {
    profile_id: 7,
    job_description: 'Python backend role',
    company_name: 'Example',
    role_title: 'Backend Engineer',
    location: null,
    salary: null,
    extra_context: '',
    tone: 'professional',
    job_url: null,
    fit_context: 'Browser-provided context must be ignored',
    match_score: 99,
    fit_analysis_json: JSON.stringify({ role_match_analysis_id: 42 }),
    application_id: null,
  };
}

describe('role match product compatibility', () => {
  test('redirects existing imports through compatibility modules', () => {
    expect(config).toContain("'$lib/api': './src/lib/api-compat.ts'");
    expect(config).toContain(
      "'$lib/components/FitAnalysisDisplay.svelte': './src/lib/components/RoleMatchFitAnalysisDisplay.svelte'",
    );
  });

  test('replaces legacy fit analysis with a role match API call', async () => {
    let requestedUrl = '';
    let requestedBody: unknown;
    globalThis.fetch = (async (input, init) => {
      requestedUrl = String(input);
      requestedBody = JSON.parse(String(init?.body));
      return new Response(JSON.stringify(analysisFixture()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }) as typeof fetch;

    const result = await analyzeFit(7, 'Python backend role');

    expect(requestedUrl).toEndWith('/analyze/role-match');
    expect(requestedBody).toEqual({
      profile_id: 7,
      job_description: 'Python backend role',
    });
    expect(result.role_match_analysis_id).toBe(42);
    expect(result.role_match_analysis.score).toBe(80);
    expect(result.pros).toEqual(['Python backend capability']);
  });

  test('uses verified generation and strips browser-provided scoring context', async () => {
    let requestedUrl = '';
    let requestedBody: Record<string, unknown> = {};
    globalThis.fetch = (async (input, init) => {
      requestedUrl = String(input);
      requestedBody = JSON.parse(String(init?.body));
      return new Response('event: done\ndata: [DONE]\n\n', { status: 200 });
    }) as typeof fetch;

    await generateCoverLetterStream(coverLetterRequest());

    expect(requestedUrl).toEndWith('/generate/cover-letter/role-match');
    expect(requestedBody.role_match_analysis_id).toBe(42);
    expect(requestedBody.match_score).toBeUndefined();
    expect(requestedBody.fit_context).toBeUndefined();
    expect(requestedBody.fit_analysis_json).toBeUndefined();
  });

  test('falls back to legacy generation when no role analysis exists', async () => {
    let requestedUrl = '';
    globalThis.fetch = (async (input) => {
      requestedUrl = String(input);
      return new Response('event: done\ndata: [DONE]\n\n', { status: 200 });
    }) as typeof fetch;
    const request = coverLetterRequest();
    request.fit_analysis_json = null;

    await generateCoverLetterStream(request);

    expect(requestedUrl).toEndWith('/generate/cover-letter');
  });

  test('renders new and legacy analysis through one stable component import', () => {
    expect(display).toContain('<RoleMatchResult');
    expect(display).toContain('<RoleMatchReviewPanel');
    expect(display).toContain('<RoleMatchVersionCompare');
    expect(display).toContain('<LegacyFitAnalysisDisplay');
  });
});
