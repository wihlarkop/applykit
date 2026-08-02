export const DEFAULT_OLLAMA_BASE_URL = 'http://localhost:11434';

export type SettingsModalMode = 'connect' | 'edit';
export type ConnectionTestMode = 'draft' | 'stored' | 'disabled';
export type SettingsSaveResult =
  | { status: 'saved' }
  | { status: 'save_failed'; error: unknown }
  | { status: 'refresh_failed'; error: unknown };

export function normalizeOllamaBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

export function ollamaBaseUrlError(value: string): string | null {
  const normalized = normalizeOllamaBaseUrl(value);
  if (!normalized) return 'Enter the Ollama server URL.';

  try {
    const parsed = new URL(normalized);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return 'Base URL must start with http:// or https://.';
    }
    if (!parsed.hostname) return 'Base URL must include a valid host.';
    if (parsed.username || parsed.password) {
      return 'Base URL must not contain embedded credentials.';
    }
    if (parsed.search || parsed.hash) {
      return 'Base URL must not include a query string or fragment.';
    }
  } catch {
    return 'Enter a valid URL including http:// or https://.';
  }

  return null;
}

export function focusTrapTarget<T>(
  focusable: readonly T[],
  activeElement: T | null,
  panelElement: T,
  shiftKey: boolean,
): T | null {
  if (focusable.length === 0) return null;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (shiftKey && (activeElement === panelElement || activeElement === first)) {
    return last;
  }
  if (!shiftKey && activeElement === last) return first;
  return null;
}

export function focusRestorationTarget<T extends { isConnected: boolean }>(
  candidates: readonly (T | null)[],
): T | null {
  return candidates.find((candidate): candidate is T => Boolean(candidate?.isConnected)) ?? null;
}

export async function saveSettingsWithRefresh(
  persist: () => Promise<unknown>,
  refresh: () => Promise<void>,
): Promise<SettingsSaveResult> {
  try {
    await persist();
  } catch (error) {
    return { status: 'save_failed', error };
  }

  try {
    await refresh();
  } catch (error) {
    return { status: 'refresh_failed', error };
  }

  return { status: 'saved' };
}

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
