import type {
  ResumeReadinessBand,
  ResumeReadinessStatus,
} from './resume-readiness-types';

export type NextAction =
  | 'complete_profile'
  | 'configure_ai'
  | 'generate_resume'
  | 'check_resume_readiness'
  | 'improve_resume'
  | 'prepare_application'
  | 'review_applications';

export interface NextActionInput {
  profileReady: boolean;
  aiReady: boolean;
  hasGeneratedResume: boolean;
  resumeReadinessStatus: ResumeReadinessStatus | null;
  resumeReadinessBand: ResumeReadinessBand | null;
  applicationCount: number;
}

export interface NextActionPresentation {
  id: NextAction;
  title: string;
  description: string;
  href: string;
  actionLabel: string;
}

const PRESENTATIONS: Record<NextAction, Omit<NextActionPresentation, 'id'>> = {
  complete_profile: {
    title: 'Complete your career profile',
    description: 'Add the experience and skills ApplyKit needs as factual source evidence.',
    href: '/profile',
    actionLabel: 'Complete profile',
  },
  configure_ai: {
    title: 'Verify your AI connection',
    description: 'Connect and test a provider before generating tailored application materials.',
    href: '/settings',
    actionLabel: 'Open AI settings',
  },
  generate_resume: {
    title: 'Create your first saved resume',
    description: 'Generate an immutable resume version that can be downloaded and validated.',
    href: '/resume',
    actionLabel: 'Create resume',
  },
  check_resume_readiness: {
    title: 'Validate your resume output',
    description: 'Run Resume Readiness against the exported PDF before using it for applications.',
    href: '/resume',
    actionLabel: 'Check readiness',
  },
  improve_resume: {
    title: 'Address the highest-impact resume findings',
    description: 'Review parseability, quality, and tailoring issues, then run the analysis again.',
    href: '/resume',
    actionLabel: 'Improve resume',
  },
  prepare_application: {
    title: 'Prepare a role-specific application',
    description: 'Import a job, review evidence match, and prepare application documents.',
    href: '/smart-apply',
    actionLabel: 'Prepare application',
  },
  review_applications: {
    title: 'Review your active applications',
    description: 'Check statuses, notes, and the next action across your application pipeline.',
    href: '/applications',
    actionLabel: 'Open applications',
  },
};

export function deriveNextAction(input: NextActionInput): NextAction {
  if (!input.profileReady) return 'complete_profile';
  if (!input.aiReady) return 'configure_ai';
  if (!input.hasGeneratedResume) return 'generate_resume';
  if (
    input.resumeReadinessStatus == null
    || input.resumeReadinessStatus === 'failed'
  ) return 'check_resume_readiness';
  if (
    input.resumeReadinessStatus === 'needs_review'
    || input.resumeReadinessBand === 'not_ready'
    || input.resumeReadinessBand === 'needs_improvement'
  ) return 'improve_resume';
  if (input.applicationCount > 0) return 'review_applications';
  return 'prepare_application';
}

export function presentNextAction(input: NextActionInput): NextActionPresentation {
  const id = deriveNextAction(input);
  return { id, ...PRESENTATIONS[id] };
}
