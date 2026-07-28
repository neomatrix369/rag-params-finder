"""Deprecated import path — use ``server.db.mongo.mongodb_uri``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.mongodb_uri.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.mongo import mongodb_uri as _impl

sys.modules[__name__] = _impl
