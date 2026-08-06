export type RoleMatchState = 'success' | 'needs_review' | 'failed';
export type RoleMatchConfidence = 'high' | 'medium' | 'low';
export type RoleMatchEligibility =
  | 'eligible'
  | 'likely_eligible'
  | 'eligibility_unclear'
  | 'likely_ineligible'
  | 'ineligible';
export type RoleMatchCarryStatus = 'carried_forward' | 'needs_review' | 'not_applicable';

export interface RoleMatchInsight {
  title: string;
  explanation: string;
  evidence_label?: string | null;
}

export interface RoleMatchSummaryResponse {
  headline: string;
  description: string;
  strengths: RoleMatchInsight[];
  concerns: RoleMatchInsight[];
  next_step: string;
}

export interface RoleMatchCategoryResponse {
  category: string;
  score: number;
  known_coverage: number;
  unknown_coverage: number;
  known_match: number;
  requirement_count: number;
}

export interface RoleMatchEvidenceResponse {
  id: number;
  evidence_id: string;
  source_type: string;
  source_text: string;
  relationship: string;
  depth: string;
  duplicate: boolean;
  contradiction: boolean;
  explanation?: string | null;
}

export interface RoleMatchRequirementResponse {
  id: number;
  cluster_id: string;
  canonical_key: string;
  canonical_text: string;
  primary_category: string;
  importance: string;
  mention_count: number;
  importance_conflict: boolean;
  source_quotes: string[];
  excluded: boolean;
  exclusion_reason?: string | null;
  match_level?: string | null;
  strength?: number | null;
  explanation?: string | null;
  evidence: RoleMatchEvidenceResponse[];
}

export interface ExcludedAnalysisItemResponse {
  source_id: string;
  text: string;
  reason: string;
}

export interface RoleMatchOverrideResponse {
  id: number;
  requirement_key: string;
  field_name: string;
  extracted_value: unknown;
  effective_value: unknown;
  reason: string;
  source: string;
  carry_status: RoleMatchCarryStatus;
  source_override_id?: number | null;
  created_at: string;
}

export interface RoleMatchAnalysisResponse {
  id: number;
  parent_analysis_id?: number | null;
  created_at: string;
  state: RoleMatchState;
  score?: number | null;
  score_band?: string | null;
  confidence?: RoleMatchConfidence | null;
  eligibility: RoleMatchEligibility;
  show_authoritative_score: boolean;
  summary?: RoleMatchSummaryResponse | null;
  category_breakdown: RoleMatchCategoryResponse[];
  requirements: RoleMatchRequirementResponse[];
  excluded_items: ExcludedAnalysisItemResponse[];
  overrides: RoleMatchOverrideResponse[];
  override_review_count: number;
  rules_version: string;
  prompt_version: string;
  legacy: boolean;
  failure_code?: string | null;
}

export interface AnalyzeRoleMatchRequest {
  profile_id: number;
  job_description: string;
  application_id?: number | null;
  parent_analysis_id?: number | null;
}

export interface ReanalyzeRoleMatchRequest {
  profile_id?: number | null;
  job_description?: string | null;
  application_id?: number | null;
}

export type RoleMatchOverrideField =
  | 'importance'
  | 'excluded'
  | 'experience_status'
  | 'evidence_unlink';

export interface RoleMatchOverrideInput {
  requirement_key: string;
  field_name: RoleMatchOverrideField;
  effective_value: unknown;
  reason: string;
}

export interface RoleMatchOverridesRequest {
  overrides: RoleMatchOverrideInput[];
}

export interface RoleMatchVersionItem {
  id: number;
  parent_analysis_id?: number | null;
  created_at: string;
  state: RoleMatchState;
  score?: number | null;
  confidence?: RoleMatchConfidence | null;
  eligibility: RoleMatchEligibility;
  superseded_by_id?: number | null;
}

export interface RoleMatchVersionsResponse {
  items: RoleMatchVersionItem[];
}

export interface RoleMatchRequirementChange {
  canonical_key: string;
  changes: Record<string, { from: unknown; to: unknown }>;
}

export interface RoleMatchComparisonResponse {
  from_analysis_id: number;
  to_analysis_id: number;
  score_change?: number | null;
  added_requirements: string[];
  removed_requirements: string[];
  changed_requirements: RoleMatchRequirementChange[];
}
