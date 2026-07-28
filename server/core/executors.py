"""Deprecated import path — use ``server.core.pipeline.executors``."""

from __future__ import annotations

import sys

from server.core.pipeline import executors as _impl

sys.modules[__name__] = _impl
