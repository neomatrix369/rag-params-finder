/**
 * Tests for the Glossary control and its pure data module.
 *
 * Author: RAG Params Finder contributors
 * Created: 2026-11-05
 * Scope: Slice 67 glossary - open/close/focus and vocabulary GWT scenarios
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import GlossaryButton from './GlossaryButton';
import { GLOSSARY } from './glossary';

describe('GlossaryButton', () => {
  it('Given the control, when clicked, then a Glossary dialog lists every term in order', () => {
    /**
     * Scenario: Clicking Glossary opens a dialog with the fixed term list.
     * Slice: 67 - one glossary in the UI
     */
    // -- Given --
    render(<GlossaryButton />);
    expect(screen.queryByRole('dialog')).toBeNull();

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Glossary' }));

    // -- Then --
    const dialog = screen.getByRole('dialog', { name: 'Glossary' });
    const terms = within(dialog).getAllByRole('term').map((node) => node.textContent);
    expect(terms).toEqual(GLOSSARY.map((entry) => entry.term));
    expect(terms).toEqual(
      expect.arrayContaining(['Run', 'Planned runs', 'Configuration', 'Trial', 'Query result']),
    );
  });

  it('Given the dialog is open, when Escape is pressed, then it closes and focus returns to the button', () => {
    /**
     * Scenario: Keyboard users can dismiss the dialog and keep their place.
     * Slice: 67 - one glossary in the UI
     */
    // -- Given --
    render(<GlossaryButton isDark />);
    const button = screen.getByRole('button', { name: 'Glossary' });
    fireEvent.click(button);

    // -- When --
    fireEvent.keyDown(document, { key: 'Escape' });

    // -- Then --
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(button).toHaveFocus();
  });
});

describe('GLOSSARY data', () => {
  it('Given every entry, when scanned, then the retired word "combination" never appears', () => {
    /**
     * Scenario: The vocabulary decision retired "combination".
     * Slice: 67 - vocabulary decision
     */
    // -- Given --
    const text = GLOSSARY.map((entry) => `${entry.term} ${entry.definition}`).join(' ');

    // -- When / Then --
    expect(text).not.toMatch(/combination/i);
  });

  it('Given the entries, when listed, then terms are unique and non-empty', () => {
    /**
     * Scenario: Stable, duplicate-free data.
     * Slice: 67 - one glossary in the UI
     */
    // -- Given --
    const terms = GLOSSARY.map((entry) => entry.term);

    // -- Then --
    expect(new Set(terms).size).toBe(terms.length);
    expect(GLOSSARY.every((entry) => entry.term && entry.definition)).toBe(true);
  });
});
