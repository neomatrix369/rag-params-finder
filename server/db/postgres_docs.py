"""Deprecated import path — use ``server.db.postgres.postgres_docs``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.postgres_docs.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.postgres import postgres_docs as _impl

sys.modules[__name__] = _impl
