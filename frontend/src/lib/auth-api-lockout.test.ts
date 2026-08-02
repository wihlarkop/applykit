import { expect, test } from 'bun:test';

import { loginOwner } from './auth-api';


test('login surfaces backend lockout retry timing', async () => {
    const fetchFn = async () => new Response(JSON.stringify({
        error: {
            code: 'AUTH_LOCKED',
            message: 'Too many attempts. Try again later.',
            details: { retry_after_seconds: 61 },
        },
    }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' },
    });

    await expect(loginOwner(
        { password: 'wrong password', remember_device: false },
        fetchFn as typeof fetch,
    )).rejects.toMatchObject({
        message: 'Too many attempts. Try again in 2 minutes.',
        code: 'AUTH_LOCKED',
        status: 429,
    });
});
