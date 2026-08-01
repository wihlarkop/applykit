import { describe, expect, test } from 'bun:test';

import { ApiError, parseApiError } from './api-error';


describe('parseApiError', () => {
    test('reads the new nested error envelope', () => {
        const error = parseApiError(
            {
                error: {
                    code: 'PROFILE_NOT_FOUND',
                    message: 'Profile was not found.',
                    details: { profile_id: 42 },
                },
            },
            'Fallback message.',
            404
        );

        expect(error).toBeInstanceOf(ApiError);
        expect(error.message).toBe('Profile was not found.');
        expect(error.code).toBe('PROFILE_NOT_FOUND');
        expect(error.details).toEqual({ profile_id: 42 });
        expect(error.status).toBe(404);
    });

    test('supports the previous top-level error shape', () => {
        const error = parseApiError(
            {
                message: 'Validation failed.',
                error_code: 'VALIDATION_ERROR',
                details: { field: 'name' },
            },
            'Fallback message.',
            422
        );

        expect(error.message).toBe('Validation failed.');
        expect(error.code).toBe('VALIDATION_ERROR');
        expect(error.details).toEqual({ field: 'name' });
    });

    test('supports legacy detail and code fields', () => {
        const error = parseApiError(
            { detail: 'Unknown provider', code: 'NOT_FOUND' },
            'Fallback message.',
            404
        );

        expect(error.message).toBe('Unknown provider');
        expect(error.code).toBe('NOT_FOUND');
    });

    test('does not stringify nested objects into a public message', () => {
        const secret = 'sk-secret-value';
        const error = parseApiError(
            { detail: { api_key: secret } },
            'Safe fallback.',
            500
        );

        expect(error.message).toBe('Safe fallback.');
        expect(error.message).not.toContain(secret);
    });

    test('prefers the new envelope when multiple formats are present', () => {
        const error = parseApiError(
            {
                error: { code: 'HTTP_ERROR', message: 'New message.', details: {} },
                message: 'Old message.',
                detail: 'Older message.',
            },
            'Fallback message.'
        );

        expect(error.message).toBe('New message.');
        expect(error.code).toBe('HTTP_ERROR');
    });
});
