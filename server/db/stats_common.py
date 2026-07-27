"""Deprecated import path — use ``server.db.ports.stats_common``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.stats_common.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.ports import stats_common as _impl

sys.modules[__name__] = _impl
