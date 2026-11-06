import { useEffect, useMemo, useRef, useState } from 'react';
import type { WalkthruRun } from '../../walkthru/walkthruResults';
import {
  FEW_OVERLAP_THRESHOLD,
  countCrossStoreGroups,
  filterRunsByStore,
  groupRuns,
  primaryStore,
  suggestedRunId,
  type LeaderboardGroup,
  type LeaderboardInput,
  groupSize,
} from '../../walkthru/leaderboard';
import { displayDatabaseProvider } from '../../utils/storageLabels';
import InfoTip from '../chrome/InfoTip';
import Pagination from '../chrome/Pagination';
import {
  OVERLAP_EXPLAIN,
  SCORE_COLUMN_EXPLAIN,
  SCORE_NOTE,
  dedupNote,
  rankExplain,
  scoreCellLabel,
  type RankScope,
} from './scoreLabels';

export type CrossStoreLeaderboardProps = {
  results: LeaderboardInput;
  selectedRunId?: string;
  onSelectRun: (runId: string) => void;
  /** Store highlighted as the suggested pick; defaults to the primary store (Redis 8). */
  suggestedStore?: string;
  /** When true the suggested pick is selected once on mount. */
  autoplay?: boolean;
  /** When false there is no suggested pick (no badge, no autoplay selection). Defaults to true. */
  suggest?: boolean;
  /** Overrides the intro sentence under the heading. */
  description?: string;
  /** Duplicate rows removed upstream, when the source reports it; the note states the rule either way. */
  collapsedDuplicates?: number;
  /** Where the rank column is counted: 'export' (default, Walkthru) or 'group' (live Compare). */
  rankScope?: RankScope;
};

const DEFAULT_DESCRIPTION =
  'Same dataset, questions and config, run on different stores. Rows are ordered by similarity score (normalised across this export). It measures similarity only.';

const DEFAULT_PER_PAGE = 10;

function groupTitle(group: LeaderboardGroup): string {
  const first = group.runs[0];
  return `${first.embedding_model} · ${first.chunking_method} · ${first.chunk_size} · ${first.retrieval_method}`;
}

function overlapNote(crossStore: number, total: number): string {
  const noun = crossStore === 1 ? 'config was' : 'configs were';
  return `Only ${crossStore} ${noun} run on more than one store (of ${total}), so cross-store comparison is limited.`;
}

function RunRow({
  run,
  selected,
  suggested,
  groupRunCount,
  onSelect,
}: {
  run: WalkthruRun;
  groupRunCount: number;
  selected: boolean;
  suggested: boolean;
  onSelect: (runId: string) => void;
}) {
  return (
    <tr
      data-testid={`run-row-${run.run_id}`}
      data-suggested={suggested}
      className={`border-t border-line ${suggested ? 'bg-accent-soft' : ''} ${selected ? 'ring-2 ring-inset ring-accent' : ''}`}
    >
      <td className="px-3 py-2 text-sm font-semibold text-ink">
        {displayDatabaseProvider(run.store)}
        {suggested ? (
          <span className="ml-2 rounded border border-accent px-1.5 py-0.5 text-xs font-semibold text-accent-strong">
            Suggested pick
          </span>
        ) : null}
      </td>
      <td className="px-3 py-2 text-sm text-ink">{run.embedding_model}</td>
      <td className="px-3 py-2 text-sm capitalize text-ink">{run.chunking_method}</td>
      <td className="px-3 py-2 text-sm text-ink">{run.chunk_size}</td>
      <td className="px-3 py-2 text-sm text-ink">{run.retrieval_method}</td>
      <td className="px-3 py-2 text-sm font-semibold text-ink">{scoreCellLabel(run.max_score, groupRunCount)}</td>
      <td className="px-3 py-2 text-sm text-ink">#{run.rank}</td>
      <td className="px-3 py-2 text-sm text-muted">{(run.elapsed_ms / 1000).toFixed(1)}s</td>
      <td className="px-3 py-2 text-right">
        <button
          type="button"
          aria-pressed={selected}
          aria-label={`Select ${run.store} run ${run.run_id}`}
          onClick={() => onSelect(run.run_id)}
          className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent aria-pressed:border-accent aria-pressed:bg-accent-soft"
        >
          {selected ? 'Selected' : 'Select'}
        </button>
      </td>
    </tr>
  );
}

/**
 * Cross-store leaderboard (Slice 56 Part C3): same-config runs grouped across stores, ordered by the
 * exporter's rank, with a store filter and a choice step that suggests the primary store's best run.
 * Props-driven and offline; scores are similarity scores, never accuracy.
 */
export default function CrossStoreLeaderboard({
  results,
  selectedRunId,
  onSelectRun,
  suggestedStore,
  autoplay = false,
  suggest = true,
  description = DEFAULT_DESCRIPTION,
  collapsedDuplicates,
  rankScope = 'export',
}: CrossStoreLeaderboardProps) {
  const [storeFilter, setStoreFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(DEFAULT_PER_PAGE);

  const suggested = suggest ? (suggestedStore ?? primaryStore(results)) : undefined;
  const suggestedId = suggestedRunId(results, suggested);

  const allGroups = useMemo(() => groupRuns(results.runs), [results.runs]);
  const crossStore = countCrossStoreGroups(allGroups);
  const groups = useMemo(() => groupRuns(filterRunsByStore(results.runs, storeFilter)), [results.runs, storeFilter]);
  const visible = groups.slice((page - 1) * perPage, page * perPage);

  const autoplayed = useRef(false);
  const onSelectRef = useRef(onSelectRun);
  onSelectRef.current = onSelectRun;
  useEffect(() => {
    if (!autoplay || autoplayed.current || suggestedId === undefined) return;
    autoplayed.current = true;
    onSelectRef.current(suggestedId);
  }, [autoplay, suggestedId]);

  const chooseStore = (store: string | null) => {
    setStoreFilter(store);
    setPage(1);
  };

  return (
    <section aria-label="Cross-store leaderboard" className="space-y-4">
      <div>
        <h3 className="font-display text-lg font-semibold text-ink">Cross-store leaderboard</h3>
        <p className="text-sm text-muted">{description}</p>
      </div>

      {allGroups.length === 0 ? (
        <p role="note" className="rounded-lg border border-line bg-canvas p-3 text-sm text-ink">
          No runs are bundled in this export, so there is nothing to compare yet.
        </p>
      ) : (
        <p
          role="note"
          data-testid="overlap-note"
          className="flex items-center justify-between gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-ink"
        >
          {crossStore < FEW_OVERLAP_THRESHOLD && crossStore < allGroups.length
            ? overlapNote(crossStore, allGroups.length)
            : `${crossStore} of ${allGroups.length} ${allGroups.length === 1 ? 'config was' : 'configs were'} run on more than one store.`}
          <InfoTip label="About the store overlap">{OVERLAP_EXPLAIN}</InfoTip>
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by store">
        {[null, ...Object.keys(results.stores)].map((store) => (
          <button
            key={store ?? 'all'}
            type="button"
            aria-pressed={storeFilter === store}
            onClick={() => chooseStore(store)}
            className="min-h-11 rounded-lg border border-line bg-paper px-3 text-sm font-semibold text-ink hover:border-accent aria-pressed:border-accent aria-pressed:bg-accent-soft"
          >
            {store === null ? 'All stores' : displayDatabaseProvider(store)}
          </button>
        ))}
      </div>

      <p data-testid="score-note" className="text-xs text-muted">{SCORE_NOTE}</p>
      <p data-testid="dedup-note" className="text-xs text-muted">{dedupNote(collapsedDuplicates)}</p>
      <p className="text-xs text-muted">Elapsed time is indicative — runs were not timing-controlled.</p>

      <div className="space-y-4">
        {visible.map((group) => (
          <div key={group.groupId} data-testid={`group-${group.groupId}`} className="overflow-hidden rounded-panel border border-line bg-paper">
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <h4 className="text-sm font-bold text-ink">{groupTitle(group)}</h4>
              <span className="text-xs text-muted">
                {group.spansStores ? `Run on ${group.stores.length} stores` : `Run on 1 store (${group.stores[0]})`}
              </span>
            </div>
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[40rem] text-left">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-muted">
                    <th scope="col" className="px-3 py-1">Store</th>
                    <th scope="col" className="px-3 py-1">Embedding model</th>
                    <th scope="col" className="px-3 py-1">Chunking</th>
                    <th scope="col" className="px-3 py-1">Chunk size</th>
                    <th scope="col" className="px-3 py-1">Retrieval</th>
                    <th scope="col" className="px-3 py-1">
                      <span className="inline-flex items-center gap-1">
                        Similarity score
                        <InfoTip label="About the similarity score">{SCORE_COLUMN_EXPLAIN}</InfoTip>
                      </span>
                    </th>
                    <th scope="col" className="px-3 py-1">
                      <span className="inline-flex items-center gap-1">
                        Rank
                        <InfoTip label="About the rank">{rankExplain(rankScope)}</InfoTip>
                      </span>
                    </th>
                    <th scope="col" className="px-3 py-1">Elapsed (indicative)</th>
                    <th scope="col" className="px-3 py-1"><span className="sr-only">Choose</span></th>
                  </tr>
                </thead>
                <tbody>
                  {group.runs.map((run) => (
                    <RunRow
                      key={run.run_id}
                      run={run}
                      selected={run.run_id === selectedRunId}
                      suggested={run.store === suggested}
                      groupRunCount={groupSize(results.runs, group.groupId)}
                      onSelect={onSelectRun}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {groups.length > DEFAULT_PER_PAGE ? (
        <Pagination
          currentPage={page}
          totalItems={groups.length}
          itemsPerPage={perPage}
          onPageChange={setPage}
          onItemsPerPageChange={(items) => {
            setPerPage(items);
            setPage(1);
          }}
          selectId="cross-store-leaderboard-per-page"
        />
      ) : null}
    </section>
  );
}
