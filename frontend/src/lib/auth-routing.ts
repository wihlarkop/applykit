import type { AuthStatus } from './auth-types';
import { sanitizeReturnTo } from './auth-utils';

const AUTH_ROUTES = new Set(['/login', '/setup']);

function currentDestination(pathname: string, search: string): string {
    return sanitizeReturnTo(`${pathname}${search}`);
}

function encodedReturnTo(pathname: string, search: string): string {
    return encodeURIComponent(currentDestination(pathname, search));
}

export function resolveAuthDestination(
    status: AuthStatus,
    pathname: string,
    search: string,
): string | null {
    const params = new URLSearchParams(search);
    const isAuthRoute = AUTH_ROUTES.has(pathname);

    if (status.auth_mode === 'disabled') {
        if (pathname === '/settings/security') return '/settings';
        return isAuthRoute ? '/' : null;
    }

    if (status.setup_required) {
        if (pathname === '/setup') return null;
        if (pathname === '/login') return '/setup';
        return `/setup?returnTo=${encodedReturnTo(pathname, search)}`;
    }

    if (!status.authenticated) {
        if (pathname === '/login') return null;
        if (pathname === '/setup') return '/login';
        return `/login?returnTo=${encodedReturnTo(pathname, search)}`;
    }

    if (pathname === '/login' && params.get('reauth') === '1') return null;
    if (isAuthRoute) return sanitizeReturnTo(params.get('returnTo'));
    return null;
}
