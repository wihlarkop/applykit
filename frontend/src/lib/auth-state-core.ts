import type { AuthenticatedSession, AuthMode, AuthStatus } from './auth-types';

export interface AuthStateCore {
    authMode: AuthMode;
    setupRequired: boolean;
    authenticated: boolean;
    sessionExpiresAt: string | null;
    checking: boolean;
    applyStatus(status: AuthStatus): void;
    applySession(session: AuthenticatedSession): void;
    clearSession(): void;
    markExpired(): void;
    setChecking(value: boolean): void;
}

export function createAuthStateCore(): AuthStateCore {
    return {
        authMode: 'disabled',
        setupRequired: false,
        authenticated: true,
        sessionExpiresAt: null,
        checking: true,

        applyStatus(status) {
            this.authMode = status.auth_mode;
            this.setupRequired = status.setup_required;
            this.authenticated = status.auth_mode === 'disabled' || status.authenticated;
            this.sessionExpiresAt = status.session_expires_at;
            this.checking = false;
        },

        applySession(session) {
            this.authMode = 'password';
            this.setupRequired = false;
            this.authenticated = session.authenticated;
            this.sessionExpiresAt = session.session_expires_at;
            this.checking = false;
        },

        clearSession() {
            if (this.authMode === 'password') this.authenticated = false;
            this.sessionExpiresAt = null;
            this.checking = false;
        },

        markExpired() {
            this.authMode = 'password';
            this.authenticated = false;
            this.sessionExpiresAt = null;
            this.checking = false;
        },

        setChecking(value) {
            this.checking = value;
        },
    };
}
