import { describe, expect, test } from 'bun:test';
import { buildRoleMatchViewModel } from './role-match-presenter';
import type { RoleMatchAnalysisResponse } from './types';

function strongFixture(): RoleMatchAnalysisResponse {
  return {
    id: 12,
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
      description: 'Your background supports most important requirements.',
      strengths: [
        {
          title: 'Production Python backend capability',
          explanation: 'Supported by recent work examples.',
          evidence_label: 'Work experience',
        },
      ],
      concerns: [
        {
          title: 'Terraform experience needs clearer proof',
          explanation: 'Add a real work example if available.',
          evidence_label: 'Preferred qualification',
        },
      ],
      next_step: 'Strengthen the Terraform example before applying.',
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

describe('role match presenter', () => {
  test('uses the approved human-friendly hierarchy', () => {
    const view = buildRoleMatchViewModel(strongFixture());

    expect(view.headline).toBe('Your profile is a strong match');
    expect(view.scoreText).toBe('80/100');
    expect(view.confidenceLabel).toBe('High confidence');
    expect(view.eligibilityLabel).toBe('Likely eligible');
    expect(view.sections.strengths.title).toBe('What makes you a good fit');
    expect(view.sections.gaps.title).toBe('What may hold you back');
    expect(view.sections.nextStep.title).toBe('Your best next step');
    expect(JSON.stringify(view)).not.toContain('raw_score');
    expect(JSON.stringify(view)).not.toContain('soft cap');
  });

  test('review state hides the authoritative score', () => {
    const response = strongFixture();
    response.state = 'needs_review';
    response.score = null;
    response.score_band = null;
    response.show_authoritative_score = false;
    response.failure_code = 'insufficient_known_coverage';
    response.summary = null;

    const view = buildRoleMatchViewModel(response);

    expect(view.showScore).toBe(false);
    expect(view.headline).toBe('Analysis needs review');
    expect(view.scoreText).toBeNull();
    expect(view.reviewReason).toContain('enough job requirements');
  });
});
