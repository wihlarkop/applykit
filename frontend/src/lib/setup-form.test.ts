import { describe, expect, test } from 'bun:test';

import { setupFormEligible } from './setup-form';


describe('setupFormEligible', () => {
    test('requires a token, a valid-length password, and matching confirmation', () => {
        expect(setupFormEligible('token', 'a'.repeat(12), 'a'.repeat(12))).toBeTrue();
        expect(setupFormEligible('', 'a'.repeat(12), 'a'.repeat(12))).toBeFalse();
        expect(setupFormEligible('token', 'a'.repeat(11), 'a'.repeat(11))).toBeFalse();
        expect(setupFormEligible('token', 'a'.repeat(12), 'b'.repeat(12))).toBeFalse();
    });
});
