"""Deprecated import path — use ``server.db.ports.retriever_backend``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.db.retriever_backend.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.db.ports import retriever_backend as _impl

sys.modules[__name__] = _impl
