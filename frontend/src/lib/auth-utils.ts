const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const AUTH_LOOP_PATHS = new Set(['/login', '/setup']);
const MIN_PASSWORD_LENGTH = 12;
const MAX_PASSWORD_LENGTH = 128;
const EXPIRY_WARNING_MS = 5 * 60 * 1000;


export function sanitizeReturnTo(value: string | null | undefined): string {
    if (!value || !value.startsWith('/') || value.startsWith('//')) return '/';

    try {
        const decoded = decodeURIComponent(value);
        if (decoded.startsWith('//') || decoded.includes('://')) return '/';

        const url = new URL(value, 'http://applykit.local');
        if (url.origin !== 'http://applykit.local') return '/';
        if (AUTH_LOOP_PATHS.has(url.pathname)) return '/';
        return `${url.pathname}${url.search}${url.hash}`;
    } catch {
        return '/';
    }
}


export function readCookie(name: string, cookieSource?: string): string | null {
    const source = cookieSource ?? (typeof document === 'undefined' ? '' : document.cookie);
    for (const item of source.split(';')) {
        const [rawName, ...rawValueParts] = item.trim().split('=');
        if (rawName !== name) continue;
        try {
            return decodeURIComponent(rawValueParts.join('='));
        } catch {
            return null;
        }
    }
    return null;
}


export function isUnsafeMethod(method?: string): boolean {
    if (!method) return false;
    return !SAFE_METHODS.has(method.toUpperCase());
}


export function passwordFormEligible(
    password: string,
    confirmation: string,
    tokenRequired?: string,
): boolean {
    return password.length >= MIN_PASSWORD_LENGTH
        && password.length <= MAX_PASSWORD_LENGTH
        && password === confirmation
        && (tokenRequired === undefined || tokenRequired.trim().length > 0);
}


export function sessionRemainingMs(
    expiresAt: string | null,
    nowMs: number = Date.now(),
): number | null {
    if (!expiresAt) return null;
    const expiryMs = Date.parse(expiresAt);
    if (!Number.isFinite(expiryMs)) return null;
    return expiryMs - nowMs;
}


export function shouldShowExpiryWarning(
    expiresAt: string | null,
    nowMs: number = Date.now(),
): boolean {
    const remaining = sessionRemainingMs(expiresAt, nowMs);
    return remaining !== null && remaining > 0 && remaining <= EXPIRY_WARNING_MS;
}
