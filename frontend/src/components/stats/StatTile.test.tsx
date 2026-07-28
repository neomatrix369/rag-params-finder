/**
 * Author: Slice 45
 * Created: 2026-07-28
 * Scope: shared StatTile densities
 */
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatTile from './StatTile';

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
});
