import { describe, expect, test } from 'bun:test';

import {
    isUnsafeMethod,
    passwordFormEligible,
    readCookie,
    sanitizeReturnTo,
    sessionRemainingMs,
    shouldShowExpiryWarning,
} from './auth-utils';


describe('sanitizeReturnTo', () => {
    test('keeps safe internal paths including query strings', () => {
        expect(sanitizeReturnTo('/tracker?status=applied')).toBe('/tracker?status=applied');
    });

    test('rejects external, protocol-relative, and auth-loop destinations', () => {
        expect(sanitizeReturnTo('https://evil.example')).toBe('/');
        expect(sanitizeReturnTo('//evil.example')).toBe('/');
        expect(sanitizeReturnTo('/login')).toBe('/');
        expect(sanitizeReturnTo('/setup?token=secret')).toBe('/');
        expect(sanitizeReturnTo(null)).toBe('/');
    });

    test('rejects values whose decoded path becomes external-looking', () => {
        expect(sanitizeReturnTo('/%2F%2Fevil.example')).toBe('/');
    });
});


describe('readCookie', () => {
    test('reads and decodes the requested cookie', () => {
        expect(readCookie('applykit_csrf', 'other=1; applykit_csrf=hello%20world')).toBe('hello world');
    });

    test('returns null for missing or malformed values', () => {
        expect(readCookie('applykit_csrf', 'other=1')).toBeNull();
        expect(readCookie('applykit_csrf', 'applykit_csrf=%E0%A4%A')).toBeNull();
    });
});


describe('isUnsafeMethod', () => {
    test('treats only mutation methods as unsafe', () => {
        expect(isUnsafeMethod('GET')).toBeFalse();
        expect(isUnsafeMethod('HEAD')).toBeFalse();
        expect(isUnsafeMethod('OPTIONS')).toBeFalse();
        expect(isUnsafeMethod('POST')).toBeTrue();
        expect(isUnsafeMethod('patch')).toBeTrue();
        expect(isUnsafeMethod(undefined)).toBeFalse();
    });
});


describe('passwordFormEligible', () => {
    test('accepts matching passwords from 12 through 128 characters', () => {
        expect(passwordFormEligible('a'.repeat(12), 'a'.repeat(12))).toBeTrue();
        expect(passwordFormEligible('a'.repeat(128), 'a'.repeat(128))).toBeTrue();
    });

    test('rejects invalid lengths, mismatch, and a required empty token', () => {
        expect(passwordFormEligible('a'.repeat(11), 'a'.repeat(11))).toBeFalse();
        expect(passwordFormEligible('a'.repeat(129), 'a'.repeat(129))).toBeFalse();
        expect(passwordFormEligible('a'.repeat(12), 'b'.repeat(12))).toBeFalse();
        expect(passwordFormEligible('a'.repeat(12), 'a'.repeat(12), '')).toBeFalse();
        expect(passwordFormEligible('a'.repeat(12), 'a'.repeat(12), 'token')).toBeTrue();
    });
});


describe('session expiry helpers', () => {
    const now = Date.parse('2026-08-02T10:00:00Z');

    test('returns remaining milliseconds without extending the session', () => {
        expect(sessionRemainingMs('2026-08-02T10:05:00Z', now)).toBe(300_000);
        expect(sessionRemainingMs('2026-08-02T09:59:00Z', now)).toBe(-60_000);
        expect(sessionRemainingMs(null, now)).toBeNull();
    });

    test('shows the warning only during the final positive five minutes', () => {
        expect(shouldShowExpiryWarning('2026-08-02T10:05:00Z', now)).toBeTrue();
        expect(shouldShowExpiryWarning('2026-08-02T10:05:00.001Z', now)).toBeFalse();
        expect(shouldShowExpiryWarning('2026-08-02T10:00:00Z', now)).toBeFalse();
    });
});
