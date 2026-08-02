import { sessionRemainingMs } from './auth-utils';

export type SessionExpiryState = 'inactive' | 'active' | 'expired';

export function nextExpiryState(
    expiresAt: string | null,
    nowMs: number = Date.now(),
): SessionExpiryState {
    const remaining = sessionRemainingMs(expiresAt, nowMs);
    if (remaining === null) return 'inactive';
    if (remaining <= 0) return 'expired';
    if (remaining <= 5 * 60 * 1000) return 'active';
    return 'inactive';
}
