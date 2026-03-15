import { browser } from '$app/environment';

export type ActiveProfile = {
  id: number;
  label: string;
  color: string;
  icon: string;
};

function createActiveProfile() {
  let profile = $state<ActiveProfile | null>(null);

  return {
    get current() { return profile; },
    set(p: ActiveProfile) {
      profile = p;
      if (browser) localStorage.setItem('activeProfile', JSON.stringify(p));
    },
    // `validated` is already validated by +layout.ts against the live profile list.
    // We must NOT re-read localStorage here — it may contain a deleted profile ID.
    initFromStorage(validated: ActiveProfile | null) {
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
