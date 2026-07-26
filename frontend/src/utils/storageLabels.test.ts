/**
 * Tests for backend-aware storage labels (Slice 35 copy hygiene).
 */
import { describe, expect, it } from 'vitest';
import {
  clusterHostLabel,
  collectionOrTableLabel,
  isMongoProvider,
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
});
