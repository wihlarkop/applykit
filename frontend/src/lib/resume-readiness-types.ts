export type ResumeReadinessMode = 'general' | 'job_specific';
export type ResumeReadinessStatus = 'complete' | 'needs_review' | 'failed';
export type ResumeReadinessBand =
  | 'excellent'
  | 'good'
  | 'needs_improvement'
  | 'not_ready';
export type ResumeReadinessCategory = 'parseability' | 'quality' | 'tailoring';
export type ResumeReadinessSeverity = 'info' | 'improvement' | 'important' | 'critical';
export type ResumeReadinessOutcome = 'pass' | 'warning' | 'fail' | 'unknown' | 'excluded';

export interface CreateResumeReadinessRequest {
  generated_cv_id: number;
  job_description?: string | null;
  role_match_analysis_id?: number | null;
}

export interface ResumeReadinessScore {
  score: number | null;
  band: ResumeReadinessBand | null;
  hard_gate: string | null;
}

export interface ResumeReadinessCategoryResult {
  score: number;
  band: ResumeReadinessBand;
  score_cap: number | null;
}

export interface ResumeReadinessFinding {
  id: number | null;
  rule_id: string;
  category: ResumeReadinessCategory;
  severity: ResumeReadinessSeverity;
  outcome: ResumeReadinessOutcome;
  score_delta: number;
  score_cap: number | null;
  title: string;
  explanation: string;
  evidence: Record<string, unknown>;
  locations: string[];
  requires_review: boolean;
}

export interface ResumeReadinessExtraction {
  page_count: number;
  has_text_layer: boolean;
  text_preview: string;
  warnings: string[];
  source_coverage: number | null;
}

export interface ResumeReadinessResponse {
  id: number;
  generated_cv_id: number;
  profile_id: number | null;
  role_match_analysis_id: number | null;
  supersedes_analysis_id: number | null;
  mode: ResumeReadinessMode;
  status: ResumeReadinessStatus;
  overall: ResumeReadinessScore;
  categories: {
    parseability: ResumeReadinessCategoryResult | null;
    quality: ResumeReadinessCategoryResult | null;
    tailoring: ResumeReadinessCategoryResult | null;
  };
  summary: {
    critical: number;
    important: number;
    improvements: number;
    passed: number;
    unknown: number;
  };
  findings: ResumeReadinessFinding[];
  extraction: ResumeReadinessExtraction | null;
  versions: {
    rules: string;
    extraction: string;
    semantic: string | null;
  };
  failure_code: string | null;
  created_at: string;
}

export interface ResumeReadinessListResponse {
  items: ResumeReadinessResponse[];
  total: number;
}
