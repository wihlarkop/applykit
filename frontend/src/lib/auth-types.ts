export type AuthMode = 'disabled' | 'password';

export interface AuthStatus {
    auth_mode: AuthMode;
    setup_required: boolean;
    authenticated: boolean;
    session_expires_at: string | null;
}

export interface AuthenticatedSession {
    authenticated: true;
    remember_device: boolean;
    session_expires_at: string;
}

export interface SecuritySummary {
    other_sessions: number;
}

export interface RevokeSessionsResponse {
    revoked_sessions: number;
}
