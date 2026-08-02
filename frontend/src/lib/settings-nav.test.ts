import { describe, expect, test } from 'bun:test';

import { settingsTabs } from './settings-nav';


describe('settingsTabs', () => {
    test('shows only AI integrations in disabled mode', () => {
        expect(settingsTabs('disabled')).toEqual([
            { href: '/settings', label: 'AI Integrations' },
        ]);
    });

    test('shows Security only in password mode', () => {
        expect(settingsTabs('password')).toEqual([
            { href: '/settings', label: 'AI Integrations' },
            { href: '/settings/security', label: 'Security' },
        ]);
    });
});
