import { browser } from '$app/environment';
import { isRedirect, redirect } from '@sveltejs/kit';
import { createProfile, listProfiles } from '$lib/api';
import { activeProfile } from '$lib/activeProfile.svelte';
import { getAuthStatus } from '$lib/auth-api';
import { resolveAuthDestination } from '$lib/auth-routing';
import { authState } from '$lib/auth-state.svelte';
import { profiles } from '$lib/profiles.svelte';
import { getReadiness } from '$lib/readiness-api';
import type { ReadinessResponse } from '$lib/readiness-types';
import { resolveReadinessDestination } from '$lib/readiness-routing';

export const ssr = false;

export const load = async ({ url, fetch }) => {
  const pathname = url.pathname;
  const isAuthRoute = pathname === '/login' || pathname === '/setup';

  const authStatus = await getAuthStatus(fetch);
  authState.applyStatus(authStatus);
  const authDestination = resolveAuthDestination(authStatus, pathname, url.search);
  if (authDestination) throw redirect(307, authDestination);

  if (isAuthRoute) {
    return {
      authStatus,
      isAuthRoute: true,
      readiness: null,
      activeProfileId: null,
    };
  }

  let readiness: ReadinessResponse | null = null;
  let activeProfileId: number | null = null;

  try {
    let response = await listProfiles(fetch);
    if (response.items.length === 0) {
      await createProfile({ label: 'Default', color: '#6366f1', icon: '💼' }, fetch);
      response = await listProfiles(fetch);
    }

    profiles.set(response.items);

    let storedId: number | null = activeProfile.current?.id ?? null;
    if (browser && storedId == null) {
      try {
        const raw = localStorage.getItem('activeProfile');
        if (raw) storedId = JSON.parse(raw)?.id ?? null;
      } catch {
        // Corrupted local preference is ignored and replaced by the first profile.
      }
    }

    const activeItem =
      (storedId != null ? response.items.find((profile) => profile.id === storedId) : null) ??
      response.items[0] ??
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
    activeProfileId = validated?.id ?? null;

    if (activeProfileId != null) {
      readiness = await getReadiness(activeProfileId, fetch);
      const readinessDestination = resolveReadinessDestination(readiness, pathname);
      if (readinessDestination) throw redirect(307, readinessDestination);
    }
  } catch (error: unknown) {
    if (isRedirect(error)) throw error;
    console.warn('Could not load readiness. Allowing navigation.', error);
  }

  return {
    authStatus,
    isAuthRoute: false,
    readiness,
    activeProfileId,
  };
};
