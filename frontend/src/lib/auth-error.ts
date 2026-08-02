import { ApiError } from './api-error';

function retryAfterSeconds(details: unknown): number | null {
    if (typeof details !== 'object' || details === null || Array.isArray(details)) return null;
    const value = (details as Record<string, unknown>).retry_after_seconds;
    return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
}

export function authenticationErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError && error.code === 'AUTH_LOCKED') {
        const seconds = retryAfterSeconds(error.details);
        if (seconds !== null) {
            const minutes = Math.max(1, Math.ceil(seconds / 60));
            return `Too many attempts. Try again in ${minutes} minute${minutes === 1 ? '' : 's'}.`;
        }
    }
    return error instanceof Error && error.message ? error.message : fallback;
}
