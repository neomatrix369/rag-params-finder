import type { ReactNode } from 'react';
import { APP_FOOTNOTE_SUMMARY, APP_NAME, APP_READ_ONLY_NOTE, APP_TAGLINE } from '../constants';

/** canvas: slate page + soft card · darkFrame: explorer shell over slate-900 */
export type ChromeTone = 'canvas' | 'darkFrame';

export type AppPageChromeProps = {
  pageEyebrow?: string;
  pageTitle: string;
  pageHint?: string;
  /** Quiet row under the title — e.g. monospace experiment id */
  pageMeta?: ReactNode;
  topRight?: ReactNode;
  children?: ReactNode;
  tone?: ChromeTone;
  /** When false, hides the expandable CLI/API note on dense pages like experiment detail. */
  showDashboardFootnote?: boolean;
};

export default function AppPageChrome({
  pageEyebrow,
  pageTitle,
  pageHint,
  pageMeta,
  topRight,
  children,
  tone = 'canvas',
  showDashboardFootnote = true,
}: AppPageChromeProps) {
  const isDark = tone === 'darkFrame';

  const shellClass = isDark
    ? 'bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950'
    : 'bg-gradient-to-b from-slate-200/35 via-slate-50 to-slate-50';

  const panelClass = isDark
    ? 'rounded-xl border border-slate-600/50 bg-gradient-to-br from-slate-800/95 to-slate-900/95 shadow-lg shadow-black/20 ring-1 ring-white/[0.05]'
    : 'rounded-xl border border-slate-200/90 bg-white/90 shadow-sm shadow-slate-900/5 ring-1 ring-slate-900/[0.04] backdrop-blur-sm';

  const brandNameClass = isDark ? 'text-white' : 'text-slate-900';
  const taglineClass = isDark ? 'text-slate-400' : 'text-slate-500';
  const topDividerClass = isDark ? 'border-t-slate-600/55' : 'border-t-slate-200/90';
  const rightColumnTintClass = isDark ? 'sm:bg-blue-400/[0.08]' : 'sm:bg-blue-600/[0.055]';
  const rightColumnBorderClass = isDark ? 'sm:border-slate-700/55' : 'sm:border-slate-200';
  const eyebrowClass = isDark ? 'text-blue-400/90' : 'text-blue-700/85';
  const titleClass = isDark ? 'text-white' : 'text-slate-900';
  const hintClass = isDark ? 'text-slate-300' : 'text-slate-600';
  const metaClass = isDark ? 'text-slate-400' : 'text-slate-500';
  const footnoteMutedClass = isDark ? 'text-slate-500' : 'text-slate-500';
  const footnoteExpandedClass = isDark ? 'text-slate-400' : 'text-slate-600';
  const detailsSummaryClass = isDark
    ? 'rounded-md px-1 py-1 text-[11px] font-medium leading-snug text-slate-400 outline-none hover:bg-white/[0.04] hover:text-slate-300'
    : 'rounded-md px-1 py-1 text-[11px] font-medium leading-snug text-slate-600 outline-none hover:bg-slate-100 hover:text-slate-800';

  return (
    <>
      <header className={`shrink-0 ${shellClass}`} role="banner">
        <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6">
          <div className={`${panelClass} px-4 py-3 sm:px-5 sm:py-3`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch sm:gap-6">
              <div className="flex shrink-0 items-start gap-3 sm:max-w-[min(22rem,40vw)] md:max-w-md">
                <span
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-black leading-none text-white shadow-md sm:h-12 sm:w-12 sm:rounded-2xl sm:text-base ${
                    isDark
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-600 shadow-black/35'
                      : 'bg-gradient-to-br from-blue-600 to-blue-700 shadow-blue-900/25'
                  }`}
                  aria-hidden
                >
                  R
                </span>
                <div className="min-w-0 pt-0.5">
                  <p
                    className={`text-lg font-bold leading-tight tracking-tight sm:text-xl sm:leading-none ${brandNameClass}`}
                  >
                    {APP_NAME}
                  </p>
                  <p
                    className={`mt-2 line-clamp-3 text-xs leading-snug sm:line-clamp-none sm:text-sm sm:leading-relaxed ${taglineClass}`}
                  >
                    {APP_TAGLINE}
                  </p>
                </div>
              </div>

              {topRight ? (
                <div className="flex justify-end sm:hidden">{topRight}</div>
              ) : null}

              <div
                className={`min-w-0 flex-1 rounded-r-lg pt-3 sm:rounded-xl sm:border sm:py-3.5 sm:pl-6 sm:pr-5 ${topDividerClass} ${rightColumnBorderClass} ${rightColumnTintClass}`}
              >
                <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
                  <div className="min-w-0 flex-1">
                    {pageEyebrow ? (
                      <p
                        className={`mb-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${eyebrowClass}`}
                      >
                        {pageEyebrow}
                      </p>
                    ) : null}
                    <h1 className={`text-lg font-bold tracking-tight sm:text-xl md:text-[1.35rem] ${titleClass}`}>
                      {pageTitle}
                    </h1>
                    {pageMeta ? (
                      <div className={`mt-1.5 text-[12px] ${metaClass}`}>{pageMeta}</div>
                    ) : null}
                    {pageHint ? (
                      <p className={`mt-2 line-clamp-2 text-[13px] leading-snug ${hintClass}`}>{pageHint}</p>
                    ) : null}
                    {showDashboardFootnote ? (
                      <details className={`group mt-2 border-0 ${footnoteMutedClass}`}>
                        <summary
                          className={`${detailsSummaryClass} [&::-webkit-details-marker]:hidden ${isDark ? '' : '-ml-0.5'}`}
                          style={{ listStyle: 'none' }}
                        >
                          <span className="underline decoration-slate-300/70 underline-offset-2 hover:decoration-current">
                            {APP_FOOTNOTE_SUMMARY}
                          </span>{' '}
                          <span
                            className={`tabular-nums group-open:hidden ${
                              isDark ? 'text-slate-500' : 'text-slate-400'
                            }`}
                          >
                            ▸
                          </span>
                          <span
                            className={`hidden tabular-nums group-open:inline ${
                              isDark ? 'text-slate-500' : 'text-slate-400'
                            }`}
                          >
                            ▾
                          </span>
                        </summary>
                        <p
                          className={`mt-2 border-l-[2px] pl-3 text-[11px] leading-relaxed ${footnoteExpandedClass} ${
                            isDark ? 'border-blue-400/30' : 'border-blue-600/35'
                          }`}
                        >
                          {APP_READ_ONLY_NOTE}
                        </p>
                      </details>
                    ) : null}
                  </div>
                  {topRight ? <div className="hidden shrink-0 sm:block">{topRight}</div> : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
