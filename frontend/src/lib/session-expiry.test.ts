import { describe, expect, test } from 'bun:test';

import { nextExpiryState } from './session-expiry';


describe('nextExpiryState', () => {
    const now = Date.parse('2026-08-02T10:00:00Z');

    test('is inactive without an expiry or before the warning window', () => {
        expect(nextExpiryState(null, now)).toBe('inactive');
        expect(nextExpiryState('2026-08-02T10:05:00.001Z', now)).toBe('inactive');
    });

    test('is active during the final positive five minutes', () => {
        expect(nextExpiryState('2026-08-02T10:05:00Z', now)).toBe('active');
        expect(nextExpiryState('2026-08-02T10:00:00.001Z', now)).toBe('active');
    });

    test('is expired at or after the absolute expiry', () => {
        expect(nextExpiryState('2026-08-02T10:00:00Z', now)).toBe('expired');
        expect(nextExpiryState('2026-08-02T09:59:59Z', now)).toBe('expired');
    });
});
