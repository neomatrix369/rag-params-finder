"""Deprecated import path — use ``server.core.retrieval.retriever_mongo``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.retriever_mongo.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.retrieval import retriever_mongo as _impl

sys.modules[__name__] = _impl
