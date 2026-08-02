import { describe, expect, test } from 'bun:test';

import { changePasswordEligible, otherSessionsLabel } from './security-form';


describe('changePasswordEligible', () => {
    test('requires current password plus a valid matching new password', () => {
        expect(changePasswordEligible('current', 'a'.repeat(12), 'a'.repeat(12))).toBeTrue();
        expect(changePasswordEligible('', 'a'.repeat(12), 'a'.repeat(12))).toBeFalse();
        expect(changePasswordEligible('current', 'a'.repeat(11), 'a'.repeat(11))).toBeFalse();
        expect(changePasswordEligible('current', 'a'.repeat(12), 'b'.repeat(12))).toBeFalse();
    });
});


describe('otherSessionsLabel', () => {
    test('formats zero, singular, and plural counts without device metadata', () => {
        expect(otherSessionsLabel(0)).toBe('No other active sessions');
        expect(otherSessionsLabel(1)).toBe('1 other active session');
        expect(otherSessionsLabel(2)).toBe('2 other active sessions');
    });
});
