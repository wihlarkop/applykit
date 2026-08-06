export * from './api';

import {
  generateCoverLetterStream as legacyGenerateCoverLetterStream,
} from './api';
import { apiFetch } from './api-client';
import { parseApiError } from './api-error';
import { analyzeRoleMatch } from './role-match-api';
import type { RoleMatchAnalysisResponse } from './role-match-types';
import type { CoverLetterRequest, FitAnalysisResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

export interface RoleMatchCompatibleFitAnalysis extends FitAnalysisResponse {
  role_match_analysis_id: number;
  role_match_analysis: RoleMatchAnalysisResponse;
}

function toLegacyCompatibleAnalysis(
  analysis: RoleMatchAnalysisResponse,
): RoleMatchCompatibleFitAnalysis {
  const strengths = analysis.summary?.strengths ?? [];
  const concerns = analysis.summary?.concerns ?? [];
  const missing = analysis.requirements.filter((requirement) =>
    ['no_evidence', 'unknown'].includes(requirement.match_level ?? 'unknown'),
  );
  const redFlags = ['likely_ineligible', 'ineligible'].includes(analysis.eligibility)
    ? [`Eligibility status: ${analysis.eligibility.replaceAll('_', ' ')}`]
    : [];

  return {
    match_score: analysis.show_authoritative_score ? analysis.score ?? 0 : 0,
    pros: strengths.map((item) => item.title),
    cons: concerns.map((item) => item.title),
    missing_keywords: missing.map((requirement) => requirement.canonical_text),
    red_flags: redFlags,
    suggested_emphasis:
      analysis.summary?.next_step ??
      'Review the identified requirements before tailoring your application.',
    interview_questions: [],
    role_match_analysis_id: analysis.id,
    role_match_analysis: analysis,
  };
}

export async function analyzeFit(
  profile_id: number,
  job_description: string,
): Promise<RoleMatchCompatibleFitAnalysis> {
  const analysis = await analyzeRoleMatch({ profile_id, job_description });
  return toLegacyCompatibleAnalysis(analysis);
}

function analysisIdFromRequest(data: CoverLetterRequest): number | null {
  const direct = (data as CoverLetterRequest & { role_match_analysis_id?: number })
    .role_match_analysis_id;
  if (typeof direct === 'number') return direct;
  if (!data.fit_analysis_json) return null;
  try {
    const parsed = JSON.parse(data.fit_analysis_json) as {
      role_match_analysis_id?: unknown;
    };
    return typeof parsed.role_match_analysis_id === 'number'
      ? parsed.role_match_analysis_id
      : null;
  } catch {
    return null;
  }
}

export async function generateCoverLetterStream(
  data: CoverLetterRequest,
): Promise<Response> {
  const analysisId = analysisIdFromRequest(data);
  if (analysisId === null) return legacyGenerateCoverLetterStream(data);

  const payload: Record<string, unknown> = {
    ...data,
    role_match_analysis_id: analysisId,
  };
  delete payload.match_score;
  delete payload.fit_context;
  delete payload.fit_analysis_json;

  const response = await apiFetch(`${BASE_URL}/generate/cover-letter/role-match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorPayload: unknown = await response.json().catch(() => undefined);
    throw parseApiError(
      errorPayload,
      'The cover letter could not be generated from this role match.',
      response.status,
    );
  }
  return response;
}
