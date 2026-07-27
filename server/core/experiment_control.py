"""Deprecated import path — use ``server.core.pipeline.experiment_control``."""

from __future__ import annotations

import sys

from server.core.pipeline import experiment_control as _impl

sys.modules[__name__] = _impl
