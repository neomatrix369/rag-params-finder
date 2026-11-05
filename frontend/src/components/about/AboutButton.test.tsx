/**
 * Tests for AboutButton: opens the About dialog, Esc closes, focus returns to the button.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 56 Part C1 - About box open/close/focus GWT scenarios
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AboutButton from './AboutButton';

describe('AboutButton', () => {
  it('Given the header button, when clicked, then the About dialog opens', () => {
    /**
     * Scenario: Clicking About opens the dialog.
     * Slice: 56 Part C1 - About box
     */
    // -- Given --
    render(<AboutButton />);
    expect(screen.queryByRole('dialog')).toBeNull();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'About' }));

    // -- Then --
    expect(screen.getByRole('dialog', { name: 'About RAG Params Finder' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'About' })).toHaveAttribute('aria-haspopup', 'dialog');
  });

  it('Given the dialog is open, when Esc is pressed, then it closes and focus returns to About', () => {
    /**
     * Scenario: Esc closes the dialog; the About button regains focus even when the
     *   click did not focus it (Safari/Firefox on macOS).
     * Slice: 56 Part C1 - About box
     */
    // -- Given --
    render(<AboutButton />);
    const button = screen.getByRole('button', { name: 'About' });
    fireEvent.click(button);
    expect(button).not.toHaveFocus();

    // -- When --
    fireEvent.keyDown(document, { key: 'Escape' });

    // -- Then --
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(button).toHaveFocus();
  });

  it('Given the dialog is open, when focus is trapped and Tab wraps, then it never leaves the dialog', () => {
    /**
     * Scenario: Tab from the last control inside the About dialog wraps to the first.
     * Slice: 56 Part C1 - About box (focus trapped while open)
     */
    // -- Given --
    render(<AboutButton />);
    fireEvent.click(screen.getByRole('button', { name: 'About' }));
    const dialog = screen.getByRole('dialog');
    const focusables = dialog.querySelectorAll<HTMLElement>('a[href], button');
    const last = focusables[focusables.length - 1];
    last.focus();

    // -- When --
    fireEvent.keyDown(last, { key: 'Tab' });

    // -- Then --
    expect(focusables[0]).toHaveFocus();
    expect(dialog.contains(document.activeElement)).toBe(true);
  });

  it('Given the dark header tone, when rendered, then the button uses the dark styling', () => {
    /**
     * Scenario: The button adapts to the darkFrame chrome tone.
     * Slice: 56 Part C1 - About box (header placement)
     */
    // -- Given / When --
    render(<AboutButton isDark />);

    // -- Then --
    expect(screen.getByRole('button', { name: 'About' }).className).toContain('text-white');
  });
});
