import { describe, expect, test } from 'bun:test';

import { resolveAuthDestination } from './auth-routing';
import type { AuthStatus } from './auth-types';

const disabled: AuthStatus = {
    auth_mode: 'disabled',
    setup_required: false,
    authenticated: true,
    session_expires_at: null,
};

const setupRequired: AuthStatus = {
    auth_mode: 'password',
    setup_required: true,
    authenticated: false,
    session_expires_at: null,
};

const loggedOut: AuthStatus = {
    auth_mode: 'password',
    setup_required: false,
    authenticated: false,
    session_expires_at: null,
};

const loggedIn: AuthStatus = {
    auth_mode: 'password',
    setup_required: false,
    authenticated: true,
    session_expires_at: '2026-08-09T10:00:00Z',
};


describe('resolveAuthDestination', () => {
    test('preserves the disabled local flow but hides security settings', () => {
        expect(resolveAuthDestination(disabled, '/', '')).toBeNull();
        expect(resolveAuthDestination(disabled, '/settings/security', '')).toBe('/settings');
        expect(resolveAuthDestination(disabled, '/login', '')).toBe('/');
    });

    test('routes an unclaimed installation to setup', () => {
        expect(resolveAuthDestination(setupRequired, '/tracker', '?status=applied'))
            .toBe('/setup?returnTo=%2Ftracker%3Fstatus%3Dapplied');
        expect(resolveAuthDestination(setupRequired, '/setup', '')).toBeNull();
        expect(resolveAuthDestination(setupRequired, '/login', '')).toBe('/setup');
    });

    test('routes a claimed logged-out installation to login', () => {
        expect(resolveAuthDestination(loggedOut, '/tracker', '?status=applied'))
            .toBe('/login?returnTo=%2Ftracker%3Fstatus%3Dapplied');
        expect(resolveAuthDestination(loggedOut, '/login', '?returnTo=%2Ftracker')).toBeNull();
        expect(resolveAuthDestination(loggedOut, '/setup', '')).toBe('/login');
    });

    test('redirects authenticated users away from auth routes safely', () => {
        expect(resolveAuthDestination(loggedIn, '/login', '?returnTo=%2Fhistory')).toBe('/history');
        expect(resolveAuthDestination(loggedIn, '/setup', '?returnTo=https%3A%2F%2Fevil.example')).toBe('/');
        expect(resolveAuthDestination(loggedIn, '/tracker', '')).toBeNull();
    });

    test('allows the special reauth login page for an authenticated session', () => {
        expect(resolveAuthDestination(loggedIn, '/login', '?reauth=1')).toBeNull();
    });
});
