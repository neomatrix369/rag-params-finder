"""Deprecated import path — use ``server.db.mongo.atlas``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.atlas.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.mongo import atlas as _impl

sys.modules[__name__] = _impl
