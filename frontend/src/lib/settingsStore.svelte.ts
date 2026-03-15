function createSettingsStore() {
  let version = $state(0);

  return {
    get version() {
      return version;
    },
    notify() {
      version++;
    },
  };
}

export const settingsStore = createSettingsStore();
