import { describe, expect, test } from 'bun:test';

import { loginSuccessDestination } from './login-flow';


describe('loginSuccessDestination', () => {
    test('returns a sanitized destination for a normal login', () => {
        expect(loginSuccessDestination(new URL('http://applykit.local/login?returnTo=%2Fhistory')))
            .toEqual({ kind: 'navigate', path: '/history' });
        expect(loginSuccessDestination(new URL('http://applykit.local/login?returnTo=https%3A%2F%2Fevil.example')))
            .toEqual({ kind: 'navigate', path: '/' });
    });

    test('returns a reauthentication completion state', () => {
        expect(loginSuccessDestination(new URL('http://applykit.local/login?reauth=1')))
            .toEqual({ kind: 'reauth-complete' });
    });
});
