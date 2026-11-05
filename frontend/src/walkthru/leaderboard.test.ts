/**
 * Tests for the pure cross-store leaderboard helpers.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C3 - grouping by group_id, rank order, store filter, suggested pick, overlap count
 */
import { describe, expect, it } from 'vitest'
import { makeWalkthruResults, makeWalkthruRun } from '../test/helpers/walkthruResults'
import {
  FEW_OVERLAP_THRESHOLD,
  compareToLeaderboard,
  countCrossStoreGroups,
  filterRunsByStore,
  groupRuns,
  primaryStore,
  suggestedRunId,
} from './leaderboard'

describe('groupRuns', () => {
  it('Given runs with two group_ids, when grouped, then runs are never paired across groups', () => {
    /**
     * Scenario: Runs that differ in dataset, questions or config are never paired.
     * Slice: 56 Part C3 - grouping by group_id
     */
    // -- Given --
    const { runs } = makeWalkthruResults()

    // -- When --
    const groups = groupRuns(runs)

    // -- Then --
    expect(groups.map((g) => g.groupId)).toEqual(['group-a', 'group-b'])
    for (const group of groups) {
      expect(group.runs.every((r) => r.group_id === group.groupId)).toBe(true)
    }
    expect(groups[0].runs.map((r) => r.run_id)).toEqual(['run-redis-best', 'run-pg-best', 'run-mongo-best'])
    expect(groups[0].stores).toEqual(['redis', 'postgres', 'mongodb'])
    expect(groups[0].spansStores).toBe(true)
  })

  it('Given shuffled ranks, when grouped, then runs follow the exporter rank and groups follow their best rank', () => {
    /**
     * Scenario: Ordering uses the exporter's rank as given; nothing is re-scored or sorted by speed.
     * Slice: 56 Part C3 - sort by rank
     */
    // -- Given --
    const slowTop = makeWalkthruRun({ run_id: 'slow-top', group_id: 'g2', rank: 1, elapsed_ms: 999999 })
    const fastLow = makeWalkthruRun({ run_id: 'fast-low', group_id: 'g2', store: 'postgres', rank: 4, elapsed_ms: 1 })
    const other = makeWalkthruRun({ run_id: 'other', group_id: 'g1', rank: 2 })

    // -- When --
    const groups = groupRuns([fastLow, other, slowTop])

    // -- Then --
    expect(groups.map((g) => g.groupId)).toEqual(['g2', 'g1'])
    expect(groups[0].runs.map((r) => r.run_id)).toEqual(['slow-top', 'fast-low'])
  })

  it('Given equal best ranks, when grouped, then the input (server) order is kept', () => {
    /**
     * Scenario: Groups sharing a best rank keep their first-seen input order (live compare data is server-ordered).
     * Slice: 56 Part C3 - stable ordering
     */
    // -- Given --
    const b = makeWalkthruRun({ run_id: 'b', group_id: 'gb', rank: 1 })
    const a = makeWalkthruRun({ run_id: 'a', group_id: 'ga', rank: 1 })

    // -- When --
    const groups = groupRuns([b, a])

    // -- Then --
    expect(groups.map((g) => g.groupId)).toEqual(['gb', 'ga'])
    expect(groups[0].spansStores).toBe(false)
  })
})

describe('groupRuns ties', () => {
  it('Given two runs with the same rank in one group, when grouped, then run_id breaks the tie', () => {
    /**
     * Scenario: Deterministic run order inside a group when ranks tie.
     * Slice: 56 Part C3 - stable ordering
     */
    // -- Given --
    const z = makeWalkthruRun({ run_id: 'z', rank: 1 })
    const a = makeWalkthruRun({ run_id: 'a', rank: 1, store: 'postgres' })

    // -- When --
    const [group] = groupRuns([z, a])

    // -- Then --
    expect(group.runs.map((r) => r.run_id)).toEqual(['a', 'z'])
  })
})

describe('filterRunsByStore', () => {
  it('Given a store name, when filtered, then only that store remains; null keeps all', () => {
    /**
     * Scenario: The store filter narrows the leaderboard.
     * Slice: 56 Part C3 - store filter
     */
    // -- Given --
    const { runs } = makeWalkthruResults()

    // -- When --
    const onlyPg = filterRunsByStore(runs, 'postgres')
    const all = filterRunsByStore(runs, null)

    // -- Then --
    expect(onlyPg.map((r) => r.run_id)).toEqual(['run-pg-best', 'run-pg-worst'])
    expect(all).toHaveLength(runs.length)
  })
})

describe('countCrossStoreGroups', () => {
  it('Given groups, when counted, then only groups spanning 2+ stores count', () => {
    /**
     * Scenario: Overlap is the number of configs run on more than one store.
     * Slice: 56 Part C3 - fallback overlap count
     */
    // -- Given --
    const multi = groupRuns(makeWalkthruResults().runs)
    const single = groupRuns([makeWalkthruRun()])

    // -- When / Then --
    expect(countCrossStoreGroups(multi)).toBe(2)
    expect(countCrossStoreGroups(single)).toBe(0)
    expect(FEW_OVERLAP_THRESHOLD).toBeGreaterThan(0)
  })
})

describe('primaryStore and suggestedRunId', () => {
  it('Given a primary store, when asked, then it is returned and its best run is suggested', () => {
    /**
     * Scenario: The primary store (Redis 8) is the default suggestion.
     * Slice: 56 Part C3 - choice step
     */
    // -- Given --
    const results = makeWalkthruResults()

    // -- When / Then --
    expect(primaryStore(results)).toBe('redis')
    expect(suggestedRunId(results, 'redis')).toBe('run-redis-best')
    expect(suggestedRunId(results, 'postgres')).toBe('run-pg-best')
  })

  it('Given no primary flag, when asked, then the first store is used', () => {
    /**
     * Scenario: Tolerate an export with no primary store flag.
     * Slice: 56 Part C3 - fallback
     */
    // -- Given --
    const base = makeWalkthruResults()
    const stores = Object.fromEntries(
      Object.entries(base.stores).map(([name, s]) => [name, { ...s, is_primary: false }]),
    )

    // -- When / Then --
    expect(primaryStore({ ...base, stores })).toBe('redis')
    expect(primaryStore({ ...base, stores: {} })).toBeUndefined()
  })

  it('Given a store summary pointing at a missing run, when asked, then the lowest-ranked run of that store is used', () => {
    /**
     * Scenario: best_run_id absent from runs falls back to the store's best-ranked run.
     * Slice: 56 Part C3 - robustness
     */
    // -- Given --
    const base = makeWalkthruResults()
    const results = {
      ...base,
      stores: { ...base.stores, redis: { ...base.stores.redis, best_run_id: 'gone' } },
    }

    // -- When / Then --
    expect(suggestedRunId(results, 'redis')).toBe('run-redis-best')
    expect(suggestedRunId(results, 'nope')).toBeUndefined()
    expect(suggestedRunId(results, undefined)).toBeUndefined()
  })
})

describe('compareToLeaderboard', () => {
  it('Given a compare response, when adapted, then runs keep server order and no store is primary', () => {
    /**
     * Scenario: The live response becomes leaderboard input without re-scoring or reordering.
     * Slice: 66 - live cross-store compare adapter
     */
    // -- Given --
    const a1 = makeWalkthruRun({ run_id: 'a1', group_id: 'g-a', store: 'redis', rank: 1 })
    const a2 = makeWalkthruRun({ run_id: 'a2', group_id: 'g-a', store: 'postgres', rank: 2 })
    const b1 = makeWalkthruRun({ run_id: 'b1', group_id: 'g-b', store: 'redis', rank: 1 })
    const response = {
      groups: [
        { group_id: 'g-b', runs: [b1] },
        { group_id: 'g-a', runs: [a1, a2] },
      ],
      stores: ['redis', 'postgres'],
      group_count: 2,
      run_count: 3,
      cross_store_group_count: 1,
    }

    // -- When --
    const { stores, runs } = compareToLeaderboard(response)

    // -- Then --
    expect(runs.map((r) => r.run_id)).toEqual(['b1', 'a1', 'a2'])
    expect(Object.values(stores).every((s) => !s.is_primary)).toBe(true)
    expect(stores.redis).toMatchObject({ run_count: 2, best_run_id: 'b1', worst_run_id: 'a1' })
    expect(stores.postgres).toMatchObject({ run_count: 1, best_run_id: 'a2' })
    expect(groupRuns(runs).map((g) => g.groupId)).toEqual(['g-b', 'g-a'])
  })
})
