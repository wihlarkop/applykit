import { describe, expect, test } from 'bun:test';
import { deriveNextAction } from './dashboard-next-action';

describe('deriveNextAction', () => {
  test('prioritizes an incomplete profile', () => {
    expect(deriveNextAction({
      profileReady: false,
      aiReady: true,
      hasGeneratedResume: false,
      resumeReadinessStatus: null,
      resumeReadinessBand: null,
      applicationCount: 0,
    })).toBe('complete_profile');
  });

  test('asks for readiness after a saved resume exists', () => {
    expect(deriveNextAction({
      profileReady: true,
      aiReady: true,
      hasGeneratedResume: true,
      resumeReadinessStatus: null,
      resumeReadinessBand: null,
      applicationCount: 0,
    })).toBe('check_resume_readiness');
  });

  test('asks for improvement after a weak result', () => {
    expect(deriveNextAction({
      profileReady: true,
      aiReady: true,
      hasGeneratedResume: true,
      resumeReadinessStatus: 'complete',
      resumeReadinessBand: 'needs_improvement',
      applicationCount: 0,
    })).toBe('improve_resume');
  });

  test('moves to preparation after a good resume', () => {
    expect(deriveNextAction({
      profileReady: true,
      aiReady: true,
      hasGeneratedResume: true,
      resumeReadinessStatus: 'complete',
      resumeReadinessBand: 'good',
      applicationCount: 0,
    })).toBe('prepare_application');
  });
});
