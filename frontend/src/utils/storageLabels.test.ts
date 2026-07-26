/**
 * Tests for backend-aware storage labels (Slice 35 + separation hygiene).
 */
import { describe, expect, it } from 'vitest';
import {
  clusterHostLabel,
  collectionOrTableLabel,
  displayDatabaseProvider,
  explorerFetchFeedText,
  explorerPayloadHint,
  experimentHydratingBlurb,
  isMongoProvider,
  waitingForFirstByteHint,
} from './storageLabels';

describe('storageLabels', () => {
  it('keeps Atlas host for mongodb provider', () => {
    expect(clusterHostLabel('mongodb')).toBe('Atlas host');
    expect(collectionOrTableLabel('mongodb')).toBe('Collection');
    expect(isMongoProvider('mongodb')).toBe(true);
  });

  it('uses Host and Table for postgres/supabase providers', () => {
    expect(clusterHostLabel('postgres')).toBe('Host');
    expect(clusterHostLabel('supabase')).toBe('Host');
    expect(collectionOrTableLabel('postgres')).toBe('Table');
    expect(collectionOrTableLabel('supabase')).toBe('Table');
    expect(isMongoProvider('postgres')).toBe(false);
  });

  it('displays provider without inventing mongodb when unset', () => {
    expect(displayDatabaseProvider('supabase')).toBe('supabase');
    expect(displayDatabaseProvider(undefined)).toBe('—');
    expect(displayDatabaseProvider('')).toBe('—');
  });

  it('uses backend-neutral loading copy for non-mongo providers', () => {
    expect(explorerFetchFeedText('postgres')).toContain('storage');
    expect(explorerPayloadHint('postgres')).toContain('storage');
    expect(experimentHydratingBlurb('postgres')).toContain('storage');
    expect(waitingForFirstByteHint('postgres')).not.toContain('Atlas');
  });

  it('keeps Mongo wording when provider is mongodb', () => {
    expect(explorerFetchFeedText('mongodb')).toContain('Mongo');
    expect(explorerPayloadHint('mongodb')).toContain('Mongo');
    expect(experimentHydratingBlurb('mongodb')).toContain('Mongo');
    expect(waitingForFirstByteHint('mongodb')).toContain('Atlas');
  });
});
