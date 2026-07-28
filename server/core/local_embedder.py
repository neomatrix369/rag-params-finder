"""Deprecated import path — use ``server.core.embedding.local_embedder``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.local_embedder.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.embedding import local_embedder as _impl

sys.modules[__name__] = _impl
