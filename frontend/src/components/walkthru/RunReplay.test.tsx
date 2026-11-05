/**
 * Tests for RunReplay: stage stepping, recorded facts only, run picking, autoplay, no network.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: SLICE-56 Part B - run replay GWT scenarios (DECISIONS #274)
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RunReplay from './RunReplay'
import { makeWalkthruResults } from '../../test/helpers/walkthruResults'

const next = () => fireEvent.click(screen.getByRole('button', { name: 'Next stage' }))
const toEnd = () => Array.from({ length: 7 }).forEach(next)

describe('RunReplay', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('Given the bundled export, when opened, then the Redis run is shown at the first stage with recorded facts', () => {
    /**
     * Scenario: Default run and honest facts.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const results = makeWalkthruResults()

    // -- When --
    render(<RunReplay results={results} />)

    // -- Then --
    expect(screen.getByLabelText('Run')).toHaveValue('run-redis-best')
    expect(screen.getByText('Stage 1 of 8: QUEUED')).toBeInTheDocument()
    expect(screen.getByText('stage sequence; only total time was recorded')).toBeInTheDocument()
    expect(screen.getByText('12.5 s')).toBeInTheDocument()
    expect(screen.getByText('complete')).toBeInTheDocument()
    expect(screen.getByText('2026-11-01T10:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('2026-11-01T10:00:12Z')).toBeInTheDocument()
    expect(screen.getByText('Total time (indicative)')).toBeInTheDocument()
    expect(screen.queryByText(/Best Overall Parameters/)).toBeNull()
  })

  it('Given the replay, when Next and Back are pressed, then it steps through the stages and respects the ends', () => {
    /**
     * Scenario: Next/Back step QUEUED to COMPLETE and are disabled at the ends.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    render(<RunReplay results={makeWalkthruResults()} />)
    const back = screen.getByRole('button', { name: 'Previous stage' })
    expect(back).toBeDisabled()

    // -- When --
    next()
    next()

    // -- Then --
    expect(screen.getByText('Stage 3 of 8: CHUNKING')).toBeInTheDocument()
    expect(back).toBeEnabled()

    // -- When --
    fireEvent.click(back)
    expect(screen.getByText('Stage 2 of 8: PARSING')).toBeInTheDocument()
    toEnd()

    // -- Then --
    expect(screen.getByText('Stage 8 of 8: COMPLETE')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next stage' })).toBeDisabled()
  })

  it('Given the first stages, when viewed, then no results are shown until COMPLETE', () => {
    /**
     * Scenario: Results appear only at the final stage, via the existing components.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    render(<RunReplay results={makeWalkthruResults()} />)

    // -- When / Then --
    expect(screen.queryByText(/Individual chunk results/)).toBeNull()
    toEnd()
    expect(screen.getByText('Best parameters on redis')).toBeInTheDocument()
    expect(screen.queryByText('Best Overall Parameters')).toBeNull()
    expect(screen.getByText(/Individual chunk results/)).toBeInTheDocument()
    expect(screen.getByText(/Applications for the Pell Grant close on June 30/)).toBeInTheDocument()
    expect(screen.getByText(/Rank 1 in this export/)).toBeInTheDocument()
    expect(screen.getByText(/similarity scores/)).toBeInTheDocument()
  })

  it('Given a non-best run, when COMPLETE is reached, then no "best parameters" claim is made', () => {
    /**
     * Scenario: A weaker run shows its parameters without the best-run heading.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    render(<RunReplay results={makeWalkthruResults()} runId="run-redis-worst" />)

    // -- When --
    toEnd()

    // -- Then --
    expect(screen.queryByText('Best Overall Parameters')).toBeNull()
    expect(screen.queryByText(/^Best parameters on /)).toBeNull()
    expect(screen.getByText(/max similarity score 20/)).toBeInTheDocument()
    expect(screen.getByText(/Unrelated campus parking guidance/)).toBeInTheDocument()
  })

  it('Given a stage reached, when a different run is picked, then the replay restarts and shows that run', () => {
    /**
     * Scenario: Uncontrolled pick restarts at the first stage and notifies the parent.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const onSelectRun = vi.fn()
    render(<RunReplay results={makeWalkthruResults()} onSelectRun={onSelectRun} />)
    next()
    next()

    // -- When --
    fireEvent.change(screen.getByLabelText('Run'), { target: { value: 'run-pg-best' } })

    // -- Then --
    expect(onSelectRun).toHaveBeenCalledWith('run-pg-best')
    expect(screen.getByLabelText('Run')).toHaveValue('run-pg-best')
    expect(screen.getByText('Stage 1 of 8: QUEUED')).toBeInTheDocument()
    expect(screen.getByText('15.0 s')).toBeInTheDocument()
  })

  it('Given a controlled runId, when it changes, then the replay restarts on the new run', () => {
    /**
     * Scenario: Parent-driven selection (leaderboard pick) restarts the replay.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const results = makeWalkthruResults()
    const { rerender } = render(<RunReplay results={results} runId="run-redis-best" />)
    next()

    // -- When --
    rerender(<RunReplay results={results} runId="run-mongo-best" />)

    // -- Then --
    expect(screen.getByLabelText('Run')).toHaveValue('run-mongo-best')
    expect(screen.getByText('Stage 1 of 8: QUEUED')).toBeInTheDocument()
    expect(screen.getByText('18.0 s')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Run')).getAllByRole('option')).toHaveLength(6)
  })

  it('Given Autoplay is off, when time passes, then nothing advances', () => {
    /**
     * Scenario: Autoplay is off by default; only Next advances.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    vi.useFakeTimers()
    render(<RunReplay results={makeWalkthruResults()} autoplayIntervalMs={100} />)
    expect(screen.getByLabelText('Autoplay')).not.toBeChecked()

    // -- When --
    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    // -- Then --
    expect(screen.getByText('Stage 1 of 8: QUEUED')).toBeInTheDocument()
  })

  it('Given Autoplay is on, when time passes, then stages advance and stop at COMPLETE; off stops it', () => {
    /**
     * Scenario: Autoplay advances on the injected interval, stops at the end and can be switched off.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    vi.useFakeTimers()
    render(<RunReplay results={makeWalkthruResults()} autoplayIntervalMs={100} />)

    // -- When --
    fireEvent.click(screen.getByLabelText('Autoplay'))
    act(() => {
      vi.advanceTimersByTime(100)
    })
    act(() => {
      vi.advanceTimersByTime(100)
    })

    // -- Then --
    expect(screen.getByText('Stage 3 of 8: CHUNKING')).toBeInTheDocument()

    // -- When --
    fireEvent.click(screen.getByLabelText('Autoplay'))
    act(() => {
      vi.advanceTimersByTime(5_000)
    })

    // -- Then --
    expect(screen.getByText('Stage 3 of 8: CHUNKING')).toBeInTheDocument()

    // -- When --
    fireEvent.click(screen.getByLabelText('Autoplay'))
    for (let tick = 0; tick < 10; tick += 1) {
      act(() => {
        vi.advanceTimersByTime(100)
      })
    }

    // -- Then --
    expect(screen.getByText('Stage 8 of 8: COMPLETE')).toBeInTheDocument()
  })

  it('Given the replay, when it runs end to end, then no network request is made', () => {
    /**
     * Scenario: Zero network.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)

    // -- When --
    render(<RunReplay results={makeWalkthruResults()} />)
    toEnd()
    fireEvent.change(screen.getByLabelText('Run'), { target: { value: 'run-pg-best' } })

    // -- Then --
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('Given the rendered replay, when inspected, then it carries no animation of its own and suppresses the pulse on reduced motion', () => {
    /**
     * Scenario: prefers-reduced-motion respected by construction.
     * Slice: 56 Part B - run replay
     */
    // -- Given / When --
    render(<RunReplay results={makeWalkthruResults()} />)
    const section = screen.getByRole('region', { name: 'Run replay' })

    // -- Then --
    expect(section.className).toContain('motion-reduce:[&_.animate-pulse]:animate-none')
    // The only animation is PhaseIndicator's own pulse, which the guard class above neutralises.
    const withoutGuard = section.outerHTML
      .replace('motion-reduce:[&amp;_.animate-pulse]:animate-none', '')
      .replace('animate-pulse', '')
    expect(withoutGuard).not.toMatch(/animate-|transition|duration-/)
  })

  it('Given an export with no runs, when opened, then an honest empty message is shown', () => {
    /**
     * Scenario: Empty export does not crash.
     * Slice: 56 Part B - run replay
     */
    // -- Given / When --
    render(<RunReplay results={makeWalkthruResults({ runs: [], stores: {} })} />)

    // -- Then --
    expect(screen.getByText('No recorded runs are bundled with this build.')).toBeInTheDocument()
  })

  it('Given copy, when the replay is complete, then it never claims correctness or accuracy', () => {
    /**
     * Scenario: Copy discipline - similarity score, timings indicative.
     * Slice: 56 Part B - run replay
     */
    // -- Given --
    render(<RunReplay results={makeWalkthruResults()} />)

    // -- When --
    toEnd()

    // -- Then --
    const own = screen.getByRole('region', { name: 'Run replay' }).textContent ?? ''
    expect(own).not.toMatch(/accura|\bhit\b|is correct|relevance/i)
    expect(own).toMatch(/Similarity score/)
    expect(own).toMatch(/indicative/)
  })
})
