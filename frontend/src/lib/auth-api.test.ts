import { describe, expect, test } from 'bun:test';

import {
    changeOwnerPassword,
    getAuthStatus,
    getSecuritySummary,
    loginOwner,
    logoutOwner,
    revokeOtherSessions,
    setupOwner,
} from './auth-api';

function jsonResponse(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
    });
}


describe('auth API', () => {
    test('includes credentials for status requests', async () => {
        let request: RequestInit | undefined;
        const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
            request = init;
            return jsonResponse({
                auth_mode: 'password',
                setup_required: false,
                authenticated: false,
                session_expires_at: null,
            });
        };

        await getAuthStatus(fetchFn as typeof fetch);
        expect(request?.credentials).toBe('include');
        expect(request?.method).toBe('GET');
    });

    test('sends setup and login payloads exactly as the backend expects', async () => {
        const calls: Array<{ url: string; init?: RequestInit }> = [];
        const fetchFn = async (input: RequestInfo | URL, init?: RequestInit) => {
            calls.push({ url: String(input), init });
            return jsonResponse({
                authenticated: true,
                remember_device: false,
                session_expires_at: '2026-08-09T10:00:00Z',
            }, calls.length === 1 ? 201 : 200);
        };

        await setupOwner({ setup_token: 'token', password: 'secure passphrase' }, fetchFn as typeof fetch);
        await loginOwner({ password: 'secure passphrase', remember_device: true }, fetchFn as typeof fetch);

        expect(JSON.parse(String(calls[0].init?.body))).toEqual({
            setup_token: 'token',
            password: 'secure passphrase',
        });
        expect(JSON.parse(String(calls[1].init?.body))).toEqual({
            password: 'secure passphrase',
            remember_device: true,
        });
    });

    test('adds the CSRF header to unsafe authenticated operations', async () => {
        const calls: RequestInit[] = [];
        const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
            calls.push(init ?? {});
            return init?.method === 'POST' && calls.length === 1
                ? new Response(null, { status: 204 })
                : jsonResponse(calls.length === 2
                    ? { other_sessions: 2 }
                    : calls.length === 3
                        ? { authenticated: true, remember_device: false, session_expires_at: '2026-08-09T10:00:00Z' }
                        : { revoked_sessions: 2 });
        };

        await logoutOwner(fetchFn as typeof fetch, 'csrf-value');
        await getSecuritySummary(fetchFn as typeof fetch);
        await changeOwnerPassword(
            { current_password: 'old passphrase', new_password: 'new secure passphrase' },
            fetchFn as typeof fetch,
            'csrf-value',
        );
        await revokeOtherSessions(fetchFn as typeof fetch, 'csrf-value');

        expect(new Headers(calls[0].headers).get('X-CSRF-Token')).toBe('csrf-value');
        expect(new Headers(calls[1].headers).get('X-CSRF-Token')).toBeNull();
        expect(new Headers(calls[2].headers).get('X-CSRF-Token')).toBe('csrf-value');
        expect(new Headers(calls[3].headers).get('X-CSRF-Token')).toBe('csrf-value');
    });

    test('throws the existing sanitized API error type', async () => {
        const fetchFn = async () => jsonResponse({
            error: { code: 'AUTH_INVALID', message: 'Invalid password.', details: {} },
        }, 401);

        await expect(loginOwner({ password: 'wrong', remember_device: false }, fetchFn as typeof fetch))
            .rejects.toMatchObject({ message: 'Invalid password.', code: 'AUTH_INVALID', status: 401 });
    });
});
