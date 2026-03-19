import { browser } from '$app/environment';
import type { ProfileData, ProfileListItem } from './types';

export type ActiveProfile = {
  id: number;
  label: string;
  color: string;
  icon: string;
  name: string;
};

type ProfilePick = Pick<ProfileData, 'id' | 'label' | 'color' | 'icon' | 'name'> & Partial<Pick<ProfileListItem, 'id' | 'label' | 'color' | 'icon' | 'name'>>;

function createActiveProfile() {
  let profile = $state<ActiveProfile | null>(null);

  return {
    get current() { return profile; },

    set(p: ActiveProfile) {
      profile = p;
      if (browser) localStorage.setItem('activeProfile', JSON.stringify(p));
    },

    setFromProfileData(p: ProfilePick) {
      const ap: ActiveProfile = {
        id: p.id!,
        label: p.label ?? '',
        color: p.color ?? '',
        icon: p.icon ?? '',
        name: p.name ?? '',
      };
      profile = ap;
      if (browser) localStorage.setItem('activeProfile', JSON.stringify(ap));
    },

    // `validated` is already validated by +layout.ts against the live profile list.
    // We must NOT re-read localStorage here — it may contain a deleted profile ID.
    initFromStorage(validated: ActiveProfile | null) {
      // Skip re-assignment if the same profile ID is already set — prevents
      // reactive effects (e.g. clearing coverLetterText) from firing on every
      // layout re-run when the profile hasn't actually changed.
      if (profile?.id === validated?.id) return;
      profile = validated;
      if (!browser) return;
      if (validated) localStorage.setItem('activeProfile', JSON.stringify(validated));
      else localStorage.removeItem('activeProfile');
    },

    clear() {
      profile = null;
      if (browser) localStorage.removeItem('activeProfile');
    },
  };
}

export const activeProfile = createActiveProfile();
