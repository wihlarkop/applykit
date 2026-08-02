import type { AuthMode } from './auth-types';

export interface SettingsTab {
    href: string;
    label: string;
}

export function settingsTabs(authMode: AuthMode): SettingsTab[] {
    const tabs: SettingsTab[] = [
        { href: '/settings', label: 'AI Integrations' },
    ];
    if (authMode === 'password') {
        tabs.push({ href: '/settings/security', label: 'Security' });
    }
    return tabs;
}
