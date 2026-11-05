/**
 * Tests for StatCard explain affordance.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67C — StatCard explain prop in both layouts
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StatCard from './StatCard';
import { explainLabel } from '../../chrome/infoTipUtils';
import { normalizeIds } from '../../../test/helpers/normalizeIds';

describe('StatCard', () => {
  it('Given no explain, when rendered in either layout, then label and value show and no info button exists', () => {
    /**
     * Scenario: Unchanged behaviour without explain.
     * Slice: 67C — explain UI.
     */
    // -- Given / When --
    render(
      <>
        <StatCard label="Total" value={12} icon={<i />} trend="+1" />
        <StatCard compact label="Failed" value={2} icon={<i />} trend="-1" />
      </>,
    );
    // -- Then --
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('Given explain in each layout, when tapped, then the formula is shown and described by the button', () => {
    /**
     * Scenario: StatCard.explain renders an InfoTip next to the label.
     * Slice: 67C — explain UI.
     * Given compact and full cards with explain,
     * When each info button is tapped,
     * Then each tip is visible and wired through aria-describedby.
     */
    // -- Given --
    render(
      <>
        <StatCard label="Total" value={12} icon={<i />} explain="models x sizes" />
        <StatCard compact label="Failed" value={2} icon={<i />} explain="runs that errored" />
      </>,
    );
    // -- When --
    const total = screen.getByRole('button', { name: explainLabel('Total') });
    fireEvent.click(total);
    fireEvent.click(screen.getByRole('button', { name: explainLabel('Failed') }));
    // -- Then --
    expect(screen.getByText('models x sizes')).toBeVisible();
    expect(screen.getByText('runs that errored')).toBeVisible();
    expect(total.getAttribute('aria-describedby')).toBe(screen.getByText('models x sizes').id);
  });

  it('Given identical props, when rendered twice, then the output markup is identical', () => {
    /**
     * Scenario: Determinism — same props, same output.
     * Slice: 67C — explain UI.
     */
    // -- Given --
    const props = { label: 'Total', value: 12, icon: <i />, explain: 'e' };
    // -- When --
    const first = render(<StatCard {...props} />);
    const a = normalizeIds(first.container.innerHTML);
    first.unmount();
    const b = normalizeIds(render(<StatCard {...props} />).container.innerHTML);
    // -- Then --
    expect(b).toBe(a);
  });
});
