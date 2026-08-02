import { describe, expect, test } from 'bun:test';

import {
    DRAFT_PREFIX,
    armDraftRecovery,
    clearDraft,
    consumeDraft,
    draftKey,
    saveDraft,
} from './draft-recovery';

class MemoryStorage implements Storage {
    private values = new Map<string, string>();

    get length(): number { return this.values.size; }

    clear(): void { this.values.clear(); }

    getItem(key: string): string | null { return this.values.get(key) ?? null; }

    key(index: number): string | null { return [...this.values.keys()][index] ?? null; }

    removeItem(key: string): void { this.values.delete(key); }

    setItem(key: string, value: string): void { this.values.set(key, value); }
}

describe('draft recovery storage', () => {
    const now = Date.parse('2026-08-02T10:00:00Z');

    test('builds route keys with optional profile isolation', () => {
        expect(draftKey('/generate')).toBe(`${DRAFT_PREFIX}/generate`);
        expect(draftKey('/profile', 7)).toBe(`${DRAFT_PREFIX}/profile:profile:7`);
    });

    test('saves an unarmed versioned working copy', () => {
        const storage = new MemoryStorage();
        const key = draftKey('/generate', 3);

        expect(saveDraft(storage, key, { jobDescription: 'Backend role' }, now)).toBe(true);
        expect(JSON.parse(storage.getItem(key)!)).toEqual({
            version: 1,
            savedAt: now,
            armed: false,
            data: { jobDescription: 'Backend role' },
        });
    });

    test('arms every ApplyKit draft and leaves unrelated storage untouched', () => {
        const storage = new MemoryStorage();
        const first = draftKey('/generate', 1);
        const second = draftKey('/cover-letter', 1);
        saveDraft(storage, first, { value: 'one' }, now);
        saveDraft(storage, second, { value: 'two' }, now);
        storage.setItem('other-app', JSON.stringify({ armed: false }));

        armDraftRecovery(storage);

        expect(JSON.parse(storage.getItem(first)!).armed).toBe(true);
        expect(JSON.parse(storage.getItem(second)!).armed).toBe(true);
        expect(storage.getItem('other-app')).toBe(JSON.stringify({ armed: false }));
    });

    test('consumes only armed drafts and removes the storage copy immediately', () => {
        const storage = new MemoryStorage();
        const key = draftKey('/smart-apply', 4);
        saveDraft(storage, key, { roleTitle: 'Senior Engineer' }, now);

        expect(consumeDraft(storage, key, now)).toBeNull();
        expect(storage.getItem(key)).not.toBeNull();

        armDraftRecovery(storage);
        expect(consumeDraft<{ roleTitle: string }>(storage, key, now)).toEqual({
            roleTitle: 'Senior Engineer',
        });
        expect(storage.getItem(key)).toBeNull();
    });

    test('removes malformed, unsupported, and expired entries', () => {
        const storage = new MemoryStorage();
        const malformed = draftKey('/malformed');
        const unsupported = draftKey('/unsupported');
        const expired = draftKey('/expired');
        storage.setItem(malformed, '{');
        storage.setItem(unsupported, JSON.stringify({ version: 2, savedAt: now, armed: true, data: {} }));
        storage.setItem(expired, JSON.stringify({
            version: 1,
            savedAt: now - 24 * 60 * 60 * 1000 - 1,
            armed: true,
            data: { stale: true },
        }));

        expect(consumeDraft(storage, malformed, now)).toBeNull();
        expect(consumeDraft(storage, unsupported, now)).toBeNull();
        expect(consumeDraft(storage, expired, now)).toBeNull();
        expect(storage.length).toBe(0);
    });

    test('rejects File and Blob values recursively without replacing the previous draft', () => {
        const storage = new MemoryStorage();
        const key = draftKey('/import', 2);
        saveDraft(storage, key, { pastedText: 'safe' }, now);
        const previous = storage.getItem(key);

        expect(saveDraft(storage, key, { nested: { upload: new File(['secret'], 'cv.pdf') } }, now + 1)).toBe(false);
        expect(saveDraft(storage, key, { nested: [new Blob(['secret'])] }, now + 1)).toBe(false);
        expect(storage.getItem(key)).toBe(previous);
    });

    test('clearDraft removes the matching entry', () => {
        const storage = new MemoryStorage();
        const key = draftKey('/profile', 9);
        saveDraft(storage, key, { name: 'Wihlarko' }, now);
        clearDraft(storage, key);
        expect(storage.getItem(key)).toBeNull();
    });
});
