/**
 * Backend-aware labels for vector DB stats panels and loading copy.
 * Mongo keeps Atlas vocabulary; Postgres/Supabase uses Host / Table.
 */

export function isMongoProvider(databaseProvider: string | undefined | null): boolean {
  const provider = (databaseProvider ?? '').toLowerCase();
  return provider === 'mongodb' || provider === 'mongo';
}

/** Display label for database_provider — never invents a backend when unset. */
export function displayDatabaseProvider(
  databaseProvider: string | undefined | null,
): string {
  const trimmed = (databaseProvider ?? '').trim();
  return trimmed.length > 0 ? trimmed : '—';
}

export function clusterHostLabel(databaseProvider: string | undefined | null): string {
  return isMongoProvider(databaseProvider) ? 'Atlas host' : 'Host';
}

export function collectionOrTableLabel(databaseProvider: string | undefined | null): string {
  return isMongoProvider(databaseProvider) ? 'Collection' : 'Table';
}

export function clusterSectionTitle(databaseProvider: string | undefined | null): string {
  return isMongoProvider(databaseProvider) ? 'Cluster & Collection' : 'Cluster & Table';
}

export function storageQuotaHint(databaseProvider: string | undefined | null): string {
  return isMongoProvider(databaseProvider)
    ? 'Configure Atlas Admin API to show cluster quota'
    : 'Quota display depends on backend metrics';
}

export function sweepWriteHint(databaseProvider: string | undefined | null): string {
  const base =
    'Counting chunks and storage across experiments. This is separate from the experiment list and may take longer while a sweep is writing';
  if (isMongoProvider(databaseProvider)) {
    return `${base} to Atlas.`;
  }
  return `${base}.`;
}

export function explorerFetchFeedText(databaseProvider?: string | null): string {
  if (isMongoProvider(databaseProvider)) {
    return 'Fetching explorer aggregates (Mongo + analyzer)…';
  }
  return 'Fetching explorer aggregates (storage + analyzer)…';
}

export function explorerPayloadHint(databaseProvider?: string | null): string {
  if (isMongoProvider(databaseProvider)) {
    return 'Explorer builds ranked configs plus detailed hits from Mongo — response can be megabytes.';
  }
  return 'Explorer builds ranked configs plus detailed hits from storage — response can be megabytes.';
}

export function experimentHydratingBlurb(databaseProvider?: string | null): string {
  if (isMongoProvider(databaseProvider)) {
    return 'Hydrating payloads from Mongo + your orchestration backend.';
  }
  return 'Hydrating payloads from storage + your orchestration backend.';
}

export function waitingForFirstByteHint(databaseProvider?: string | null): string {
  if (isMongoProvider(databaseProvider)) {
    return 'Waiting for first byte… (TLS, Atlas latency, or large JSON can take a few seconds)';
  }
  return 'Waiting for first byte… (TLS handshake or large JSON can take a few seconds)';
}
