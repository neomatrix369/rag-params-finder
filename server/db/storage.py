"""Deprecated import path — use ``server.db.ports.storage``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.storage.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.ports import storage as _impl

sys.modules[__name__] = _impl
