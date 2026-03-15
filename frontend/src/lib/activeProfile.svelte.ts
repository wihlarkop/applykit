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
    initFromStorage(fallback: ActiveProfile | null) {
      if (!browser) { profile = fallback; return; }
      const stored = localStorage.getItem('activeProfile');
      if (stored) {
        try { profile = JSON.parse(stored) as ActiveProfile; return; }
        catch { /* fall through */ }
      }
      profile = fallback;
      if (fallback) localStorage.setItem('activeProfile', JSON.stringify(fallback));
    },
    clear() {
      profile = null;
      if (browser) localStorage.removeItem('activeProfile');
    },
  };
}

export const activeProfile = createActiveProfile();
