import { redirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { getOnboardingStatus, getStatus, listProfiles, createProfile } from '$lib/api';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

export const ssr = false;

export const load = async ({ url }) => {
  let isOnboarded = true;
  let isApiKeyConfigured = true; // fail open — if /api/status unreachable, don't lock users out

  try {
    const [onboarding, llmStatus] = await Promise.all([getOnboardingStatus(), getStatus()]);
    isOnboarded = onboarding.is_onboarded;
    isApiKeyConfigured = llmStatus.api_key_configured;

    try {
      let res = await listProfiles();

      // Fresh install: no profiles yet — create the default one
      if (res.items.length === 0) {
        await createProfile({ label: 'Default', color: '#6366f1', icon: '💼' });
        res = await listProfiles();
      }

      profiles.set(res.items);

      // Validate stored active profile or fall back to first
      let storedId: number | null = null;
      if (browser) {
        try {
          const raw = localStorage.getItem('activeProfile');
          if (raw) storedId = JSON.parse(raw)?.id ?? null;
        } catch { /* corrupted localStorage — ignore */ }
      }
      const activeItem = (storedId != null ? res.items.find(p => p.id === storedId) : null) ?? res.items[0] ?? null;
      const validated = activeItem ? { id: activeItem.id, label: activeItem.label, color: activeItem.color, icon: activeItem.icon, name: activeItem.name } : null;
      activeProfile.initFromStorage(validated);
    } catch (e) {
      console.warn('Could not load profiles', e);
    }

    const onSettings = url.pathname.startsWith('/settings');
    const onOnboarding = url.pathname.startsWith('/onboarding');
    const onProfile = url.pathname === '/profile' || url.pathname.startsWith('/profile/');

    // Gate 1: API key must be configured
    if (!isApiKeyConfigured && !onSettings) {
      throw redirect(307, '/settings');
    }

    // Gate 2: Profile must exist (onboarding)
    if (!isOnboarded && !onSettings && !onOnboarding && !onProfile) {
      throw redirect(307, '/onboarding');
    }
  } catch (err: any) {
    if (err?.status === 307) throw err;
    console.warn('Could not check onboarding status. Allowing navigation.', err);
  }

  return { isOnboarded, isApiKeyConfigured };
};
