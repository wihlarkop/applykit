import { describe, expect, test } from 'bun:test';
import {
  groupFindings,
  readinessCallToAction,
} from './resume-readiness-policy';
import type {
  ResumeReadinessFinding,
  ResumeReadinessResponse,
} from './resume-readiness-types';

function finding(
  id: number,
  severity: ResumeReadinessFinding['severity'],
  outcome: ResumeReadinessFinding['outcome'],
): ResumeReadinessFinding {
  return {
    id,
    rule_id: `RULE-${id}`,
    category: 'quality',
    severity,
    outcome,
    score_delta: 0,
    score_cap: null,
    title: 'Finding',
    explanation: 'Explanation',
    evidence: {},
    locations: [],
    requires_review: false,
  };
}

describe('resume readiness presentation', () => {
  test('groups critical findings before improvements', () => {
    const grouped = groupFindings([
      finding(1, 'improvement', 'warning'),
      finding(2, 'critical', 'fail'),
    ]);

    expect(grouped.critical.map((item) => item.id)).toEqual([2]);
    expect(grouped.improvement.map((item) => item.id)).toEqual([1]);
  });

  test('does not present failed analysis as a low score', () => {
    const analysis = {
      status: 'failed',
      overall: { score: null, band: null, hard_gate: null },
    } as ResumeReadinessResponse;

    expect(readinessCallToAction(analysis).id).toBe('retry');
  });

  test('asks for review when extraction is uncertain', () => {
    const analysis = {
      status: 'needs_review',
      overall: { score: 55, band: 'not_ready', hard_gate: 'PARSE-012' },
    } as ResumeReadinessResponse;

    expect(readinessCallToAction(analysis).id).toBe('review');
  });
});
