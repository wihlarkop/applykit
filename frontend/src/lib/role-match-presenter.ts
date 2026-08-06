import type {
  RoleMatchAnalysisResponse,
  RoleMatchInsight,
  RoleMatchRequirementResponse,
} from './role-match-types';

const scoreBandLabels: Record<string, string> = {
  exceptional_evidence_match: 'Exceptional evidence match',
  strong_evidence_match: 'Strong evidence match',
  moderate_evidence_match: 'Moderate evidence match',
  limited_evidence_match: 'Limited evidence match',
  weak_evidence_match: 'Weak evidence match',
};

const confidenceLabels = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence',
} as const;

const eligibilityLabels = {
  eligible: 'Eligible',
  likely_eligible: 'Likely eligible',
  eligibility_unclear: 'Eligibility unclear',
  likely_ineligible: 'Likely ineligible',
  ineligible: 'Ineligible',
} as const;

const reviewReasons: Record<string, string> = {
  insufficient_known_coverage:
    'We could not confidently identify enough job requirements from the available profile evidence.',
  insufficient_requirements:
    'We could not identify enough job requirements to calculate a reliable match.',
  low_confidence:
    'Important requirements are still supported by incomplete or inconsistent evidence.',
  too_many_unresolved_conflicts:
    'Several requirements need review before the result can be treated as reliable.',
  invalid_requirement_extraction:
    'The job requirements could not be extracted reliably. Review the job description and try again.',
  provider_failure:
    'The analysis provider could not complete this request. No score was estimated.',
  scoring_failed:
    'The evidence could not be evaluated safely. No score was estimated.',
};

export interface RoleMatchViewModel {
  showScore: boolean;
  score: number | null;
  scoreText: string | null;
  scoreBandLabel: string | null;
  headline: string;
  description: string;
  confidenceLabel: string | null;
  eligibilityLabel: string;
  reviewReason: string | null;
  sections: {
    strengths: { title: string; items: RoleMatchInsight[] };
    gaps: { title: string; items: RoleMatchInsight[] };
    nextStep: { title: string; text: string };
  };
  requirements: RoleMatchRequirementResponse[];
  analysis: RoleMatchAnalysisResponse;
}

export function buildRoleMatchViewModel(
  analysis: RoleMatchAnalysisResponse,
): RoleMatchViewModel {
  const showScore =
    analysis.show_authoritative_score &&
    analysis.state === 'success' &&
    typeof analysis.score === 'number';
  const summary = analysis.summary;

  return {
    showScore,
    score: showScore ? analysis.score ?? null : null,
    scoreText: showScore ? `${analysis.score}/100` : null,
    scoreBandLabel:
      showScore && analysis.score_band
        ? scoreBandLabels[analysis.score_band] ?? 'Evidence match'
        : null,
    headline: showScore
      ? summary?.headline ?? 'Your profile evidence has been assessed'
      : 'Analysis needs review',
    description: showScore
      ? summary?.description ?? 'Review the evidence details below.'
      : 'We need a little more reliable information before showing a match score.',
    confidenceLabel: analysis.confidence
      ? confidenceLabels[analysis.confidence]
      : null,
    eligibilityLabel: eligibilityLabels[analysis.eligibility],
    reviewReason: showScore
      ? null
      : reviewReasons[analysis.failure_code ?? ''] ??
        'Review the extracted requirements and evidence before using this result.',
    sections: {
      strengths: {
        title: 'What makes you a good fit',
        items: summary?.strengths ?? [],
      },
      gaps: {
        title: 'What may hold you back',
        items: summary?.concerns ?? [],
      },
      nextStep: {
        title: 'Your best next step',
        text:
          summary?.next_step ??
          'Review the identified requirements and add truthful evidence where it is missing.',
      },
    },
    requirements: analysis.requirements,
    analysis,
  };
}
