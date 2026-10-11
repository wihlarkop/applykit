import type {
  ResumeReadinessFinding,
  ResumeReadinessResponse,
} from './resume-readiness-types';

export interface GroupedReadinessFindings {
  critical: ResumeReadinessFinding[];
  important: ResumeReadinessFinding[];
  improvement: ResumeReadinessFinding[];
  passed: ResumeReadinessFinding[];
  other: ResumeReadinessFinding[];
}

export type ResumeReadinessActionId = 'run' | 'retry' | 'review' | 'improve' | 'ready';

export interface ResumeReadinessAction {
  id: ResumeReadinessActionId;
  label: string;
  description: string;
}

export function groupFindings(
  findings: ResumeReadinessFinding[],
): GroupedReadinessFindings {
  const grouped: GroupedReadinessFindings = {
    critical: [],
    important: [],
    improvement: [],
    passed: [],
    other: [],
  };

  for (const finding of findings) {
    if (finding.outcome === 'pass') {
      grouped.passed.push(finding);
    } else if (finding.severity === 'critical') {
      grouped.critical.push(finding);
    } else if (finding.severity === 'important') {
      grouped.important.push(finding);
    } else if (finding.severity === 'improvement') {
      grouped.improvement.push(finding);
    } else {
      grouped.other.push(finding);
    }
  }

  return grouped;
}

export function readinessCallToAction(
  analysis: ResumeReadinessResponse | null,
): ResumeReadinessAction {
  if (!analysis) {
    return {
      id: 'run',
      label: 'Check Resume Readiness',
      description: 'Validate the saved resume PDF before using it for applications.',
    };
  }

  if (analysis.status === 'failed') {
    return {
      id: 'retry',
      label: 'Try analysis again',
      description: 'The previous analysis failed and did not produce a score.',
    };
  }

  if (analysis.status === 'needs_review') {
    return {
      id: 'review',
      label: 'Review analysis issues',
      description: 'Extraction uncertainty prevents a fully authoritative result.',
    };
  }

  if (
    analysis.overall.band === 'not_ready'
    || analysis.overall.band === 'needs_improvement'
  ) {
    return {
      id: 'improve',
      label: 'Improve this resume',
      description: 'Address the highest-impact findings, then run the analysis again.',
    };
  }

  return {
    id: 'ready',
    label: 'Resume is ready',
    description: 'No critical readiness blocker was found.',
  };
}

export function formatReadinessBand(band: string | null): string {
  if (!band) return 'Not scored';
  return band
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
