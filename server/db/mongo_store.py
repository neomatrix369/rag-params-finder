"""Deprecated import path — use ``server.db.mongo.mongo_store``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.mongo_store.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.mongo import mongo_store as _impl

sys.modules[__name__] = _impl
