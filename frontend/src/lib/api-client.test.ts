import { describe, expect, test } from 'bun:test';

import { apiFetch, onUnauthorized } from './api-client';


describe('apiFetch', () => {
    test('includes credentials and preserves caller headers', async () => {
        let captured: RequestInit | undefined;
        const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
            captured = init;
            return new Response('{}', { status: 200 });
        };

        await apiFetch('/test', {
            method: 'GET',
            headers: { 'X-Custom': 'value' },
        }, fetchFn as typeof fetch, '');

        expect(captured?.credentials).toBe('include');
        expect(new Headers(captured?.headers).get('X-Custom')).toBe('value');
        expect(new Headers(captured?.headers).get('X-CSRF-Token')).toBeNull();
    });

    test('adds CSRF to unsafe methods without replacing headers', async () => {
        let captured: RequestInit | undefined;
        const fetchFn = async (_input: RequestInfo | URL, init?: RequestInit) => {
            captured = init;
            return new Response('{}', { status: 200 });
        };

        await apiFetch('/test', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
        }, fetchFn as typeof fetch, 'applykit_csrf=csrf-value');

        const headers = new Headers(captured?.headers);
        expect(headers.get('Content-Type')).toBe('application/json');
        expect(headers.get('X-CSRF-Token')).toBe('csrf-value');
    });

    test('notifies once on 401 and never replays the request', async () => {
        let fetchCount = 0;
        let unauthorizedCount = 0;
        const unsubscribe = onUnauthorized(() => unauthorizedCount++);
        const fetchFn = async () => {
            fetchCount++;
            return new Response('{}', { status: 401 });
        };

        const response = await apiFetch('/test', { method: 'POST' }, fetchFn as typeof fetch, '');
        unsubscribe();

        expect(response.status).toBe(401);
        expect(fetchCount).toBe(1);
        expect(unauthorizedCount).toBe(1);
    });
});
