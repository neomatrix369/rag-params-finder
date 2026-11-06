/**
 * Tests for CrossStoreLeaderboard: grouping, filter, timings label, choice step, autoplay, fallback.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C3 - cross-store leaderboard + choice step GWT scenarios
 */
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { makeWalkthruResults, makeWalkthruRun } from '../../test/helpers/walkthruResults'
import CrossStoreLeaderboard from './CrossStoreLeaderboard'

describe('CrossStoreLeaderboard', () => {
  it('Given the bundled export, when rendered, then rows show store, model, chunking, size, retrieval, score and rank per group', () => {
    /**
     * Scenario: Rows carry the contract fields, grouped by group_id and ordered by rank.
     * Slice: 56 Part C3 - leaderboard rows
     */
    // -- Given --
    const results = makeWalkthruResults()

    // -- When --
    render(<CrossStoreLeaderboard results={results} onSelectRun={() => {}} />)

    // -- Then --
    const groupA = screen.getByTestId('group-group-a')
    const rows = within(groupA).getAllByRole('row').slice(1)
    expect(rows.map((r) => r.getAttribute('data-testid'))).toEqual([
      'run-row-run-redis-best',
      'run-row-run-pg-best',
      'run-row-run-mongo-best',
    ])
    const redisRow = within(groupA).getByTestId('run-row-run-redis-best')
    for (const text of ['redis', 'all-MiniLM-L6-v2', 'recursive', '512', 'dense', '100.0', '#1']) {
      expect(within(redisRow).getByText(text, { exact: false })).toBeInTheDocument()
    }
    expect(within(screen.getByTestId('group-group-b')).getAllByRole('row')).toHaveLength(4)
    expect(screen.getAllByText('Similarity score').length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toMatch(/accuracy|correct|faster|fastest/i)
  })

  it('Given a store filter, when a store is chosen, then only its runs show; All stores restores them', () => {
    /**
     * Scenario: The store filter narrows and restores the leaderboard.
     * Slice: 56 Part C3 - store filter
     */
    // -- Given --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} />)

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'postgres' }))

    // -- Then --
    expect(screen.getByTestId('run-row-run-pg-best')).toBeInTheDocument()
    expect(screen.queryByTestId('run-row-run-redis-best')).toBeNull()
    expect(screen.getByRole('button', { name: 'postgres' })).toHaveAttribute('aria-pressed', 'true')

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'All stores' }))

    // -- Then --
    expect(screen.getByTestId('run-row-run-redis-best')).toBeInTheDocument()
  })

  it('Given timings are shown, when rendered, then they are labelled indicative and nothing is ordered by speed', () => {
    /**
     * Scenario: Timings carry the indicative label; row order ignores elapsed_ms.
     * Slice: 56 Part C3 - timings
     */
    // -- Given --
    const fastLow = makeWalkthruRun({ run_id: 'fast-low', store: 'postgres', rank: 2, elapsed_ms: 1000 })
    const slowTop = makeWalkthruRun({ run_id: 'slow-top', rank: 1, elapsed_ms: 90000 })
    const results = makeWalkthruResults({ runs: [fastLow, slowTop] })

    // -- When --
    render(<CrossStoreLeaderboard results={results} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByText(/indicative — runs were not timing-controlled/)).toBeInTheDocument()
    expect(screen.getByText('90.0s')).toBeInTheDocument()
    const ids = within(screen.getByTestId('group-group-a'))
      .getAllByRole('row')
      .slice(1)
      .map((r) => r.getAttribute('data-testid'))
    expect(ids).toEqual(['run-row-slow-top', 'run-row-fast-low'])
  })

  it('Given the choice step, when rendered, then primary-store runs are highlighted and selecting a row calls onSelectRun', () => {
    /**
     * Scenario: Redis 8 (primary) runs are the suggested pick; picking a row reports its run id.
     * Slice: 56 Part C3 - choice step
     */
    // -- Given --
    const onSelectRun = vi.fn()
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} selectedRunId="run-pg-best" onSelectRun={onSelectRun} />)

    // -- Then --
    expect(screen.getByTestId('run-row-run-redis-best')).toHaveAttribute('data-suggested', 'true')
    expect(screen.getByTestId('run-row-run-pg-best')).toHaveAttribute('data-suggested', 'false')
    expect(screen.getAllByText('Suggested pick')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Select postgres run run-pg-best' })).toHaveAttribute('aria-pressed', 'true')

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Select mongodb run run-mongo-best' }))

    // -- Then --
    expect(onSelectRun).toHaveBeenCalledWith('run-mongo-best')
  })

  it('Given suggestedStore, when set, then that store is highlighted instead of the primary', () => {
    /**
     * Scenario: The suggested store is overridable.
     * Slice: 56 Part C3 - choice step
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} suggestedStore="mongodb" onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('run-row-run-mongo-best')).toHaveAttribute('data-suggested', 'true')
    expect(screen.getByTestId('run-row-run-redis-best')).toHaveAttribute('data-suggested', 'false')
  })

  it('Given suggest=false, when rendered with autoplay, then there is no suggested pick and the description is overridden', () => {
    /**
     * Scenario: The live compare view has no primary store, so nothing is suggested or auto-selected.
     * Slice: 66 - live cross-store compare
     */
    // -- Given --
    const onSelectRun = vi.fn()

    // -- When --
    render(
      <CrossStoreLeaderboard
        results={makeWalkthruResults()}
        suggest={false}
        autoplay
        description="Live description."
        onSelectRun={onSelectRun}
      />,
    )

    // -- Then --
    expect(screen.queryByText('Suggested pick')).not.toBeInTheDocument()
    expect(screen.getByTestId('run-row-run-redis-best')).toHaveAttribute('data-suggested', 'false')
    expect(onSelectRun).not.toHaveBeenCalled()
    expect(screen.getByText('Live description.')).toBeInTheDocument()
  })

  it('Given autoplay, when mounted, then the suggested pick is selected once', () => {
    /**
     * Scenario: Autoplay takes the suggestion automatically, only once even across re-renders.
     * Slice: 56 Part C3 - autoplay
     */
    // -- Given --
    const onSelectRun = vi.fn()
    const results = makeWalkthruResults()

    // -- When --
    const { rerender } = render(<CrossStoreLeaderboard results={results} autoplay onSelectRun={onSelectRun} />)
    rerender(<CrossStoreLeaderboard results={results} autoplay onSelectRun={(id) => onSelectRun(id)} />)

    // -- Then --
    expect(onSelectRun).toHaveBeenCalledTimes(1)
    expect(onSelectRun).toHaveBeenCalledWith('run-redis-best')
  })

  it('Given autoplay is off, when mounted, then nothing is selected automatically', () => {
    /**
     * Scenario: Default is manual choice.
     * Slice: 56 Part C3 - autoplay off
     */
    // -- Given --
    const onSelectRun = vi.fn()

    // -- When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={onSelectRun} />)

    // -- Then --
    expect(onSelectRun).not.toHaveBeenCalled()
  })

  it('Given autoplay but no stores, when mounted, then no selection is attempted', () => {
    /**
     * Scenario: Nothing to suggest means nothing to autoplay.
     * Slice: 56 Part C3 - fallback
     */
    // -- Given --
    const onSelectRun = vi.fn()

    // -- When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults({ stores: {}, runs: [] })} autoplay onSelectRun={onSelectRun} />)

    // -- Then --
    expect(onSelectRun).not.toHaveBeenCalled()
    expect(screen.getByText(/No runs are bundled in this export/)).toBeInTheDocument()
  })

  it('Given only one store ran, when rendered, then the leaderboard shows and states the overlap limit', () => {
    /**
     * Scenario: Fallback - few overlapping configs still render with a clear note.
     * Slice: 56 Part C3 - fallback
     */
    // -- Given --
    const only = makeWalkthruRun()
    const base = makeWalkthruResults()
    const results = makeWalkthruResults({ runs: [only], stores: { redis: base.stores.redis } })

    // -- When --
    render(<CrossStoreLeaderboard results={results} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('Only 0 configs were run on more than one store')
    expect(screen.getByTestId('run-row-run-redis-best')).toBeInTheDocument()
    expect(screen.getByText('Run on 1 store (redis)')).toBeInTheDocument()
  })

  it('Given exactly one overlapping config, when rendered, then the note is singular', () => {
    /**
     * Scenario: Singular wording for one cross-store config.
     * Slice: 56 Part C3 - fallback
     */
    // -- Given --
    const a = makeWalkthruRun()
    const b = makeWalkthruRun({ run_id: 'pg', store: 'postgres', rank: 2 })
    const solo = makeWalkthruRun({ run_id: 'solo', group_id: 'group-solo', rank: 3 })
    const results = makeWalkthruResults({ runs: [a, b, solo] })

    // -- When --
    render(<CrossStoreLeaderboard results={results} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('Only 1 config was run on more than one store (of 2)')
    expect(screen.getByText('Run on 2 stores')).toBeInTheDocument()
  })

  it('Given the only config overlaps, when rendered, then the plain summary is singular', () => {
    /**
     * Scenario: Grammar of the plain summary when there is a single config.
     * Slice: 56 Part C3 - fallback boundary
     */
    // -- Given --
    const runs = [makeWalkthruRun(), makeWalkthruRun({ run_id: 'pg', store: 'postgres', rank: 2 })]

    // -- When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults({ runs })} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('1 of 1 config was run on more than one store.')
  })

  it('Given every config overlaps, when rendered, then the note is a plain summary', () => {
    /**
     * Scenario: No warning wording when overlap is not limited.
     * Slice: 56 Part C3 - fallback boundary
     */
    // -- Given --
    const runs = ['g1', 'g2', 'g3'].flatMap((g, i) => [
      makeWalkthruRun({ run_id: `${g}-r`, group_id: g, rank: i * 2 + 1 }),
      makeWalkthruRun({ run_id: `${g}-p`, group_id: g, store: 'postgres', rank: i * 2 + 2 }),
    ])

    // -- When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults({ runs })} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('overlap-note')).toHaveTextContent('3 of 3 configs were run on more than one store.')
  })

  it('Given more groups than one page, when paged and filtered, then pagination applies and resets', () => {
    /**
     * Scenario: Long lists are paginated; changing the filter or page size returns to page 1.
     * Slice: 56 Part C3 - pagination
     */
    // -- Given --
    const runs = Array.from({ length: 12 }, (_, i) =>
      makeWalkthruRun({ run_id: `r${i}`, group_id: `g${String(i).padStart(2, '0')}`, rank: i + 1 }),
    )
    const base = makeWalkthruResults()
    render(
      <CrossStoreLeaderboard
        results={makeWalkthruResults({ runs, stores: { redis: base.stores.redis } })}
        onSelectRun={() => {}}
      />,
    )
    expect(screen.getAllByRole('table')).toHaveLength(10)

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    // -- Then --
    expect(screen.getAllByRole('table')).toHaveLength(2)

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'redis' }))

    // -- Then --
    expect(screen.getAllByRole('table')).toHaveLength(10)

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '25' } })

    // -- Then --
    expect(screen.getAllByRole('table')).toHaveLength(12)
  })

  it('Given a group with a single run, when rendered, then it says "Only run" and shows no 100.0', () => {
    /**
     * Scenario: Scores are min-max normalised within a group, so a lone run is trivially 100.
     * Slice: 67D - lone-run score is not shown as a result
     */
    // -- Given --
    const lone = makeWalkthruRun({ run_id: 'lone', group_id: 'solo', rank: 1, max_score: 100 })
    const results = makeWalkthruResults({ runs: [lone] })

    // -- When --
    render(<CrossStoreLeaderboard results={results} onSelectRun={() => {}} />)

    // -- Then --
    const row = screen.getByTestId('run-row-lone')
    expect(within(row).getByText(/only run in this group/i)).toBeInTheDocument()
    expect(within(row).queryByText('100.0')).not.toBeInTheDocument()
  })

  it('Given a multi-run group filtered down to one visible row, when rendered, then the row still shows a numeric score', () => {
    /**
     * Scenario: the lone-run marker depends on the real group size, not on how many rows the filter leaves.
     * Slice: 67D - score label stays truthful under the store filter.
     */
    // -- Given --
    const redis = makeWalkthruRun({ run_id: 'redis-1', store: 'redis', group_id: 'shared', rank: 1, max_score: 100 })
    const pg = makeWalkthruRun({ run_id: 'pg-1', store: 'postgres', group_id: 'shared', rank: 2, max_score: 62.5 })
    render(<CrossStoreLeaderboard results={makeWalkthruResults({ runs: [redis, pg] })} onSelectRun={() => {}} />)

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'postgres' }))

    // -- Then --
    const row = screen.getByTestId('run-row-pg-1')
    expect(within(row).getByText('62.5')).toBeInTheDocument()
    expect(within(row).queryByText(/only run in this group/i)).not.toBeInTheDocument()
  })

  it('Given any leaderboard, when rendered, then the score is described as the max, normalised per group', () => {
    /**
     * Scenario: The column label hides max-not-average and the normalisation scope.
     * Slice: 67D - score explanation
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} />)

    // -- Then --
    const note = screen.getByTestId('score-note')
    expect(note).toHaveTextContent(/highest.*not the average/i)
    expect(note).toHaveTextContent(/normalised per group/i)
    expect(note).toHaveTextContent(/0.100/)
  })

  it('Given a reported collapsed count, when rendered, then the note states the number', () => {
    /**
     * Scenario: A known dedup count is shown verbatim.
     * Slice: 67D - dedup count
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} collapsedDuplicates={2} />)

    // -- Then --
    expect(screen.getByTestId('dedup-note')).toHaveTextContent(/^2 duplicate rows were collapsed/)
  })

  it('Given any leaderboard, when rendered, then a visible note says duplicate runs are collapsed to the latest', () => {
    /**
     * Scenario: Dedup is visible, not silent. The count is not in the payload, so the rule is stated.
     * Slice: 67D - dedup note
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getByTestId('dedup-note')).toHaveTextContent(/same config.*more than once.*only the latest run/i)
  })

  it('Given collapsedDuplicates of 0 and 1, when rendered, then each count is stated with the right noun', () => {
    /**
     * Scenario: 0 and 1 are real counts, not "absent".
     * Slice: 67G - dedup visibility
     */
    // -- Given / When --
    const { rerender } = render(
      <CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} collapsedDuplicates={0} />,
    )
    const zero = screen.getByTestId('dedup-note').textContent
    rerender(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} collapsedDuplicates={1} />)

    // -- Then --
    expect(zero).toMatch(/^0 duplicate rows were collapsed/)
    expect(screen.getByTestId('dedup-note')).toHaveTextContent(/^1 duplicate row was collapsed/)
  })

  it('Given the leaderboard, when rendered, then score, rank and overlap each carry an InfoTip', () => {
    /**
     * Scenario: Score normalisation, lone-run, rank and overlap are explained in tips.
     * Slice: 67G - Compare/Walkthru explanations
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.getAllByRole('button', { name: 'About the similarity score' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'About the rank' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: 'About the store overlap' })).toBeInTheDocument()
    expect(screen.getAllByText(/lowest run in the group is 0 and the highest is 100/).length).toBeGreaterThan(0)
  })

  it.each([
    ['group' as const, 'counted inside its group'],
    ['export' as const, 'counted across the whole export'],
  ])('Given rankScope %s, when rendered, then the rank tip says "%s"', (rankScope, phrase) => {
    /**
     * Scenario: The rank tip names where rank is counted.
     * Slice: 67G - rank scope
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} rankScope={rankScope} />)

    // -- Then --
    expect(screen.getAllByText((content) => content.includes(phrase)).length).toBeGreaterThan(0)
  })

  it('Given no rankScope, when rendered, then the Walkthru default (whole export) applies', () => {
    /**
     * Scenario: Walkthru passes no prop; rank spans the export.
     * Slice: 67G - rank scope default
     */
    // -- Given / When --
    render(<CrossStoreLeaderboard results={makeWalkthruResults()} onSelectRun={() => {}} />)

    // -- Then --
    expect(screen.queryByText(/counted inside its group/)).not.toBeInTheDocument()
  })
})
