import { browser } from '$app/environment';
import { redirect, isRedirect } from '@sveltejs/kit';
import { getOnboardingStatus, getStatus, listProfiles, createProfile } from '$lib/api';
import { getAuthStatus } from '$lib/auth-api';
import { resolveAuthDestination } from '$lib/auth-routing';
import { authState } from '$lib/auth-state.svelte';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

let cachedOnboarded: boolean | null = null;
let cachedApiKeyConfigured: boolean | null = null;
let profilesLoaded = false;

export const ssr = false;

export const load = async ({ url, fetch }) => {
  const pathname = url.pathname;
  const isAuthRoute = pathname === '/login' || pathname === '/setup';
  const onSettings = pathname.startsWith('/settings');
  const onOnboarding = pathname.startsWith('/onboarding');
  const onProfile = pathname === '/profile' || pathname.startsWith('/profile/');

  const authStatus = await getAuthStatus(fetch);
  authState.applyStatus(authStatus);
  const authDestination = resolveAuthDestination(authStatus, pathname, url.search);
  if (authDestination) throw redirect(307, authDestination);

  if (isAuthRoute) {
    return {
      authStatus,
      isAuthRoute: true,
      isOnboarded: cachedOnboarded ?? true,
      isApiKeyConfigured: cachedApiKeyConfigured ?? true,
    };
  }

  if (onSettings || onOnboarding) {
    cachedOnboarded = null;
    cachedApiKeyConfigured = null;
    profilesLoaded = false;
  }

  let isOnboarded = cachedOnboarded ?? true;
  let isApiKeyConfigured = cachedApiKeyConfigured ?? true;

  try {
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
          (storedId != null ? res.items.find((profile) => profile.id === storedId) : null) ??
          res.items[0] ??
          null;
        const validated = activeItem
          ? {
              id: activeItem.id,
              label: activeItem.label,
              color: activeItem.color,
              icon: activeItem.icon,
              name: activeItem.name,
            }
          : null;
        activeProfile.initFromStorage(validated);
      } catch (error) {
        console.warn('Could not load profiles. Using defaults.', error);
      }
    }

    if (!isApiKeyConfigured && !onSettings) {
      throw redirect(307, '/settings');
    }

    if (!isOnboarded && !onSettings && !onOnboarding && !onProfile) {
      throw redirect(307, '/onboarding');
    }
  } catch (error: unknown) {
    if (isRedirect(error)) throw error;
    console.warn('Could not check onboarding status. Allowing navigation.', error);
  }

  return { authStatus, isAuthRoute: false, isOnboarded, isApiKeyConfigured };
};
