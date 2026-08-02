import { describe, expect, test } from 'bun:test';

import { ApiError } from './api-error';
import { authenticationErrorMessage } from './auth-error';


describe('authenticationErrorMessage', () => {
    test('shows backend retry timing for authentication lockouts', () => {
        const error = new ApiError(
            'Too many attempts. Try again later.',
            'AUTH_LOCKED',
            { retry_after_seconds: 901 },
            429,
        );

        expect(authenticationErrorMessage(error, 'Sign in failed.'))
            .toBe('Too many attempts. Try again in 16 minutes.');
    });

    test('uses sanitized API messages and stable fallbacks', () => {
        expect(authenticationErrorMessage(new Error('Invalid password.'), 'Sign in failed.'))
            .toBe('Invalid password.');
        expect(authenticationErrorMessage('unexpected', 'Sign in failed.'))
            .toBe('Sign in failed.');
    });
});
