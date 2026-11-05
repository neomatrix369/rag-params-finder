/**
 * Author: Slice 45
 * Created: 2026-07-28
 * Scope: shared StatTile densities
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import StatTile from './StatTile';

const strip = (html: string) => html.replace(/_r_[0-9a-z]+_/g, 'ID'); // React useId counter, not randomness

describe('StatTile', () => {
  it('Given comfortable density, when rendered, then label and value appear', () => {
    /**
     * Scenario: Comfortable StatTile shows label, value, and hint.
     * Slice: 45 — FE shared primitives (StatTile).
     * Given label Chunks, value 12, and a hint,
     * When rendered at default density,
     * Then label, value, and hint are visible.
     */
    // -- Given / When --
    render(<StatTile label="Chunks" value={12} hint="across runs" />);
    // -- Then --
    expect(screen.getByText('Chunks')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('across runs')).toBeInTheDocument();
  });

  it('Given compact density, when rendered without hint, then only label and value appear', () => {
    /**
     * Scenario: Compact StatTile omits hint when none is provided.
     * Slice: 45 — FE shared primitives (StatTile).
     * Given compact density without a hint,
     * When rendered,
     * Then only label and value appear.
     */
    // -- Given / When --
    render(<StatTile label="Runs" value="3" density="compact" />);
    // -- Then --
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('Given a hint, when rendered, then it is exposed through an InfoTip described by the hint', () => {
    /**
     * Scenario: StatTile.hint renders through InfoTip (Slice 67C).
     * Slice: 67C — explain UI.
     * Given a tile with a hint,
     * When rendered,
     * Then the info button is described by the tooltip holding the hint, exactly once.
     */
    // -- Given / When --
    render(<StatTile label="Chunks" value={12} hint="across runs" />);
    // -- Then --
    const button = screen.getByRole('button', { name: 'About Chunks' });
    expect(button).toHaveAttribute('aria-describedby', screen.getByRole('tooltip', { hidden: true }).id);
    expect(screen.getAllByText('across runs')).toHaveLength(1);
  });

  it('Given an explain prop on each density, when tapped, then the formula opens', () => {
    /**
     * Scenario: StatTile.explain adds a second tip about how the number is derived.
     * Slice: 67C — explain UI.
     * Given comfortable and compact tiles with explain,
     * When the explain button is tapped,
     * Then the formula tip becomes visible.
     */
    // -- Given --
    render(
      <>
        <StatTile label="Total" value={12} explain="models x sizes" />
        <StatTile label="Runs" value={3} density="compact" explain="done + failed" />
      </>,
    );
    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'How Total is calculated' }));
    fireEvent.click(screen.getByRole('button', { name: 'How Runs is calculated' }));
    // -- Then --
    expect(screen.getByText('models x sizes')).toBeVisible();
    expect(screen.getByText('done + failed')).toBeVisible();
  });

  it('Given no hint and no explain, when rendered, then there is no info button', () => {
    /**
     * Scenario: Self-explanatory tiles stay clean.
     * Slice: 67C — explain UI.
     */
    // -- Given / When --
    render(<StatTile label="Runs" value="3" />);
    // -- Then --
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('Given identical props, when rendered twice, then the output markup is identical', () => {
    /**
     * Scenario: Determinism — same props, same output (no clock, randomness or computed counts).
     * Slice: 67C — explain UI.
     */
    // -- Given --
    const props = { label: 'Total', value: 12, hint: 'h', explain: 'e' } as const;
    // -- When --
    const first = render(<StatTile {...props} />);
    const a = strip(first.container.innerHTML);
    first.unmount();
    const b = strip(render(<StatTile {...props} />).container.innerHTML);
    // -- Then --
    expect(b).toBe(a);
  });
});
