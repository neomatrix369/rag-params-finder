import type { ReactNode } from 'react';

export type DashboardShellProps = {
  header: ReactNode;
  sidebar: ReactNode;
  /** Responsive width utility for the rail, e.g. `w-full lg:w-60`. */
  asideWidthClass: string;
  /** List/detail screens hide help-only rails on compact viewports. */
  hideSidebarOnCompact?: boolean;
  /** Max width utility for centered main column. */
  contentMaxWidthClass?: string;
  children: ReactNode;
};

/** Shared instrument frame: ink rail, warm paper canvas, responsive content column. */
export default function DashboardShell({
  header,
  sidebar,
  asideWidthClass,
  hideSidebarOnCompact = false,
  contentMaxWidthClass = 'max-w-7xl',
  children,
}: DashboardShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-frame text-ink">
      {header}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside
          className={`${asideWidthClass} shrink-0 overflow-y-auto border-r border-white/10 bg-frame-muted p-5 ${
            hideSidebarOnCompact ? 'hidden lg:block' : 'block'
          }`}
        >
          {sidebar}
        </aside>
        <main className="app-canvas min-h-0 min-w-0 flex-1 overflow-y-auto">
          <div className={`mx-auto w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-8 ${contentMaxWidthClass}`}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
