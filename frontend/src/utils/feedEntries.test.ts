/**
 * Author: Slice 45
 * Created: 2026-07-28
 * Scope: shared feed entry append helper
 */
import { describe, expect, it } from 'vitest';
import { appendFeedEntry } from './feedEntries';

describe('appendFeedEntry', () => {
  it('Given an empty feed, when a line is appended, then the feed gains one unique entry', () => {
    // -- Given --
    const prev: ReturnType<typeof appendFeedEntry> = [];
    // -- When --
    const next = appendFeedEntry(prev, 'hello', 'default');
    // -- Then --
    expect(next).toHaveLength(1);
    expect(next[0].text).toBe('hello');
    expect(next[0].variant).toBe('default');
    expect(next[0].id).toMatch(/^\d+-\d+$/);
  });

  it('Given an existing feed, when a warning is appended, then previous entries are preserved', () => {
    // -- Given --
    const prev = appendFeedEntry([], 'first', 'default');
    // -- When --
    const next = appendFeedEntry(prev, 'boom', 'warning');
    // -- Then --
    expect(next).toHaveLength(2);
    expect(next[0].text).toBe('first');
    expect(next[1].text).toBe('boom');
    expect(next[1].variant).toBe('warning');
    expect(next[1].id).not.toBe(next[0].id);
  });
});
