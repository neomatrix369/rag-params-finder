/**
 * Replaces the values of `id` and `aria-describedby` attributes with ordinal tokens (ID0, ID1, ...)
 * so two renders of the same props compare equal even though React useId differs per mount.
 */
export function normalizeIds(html: string): string {
  const seen = new Map<string, string>();
  return html.replace(/\b(id|aria-describedby)="([^"]*)"/g, (_m, attr: string, value: string) => {
    if (!seen.has(value)) seen.set(value, `ID${seen.size}`);
    return `${attr}="${seen.get(value)}"`;
  });
}
