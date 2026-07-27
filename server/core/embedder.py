"""Deprecated import path — use ``server.core.embedding.embedder``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.embedder.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.embedding import embedder as _impl

sys.modules[__name__] = _impl
