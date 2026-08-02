import { describe, expect, test } from 'bun:test';

import { createAuthStateCore } from './auth-state-core';


describe('auth state core', () => {
    test('represents disabled mode as authenticated without a session expiry', () => {
        const state = createAuthStateCore();
        state.applyStatus({
            auth_mode: 'disabled',
            setup_required: false,
            authenticated: true,
            session_expires_at: null,
        });

        expect(state.authMode).toBe('disabled');
        expect(state.authenticated).toBeTrue();
        expect(state.sessionExpiresAt).toBeNull();
        expect(state.checking).toBeFalse();
    });

    test('tracks setup-required and unauthenticated password mode', () => {
        const state = createAuthStateCore();
        state.applyStatus({
            auth_mode: 'password',
            setup_required: true,
            authenticated: false,
            session_expires_at: null,
        });

        expect(state.setupRequired).toBeTrue();
        expect(state.authenticated).toBeFalse();
    });

    test('applies a new session after login or password change', () => {
        const state = createAuthStateCore();
        state.applySession({
            authenticated: true,
            remember_device: true,
            session_expires_at: '2026-09-01T10:00:00Z',
        });

        expect(state.authMode).toBe('password');
        expect(state.setupRequired).toBeFalse();
        expect(state.authenticated).toBeTrue();
        expect(state.sessionExpiresAt).toBe('2026-09-01T10:00:00Z');
    });

    test('clears and expires sessions without changing password mode', () => {
        const state = createAuthStateCore();
        state.applySession({
            authenticated: true,
            remember_device: false,
            session_expires_at: '2026-08-09T10:00:00Z',
        });
        state.markExpired();

        expect(state.authMode).toBe('password');
        expect(state.authenticated).toBeFalse();
        expect(state.sessionExpiresAt).toBeNull();

        state.clearSession();
        expect(state.authenticated).toBeFalse();
    });
});
