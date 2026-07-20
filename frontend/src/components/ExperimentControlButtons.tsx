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
import { devInfo, devWarn } from '../utils/devLog';

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

function PauseIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M5.75 3.5A1.25 1.25 0 0 0 4.5 4.75v10.5a1.25 1.25 0 1 0 2.5 0V4.75A1.25 1.25 0 0 0 5.75 3.5Zm8.5 0A1.25 1.25 0 0 0 13 4.75v10.5a1.25 1.25 0 1 0 2.5 0V4.75a1.25 1.25 0 0 0-1.25-1.25Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <rect x="4" y="4" width="12" height="12" rx="2" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M5.5 4.8a1.4 1.4 0 0 1 2.1-1.2l7.1 4.7a2 2 0 0 1 0 3.4l-7.1 4.7a1.4 1.4 0 0 1-2.1-1.2V4.8Z" />
    </svg>
  );
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

  const pad = size === 'sm' ? 'min-h-11 px-3 text-xs' : 'min-h-11 px-4 text-sm';
  const pauseClass =
    tone === 'dark'
      ? 'border border-amber-200/40 bg-amber-200/10 text-amber-50 hover:bg-amber-200/20'
      : 'border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100';
  const resumeClass =
    tone === 'dark'
      ? 'bg-accent text-white hover:bg-emerald-500'
      : 'bg-accent text-white hover:bg-accent-strong';
  const cancelClass =
    tone === 'dark'
      ? 'border border-red-300/40 bg-red-500/20 text-red-50 hover:bg-red-500/30'
      : 'border border-red-300 bg-red-50 text-red-800 hover:bg-red-100';

  async function runAction(
    action: () => Promise<unknown>,
    setBusy: (busy: boolean) => void,
    actionLabel: string,
  ) {
    setBusy(true);
    try {
      await action();
      devInfo('ExperimentControlButtons', `${actionLabel} OK — ${experimentId.slice(0, 8)}…`);
      await onStatusChange?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Action failed';
      devWarn('ExperimentControlButtons', `${actionLabel} failed — ${experimentId.slice(0, 8)}… — ${message}`);
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
            className={`inline-flex items-center gap-2 rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${pauseClass}`}
          >
            <PauseIcon />
            {pausing ? 'Pausing…' : 'Pause'}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={disabled}
            className={`inline-flex items-center gap-2 rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${cancelClass}`}
          >
            <StopIcon />
            {cancelling ? 'Cancelling…' : 'Cancel'}
          </button>
        </>
      )}
      {isPaused && (
        <button
          type="button"
          onClick={handleResume}
          disabled={disabled}
          className={`inline-flex items-center gap-2 rounded-lg font-semibold shadow-sm transition-colors disabled:opacity-50 ${pad} ${resumeClass}`}
        >
          <PlayIcon />
          {resuming ? 'Resuming…' : 'Resume'}
        </button>
      )}
    </div>
  );
}
