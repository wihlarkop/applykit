export const DRAFT_PREFIX = 'applykit:draft:v1:';
export const DRAFT_TTL_MS = 24 * 60 * 60 * 1000;

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

    if (Array.isArray(value)) return value.some((item) => containsBinary(item, seen));
    return Object.values(value as Record<string, unknown>).some((item) => containsBinary(item, seen));
}

export function saveDraft<T>(
    storage: Storage,
    key: string,
    data: T,
    nowMs: number = Date.now(),
): boolean {
    if (containsBinary(data)) return false;

    const envelope: DraftEnvelope<T> = {
        version: 1,
        savedAt: nowMs,
        armed: false,
        data,
    };

    try {
        storage.setItem(key, JSON.stringify(envelope));
        return true;
    } catch {
        return false;
    }
}

function parseEnvelope(value: string): DraftEnvelope<unknown> | null {
    try {
        const parsed = JSON.parse(value) as Partial<DraftEnvelope<unknown>>;
        if (
            parsed.version !== 1
            || typeof parsed.savedAt !== 'number'
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

export function armDraftRecovery(storage: Storage): void {
    const keys: string[] = [];
    try {
        for (let index = 0; index < storage.length; index += 1) {
            const key = storage.key(index);
            if (key?.startsWith(DRAFT_PREFIX)) keys.push(key);
        }
    } catch {
        return;
    }

    for (const key of keys) {
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
            // Storage failures must never interrupt authentication handling.
        }
    }
}

export function consumeDraft<T>(
    storage: Storage,
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
    if (
        !envelope
        || nowMs - envelope.savedAt > DRAFT_TTL_MS
        || envelope.savedAt > nowMs
    ) {
        clearDraft(storage, key);
        return null;
    }
    if (!envelope.armed) return null;

    clearDraft(storage, key);
    return envelope.data as T;
}

export function clearDraft(storage: Storage, key: string): void {
    try {
        storage.removeItem(key);
    } catch {
        // Draft cleanup is best effort.
    }
}
