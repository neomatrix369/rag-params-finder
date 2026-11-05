/**
 * Pure helpers for the cross-store leaderboard (Slice 56 Part C3).
 *
 * Runs are grouped by the exporter's `group_id` (same dataset + questions + config) and ordered by the
 * exporter's `rank`. Nothing here re-scores, and nothing orders by speed.
 */
import type { CompareResponse } from '../types'
import type { WalkthruResults, WalkthruRun } from './walkthruResults'

/** The slice of a Walkthru export the leaderboard reads (also what the live compare adapter produces). */
export type LeaderboardInput = Pick<WalkthruResults, 'stores' | 'runs'>

/** Fewer cross-store configs than this triggers the "limited overlap" note. */
export const FEW_OVERLAP_THRESHOLD = 3

export interface LeaderboardGroup {
  groupId: string
  /** Ordered by the exporter's rank, best first. */
  runs: WalkthruRun[]
  /** Distinct stores in first-seen (rank) order. */
  stores: string[]
  spansStores: boolean
}

const byRank = (a: WalkthruRun, b: WalkthruRun): number => a.rank - b.rank || a.run_id.localeCompare(b.run_id)

export function filterRunsByStore(runs: WalkthruRun[], store: string | null): WalkthruRun[] {
  return store === null ? runs : runs.filter((run) => run.store === store)
}

export function groupRuns(runs: WalkthruRun[]): LeaderboardGroup[] {
  const groupIds = [...new Set(runs.map((run) => run.group_id))]
  return groupIds
    .map((groupId) => {
      const members = runs.filter((run) => run.group_id === groupId)
      const sorted = [...members].sort(byRank)
      const stores = [...new Set(sorted.map((run) => run.store))]
      return { groupId, runs: sorted, stores, spansStores: stores.length > 1 }
    })
    .sort((a, b) => a.runs[0].rank - b.runs[0].rank)
}

/** Live compare response -> the `{stores, runs}` the leaderboard reads. No store is primary. */
export function compareToLeaderboard(response: CompareResponse): LeaderboardInput {
  const runs = response.groups.flatMap((group) => group.runs)
  const stores: WalkthruResults['stores'] = {}
  for (const store of response.stores) {
    const ids = runs.filter((run) => run.store === store).map((run) => run.run_id)
    // eslint-disable-next-line security/detect-object-injection -- store names come from the server catalog
    stores[store] = {
      is_primary: false,
      run_count: ids.length,
      best_run_id: ids[0],
      median_run_id: ids[Math.floor(ids.length / 2)],
      worst_run_id: ids[ids.length - 1],
    }
  }
  return { stores, runs }
}

export function countCrossStoreGroups(groups: LeaderboardGroup[]): number {
  return groups.filter((group) => group.spansStores).length
}

/** The store flagged primary in the export (Redis 8), else the first store listed. */
export function primaryStore(results: LeaderboardInput): string | undefined {
  const entries = Object.entries(results.stores)
  return (entries.find(([, summary]) => summary.is_primary) ?? entries[0])?.[0]
}

/** A store's best run: the exporter's `best_run_id`, else its best-ranked run. */
export function suggestedRunId(results: LeaderboardInput, store: string | undefined): string | undefined {
  if (store === undefined) return undefined
  const storeRuns = results.runs.filter((run) => run.store === store)
  const best = Object.entries(results.stores).find(([name]) => name === store)?.[1].best_run_id
  if (best !== undefined && storeRuns.some((run) => run.run_id === best)) return best
  return [...storeRuns].sort(byRank)[0]?.run_id
}
