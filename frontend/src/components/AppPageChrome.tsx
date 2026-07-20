import type { ReactNode } from 'react';
import { APP_FOOTNOTE_SUMMARY, APP_NAME, APP_READ_ONLY_NOTE, APP_TAGLINE } from '../constants';

/** canvas: warm page treatment · darkFrame: shared ink application frame */
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

function BrandBlock({ isDark }: { isDark: boolean }) {
  return (
    <div className="flex min-w-0 items-start gap-3 lg:col-span-2 lg:py-2">
      <span
        className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent text-base font-black text-white shadow-lift ring-1 ring-white/20 sm:h-12 sm:w-12"
        aria-hidden="true"
      >
        R
        <span className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-frame bg-amber-300" />
      </span>
      <div className="min-w-0 pt-0.5">
        <p className={`font-display text-xl font-semibold leading-none tracking-tight ${isDark ? 'text-white' : 'text-ink'}`}>
          {APP_NAME}
        </p>
        <p className={`mt-2 max-w-md text-xs leading-relaxed sm:text-sm ${isDark ? 'text-slate-300' : 'text-muted'}`}>
          {APP_TAGLINE}
        </p>
      </div>
    </div>
  );
}

function DashboardFootnote({ isDark }: { isDark: boolean }) {
  return (
    <details className="group mt-3 text-xs">
      <summary
        className={`w-fit cursor-pointer rounded-md py-1 font-semibold underline decoration-dotted underline-offset-4 ${
          isDark ? 'text-slate-300 hover:text-white' : 'text-muted hover:text-ink'
        }`}
      >
        {APP_FOOTNOTE_SUMMARY}
        <span className="ml-1 group-open:hidden" aria-hidden="true">↗</span>
      </summary>
      <p className={`mt-2 max-w-2xl border-l-2 border-accent pl-3 text-xs leading-relaxed ${isDark ? 'text-slate-300' : 'text-muted'}`}>
        {APP_READ_ONLY_NOTE}
      </p>
    </details>
  );
}

function PageContext({
  isDark,
  pageEyebrow,
  pageTitle,
  pageHint,
  pageMeta,
  topRight,
  showDashboardFootnote,
}: Omit<AppPageChromeProps, 'children' | 'tone'> & { isDark: boolean }) {
  return (
    <section className={`min-w-0 rounded-panel border px-4 py-4 sm:px-5 lg:col-span-3 ${isDark ? 'border-white/10 bg-white/5' : 'border-line bg-paper'}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {pageEyebrow ? (
            <p className={`mb-1 text-xs font-bold uppercase tracking-widest ${isDark ? 'text-emerald-300' : 'text-accent-strong'}`}>
              {pageEyebrow}
            </p>
          ) : null}
          <h1 className={`break-words font-display text-2xl font-semibold leading-tight tracking-tight sm:text-3xl ${isDark ? 'text-white' : 'text-ink'}`}>
            {pageTitle}
          </h1>
          {pageMeta ? (
            <div className={`mt-1.5 break-all font-mono text-xs ${isDark ? 'text-slate-400' : 'text-muted'}`}>
              {pageMeta}
            </div>
          ) : null}
          {pageHint ? (
            <p className={`mt-2 max-w-3xl text-sm leading-relaxed ${isDark ? 'text-slate-200' : 'text-muted'}`}>
              {pageHint}
            </p>
          ) : null}
          {showDashboardFootnote ? <DashboardFootnote isDark={isDark} /> : null}
        </div>
        {topRight ? <div className="flex w-full min-w-0 flex-wrap justify-start gap-2 sm:w-auto sm:shrink-0 sm:justify-end">{topRight}</div> : null}
      </div>
    </section>
  );
}

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

  return (
    <>
      <header className={`shrink-0 border-b ${isDark ? 'border-white/10 bg-frame' : 'border-line bg-canvas'}`} role="banner">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <div className={`grid gap-4 rounded-panel border p-4 shadow-panel lg:grid-cols-5 lg:gap-6 ${
            isDark ? 'border-white/10 bg-frame-muted' : 'border-line bg-paper'
          }`}>
            <BrandBlock isDark={isDark} />
            <PageContext
              isDark={isDark}
              pageEyebrow={pageEyebrow}
              pageTitle={pageTitle}
              pageHint={pageHint}
              pageMeta={pageMeta}
              topRight={topRight}
              showDashboardFootnote={showDashboardFootnote}
            />
          </div>
        </div>
      </header>
      {children}
    </>
  );
}
