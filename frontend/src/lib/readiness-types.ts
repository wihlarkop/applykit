export type ProfileRequirement =
  | 'name'
  | 'email'
  | 'experience_or_education'
  | 'skills';

export type AiReadinessStatus =
  | 'not_configured'
  | 'retest_required'
  | 'configuration_changed'
  | 'ready'
  | 'authentication_failed'
  | 'endpoint_unreachable'
  | 'model_unavailable'
  | 'rate_limited'
  | 'unknown_failure';

export type ConnectionFailureCategory =
  | 'authentication_failed'
  | 'endpoint_unreachable'
  | 'model_unavailable'
  | 'rate_limited'
  | 'unknown_failure';

export interface OnboardingState {
  version: number;
  seen: boolean;
  skipped: boolean;
  should_redirect: boolean;
}

export interface ProfileReadiness {
  profile_id: number;
  ready: boolean;
  completeness: number;
  missing_requirements: ProfileRequirement[];
  recommendations: string[];
}

export interface AiReadiness {
  ready: boolean;
  status: AiReadinessStatus;
  provider: string | null;
  model: string | null;
  tested_at: string | null;
  failure_category: ConnectionFailureCategory | null;
  message: string;
  configuration_fingerprint: string | null;
}

export interface ReadinessResponse {
  onboarding: OnboardingState;
  profile: ProfileReadiness;
  ai: AiReadiness;
  applykit_ready: boolean;
  checklist_visible: boolean;
  checklist_fingerprint: string;
}
