"""Deprecated import path — use ``server.core.rerank.local_reranker``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.local_reranker.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.rerank import local_reranker as _impl

sys.modules[__name__] = _impl
