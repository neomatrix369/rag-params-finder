/**
 * Backend-aware labels for vector DB stats panels.
 * Mongo keeps Atlas vocabulary; Postgres/Supabase uses Host / Table.
 */

export function isMongoProvider(databaseProvider: string | undefined | null): boolean {
  const provider = (databaseProvider ?? '').toLowerCase();
  return provider === 'mongodb' || provider === 'mongo';
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
