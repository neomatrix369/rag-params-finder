"""Cooperative cancel/pause signals for in-flight experiment sweeps."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


class ExperimentCancelledError(Exception):
    pass


class ExperimentPausedError(Exception):
    pass


@dataclass
class _SweepControl:
    cancel: threading.Event = field(default_factory=threading.Event)
    pause: threading.Event = field(default_factory=threading.Event)


_sweep_controls: dict[str, _SweepControl] = {}


def register_sweep_control(experiment_id: str) -> None:
    """Register control handles before the sweep thread starts (idempotent)."""
    if experiment_id not in _sweep_controls:
        _sweep_controls[experiment_id] = _SweepControl()


def unregister_sweep_control(experiment_id: str) -> None:
    _sweep_controls.pop(experiment_id, None)


def request_cancel(experiment_id: str) -> bool:
    """Signal a running experiment to stop. Returns True if a control was registered."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return False
    control.cancel.set()
    return True


def request_pause(experiment_id: str) -> bool:
    """Signal a running experiment to pause. Returns True if a control was registered."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return False
    control.pause.set()
    return True


def is_sweep_in_flight(experiment_id: str) -> bool:
    return experiment_id in _sweep_controls


def check_control(experiment_id: str) -> None:
    """Raise if this experiment was cancelled or paused."""
    control = _sweep_controls.get(experiment_id)
    if control is None:
        return
    if control.cancel.is_set():
        raise ExperimentCancelledError(f"Experiment {experiment_id} was cancelled")
    if control.pause.is_set():
        raise ExperimentPausedError(f"Experiment {experiment_id} was paused")
