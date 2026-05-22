import { useState, type MouseEvent } from 'react';
import {
  cancelExperiment,
  pauseExperiment,
  resumeExperiment,
} from '../services/apiClient';
import type { ExperimentStatus } from '../types';
import {
  isPausedExperimentStatus,
  isRunningExperimentStatus,
} from '../utils/experimentStatus';
import { devWarn } from '../utils/devLog';

type ControlTone = 'light' | 'dark';
type ControlSize = 'sm' | 'md';

interface ExperimentControlButtonsProps {
  experimentId: string;
  status: ExperimentStatus;
  tone?: ControlTone;
  size?: ControlSize;
  onStatusChange?: () => void | Promise<void>;
  onError?: (message: string) => void;
}

function stopRowNavigation(event: MouseEvent<HTMLDivElement>) {
  event.stopPropagation();
}

export default function ExperimentControlButtons({
  experimentId,
  status,
  tone = 'light',
  size = 'md',
  onStatusChange,
  onError,
}: ExperimentControlButtonsProps) {
  const [pausing, setPausing] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const isRunning = isRunningExperimentStatus(status);
  const isPaused = isPausedExperimentStatus(status);

  if (!isRunning && !isPaused) {
    return null;
  }

  const pad = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-4 py-2 text-sm';
  const pauseClass =
    tone === 'dark'
      ? 'border border-violet-400/50 bg-violet-500/20 text-violet-100 hover:bg-violet-500/30'
      : 'border border-violet-300 bg-violet-50 text-violet-800 hover:bg-violet-100';
  const resumeClass =
    tone === 'dark'
      ? 'bg-emerald-600 text-white hover:bg-emerald-500'
      : 'bg-emerald-600 text-white hover:bg-emerald-700';
  const cancelClass =
    tone === 'dark'
      ? 'bg-red-600/90 text-white hover:bg-red-500'
      : 'bg-red-600 text-white hover:bg-red-700';

  async function runAction(
    action: () => Promise<unknown>,
    setBusy: (busy: boolean) => void,
    actionLabel: string,
  ) {
    setBusy(true);
    try {
      await action();
      await onStatusChange?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Action failed';
      devWarn(`Control action failed (${actionLabel}, ${experimentId.slice(0, 8)}…):`, message);
      onError?.(message);
    } finally {
      setBusy(false);
    }
  }

  async function handlePause() {
    if (
      !confirm(
        'Pause this experiment? The current run will finish its phase, then execution stops.',
      )
    ) {
      return;
    }
    await runAction(() => pauseExperiment(experimentId), setPausing, 'pause');
  }

  async function handleResume() {
    await runAction(() => resumeExperiment(experimentId), setResuming, 'resume');
  }

  async function handleCancel() {
    if (
      !confirm(
        'Cancel this experiment? Runs in progress will stop after the current phase.',
      )
    ) {
      return;
    }
    await runAction(() => cancelExperiment(experimentId), setCancelling, 'cancel');
  }

  const disabled = pausing || resuming || cancelling;

  return (
    <div
      role="group"
      aria-label="Experiment controls"
      className="flex flex-wrap items-center justify-end gap-2"
      onClick={stopRowNavigation}
    >
      {isRunning && (
        <>
          <button
            type="button"
            onClick={handlePause}
            disabled={disabled}
            className={`rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${pauseClass}`}
          >
            {pausing ? 'Pausing…' : '⏸ Pause'}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={disabled}
            className={`rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${cancelClass}`}
          >
            {cancelling ? 'Cancelling…' : '⏹ Cancel'}
          </button>
        </>
      )}
      {isPaused && (
        <button
          type="button"
          onClick={handleResume}
          disabled={disabled}
          className={`rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${resumeClass}`}
        >
          {resuming ? 'Resuming…' : '▶ Resume'}
        </button>
      )}
    </div>
  );
}
