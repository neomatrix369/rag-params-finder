import { formatBytes } from '../services/fetchWithProgress';

/** Single line in the faux-agent activity log */
export type FeedEntry = {
  id: string;
  text: string;
  variant: 'default' | 'warning';
};

type Theme = 'light' | 'dark';

function pctOf(received: number | null, total: number | null): number | null {
  if (received === null || total === null || total <= 0 || received > total) return null;
  return Math.min(100, Math.round((100 * received) / total));
}

/** Human line under bar (handles 0 B + unknown total cleanly). */
function payloadSummaryLabel(
  receivedBytes: number | null,
  totalBytes: number | null,
): string | null {
  if (receivedBytes === null) return null;
  if (totalBytes !== null) {
    const pctVal = pctOf(receivedBytes, totalBytes);
    if (receivedBytes === 0) {
      return `${formatBytes(0)} of ${formatBytes(totalBytes)}${
        pctVal !== null ? ` (${pctVal}%) · reading body…` : ' · reading body…'
      }`;
    }
    return `${formatBytes(receivedBytes)} / ${formatBytes(totalBytes)}${
      pctVal !== null ? ` (${pctVal}%)` : ''
    }`;
  }
  if (receivedBytes === 0) {
    return 'Response started · reading payload (total size unknown…)';
  }
  return `${formatBytes(receivedBytes)} received (total unknown until complete)`;
}

export default function LoadingFeedbackPanel(props: {
  title: string;
  subtitle?: string;
  footer?: string;
  feed: FeedEntry[];
  /** When set, renders transfer lane (bar + caption) */
  receivedBytes: number | null;
  totalBytes: number | null;
  theme?: Theme;
  /**
   * When true (default): show animated bar before first byte (covers slow DNS/TLS/Mongo stalls).
   * Set false on error-only diagnostics where no ongoing transfer exists.
   */
  expectPayloadProgress?: boolean;
}) {
  const {
    title,
    subtitle,
    footer,
    feed,
    receivedBytes,
    totalBytes,
    theme = 'light',
    expectPayloadProgress = true,
  } = props;

  const pct = pctOf(receivedBytes, totalBytes);
  const downloadSummary = payloadSummaryLabel(receivedBytes, totalBytes);

  /** Always show lane when we have byte info, or we're mid-request and expect a payload */
  const showPayloadLane =
    downloadSummary !== null || (expectPayloadProgress && receivedBytes === null);

  const showIndeterminatePulse =
    showPayloadLane && pct === null;

  const card =
    theme === 'dark'
      ? 'rounded-xl border border-slate-600 bg-slate-800'
      : 'rounded-xl border border-slate-200 bg-white shadow-sm';
  const titleCls = theme === 'dark' ? 'text-white' : 'text-slate-900';
  const subCls = theme === 'dark' ? 'text-slate-400' : 'text-slate-600';
  const barBg = theme === 'dark' ? 'bg-slate-950' : 'bg-slate-100';
  const feedShell = theme === 'dark' ? 'border-slate-600 bg-black' : 'border-slate-200 bg-slate-950';

  return (
    <div className={`w-full max-w-lg ${card} p-6`}>
      <h2 className={`text-lg font-semibold ${titleCls}`}>{title}</h2>
      {subtitle !== undefined ? <p className={`mt-1 text-sm ${subCls}`}>{subtitle}</p> : null}

      {showPayloadLane && (
        <div className="mt-5">
          <div
            className={`flex justify-between text-xs font-medium ${
              theme === 'dark' ? 'text-slate-300' : 'text-slate-600'
            }`}
          >
            <span>Payload</span>
            {pct !== null ? <span>{pct}%</span> : <span aria-hidden>⋯</span>}
          </div>
          <div
            className={`mt-2 h-2 overflow-hidden rounded-full ${barBg}`}
            role="progressbar"
            aria-valuetext={
              pct !== null
                ? `${pct}% transferred`
                : receivedBytes !== null && receivedBytes > 0
                ? `${formatBytes(receivedBytes)} received`
                : 'waiting for response'
            }
            aria-valuenow={pct ?? undefined}
            aria-valuemin={pct !== null ? 0 : undefined}
            aria-valuemax={pct !== null ? 100 : undefined}
          >
            <div
              className={`h-full rounded-full bg-sky-500 duration-150 ${
                pct !== null
                  ? 'transition-[width]'
                  : `${showIndeterminatePulse ? 'w-1/3 animate-pulse' : 'w-0'}`
              }`}
              style={
                pct !== null ? { width: `${pct === 0 && totalBytes !== null ? 2 : pct}%` } : undefined
              }
            />
          </div>
          <div
            className={`mt-2 font-mono text-xs leading-snug ${theme === 'dark' ? 'text-slate-200' : 'text-slate-700'}`}
          >
            {downloadSummary ??
              'Waiting for first byte… (TLS, Mongo Atlas, or large JSON can take a few seconds)'}
          </div>
        </div>
      )}

      <div className={`mt-5 rounded-lg border px-3 py-2 shadow-inner ${feedShell}`}>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
          Activity
        </div>
        <ul
          className="max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-100"
          aria-live="polite"
        >
          {feed.map((entry) => (
            <li
              key={entry.id}
              className={entry.variant === 'warning' ? 'text-amber-200' : 'text-slate-200'}
            >
              — {entry.text}
            </li>
          ))}
        </ul>
      </div>

      {footer !== undefined ? (
        <p className={`mt-4 text-xs ${theme === 'dark' ? 'text-slate-500' : 'text-slate-500'}`}>
          {footer}
        </p>
      ) : null}
    </div>
  );
}
