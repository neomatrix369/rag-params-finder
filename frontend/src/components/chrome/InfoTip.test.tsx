/**
 * Tests for InfoTip, the dependency-free explain affordance.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67C — aria wiring, tap toggle, Escape, outside dismiss, no duplicate announcement
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import InfoTip from './InfoTip';
import { normalizeIds } from '../../test/helpers/normalizeIds';

describe('InfoTip', () => {
  it('Given a tip, when rendered, then the button points at the hidden tip via aria-describedby', () => {
    /**
     * Scenario: The trigger is wired to its explanation.
     * Slice: 67C — InfoTip
     */
    // -- Given / When --
    render(<InfoTip label="About Total">Grid = models x sizes</InfoTip>);

    // -- Then --
    const button = screen.getByRole('button', { name: 'About Total' });
    const tip = screen.getByRole('tooltip', { hidden: true });
    expect(button).toHaveAttribute('aria-describedby', tip.id);
    expect(tip).toHaveTextContent('Grid = models x sizes');
    expect(tip).not.toBeVisible();
    expect(button).not.toHaveAttribute('aria-expanded');
  });

  it('Given a closed tip, when tapped twice, then it opens and closes', () => {
    /**
     * Scenario: Tap (click) toggles the tip, which is the only gesture on a 390 px touch screen.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    render(<InfoTip label="About Total">Explained</InfoTip>);
    const button = screen.getByRole('button', { name: 'About Total' });

    // -- When --
    fireEvent.click(button);
    // -- Then --
    expect(screen.getByRole('tooltip')).toBeVisible();
    expect(button).toHaveAttribute('aria-describedby', screen.getByRole('tooltip').id);

    // -- When --
    fireEvent.click(button);
    // -- Then --
    expect(screen.getByRole('tooltip', { hidden: true })).not.toBeVisible();
  });

  it('Given an open tip, when Escape is pressed, then it closes and focus stays on the button', () => {
    /**
     * Scenario: Keyboard dismissal.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    render(<InfoTip label="About Total">Explained</InfoTip>);
    const button = screen.getByRole('button', { name: 'About Total' });
    button.focus();
    fireEvent.click(button);
    expect(screen.getByRole('tooltip')).toBeVisible();

    // -- When --
    fireEvent.keyDown(button, { key: 'Escape' });

    // -- Then --
    expect(screen.getByRole('tooltip', { hidden: true })).not.toBeVisible();
    expect(button).toHaveFocus();
  });

  it('Given an open tip, when another key is pressed, then it stays open', () => {
    /**
     * Scenario: Only Escape dismisses from the keyboard.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    render(<InfoTip label="About Total">Explained</InfoTip>);
    const button = screen.getByRole('button', { name: 'About Total' });
    fireEvent.click(button);

    // -- When --
    fireEvent.keyDown(button, { key: 'a' });

    // -- Then --
    expect(screen.getByRole('tooltip')).toBeVisible();
  });

  it('Given an open tip, when the user taps elsewhere, then it closes', () => {
    /**
     * Scenario: Outside tap dismisses so tips do not pile up on a phone.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    render(
      <div>
        <InfoTip label="About Total">Explained</InfoTip>
        <p>elsewhere</p>
      </div>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'About Total' }));

    // -- When --
    fireEvent.pointerDown(screen.getByText('elsewhere'));

    // -- Then --
    expect(screen.getByRole('tooltip', { hidden: true })).not.toBeVisible();
  });

  it('Given an open tip, when the user taps inside the tip, then it stays open', () => {
    /**
     * Scenario: Interacting with the tip itself does not dismiss it.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    render(<InfoTip label="About Total">Explained</InfoTip>);
    fireEvent.click(screen.getByRole('button', { name: 'About Total' }));

    // -- When --
    fireEvent.pointerDown(screen.getByText('Explained'));

    // -- Then --
    expect(screen.getByRole('tooltip')).toBeVisible();
  });

  it('Given a tip, when inspected, then there is one tip node, no live region and a short accessible name', () => {
    /**
     * Scenario: No duplicate screen-reader announcement.
     * Slice: 67C — InfoTip
     * The tip is read once through aria-describedby: the button name must not repeat it and the
     * tip must not be a live region. The actual double read by assistive technology is not
     * observable in jsdom; this is checked structurally only (one node, no live region, short name).
     */
    // -- Given / When --
    const { container } = render(<InfoTip label="About Total">Grid = 12</InfoTip>);

    // -- Then --
    expect(screen.getAllByText('Grid = 12')).toHaveLength(1);
    expect(container.querySelector('[aria-live]')).toBeNull();
    expect(screen.getByRole('button', { name: 'About Total' })).not.toHaveTextContent('Grid = 12');
  });

  it('Given the trigger, when inspected, then it is a real button with a 44 px target and hidden icon', () => {
    /**
     * Scenario: Touch target and keyboard reachability.
     * Slice: 67C — InfoTip
     * A native button gives Tab focus and Enter/Space activation; jsdom has no layout so the
     * 44 px minimum is asserted through its Tailwind classes (min-h-11 / min-w-11 = 2.75rem).
     */
    // -- Given / When --
    render(<InfoTip label="About Total">Explained</InfoTip>);

    // -- Then --
    const button = screen.getByRole('button', { name: 'About Total' });
    expect(button).toHaveAttribute('type', 'button');
    expect(button).toHaveClass('min-h-11', 'min-w-11');
    expect(button.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('Given identical props, when rendered twice, then the output markup is identical', () => {
    /**
     * Scenario: Determinism — InfoTip only renders the text it is given; the aria id is the
     * caller-supplied id (or React useId by default), never a clock or randomness.
     * Slice: 67C — InfoTip
     */
    // -- Given --
    const tree = (
      <InfoTip label="About Total" id="tip-total">
        Grid = 12
      </InfoTip>
    );
    // -- When --
    const first = render(tree);
    const a = normalizeIds(first.container.innerHTML);
    first.unmount();
    const b = normalizeIds(render(tree).container.innerHTML);
    // -- Then --
    expect(b).toBe(a);
  });

  it('Given the trigger, when reached by keyboard, then it is tabbable, focusable and toggles on Enter and Space', () => {
    /**
     * Scenario: Keyboard path Tab, Enter/Space, Escape.
     * Slice: 67C — InfoTip
     * user-event is not a dependency, and jsdom does not turn Enter/Space keydown into a click, so
     * native activation cannot be simulated. We assert what makes it work in browsers: a native
     * <button type="button"> that is in the tab order (tabIndex >= 0), focusable, and whose click
     * (what Enter/Space dispatch) toggles the tip; Escape then closes it.
     */
    // -- Given --
    render(<InfoTip label="About Total">Explained</InfoTip>);
    const button = screen.getByRole('button', { name: 'About Total' });
    // -- When --
    button.focus();
    // -- Then --
    expect(button.tagName).toBe('BUTTON');
    expect(button).toHaveAttribute('type', 'button');
    expect(button.tabIndex).toBeGreaterThanOrEqual(0);
    expect(button).not.toBeDisabled();
    expect(document.activeElement).toBe(button);

    // -- When (Enter / Space activate a native button by dispatching click) --
    fireEvent.click(button);
    // -- Then --
    expect(screen.getByRole('tooltip')).toBeVisible();

    // -- When --
    fireEvent.keyDown(button, { key: 'Escape' });
    // -- Then --
    expect(screen.getByRole('tooltip', { hidden: true })).not.toBeVisible();
    expect(document.activeElement).toBe(button);
  });

  it('Given two tips, when rendered, then their ids differ', () => {
    /**
     * Scenario: Unique ids keep aria-describedby unambiguous.
     * Slice: 67C — InfoTip
     */
    // -- Given / When --
    render(
      <>
        <InfoTip label="A">one</InfoTip>
        <InfoTip label="B">two</InfoTip>
      </>,
    );

    // -- Then --
    const [a, b] = screen.getAllByRole('tooltip', { hidden: true });
    expect(a.id).not.toBe(b.id);
  });

  describe('viewport clamping and dismissal on resize', () => {
    afterEach(() => {
      vi.restoreAllMocks();
    });

    // Tip rect as a browser reports it: the applied translateX moves it by `applied`.
    const mockTipRect = (left: number, right: number) => {
      vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
        const isTip = this.getAttribute('role') === 'tooltip';
        const m = /\+ (-?\d+)px/.exec(this.style.transform);
        const applied = isTip && m ? Number(m[1]) : 0;
        const l = isTip ? left + applied : 0;
        const r = isTip ? right + applied : 0;
        return { left: l, right: r, top: 0, bottom: 0, width: r - l, height: 0, x: l, y: 0, toJSON: () => ({}) };
      });
    };

    it('Given a tip overflowing the left edge, when opened, then the clamp nudges it into view', () => {
      /**
       * Scenario: Integration of the effect with clampShift (unit-tested in infoTipUtils.test.ts).
       * Slice: 67C — InfoTip
       * jsdom innerWidth is 1024; the tip would sit at -60..196, so it is shifted right by 68.
       */
      // -- Given --
      mockTipRect(-60, 196);
      render(<InfoTip label="About Total">Explained</InfoTip>);
      // -- When --
      fireEvent.click(screen.getByRole('button', { name: 'About Total' }));
      // -- Then --
      expect(screen.getByRole('tooltip').style.transform).toBe('translateX(calc(-50% + 68px))');
    });

    it('Given a nudged tip, when closed and reopened, then it is measured from its unshifted position', () => {
      /**
       * Scenario: The shift resets on close, so each open measures an untransformed tip and the
       * nudge is the same every time (the mocked rect moves with the applied shift, like a browser).
       * Slice: 67C — InfoTip
       */
      // -- Given --
      mockTipRect(-60, 196);
      render(<InfoTip label="About Total">Explained</InfoTip>);
      const button = screen.getByRole('button', { name: 'About Total' });
      // -- When --
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);
      // -- Then --
      expect(screen.getByRole('tooltip').style.transform).toBe('translateX(calc(-50% + 68px))');
    });

    it('Given a tip that fits, when opened, then it is not shifted', () => {
      /**
       * Scenario: No nudge when there is room.
       * Slice: 67C — InfoTip
       */
      // -- Given --
      mockTipRect(100, 356);
      render(<InfoTip label="About Total">Explained</InfoTip>);
      // -- When --
      fireEvent.click(screen.getByRole('button', { name: 'About Total' }));
      // -- Then --
      expect(screen.getByRole('tooltip').style.transform).toBe('translateX(calc(-50% + 0px))');
    });

    it.each(['resize', 'orientationchange'])('Given an open tip, when %s fires, then it closes', (name) => {
      /**
       * Scenario: A stale position is never shown after the viewport changes; the tip closes.
       * Slice: 67C — InfoTip
       */
      // -- Given --
      render(<InfoTip label="About Total">Explained</InfoTip>);
      fireEvent.click(screen.getByRole('button', { name: 'About Total' }));
      expect(screen.getByRole('tooltip')).toBeVisible();
      // -- When --
      fireEvent(window, new Event(name));
      // -- Then --
      expect(screen.getByRole('tooltip', { hidden: true })).not.toBeVisible();
    });
  });
});
