/**
 * Author: Slice 35 / 45
 * Created: 2026-07-26
 * Scope: backend-aware storage labels (Mongo vs Postgres wording)
 */
import { describe, expect, it } from 'vitest';
import {
  clusterHostLabel,
  clusterSectionTitle,
  collectionOrTableLabel,
  displayDatabaseProvider,
  explorerFetchFeedText,
  explorerPayloadHint,
  experimentHydratingBlurb,
  isMongoProvider,
  storageQuotaHint,
  sweepWriteHint,
  waitingForFirstByteHint,
} from './storageLabels';

describe('storageLabels', () => {
  it('Given a mongodb provider, when labelling cluster fields, then Atlas/Collection wording is used', () => {
    /**
     * Scenario: Mongo provider keeps Atlas host and Collection labels.
     * Slice: 45 — FE docstring leftovers (storageLabels).
     * Given provider mongodb,
     * When cluster/collection labels are resolved,
     * Then Atlas/Collection wording and isMongoProvider true.
     */
    // -- Given / When / Then --
    expect(clusterHostLabel('mongodb')).toBe('Atlas host');
    expect(collectionOrTableLabel('mongodb')).toBe('Collection');
    expect(clusterSectionTitle('mongodb')).toBe('Cluster & Collection');
    expect(isMongoProvider('mongodb')).toBe(true);
    expect(isMongoProvider('mongo')).toBe(true);
  });

  it('Given postgres or supabase, when labelling cluster fields, then Host/Table wording is used', () => {
    /**
     * Scenario: Postgres/Supabase use Host and Table labels.
     * Slice: 45 — FE docstring leftovers (storageLabels).
     * Given postgres or supabase,
     * When cluster labels are resolved,
     * Then Host/Table wording and isMongoProvider false.
     */
    // -- Given / When / Then --
    expect(clusterHostLabel('postgres')).toBe('Host');
    expect(clusterHostLabel('supabase')).toBe('Host');
    expect(collectionOrTableLabel('postgres')).toBe('Table');
    expect(collectionOrTableLabel('supabase')).toBe('Table');
    expect(clusterSectionTitle('postgres')).toBe('Host & Table');
    expect(clusterSectionTitle('supabase')).toBe('Host & Table');
    expect(isMongoProvider('postgres')).toBe(false);
  });

  it('Given an unset provider, when displaying the provider name, then an em dash is shown', () => {
    /**
     * Scenario: Missing provider does not invent mongodb.
     * Slice: 45 — FE docstring leftovers (storageLabels).
     * Given undefined or empty provider,
     * When displayDatabaseProvider runs,
     * Then an em dash is returned.
     */
    // -- Given / When / Then --
    expect(displayDatabaseProvider('supabase')).toBe('supabase');
    expect(displayDatabaseProvider(undefined)).toBe('—');
    expect(displayDatabaseProvider('')).toBe('—');
  });

  it('Given a non-mongo provider, when loading copy is resolved, then Atlas-specific wording is avoided', () => {
    /**
     * Scenario: Non-mongo loading copy stays backend-neutral.
     * Slice: 45 — FE docstring leftovers (storageLabels).
     * Given postgres,
     * When explorer/hydrate/quota/sweep hints are resolved,
     * Then copy mentions storage/backend, not Atlas.
     */
    // -- Given / When / Then --
    expect(explorerFetchFeedText('postgres')).toContain('storage');
    expect(explorerPayloadHint('postgres')).toContain('storage');
    expect(experimentHydratingBlurb('postgres')).toContain('storage');
    expect(waitingForFirstByteHint('postgres')).not.toContain('Atlas');
    expect(storageQuotaHint('postgres')).toContain('backend metrics');
    expect(sweepWriteHint('postgres')).not.toContain('Atlas');
  });

  it('Given mongodb, when loading copy is resolved, then Mongo/Atlas wording is kept', () => {
    /**
     * Scenario: Mongo loading copy keeps Mongo/Atlas wording.
     * Slice: 45 — FE docstring leftovers (storageLabels).
     * Given mongodb,
     * When explorer/hydrate/quota/sweep hints are resolved,
     * Then Mongo/Atlas phrases remain.
     */
    // -- Given / When / Then --
    expect(explorerFetchFeedText('mongodb')).toContain('Mongo');
    expect(explorerPayloadHint('mongodb')).toContain('Mongo');
    expect(experimentHydratingBlurb('mongodb')).toContain('Mongo');
    expect(waitingForFirstByteHint('mongodb')).toContain('Atlas');
    expect(storageQuotaHint('mongodb')).toContain('Atlas Admin API');
    expect(sweepWriteHint('mongodb')).toContain('Atlas');
  });
});
