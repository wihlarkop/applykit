import { parseApiError } from './api-error';
import { authenticationErrorMessage } from './auth-error';
import type {
    AuthenticatedSession,
    AuthStatus,
    RevokeSessionsResponse,
    SecuritySummary,
} from './auth-types';
import { readCookie } from './auth-utils';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function authRequest<T>(
    path: string,
    options: RequestInit = {},
    fetchFn: typeof fetch = fetch,
    csrfToken?: string | null,
): Promise<T> {
    const method = (options.method ?? 'GET').toUpperCase();
    const headers = new Headers(options.headers);
    if (options.body !== undefined && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
    }
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const token = csrfToken ?? readCookie('applykit_csrf');
        if (token) headers.set('X-CSRF-Token', token);
    }

    const response = await fetchFn(`${BASE_URL}${path}`, {
        ...options,
        method,
        headers,
        credentials: 'include',
    });

    if (!response.ok) {
        const payload: unknown = await response.json().catch(() => undefined);
        const error = parseApiError(payload, 'Authentication request failed.', response.status);
        error.message = authenticationErrorMessage(error, error.message);
        throw error;
    }

    if (response.status === 204 || response.headers.get('content-length') === '0') {
        return undefined as T;
    }
    return response.json() as Promise<T>;
}

export const getAuthStatus = (fetchFn?: typeof fetch) =>
    authRequest<AuthStatus>('/auth/status', {}, fetchFn);

export const setupOwner = (
    input: { setup_token: string; password: string },
    fetchFn?: typeof fetch,
) => authRequest<AuthenticatedSession>(
    '/auth/setup',
    { method: 'POST', body: JSON.stringify(input) },
    fetchFn,
);

export const loginOwner = (
    input: { password: string; remember_device: boolean },
    fetchFn?: typeof fetch,
) => authRequest<AuthenticatedSession>(
    '/auth/login',
    { method: 'POST', body: JSON.stringify(input) },
    fetchFn,
);

export const logoutOwner = (
    fetchFn?: typeof fetch,
    csrfToken?: string | null,
) => authRequest<void>('/auth/logout', { method: 'POST' }, fetchFn, csrfToken);

export const changeOwnerPassword = (
    input: { current_password: string; new_password: string },
    fetchFn?: typeof fetch,
    csrfToken?: string | null,
) => authRequest<AuthenticatedSession>(
    '/auth/change-password',
    { method: 'POST', body: JSON.stringify(input) },
    fetchFn,
    csrfToken,
);

export const getSecuritySummary = (fetchFn?: typeof fetch) =>
    authRequest<SecuritySummary>('/auth/security', {}, fetchFn);

export const revokeOtherSessions = (
    fetchFn?: typeof fetch,
    csrfToken?: string | null,
) => authRequest<RevokeSessionsResponse>(
    '/auth/sessions/revoke-others',
    { method: 'POST' },
    fetchFn,
    csrfToken,
);
