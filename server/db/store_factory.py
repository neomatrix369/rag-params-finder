"""Deprecated import path — use ``server.db.ports.store_factory``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.store_factory.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.ports import store_factory as _impl

sys.modules[__name__] = _impl
