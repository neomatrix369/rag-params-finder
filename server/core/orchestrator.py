"""Deprecated import path — use ``server.core.pipeline.orchestrator``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.orchestrator.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.pipeline import orchestrator as _impl

sys.modules[__name__] = _impl
