"""Deprecated import path — use ``server.core.embedding.rate_limiter``.

Shim kept for one release (Slice 45). Uses module aliasing so existing
``patch("server.core.rate_limiter.*")`` targets keep working.
"""

from __future__ import annotations

import sys

from server.core.embedding import rate_limiter as _impl

sys.modules[__name__] = _impl
