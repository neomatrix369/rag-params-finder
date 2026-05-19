/** Dev-only console helpers — stripped from production builds via dead-code elimination. */

const PREFIX = '[rag-params-finder]';

export function devDebug(...args: unknown[]): void {
  if (import.meta.env.DEV) {
    console.debug(PREFIX, ...args);
  }
}

export function devWarn(...args: unknown[]): void {
  if (import.meta.env.DEV) {
    console.warn(PREFIX, ...args);
  }
}

/** Log at most once per interval (dev console breadcrumb without 2s spam). */
export function devDebugThrottled(
  key: string,
  intervalMs: number,
  message: string,
  lastAtByKey: Map<string, number>,
): void {
  if (!import.meta.env.DEV) return;
  const now = Date.now();
  const last = lastAtByKey.get(key) ?? 0;
  if (now - last < intervalMs) return;
  lastAtByKey.set(key, now);
  console.debug(PREFIX, message);
}
