"""Deprecated import path — use ``server.core.rerank.reranker``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.reranker.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.rerank import reranker as _impl

sys.modules[__name__] = _impl
