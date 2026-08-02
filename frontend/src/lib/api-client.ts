import { isUnsafeMethod, readCookie } from './auth-utils';

type UnauthorizedHandler = () => void;
const unauthorizedHandlers = new Set<UnauthorizedHandler>();

export function onUnauthorized(handler: UnauthorizedHandler): () => void {
    unauthorizedHandlers.add(handler);
    return () => unauthorizedHandlers.delete(handler);
}

function notifyUnauthorized(): void {
    for (const handler of unauthorizedHandlers) handler();
}

export async function apiFetch(
    input: RequestInfo | URL,
    init: RequestInit = {},
    fetchFn: typeof fetch = fetch,
    cookieSource?: string,
): Promise<Response> {
    const method = (init.method ?? 'GET').toUpperCase();
    const headers = new Headers(init.headers);

    if (isUnsafeMethod(method)) {
        const csrf = readCookie('applykit_csrf', cookieSource);
        if (csrf) headers.set('X-CSRF-Token', csrf);
    }

    const response = await fetchFn(input, {
        ...init,
        method,
        headers,
        credentials: 'include',
    });

    if (response.status === 401) notifyUnauthorized();
    return response;
}
