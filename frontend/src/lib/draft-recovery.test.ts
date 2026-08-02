import { describe, expect, test } from 'bun:test';

import {
  DRAFT_PREFIX,
  DRAFT_TTL_MS,
  consumeDraft,
  draftKey,
  saveDraft,
  updateDraftsForSessionEnd,
  type StorageLike,
} from './draft-recovery';

class MemoryStorage implements StorageLike {
  private values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

const now = Date.parse('2026-08-02T10:00:00Z');

describe('session-expiry draft recovery', () => {
  test('builds profile-isolated route keys', () => {
    expect(draftKey('/generate')).toBe(`${DRAFT_PREFIX}/generate`);
    expect(draftKey('/profile', 7)).toBe(`${DRAFT_PREFIX}/profile:profile:7`);
  });

  test('ordinary reload discards an unarmed working copy', () => {
    const storage = new MemoryStorage();
    const key = draftKey('/cover-letter', 7);
    saveDraft(storage, key, { jobDescription: 'Backend role' }, now);

    expect(consumeDraft(storage, key, now + 1)).toBeNull();
    expect(storage.getItem(key)).toBeNull();
  });

  test('session expiry and 401 arm drafts without touching unrelated storage', () => {
    for (const reason of ['expired', 'unauthorized'] as const) {
      const storage = new MemoryStorage();
      const key = draftKey('/generate', 7);
      saveDraft(storage, key, { jobDescription: reason }, now);
      storage.setItem('theme', 'dark');

      updateDraftsForSessionEnd(storage, reason);

      expect(consumeDraft(storage, key, now + 1)).toEqual({ jobDescription: reason });
      expect(storage.getItem('theme')).toBe('dark');
    }
  });

  test('manual sign-out removes drafts instead of arming them', () => {
    const storage = new MemoryStorage();
    const key = draftKey('/profile', 7);
    saveDraft(storage, key, { name: 'Wihlarko' }, now);
    storage.setItem('theme', 'dark');

    updateDraftsForSessionEnd(storage, 'manual');

    expect(storage.getItem(key)).toBeNull();
    expect(storage.getItem('theme')).toBe('dark');
  });

  test('keeps a draft armed when a final reactive write stores newer state', () => {
    const storage = new MemoryStorage();
    const key = draftKey('/smart-apply', 7);
    saveDraft(storage, key, { roleTitle: 'Before expiry' }, now);
    updateDraftsForSessionEnd(storage, 'unauthorized');

    saveDraft(storage, key, { roleTitle: 'Latest state' }, now + 1);

    expect(consumeDraft(storage, key, now + 2)).toEqual({ roleTitle: 'Latest state' });
  });

  test('removes malformed, unsupported, future, and expired entries', () => {
    const storage = new MemoryStorage();
    const malformed = draftKey('/malformed');
    const unsupported = draftKey('/unsupported');
    const future = draftKey('/future');
    const expired = draftKey('/expired');

    storage.setItem(malformed, '{');
    storage.setItem(unsupported, JSON.stringify({ version: 2, savedAt: now, armed: true, data: {} }));
    storage.setItem(future, JSON.stringify({ version: 1, savedAt: now + 1, armed: true, data: {} }));
    storage.setItem(expired, JSON.stringify({
      version: 1,
      savedAt: now - DRAFT_TTL_MS - 1,
      armed: true,
      data: { stale: true },
    }));

    expect(consumeDraft(storage, malformed, now)).toBeNull();
    expect(consumeDraft(storage, unsupported, now)).toBeNull();
    expect(consumeDraft(storage, future, now)).toBeNull();
    expect(consumeDraft(storage, expired, now)).toBeNull();
    expect(storage.length).toBe(0);
  });

  test('rejects File and Blob values without replacing a previous safe draft', () => {
    const storage = new MemoryStorage();
    const key = draftKey('/import', 2);
    saveDraft(storage, key, { pastedText: 'safe' }, now);
    const previous = storage.getItem(key);

    expect(saveDraft(storage, key, { upload: new File(['secret'], 'cv.pdf') }, now + 1)).toBe(false);
    expect(saveDraft(storage, key, { nested: [new Blob(['secret'])] }, now + 1)).toBe(false);
    expect(storage.getItem(key)).toBe(previous);
  });
});
