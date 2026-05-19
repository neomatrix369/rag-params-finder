/**
 * ConfirmDeleteModal
 *
 * Reusable modal for confirming experiment deletion.
 * Shows warning message, experiment details, and confirm/cancel buttons.
 */

interface ConfirmDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  experimentName: string;
  experimentId: string;
  isDeleting: boolean;
  isBulk?: boolean;
  bulkCount?: number;
}

export default function ConfirmDeleteModal({
  isOpen,
  onClose,
  onConfirm,
  experimentName,
  experimentId,
  isDeleting,
  isBulk = false,
  bulkCount = 1,
}: ConfirmDeleteModalProps) {
  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget && !isDeleting) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
            <svg
              className="h-6 w-6 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-slate-900">
              {isBulk ? `Delete ${bulkCount} Experiments?` : 'Delete Experiment?'}
            </h3>
            <p className="mt-1 text-sm text-slate-600">
              This action cannot be undone. All associated data will be permanently deleted.
            </p>
          </div>
        </div>

        {/* Experiment Details */}
        {!isBulk && (
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Experiment to Delete
            </div>
            <div className="mb-1 text-sm font-medium text-slate-900">{experimentName}</div>
            <div className="font-mono text-xs text-slate-500">{experimentId.slice(0, 8)}...</div>
          </div>
        )}

        {isBulk && (
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="text-sm text-slate-700">
              <span className="font-semibold">{bulkCount}</span> experiment{bulkCount > 1 ? 's' : ''}{' '}
              will be deleted.
            </div>
          </div>
        )}

        {/* Warning List */}
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-red-700">
            What Will Be Deleted
          </div>
          <ul className="space-y-1 text-sm text-red-700">
            <li>• Experiment metadata</li>
            <li>• Run statuses</li>
            <li>• Chunks (embeddings)</li>
            <li>• Query results</li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : isBulk ? `Delete ${bulkCount}` : 'Delete Experiment'}
          </button>
        </div>
      </div>
    </div>
  );
}
