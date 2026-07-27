"""Deprecated import path — use ``server.core.pipeline.startup_reconciliation``."""

from __future__ import annotations

import sys

from server.core.pipeline import startup_reconciliation as _impl

sys.modules[__name__] = _impl
