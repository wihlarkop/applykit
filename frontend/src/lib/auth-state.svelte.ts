import { getAuthStatus } from './auth-api';
import { onUnauthorized } from './api-client';
import { armDraftRecovery } from './draft-recovery';
import type { AuthenticatedSession, AuthMode, AuthStatus } from './auth-types';

function armBrowserDrafts(): void {
    if (typeof sessionStorage === 'undefined') return;
    armDraftRecovery(sessionStorage);
}

function createAuthState() {
    let authMode = $state<AuthMode>('disabled');
    let setupRequired = $state(false);
    let authenticated = $state(true);
    let sessionExpiresAt = $state<string | null>(null);
    let checking = $state(true);

    function applyStatus(status: AuthStatus): void {
        authMode = status.auth_mode;
        setupRequired = status.setup_required;
        authenticated = status.auth_mode === 'disabled' || status.authenticated;
        sessionExpiresAt = status.session_expires_at;
        checking = false;
    }

    function applySession(session: AuthenticatedSession): void {
        authMode = 'password';
        setupRequired = false;
        authenticated = true;
        sessionExpiresAt = session.session_expires_at;
        checking = false;
    }

    function clearSession(recoverDrafts: boolean = true): void {
        if (recoverDrafts && authMode === 'password') armBrowserDrafts();
        if (authMode === 'password') authenticated = false;
        sessionExpiresAt = null;
        checking = false;
    }

    async function refresh(fetchFn?: typeof fetch): Promise<AuthStatus> {
        checking = true;
        try {
            const status = await getAuthStatus(fetchFn);
            applyStatus(status);
            return status;
        } finally {
            checking = false;
        }
    }

    function markExpired(): void {
        armBrowserDrafts();
        authMode = 'password';
        authenticated = false;
        sessionExpiresAt = null;
        checking = false;
    }

    onUnauthorized(() => clearSession(true));

    return {
        get authMode() { return authMode; },
        get setupRequired() { return setupRequired; },
        get authenticated() { return authenticated; },
        get sessionExpiresAt() { return sessionExpiresAt; },
        get checking() { return checking; },
        applyStatus,
        applySession,
        clearSession,
        refresh,
        markExpired,
    };
}

export const authState = createAuthState();
