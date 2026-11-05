/**
 * Run replay: steps one recorded run through the fixed pipeline stages and, at the last stage,
 * shows its results through the existing explorer components. Props-driven, no network.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part B - run replay (DECISIONS #274: real totals only, no per-stage durations)
 */
import { useEffect, useState } from 'react'
import { REPLAY_PHASES } from '../../walkthru/walkthruResults'
import type { WalkthruResults } from '../../walkthru/walkthruResults'
import {
  formatElapsed,
  resolveRun,
  runLabel,
  toDetailedResults,
  toPhase,
  toRankedConfig,
} from '../../walkthru/replayAdapter'
import { BestParamsCard, DetailedResultsTab } from '../explore/ExplorePanels'
import { PhaseIndicator } from '../experiment/experimentDetail'

export interface RunReplayProps {
  results: WalkthruResults
  /** Selected run; when omitted the primary store's best run is shown. */
  runId?: string
  onSelectRun?: (runId: string) => void
  /** Autoplay step interval in ms (only used while Autoplay is on). */
  autoplayIntervalMs?: number
}

const LAST_STEP = REPLAY_PHASES.length - 1
const BTN =
  'min-h-11 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 disabled:opacity-40'

export default function RunReplay({ results, runId, onSelectRun, autoplayIntervalMs = 1500 }: RunReplayProps) {
  const [pickedId, setPickedId] = useState<string | undefined>(undefined)
  const [position, setPosition] = useState({ runId: '', step: 0 })
  const [autoplay, setAutoplay] = useState(false)

  const run = resolveRun(results, runId ?? pickedId)
  // The step belongs to the run it was taken on, so picking another run restarts at the first stage.
  const step = position.runId === run?.run_id ? position.step : 0
  const goTo = (next: number) => setPosition({ runId: run?.run_id ?? '', step: next })

  useEffect(() => {
    if (!autoplay || !run || step >= LAST_STEP) return undefined
    const timer = setTimeout(() => setPosition({ runId: run.run_id, step: step + 1 }), autoplayIntervalMs)
    return () => clearTimeout(timer)
  }, [autoplay, run, step, autoplayIntervalMs])

  if (!run) {
    return <p className="text-sm text-slate-600">No recorded runs are bundled with this build.</p>
  }

  // eslint-disable-next-line security/detect-object-injection -- step is clamped to 0..LAST_STEP by the controls
  const stage = REPLAY_PHASES[step]
  const atResults = step === LAST_STEP

  return (
    <section
      aria-label="Run replay"
      className="space-y-4 motion-reduce:[&_.animate-pulse]:animate-none"
    >
      <div>
        <label htmlFor="replay-run" className="mr-2 text-sm font-medium text-slate-700">
          Run
        </label>
        <select
          id="replay-run"
          value={run.run_id}
          onChange={(event) => {
            setPickedId(event.target.value)
            onSelectRun?.(event.target.value)
          }}
          className="min-h-11 max-w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"
        >
          {results.runs.map((candidate) => (
            <option key={candidate.run_id} value={candidate.run_id}>
              {runLabel(candidate)}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <PhaseIndicator current={toPhase(stage)} />
        <p className="text-sm font-semibold text-slate-800" aria-live="polite">
          Stage {step + 1} of {REPLAY_PHASES.length}: {stage}
        </p>
        <p className="text-xs text-slate-500">stage sequence; only total time was recorded</p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-400">Total time (indicative)</dt>
            <dd>{formatElapsed(run.elapsed_ms)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-400">Final phase</dt>
            <dd>{run.phase}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-400">Created</dt>
            <dd>{run.created_at}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-400">Updated</dt>
            <dd>{run.updated_at}</dd>
          </div>
        </dl>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={BTN}
          aria-label="Previous stage"
          disabled={step === 0}
          onClick={() => goTo(step - 1)}
        >
          Back
        </button>
        <button
          type="button"
          className={BTN}
          aria-label="Next stage"
          disabled={atResults}
          onClick={() => goTo(step + 1)}
        >
          Next
        </button>
        <label className="flex min-h-11 items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={autoplay} onChange={(event) => setAutoplay(event.target.checked)} />
          Autoplay
        </label>
      </div>

      {atResults && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Rank {run.rank} in this export (rank {run.store_rank} within {run.store}). Scores are similarity
            scores, min-max normalised across the exported runs; they do not measure whether an answer is right.
          </p>
          {run.store_rank === 1 ? (
            <BestParamsCard
              config={toRankedConfig(run)}
              scoreLabel="Similarity score"
              heading={`Best parameters on ${run.store}`}
            />
          ) : (
            <p className="rounded-lg bg-slate-100 p-3 text-sm text-slate-700">
              {runLabel(run)} - max similarity score {run.max_score}, query average {run.query_avg_score}.
            </p>
          )}
          <DetailedResultsTab results={toDetailedResults(run)} />
        </div>
      )}
    </section>
  )
}
