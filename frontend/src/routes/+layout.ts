import { redirect, isRedirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { getOnboardingStatus, getStatus, listProfiles, createProfile } from '$lib/api';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

// Module-level cache — survives across navigations within the same browser session.
// Re-fetched only when the user visits /settings or /onboarding (where values can change).
let cachedOnboarded: boolean | null = null;
let cachedApiKeyConfigured: boolean | null = null;
let profilesLoaded = false;

export const ssr = false;

export const load = async ({ url, fetch }) => {
  const pathname = url.pathname;
  const onSettings = pathname.startsWith('/settings');
  const onOnboarding = pathname.startsWith('/onboarding');
  const onProfile = pathname === '/profile' || pathname.startsWith('/profile/');

  // Bust cache when visiting pages where these values can change
  if (onSettings || onOnboarding) {
    cachedOnboarded = null;
    cachedApiKeyConfigured = null;
    profilesLoaded = false;
  }

  let isOnboarded = cachedOnboarded ?? true;
  let isApiKeyConfigured = cachedApiKeyConfigured ?? true;

  try {
    // Only hit the API if we don't have cached values yet
    if (cachedOnboarded === null || cachedApiKeyConfigured === null) {
      const [onboarding, llmStatus] = await Promise.all([
        getOnboardingStatus(fetch),
        getStatus(fetch),
      ]);
      isOnboarded = onboarding.is_onboarded;
      isApiKeyConfigured = llmStatus.api_key_configured;
      cachedOnboarded = isOnboarded;
      cachedApiKeyConfigured = isApiKeyConfigured;
    }

    // Only fetch profiles once per session
    if (!profilesLoaded) {
      try {
        let res = await listProfiles(fetch);

        if (res.items.length === 0) {
          await createProfile({ label: 'Default', color: '#6366f1', icon: '💼' }, fetch);
          res = await listProfiles(fetch);
        }

        profiles.set(res.items);
        profilesLoaded = true;

        let storedId: number | null = null;
        if (browser) {
          try {
            const raw = localStorage.getItem('activeProfile');
            if (raw) storedId = JSON.parse(raw)?.id ?? null;
          } catch { /* corrupted localStorage — ignore */ }
        }
        const activeItem =
          (storedId != null ? res.items.find((p) => p.id === storedId) : null) ??
          res.items[0] ??
          null;
        const validated = activeItem
          ? { id: activeItem.id, label: activeItem.label, color: activeItem.color, icon: activeItem.icon, name: activeItem.name }
          : null;
        activeProfile.initFromStorage(validated);
      } catch (e) {
        console.warn('Could not load profiles. Using defaults.', e);
      }
    }

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
