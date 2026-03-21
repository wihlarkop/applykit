import { redirect, isRedirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { getOnboardingStatus, getStatus, listProfiles, createProfile } from '$lib/api';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

export const ssr = false;

export const load = async ({ url, fetch }) => {
  let isOnboarded = true;
  let isApiKeyConfigured = true;

  try {
    const [onboarding, llmStatus] = await Promise.all([getOnboardingStatus(fetch), getStatus(fetch)]);
    isOnboarded = onboarding.is_onboarded;
    isApiKeyConfigured = llmStatus.api_key_configured;

    try {
      let res = await listProfiles(fetch);

      if (res.items.length === 0) {
        await createProfile({ label: 'Default', color: '#6366f1', icon: '💼' }, fetch);
        res = await listProfiles(fetch);
      }

      profiles.set(res.items);

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
      console.warn('Could not load profiles. Using defaults.', e);
    }

    const onSettings = url.pathname.startsWith('/settings');
    const onOnboarding = url.pathname.startsWith('/onboarding');
    const onProfile = url.pathname === '/profile' || url.pathname.startsWith('/profile/');

    if (!isApiKeyConfigured && !onSettings) {
      throw redirect(307, '/settings');
    }

    if (!isOnboarded && !onSettings && !onOnboarding && !onProfile) {
      throw redirect(307, '/onboarding');
    }
  } catch (err: unknown) {
    if (isRedirect(err)) throw err;
    console.warn('Could not check onboarding status. Allowing navigation.', err);
  }

  return { isOnboarded, isApiKeyConfigured };
};
