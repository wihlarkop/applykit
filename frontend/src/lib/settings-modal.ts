export type SettingsModalMode = 'connect' | 'edit';
export type ConnectionTestMode = 'draft' | 'stored' | 'disabled';

export function modalMode(
  initialProviderId: string,
  initialModel: string,
  initialApiKeyConfigured: boolean,
): SettingsModalMode {
  return initialProviderId && (Boolean(initialModel) || initialApiKeyConfigured)
    ? 'edit'
    : 'connect';
}

export function modalTitle(
  mode: SettingsModalMode,
  providerLabel: string,
): string {
  if (!providerLabel) return 'Connect AI provider';
  return `${mode === 'edit' ? 'Edit' : 'Connect'} ${providerLabel}`;
}

export function primaryActionLabel(
  mode: SettingsModalMode,
  isActive: boolean,
): string {
  return mode === 'edit' && isActive
    ? 'Save changes'
    : 'Save & set active';
}

export function connectionTestMode({
  requiresApiKey,
  apiKey,
  canReuseStoredKey,
  providerId,
}: {
  requiresApiKey: boolean;
  apiKey: string;
  canReuseStoredKey: boolean;
  providerId: string;
}): ConnectionTestMode {
  if (!providerId) return 'disabled';
  if (!requiresApiKey) return 'draft';
  if (apiKey.trim()) return 'draft';
  if (canReuseStoredKey) return 'stored';
  return 'disabled';
}
