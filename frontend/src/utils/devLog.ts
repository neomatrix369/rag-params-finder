/**
 * Dev-only console helpers — stripped from production builds via dead-code elimination.
 *
 * Option A format: `[rag-params-finder] [Scope] operation — details`
 * Example: `[rag-params-finder] [ExperimentsScreen] list poll OK — 3 experiment(s)`
 */

const PREFIX = '[rag-params-finder]';

function isDev(): boolean {
  return import.meta.env.DEV;
}

function scopedPrefix(scope: string): string {
  return `${PREFIX} [${scope}]`;
}

export function devDebug(scope: string, message: string, ...details: unknown[]): void {
  if (isDev()) {
    console.debug(scopedPrefix(scope), message, ...details);
  }
}

export function devInfo(scope: string, message: string, ...details: unknown[]): void {
  if (isDev()) {
    console.info(scopedPrefix(scope), message, ...details);
  }
}

export function devWarn(scope: string, message: string, ...details: unknown[]): void {
  if (isDev()) {
    console.warn(scopedPrefix(scope), message, ...details);
  }
}

/** Log at most once per interval (dev console breadcrumb without poll spam). */
export function devInfoThrottled(
  scope: string,
  key: string,
  intervalMs: number,
  message: string,
  lastAtByKey: Map<string, number>,
): void {
  if (!isDev()) return;
  const now = Date.now();
  const last = lastAtByKey.get(key) ?? 0;
  if (now - last < intervalMs) return;
  lastAtByKey.set(key, now);
  console.info(scopedPrefix(scope), message);
}

/** @deprecated Prefer devInfoThrottled — debug level is hidden unless Verbose is enabled. */
export function devDebugThrottled(
  scope: string,
  key: string,
  intervalMs: number,
  message: string,
  lastAtByKey: Map<string, number>,
): void {
  devInfoThrottled(scope, key, intervalMs, message, lastAtByKey);
}
