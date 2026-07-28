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
    // -- Given / When --
    render(<StatTile label="Chunks" value={12} hint="across runs" />);
    // -- Then --
    expect(screen.getByText('Chunks')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('across runs')).toBeInTheDocument();
  });

  it('Given compact density, when rendered without hint, then only label and value appear', () => {
    // -- Given / When --
    render(<StatTile label="Runs" value="3" density="compact" />);
    // -- Then --
    expect(screen.getByText('Runs')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
