import type { ReactNode } from 'react';

export type DashboardShellProps = {
  header: ReactNode;
  sidebar: ReactNode;
  /** Width utility for the rail, e.g. `w-56`, `w-72` — base sidebar styles appended. */
  asideWidthClass: string;
  /** Max width utility for centered main column. */
  contentMaxWidthClass?: string;
  children: ReactNode;
};

/** Explore-style frame: slate-900 shell, dark sidebar rail, light content canvas. */
export default function DashboardShell({
  header,
  sidebar,
  asideWidthClass,
  contentMaxWidthClass = 'max-w-7xl',
  children,
}: DashboardShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-900">
      {header}
      <div className="flex min-h-0 flex-1">
        <aside
          className={`${asideWidthClass} shrink-0 overflow-y-auto border-r border-slate-700 bg-slate-800 p-5`}
        >
          {sidebar}
        </aside>
        <main className="min-h-0 flex-1 overflow-y-auto bg-slate-50">
          <div className={`mx-auto w-full px-8 py-8 ${contentMaxWidthClass}`}>{children}</div>
        </main>
      </div>
    </div>
  );
}
