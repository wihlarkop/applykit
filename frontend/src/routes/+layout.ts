import { redirect } from '@sveltejs/kit';
import { getOnboardingStatus, listProfiles, createProfile } from '$lib/api';
import { profiles } from '$lib/profiles.svelte';
import { activeProfile } from '$lib/activeProfile.svelte';

export const ssr = false;

export const load = async ({ url }) => {
  let isOnboarded = true;

  try {
    const status = await getOnboardingStatus();
    isOnboarded = status.is_onboarded;

    try {
      let res = await listProfiles();

      // Fresh install: no profiles yet — create the default one
      if (res.items.length === 0) {
        await createProfile({ label: 'Default', color: '#6366f1', icon: '💼' });
        res = await listProfiles();
      }

      profiles.set(res.items);

      // Validate stored active profile or fall back to first
      const stored = typeof localStorage !== 'undefined'
        ? localStorage.getItem('activeProfile')
        : null;
      const storedProfile = stored ? JSON.parse(stored) : null;
      const validStored = storedProfile && res.items.some((p) => p.id === storedProfile.id);
      const fallback = res.items[0]
        ? { id: res.items[0].id, label: res.items[0].label, color: res.items[0].color, icon: res.items[0].icon }
        : null;
      activeProfile.initFromStorage(validStored ? storedProfile : fallback);
    } catch (e) {
      console.warn('Could not load profiles', e);
    }

    if (url.pathname.startsWith('/onboarding')) return { isOnboarded };
    if (!isOnboarded) {
      if (url.pathname.startsWith('/profile')) return { isOnboarded };
      throw redirect(307, '/onboarding');
    }
  } catch (err: any) {
    if (err?.status === 307) throw err;
    console.warn('Could not check onboarding status. Allowing navigation.', err);
  }

  return { isOnboarded };
};
