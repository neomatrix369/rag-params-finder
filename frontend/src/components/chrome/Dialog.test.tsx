/**
 * Tests for the Dialog primitive: portal, ARIA, Esc, backdrop, focus trap, focus return.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - generic modal dialog (also reused by later Walkthru parts)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { useRef, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import Dialog from './Dialog';

function Harness({ withRef = false }: { withRef?: boolean }) {
  const [open, setOpen] = useState(false);
  const openerRef = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button type="button" ref={openerRef} onClick={() => setOpen(true)}>
        Open it
      </button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Hello dialog"
        returnFocusRef={withRef ? openerRef : undefined}
      >
        <a href="https://example.com">first link</a>
        <button type="button">last button</button>
      </Dialog>
    </>
  );
}

describe('Dialog', () => {
  it('Given open=false, when rendered, then nothing is mounted', () => {
    /**
     * Scenario: A closed dialog has no DOM.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given / When --
    render(
      <Dialog open={false} onClose={vi.fn()} title="Hidden">
        body
      </Dialog>,
    );

    // -- Then --
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Given open=true, when rendered, then a labelled modal dialog is portalled to body', () => {
    /**
     * Scenario: role=dialog, aria-modal, accessible name from the title, rendered in document.body.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given / When --
    const { container } = render(
      <Dialog open onClose={vi.fn()} title="Hello dialog">
        <p>body text</p>
      </Dialog>,
    );

    // -- Then --
    const dialog = screen.getByRole('dialog', { name: 'Hello dialog' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(container.contains(dialog)).toBe(false);
    expect(document.body.contains(dialog)).toBe(true);
    expect(screen.getByText('body text')).toBeInTheDocument();
  });

  it('Given an open dialog, when Escape is pressed, then onClose is called', () => {
    /**
     * Scenario: Esc closes the dialog from anywhere in the document.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="T">
        x
      </Dialog>,
    );

    // -- When --
    fireEvent.keyDown(document, { key: 'Enter' });
    fireEvent.keyDown(document, { key: 'Escape' });

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Given a closed dialog, when Escape is pressed, then no handler fires', () => {
    /**
     * Scenario: The Esc listener exists only while open.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    const onClose = vi.fn();
    render(
      <Dialog open={false} onClose={onClose} title="T">
        x
      </Dialog>,
    );

    // -- When --
    fireEvent.keyDown(document, { key: 'Escape' });

    // -- Then --
    expect(onClose).not.toHaveBeenCalled();
  });

  it('Given an open dialog, when the backdrop is clicked, then onClose fires; panel clicks do not', () => {
    /**
     * Scenario: Backdrop click closes; clicks inside the panel do not.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="T">
        <p>inside</p>
      </Dialog>,
    );

    // -- When --
    fireEvent.click(screen.getByText('inside'));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId('dialog-backdrop'));

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Given the Close button, when clicked, then onClose fires', () => {
    /**
     * Scenario: A visible Close control exists for pointer and screen-reader users.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    const onClose = vi.fn();
    render(
      <Dialog open onClose={onClose} title="T">
        x
      </Dialog>,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Given an open dialog, when it mounts, then focus moves to the first focusable element', () => {
    /**
     * Scenario: Focus enters the dialog (the Close button is first in tab order).
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given / When --
    render(
      <Dialog open onClose={vi.fn()} title="T">
        <button type="button">inner</button>
      </Dialog>,
    );

    // -- Then --
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus();
  });

  it('Given focus on the last element, when Tab is pressed, then focus wraps to the first', () => {
    /**
     * Scenario: Focus is trapped - forward Tab from the last control wraps around.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Open it' }));
    const last = screen.getByRole('button', { name: 'last button' });
    last.focus();

    // -- When --
    fireEvent.keyDown(last, { key: 'Tab' });

    // -- Then --
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus();
  });

  it('Given focus on the first element, when Shift+Tab is pressed, then focus wraps to the last', () => {
    /**
     * Scenario: Focus is trapped - backward Tab from the first control wraps around.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Open it' }));
    const first = screen.getByRole('button', { name: 'Close' });
    first.focus();

    // -- When --
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });

    // -- Then --
    expect(screen.getByRole('button', { name: 'last button' })).toHaveFocus();
  });

  it('Given focus on the dialog panel itself, when Shift+Tab is pressed, then focus wraps to the last', () => {
    /**
     * Scenario: If focus rests on the panel container, Shift+Tab still stays inside.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Open it' }));
    const panel = screen.getByRole('dialog');
    panel.focus();

    // -- When --
    fireEvent.keyDown(panel, { key: 'Tab', shiftKey: true });

    // -- Then --
    expect(screen.getByRole('button', { name: 'last button' })).toHaveFocus();
  });

  it('Given focus in the middle, when Tab is pressed, then the browser default is left alone', () => {
    /**
     * Scenario: The trap only intervenes at the edges.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Open it' }));
    const middle = screen.getByRole('link', { name: 'first link' });
    middle.focus();

    // -- When --
    const notPrevented = fireEvent.keyDown(middle, { key: 'Tab' });
    const shiftNotPrevented = fireEvent.keyDown(middle, { key: 'Tab', shiftKey: true });
    const otherKey = fireEvent.keyDown(middle, { key: 'a' });

    // -- Then --
    expect(notPrevented).toBe(true);
    expect(shiftNotPrevented).toBe(true);
    expect(otherKey).toBe(true);
    expect(middle).toHaveFocus();
  });

  it('Given the opener had focus, when the dialog closes, then focus returns to the opener', () => {
    /**
     * Scenario: Without an explicit ref, the previously focused element regains focus.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness />);
    const opener = screen.getByRole('button', { name: 'Open it' });
    opener.focus();
    fireEvent.click(opener);
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    // -- When --
    fireEvent.keyDown(document, { key: 'Escape' });

    // -- Then --
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(opener).toHaveFocus();
  });

  it('Given a returnFocusRef, when the dialog closes, then that element gets focus even if it never had it', () => {
    /**
     * Scenario: Safari/Firefox do not focus a button on click; the ref makes return reliable.
     * Slice: 56 Part C1 - Dialog primitive
     */
    // -- Given --
    render(<Harness withRef />);
    const opener = screen.getByRole('button', { name: 'Open it' });
    fireEvent.click(opener);
    expect(opener).not.toHaveFocus();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    // -- Then --
    expect(opener).toHaveFocus();
  });

  it('Given an open dialog, when it renders, then no animation or transition classes are applied', () => {
    /**
     * Scenario: No motion at all, which satisfies prefers-reduced-motion by construction.
     * Slice: 56 Part C1 - Dialog primitive (reduced motion)
     */
    // -- Given / When --
    render(
      <Dialog open onClose={vi.fn()} title="T">
        x
      </Dialog>,
    );

    // -- Then --
    const html = screen.getByTestId('dialog-backdrop').outerHTML;
    expect(html).not.toMatch(/animate-|transition|duration-/);
  });
});
