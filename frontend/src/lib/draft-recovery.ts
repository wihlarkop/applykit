export const DRAFT_PREFIX = 'applykit:draft:v1:';
export const DRAFT_TTL_MS = 24 * 60 * 60 * 1000;

export type SessionEndReason = 'expired' | 'unauthorized' | 'manual';

export interface StorageLike {
  readonly length: number;
  getItem(key: string): string | null;
  key(index: number): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): void;
}

interface DraftEnvelope<T> {
  version: 1;
  savedAt: number;
  armed: boolean;
  data: T;
}

function normalizeRoute(route: string): string {
  const trimmed = route.trim();
  if (!trimmed) return '/';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

export function draftKey(route: string, profileId?: number | null): string {
  const normalized = normalizeRoute(route);
  return `${DRAFT_PREFIX}${normalized}${profileId == null ? '' : `:profile:${profileId}`}`;
}

function containsBinary(value: unknown, seen = new Set<object>()): boolean {
  if (typeof File !== 'undefined' && value instanceof File) return true;
  if (typeof Blob !== 'undefined' && value instanceof Blob) return true;
  if (value === null || typeof value !== 'object') return false;
  if (seen.has(value)) return false;
  seen.add(value);

  if (Array.isArray(value)) {
    return value.some((item) => containsBinary(item, seen));
  }
  return Object.values(value as Record<string, unknown>).some((item) => containsBinary(item, seen));
}

function parseEnvelope(value: string): DraftEnvelope<unknown> | null {
  try {
    const parsed = JSON.parse(value) as Partial<DraftEnvelope<unknown>>;
    if (
      parsed.version !== 1
      || !Number.isFinite(parsed.savedAt)
      || typeof parsed.armed !== 'boolean'
      || !Object.prototype.hasOwnProperty.call(parsed, 'data')
    ) {
      return null;
    }
    return parsed as DraftEnvelope<unknown>;
  } catch {
    return null;
  }
}

function draftKeys(storage: StorageLike): string[] {
  const keys: string[] = [];
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key?.startsWith(DRAFT_PREFIX)) keys.push(key);
    }
  } catch {
    return [];
  }
  return keys;
}

function currentArmedState(storage: StorageLike, key: string): boolean {
  try {
    const raw = storage.getItem(key);
    return raw ? parseEnvelope(raw)?.armed === true : false;
  } catch {
    return false;
  }
}

export function saveDraft<T>(
  storage: StorageLike,
  key: string,
  data: T,
  nowMs: number = Date.now(),
): boolean {
  if (containsBinary(data)) return false;

  const envelope: DraftEnvelope<T> = {
    version: 1,
    savedAt: nowMs,
    armed: currentArmedState(storage, key),
    data,
  };

  try {
    storage.setItem(key, JSON.stringify(envelope));
    return true;
  } catch {
    return false;
  }
}

export function armDraftRecovery(storage: StorageLike): void {
  for (const key of draftKeys(storage)) {
    try {
      const raw = storage.getItem(key);
      if (!raw) continue;
      const envelope = parseEnvelope(raw);
      if (!envelope) {
        storage.removeItem(key);
        continue;
      }
      storage.setItem(key, JSON.stringify({ ...envelope, armed: true }));
    } catch {
      // Browser storage failures must not interrupt authentication handling.
    }
  }
}

export function consumeDraft<T>(
  storage: StorageLike,
  key: string,
  nowMs: number = Date.now(),
): T | null {
  let raw: string | null;
  try {
    raw = storage.getItem(key);
  } catch {
    return null;
  }
  if (!raw) return null;

  const envelope = parseEnvelope(raw);
  clearDraft(storage, key);
  if (
    !envelope
    || !envelope.armed
    || envelope.savedAt > nowMs
    || nowMs - envelope.savedAt > DRAFT_TTL_MS
  ) {
    return null;
  }
  return envelope.data as T;
}

export function clearDraft(storage: StorageLike, key: string): void {
  try {
    storage.removeItem(key);
  } catch {
    // Draft cleanup is best effort.
  }
}

export function clearAllDrafts(storage: StorageLike): void {
  for (const key of draftKeys(storage)) {
    clearDraft(storage, key);
  }
}

export function updateDraftsForSessionEnd(
  storage: StorageLike,
  reason: SessionEndReason,
): void {
  if (reason === 'manual') {
    clearAllDrafts(storage);
  } else {
    armDraftRecovery(storage);
  }
}
