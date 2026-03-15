import type { ProfileListItem } from './types';

function createProfilesStore() {
  let list = $state<ProfileListItem[]>([]);
  return {
    get all() { return list; },
    set(items: ProfileListItem[]) { list = items; },
    remove(id: number) { list = list.filter((p) => p.id !== id); },
    upsert(item: ProfileListItem) {
      const idx = list.findIndex((p) => p.id === item.id);
      if (idx >= 0) list[idx] = item;
      else list = [...list, item];
    },
  };
}

export const profiles = createProfilesStore();
