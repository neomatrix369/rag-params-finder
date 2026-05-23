/**
 * Subtle background-poll indicator — fixed footprint, delayed show, minimum visible time.
 *
 * Usage:
 *   <PollingIndicator active={isPolling} />
 */

import { useEffect, useRef, useState } from 'react';

type PollingIndicatorProps = {
  active: boolean;
  /** Wait before showing (avoids flash on fast polls). */
  showDelayMs?: number;
  /** Keep visible at least this long once shown (avoids flicker). */
  minVisibleMs?: number;
  /** When true, reserve layout space even when hidden. */
  reserveSpace?: boolean;
};

function useStableSyncVisible(
  active: boolean,
  showDelayMs: number,
  minVisibleMs: number,
): boolean {
  const [visible, setVisible] = useState(false);
  const showTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const visibleSinceRef = useRef<number | null>(null);

  useEffect(() => {
    const clearShow = () => {
      if (showTimerRef.current !== null) {
        clearTimeout(showTimerRef.current);
        showTimerRef.current = null;
      }
    };
    const clearHide = () => {
      if (hideTimerRef.current !== null) {
        clearTimeout(hideTimerRef.current);
        hideTimerRef.current = null;
      }
    };

    if (active) {
      clearHide();
      if (visible) {
        return undefined;
      }
      clearShow();
      showTimerRef.current = setTimeout(() => {
        visibleSinceRef.current = Date.now();
        setVisible(true);
      }, showDelayMs);
      return clearShow;
    }

    clearShow();
    if (!visible) {
      return undefined;
    }

    const elapsed = visibleSinceRef.current
      ? Date.now() - visibleSinceRef.current
      : minVisibleMs;
    const delay = Math.max(0, minVisibleMs - elapsed);
    clearHide();
    hideTimerRef.current = setTimeout(() => {
      setVisible(false);
      visibleSinceRef.current = null;
    }, delay);
    return clearHide;
  }, [active, visible, showDelayMs, minVisibleMs]);

  return visible;
}

export default function PollingIndicator({
  active,
  showDelayMs = 500,
  minVisibleMs = 800,
  reserveSpace = true,
}: PollingIndicatorProps) {
  const visible = useStableSyncVisible(active, showDelayMs, minVisibleMs);

  if (!reserveSpace && !visible) {
    return null;
  }

  return (
    <div
      className={`flex h-5 items-center gap-2 text-xs text-slate-500 transition-opacity duration-300 ${
        visible ? 'opacity-100' : 'opacity-0'
      } ${reserveSpace ? 'min-w-[5.5rem]' : ''}`}
      role="status"
      aria-live="polite"
      aria-hidden={!visible}
    >
      <span
        className={`h-2 w-2 shrink-0 rounded-full bg-blue-500 ${
          visible ? 'animate-pulse' : ''
        }`}
        aria-hidden="true"
      />
      <span>Syncing...</span>
    </div>
  );
}
