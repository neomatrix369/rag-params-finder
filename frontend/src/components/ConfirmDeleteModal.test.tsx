/**
 * Author: RAG Params Finder contributors
 * Created: 2026-07-27
 * Scope: Slice 44 — delete confirmation modal open/closed and confirm/cancel actions.
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ConfirmDeleteModal from './ConfirmDeleteModal';

describe('ConfirmDeleteModal', () => {
  it('Given isOpen false, when rendered, then dialog content is absent', () => {
    /**
     * Scenario: Closed modal mounts nothing visible.
     * Slice: 44 — frontend coverage gate (ConfirmDeleteModal).
     * Given isOpen=false,
     * When the modal renders,
     * Then the Delete Experiment heading is not in the document.
     */
    // -- Given / When --
    render(
      <ConfirmDeleteModal
        isOpen={false}
        onClose={() => undefined}
        onConfirm={() => undefined}
        experimentName="demo"
        experimentId="abcdef12-3456"
        isDeleting={false}
      />,
    );

    // -- Then --
    expect(screen.queryByText('Delete Experiment?')).toBeNull();
  });

  it('Given open single-delete modal, when Cancel then Delete clicked, then callbacks fire', () => {
    /**
     * Scenario: Confirm and cancel invoke the provided handlers.
     * Slice: 44 — frontend coverage gate (ConfirmDeleteModal).
     * Given an open modal for one experiment,
     * When Cancel then Delete Experiment are clicked,
     * Then onClose and onConfirm are each called once.
     */
    // -- Given --
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    render(
      <ConfirmDeleteModal
        isOpen
        onClose={onClose}
        onConfirm={onConfirm}
        experimentName="demo sweep"
        experimentId="abcdef12-3456-7890"
        isDeleting={false}
      />,
    );

    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    fireEvent.click(screen.getByRole('button', { name: 'Delete Experiment' }));

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(screen.getByText('demo sweep')).toBeInTheDocument();
    expect(screen.getByText(/abcdef12/)).toBeInTheDocument();
  });

  it('Given bulk delete open, when rendered, then bulk copy is shown', () => {
    /**
     * Scenario: Bulk mode shows count instead of a single experiment card.
     * Slice: 44 — frontend coverage gate (ConfirmDeleteModal).
     * Given isBulk with bulkCount=3,
     * When the modal renders,
     * Then the heading names three experiments.
     */
    // -- Given / When --
    render(
      <ConfirmDeleteModal
        isOpen
        onClose={() => undefined}
        onConfirm={() => undefined}
        experimentName="unused"
        experimentId="unused"
        isDeleting={false}
        isBulk
        bulkCount={3}
      />,
    );

    // -- Then --
    expect(screen.getByText('Delete 3 Experiments?')).toBeInTheDocument();
    expect(screen.getByText(/will be deleted/)).toBeInTheDocument();
  });

  it('Given open modal, when backdrop is clicked, then onClose fires', () => {
    /**
     * Scenario: Backdrop click dismisses when not deleting.
     * Slice: 44 Phase B — ConfirmDeleteModal
     */
    // -- Given --
    const onClose = vi.fn();
    const { container } = render(
      <ConfirmDeleteModal
        isOpen
        onClose={onClose}
        onConfirm={() => undefined}
        experimentName="demo"
        experimentId="abcdef12-3456"
        isDeleting={false}
      />,
    );
    const backdrop = container.firstElementChild as HTMLElement;

    // -- When --
    fireEvent.click(backdrop);

    // -- Then --
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('Given deleting in progress, when backdrop is clicked, then onClose does not fire', () => {
    /**
     * Scenario: Backdrop dismiss is blocked while delete is in flight.
     * Slice: 44 Phase B — ConfirmDeleteModal
     */
    // -- Given --
    const onClose = vi.fn();
    const { container } = render(
      <ConfirmDeleteModal
        isOpen
        onClose={onClose}
        onConfirm={() => undefined}
        experimentName="demo"
        experimentId="abcdef12-3456"
        isDeleting
      />,
    );
    const backdrop = container.firstElementChild as HTMLElement;

    // -- When --
    fireEvent.click(backdrop);

    // -- Then --
    expect(onClose).not.toHaveBeenCalled();
  });
});
