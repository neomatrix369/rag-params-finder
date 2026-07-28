/**
 * Author: Slice 45
 * Created: 2026-07-28
 * Scope: shared Pagination chrome
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import Pagination from './Pagination';

describe('Pagination', () => {
  it('Given a multi-page list, when Next and per-page change, then callbacks fire', () => {
    // -- Given --
    const onPageChange = vi.fn();
    const onItemsPerPageChange = vi.fn();
    render(
      <Pagination
        currentPage={1}
        totalItems={40}
        itemsPerPage={10}
        onPageChange={onPageChange}
        onItemsPerPageChange={onItemsPerPageChange}
        selectId="test-per-page"
      />,
    );
    // -- When --
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    fireEvent.change(screen.getByLabelText('Per page:'), { target: { value: '25' } });
    // -- Then --
    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(onPageChange).toHaveBeenCalledWith(2);
    expect(onItemsPerPageChange).toHaveBeenCalledWith(25);
  });

  it('Given the first page, when Previous is clicked, then it stays disabled', () => {
    // -- Given --
    render(
      <Pagination
        currentPage={1}
        totalItems={5}
        itemsPerPage={10}
        onPageChange={vi.fn()}
        onItemsPerPageChange={vi.fn()}
        selectId="test-per-page-2"
      />,
    );
    // -- When / Then --
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
  });
});
