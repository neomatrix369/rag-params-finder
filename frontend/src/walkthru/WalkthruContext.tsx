/**
 * Walkthru entry points shared with the global chrome (Slice 56 Part C2).
 *
 * The About box lives in the app header (AppPageChrome), so it reaches the App-level Walkthru
 * through this context instead of threading callbacks through every screen. Without a provider the
 * actions are no-ops and `available` is false, so the About dialog hides its demo buttons - which
 * keeps the standalone AboutDialog tests (rendered without a provider) unchanged.
 */
import { createContext, useContext } from 'react';

export interface WalkthruActions {
  /** Start the guided Walkthru (routes to the demo screen). */
  startWalkthru: () => void;
  /** Open the demo screen directly, without the Walkthru. */
  openDemo: () => void;
  /** True only inside the App provider; the About box shows its demo buttons only then. */
  available: boolean;
}

const noop = (): void => undefined;

export const WalkthruContext = createContext<WalkthruActions>({
  startWalkthru: noop,
  openDemo: noop,
  available: false,
});

/** Access the Walkthru entry points from anywhere under the App provider. */
export function useWalkthruActions(): WalkthruActions {
  return useContext(WalkthruContext);
}
