from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from server.db.ports.registry import known_vector_stores, vector_store_can_host_run_state
from server.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:5374",
    "http://127.0.0.1:5374",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

# Matches http(s) localhost / loopback on any port — covers Vite port drift (5174+)
# without widening CORS to arbitrary hosts (see Starlette cors regex docs).
LOCALHOST_CORS_ORIGIN_REGEX: str = r"^https?://" r"(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"

# Runtime token for MongoDB Atlas / Atlas Local. Legacy env value ``mongo`` is
# normalized to ``mongodb`` so STORAGE_BACKEND matches database_provider labels.
_STORAGE_BACKEND_ALIASES: dict[str, str] = {"mongo": "mongodb"}
_KNOWN_STORAGE_BACKENDS: frozenset[str] = frozenset({"mongodb", "postgres", "sqlite"})
# Run-state-only backends: cannot host vector data; VECTOR_STORE_BACKEND must be
# set explicitly when one of these is active (Slice 55, ADR-008).
_RUN_STATE_ONLY_BACKENDS: frozenset[str] = frozenset({"sqlite"})
# Vector stores additionally allow "elasticsearch" (Slice 50) — it cannot host
# run state, so it is rejected for STORAGE_BACKEND but accepted for
# VECTOR_STORE_BACKEND. Pairing rule (ii) (49B) allows that split; the
# adapter is not registered yet, so selecting it fails when the store is resolved.
_KNOWN_VECTOR_STORE_BACKENDS: frozenset[str] = _KNOWN_STORAGE_BACKENDS | {"elasticsearch"}

# Vector-only providers named ahead of their adapter landing (Slice 50/53):
# the registry cannot yet answer ``vector_store_can_host_run_state`` for
# these (no adapter registered, so ``resolve_adapter`` raises), so the
# pairing-rule validator below falls back to this declared-vector-only list.
# Once an adapter registers, the registry lookup takes over and this entry
# becomes redundant (harmless — same answer either way).
_PENDING_VECTOR_ONLY_BACKENDS: frozenset[str] = frozenset({"elasticsearch"})


def normalize_storage_backend(value: str) -> str:
    """Map legacy ``mongo`` to canonical ``mongodb``; otherwise lower/strip."""
    backend = value.strip().lower()
    return _STORAGE_BACKEND_ALIASES.get(backend, backend)


def _can_host_run_state(backend: str) -> bool:
    """True when ``backend`` (a vector store) can also hold run state.

    Prefers the registry's declared ``VectorCapabilities.can_host_run_state``
    (DECISIONS #241 pairing rule (ii)) — never a hardcoded provider list.
    Falls back to ``_PENDING_VECTOR_ONLY_BACKENDS`` only when the provider has
    no registered adapter yet (Elasticsearch/Redis before Slice 50/53 land).
    """
    try:
        return vector_store_can_host_run_state(backend)
    except ValueError:
        return backend not in _PENDING_VECTOR_ONLY_BACKENDS


def _is_postgres_uri_placeholder(uri: str) -> bool:
    """True when URI still holds .env.example angle-bracket placeholders."""
    return "<project-ref>" in uri or "<password>" in uri or "<region>" in uri


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    voyage_api_key: str = ""
    mongodb_uri: str = ""
    server_url: str = "http://localhost:8001"
    recover_on_boot: bool = False

    # CORS — comma-separated origins allowed by the server middleware.
    # Override via CORS_ORIGINS env var, e.g. "http://localhost:5374,http://localhost:3000".
    # localhost vs 127.0.0.1 are different browser origins; defaults include both for dev.
    cors_origins: list[str] = list(_DEFAULT_CORS_ORIGINS)

    # When True, middleware also matches localhost / 127.0.0.1 / [::1] on any port (regex).
    # Set CORS_ALLOW_LOCALHOST_ORIGIN_REGEX=false when only cors_origins should apply.
    cors_allow_localhost_origin_regex: bool = True

    # Voyage AI rate limits — free-tier defaults (no payment method).
    # Override via VOYAGE_RPM_LIMIT / VOYAGE_TPM_LIMIT env vars or .env.
    voyage_rpm_limit: int = 3
    voyage_tpm_limit: int = 10_000

    # Manual cluster storage quota override (MB). When > 0, skips Atlas API auto-detect.
    # Set MONGODB_STORAGE_LIMIT_MB=0 (default) to auto-detect via Atlas Admin API or hide quota.
    mongodb_storage_limit_mb: float = 0.0

    # Optional Atlas Admin API credentials for auto-detecting cluster storage quota.
    # Create keys at cloud.mongodb.com → Organization Access Manager → API Keys.
    # ATLAS_GROUP_ID is the 24-char project ID from your Atlas project URL.
    atlas_public_key: str = ""
    atlas_private_key: str = ""
    atlas_group_id: str = ""
    # Leave blank to derive from MONGODB_URI host (e.g. thesandboxcluster.5uaqybx.mongodb.net).
    atlas_cluster_name: str = ""

    # SIE (Superlinked Inference Engine) — opt-in; disabled by default.
    # SIE_ENABLED: master on/off (same for remote gateway and local Docker).
    # SIE_ENDPOINT: where to connect. SIE_API_KEY: auth when gateway requires it.
    # See docs/user-guide/sie-setup.md.
    sie_enabled: bool = False
    sie_endpoint: str = "http://localhost:8720"
    sie_api_key: str = ""

    # Aim experiment tracking — path to the .aim repo directory (created on first log).
    # Docker: bind-mount ./.aim → /app/.aim and set AIM_REPO=/app/.aim.
    # UI: ./scripts/docker/aim-ui.sh (Docker — host `aim up` may fail on macOS OpenSSL).
    aim_repo: str = ".aim"

    # Tiebreaker metric for ranking configurations when max_score is tied.
    # Options:
    #   - "query_avg" (weighted, per-query average — fairer)
    #   - "chunk_avg" (unweighted, per-chunk — legacy)
    # Default: "query_avg" (recommended for fairness).
    # Override via TIEBREAKER_METRIC env var.
    tiebreaker_metric: str = "query_avg"

    # MongoDB ping timeout for /healthz (ms). Keep below Docker healthcheck timeout (10s).
    health_check_mongodb_timeout_ms: int = 5000

    # Active storage backend. "sqlite" (default, ADR-008) stores run-state in a
    # local SQLite file; VECTOR_STORE_BACKEND must be set explicitly with sqlite.
    # "mongodb" uses MongoDB Atlas / Atlas Local. "postgres" uses Supabase / local pgvector.
    # Legacy alias: STORAGE_BACKEND=mongo → normalized to mongodb.
    storage_backend: str = "sqlite"

    # Path for the SQLite run-state database (STORAGE_BACKEND=sqlite).
    # Created on first boot; parent directory created automatically.
    sqlite_db_path: str = "./data/run_state.db"

    # Active vector store. Defaults to storage_backend when unset (empty string
    # sentinel). Pairing rule (ii) (Slice 49B, DECISIONS #241): a store that
    # can hold run state must equal storage_backend; a vector-only store
    # (e.g. "elasticsearch") may pair with either run-state store.
    vector_store_backend: str = ""

    # Elasticsearch — required URL when VECTOR_STORE_BACKEND=elasticsearch.
    # API key is optional (cloud). Index prefix defaults to ``rpf`` → ``rpf-chunks``.
    # Never log elasticsearch_api_key.
    elasticsearch_url: str = ""
    elasticsearch_api_key: str = ""
    elasticsearch_index_prefix: str = "rpf"

    # Postgres connection string — required when STORAGE_BACKEND=postgres.
    # Hosted Supabase: Settings → Database → Connection string (Session mode pooler).
    # Local Docker: postgresql://rag:rag@localhost:5433/rag_params_finder
    database_url: str = ""
    # Optional alias for DATABASE_URL (hosted Supabase). Prefer DATABASE_URL when both set.
    supabase_uri: str = ""
    postgres_pool_max_size: int = 10
    # Seconds to wait for a free pooled connection before failing the request.
    postgres_pool_timeout_s: float = 30.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None or value == "":
            return list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, list):
            parsed = [str(x).strip() for x in value if str(x).strip()]
            return parsed if parsed else list(_DEFAULT_CORS_ORIGINS)
        if isinstance(value, str):
            parts = [x.strip() for x in value.split(",") if x.strip()]
            return parts if parts else list(_DEFAULT_CORS_ORIGINS)
        return list(_DEFAULT_CORS_ORIGINS)

    @model_validator(mode="after")
    def storage_backend_must_be_known(self) -> Settings:
        """Normalize aliases and reject unknown/vector-store-only STORAGE_BACKEND values."""
        backend = normalize_storage_backend(self.storage_backend)
        if backend == "elasticsearch":
            raise ValueError(
                "STORAGE_BACKEND=elasticsearch is not supported: elasticsearch is "
                "vector-store-only and cannot host run state. Set STORAGE_BACKEND to "
                "'mongodb', 'postgres', or 'sqlite'."
            )
        if backend not in _KNOWN_STORAGE_BACKENDS:
            raise ValueError(
                f"Unknown STORAGE_BACKEND={self.storage_backend!r}. "
                "Set STORAGE_BACKEND to 'mongodb', 'postgres', or 'sqlite' "
                "(legacy alias: 'mongo')."
            )
        self.storage_backend = backend
        return self

    @model_validator(mode="after")
    def vector_store_backend_pairing_rule(self) -> Settings:
        """Default VECTOR_STORE_BACKEND to storage_backend; enforce pairing rules.

        Slice 49B (DECISIONS #241) replaces the 49A equality lock: **if the
        vector store can host run state, VECTOR_STORE_BACKEND must equal
        STORAGE_BACKEND** (both stores are the same engine — nothing else is
        wired). A vector-only store (``can_host_run_state=False`` —
        Elasticsearch, Redis, or the test-only ``memory`` provider) may pair
        with either run-state store, because it never has to hold run state
        itself.

        Slice 55 addition: when ``STORAGE_BACKEND`` is a run-state-only backend
        (e.g. ``sqlite``), ``VECTOR_STORE_BACKEND`` MUST be set explicitly —
        SQLite cannot default as a vector store.
        """
        run_state_backend = normalize_storage_backend(self.storage_backend)
        raw = self.vector_store_backend.strip()

        # Run-state-only backends cannot serve as the vector store default.
        # NOTE: the hard enforcement (raise) lives in ensure_storage_ready() so
        # that Settings() construction succeeds in test environments that don't
        # set VECTOR_STORE_BACKEND. Here we just leave it empty — the caller
        # gets the error at server startup / store access, not at import time.
        if run_state_backend in _RUN_STATE_ONLY_BACKENDS and not raw:
            self.vector_store_backend = ""
            return self

        backend = normalize_storage_backend(raw) if raw else run_state_backend
        if backend not in _KNOWN_VECTOR_STORE_BACKENDS and backend not in known_vector_stores():
            known = ", ".join(sorted(known_vector_stores()))
            raise ValueError(f"Unknown VECTOR_STORE_BACKEND={raw!r}. Known vector stores: {known}.")
        if _can_host_run_state(backend) and backend != run_state_backend:
            raise ValueError(
                f"STORAGE_BACKEND={run_state_backend!r} with "
                f"VECTOR_STORE_BACKEND={backend!r} is not supported: {backend} can "
                "hold run state, so it must hold both. Set "
                f"VECTOR_STORE_BACKEND={run_state_backend!r}, or "
                f"STORAGE_BACKEND={backend!r}."
            )
        self.vector_store_backend = backend
        return self

    @model_validator(mode="after")
    def apply_supabase_uri_alias(self) -> Settings:
        """Copy SUPABASE_URI into database_url when DATABASE_URL is unset."""
        if not self.database_url.strip() and self.supabase_uri.strip():
            self.database_url = self.supabase_uri.strip()
        return self

    def ensure_storage_ready(self) -> None:
        """Raise when either store is missing its required connection URI.

        Called from server lifespan and store_factory so misconfiguration fails
        with one clear message before any driver I/O. Empty URIs remain allowed
        at Settings construction so unit tests can import the module without a DB.

        Checks the run-state store (STORAGE_BACKEND) and, when different
        (split store, Slice 49B DECISIONS #250), the vector store
        (VECTOR_STORE_BACKEND) too — a missing/placeholder URI on *either*
        side fails boot. An unreachable-but-configured store does not fail
        boot here (that stays a `/healthz` 503 + preflight 422 concern).
        """
        run_state = normalize_storage_backend(self.storage_backend)
        # Enforce the run-state-only pairing rule here (not at construction time)
        # so unit tests can construct Settings() without VECTOR_STORE_BACKEND.
        if run_state in _RUN_STATE_ONLY_BACKENDS and not self.vector_store_backend.strip():
            raise ValueError(
                f"STORAGE_BACKEND={run_state!r} is a run-state-only backend and "
                "cannot host vector data. Set VECTOR_STORE_BACKEND explicitly to the "
                "engine that holds your vectors (e.g. VECTOR_STORE_BACKEND=mongodb or "
                "VECTOR_STORE_BACKEND=elasticsearch)."
            )
        self._ensure_backend_uri_present(run_state)
        vector_backend = normalize_storage_backend(
            self.vector_store_backend or self.storage_backend
        )
        if vector_backend != normalize_storage_backend(self.storage_backend):
            self._ensure_backend_uri_present(vector_backend)

    def _ensure_backend_uri_present(self, backend: str) -> None:
        """Raise naming the missing/placeholder setting for one engine's URI."""
        if backend == "mongodb" and not self.mongodb_uri.strip():
            raise ValueError(
                "STORAGE_BACKEND=mongodb requires MONGODB_URI. "
                "Set it in .env or the environment (Atlas cloud or Atlas Local)."
            )
        if backend == "postgres":
            uri = self.database_url.strip()
            if not uri:
                raise ValueError(
                    "STORAGE_BACKEND=postgres requires DATABASE_URL or SUPABASE_URI. "
                    "Set it in .env (local pgvector or hosted Supabase)."
                )
            if _is_postgres_uri_placeholder(uri):
                raise ValueError(
                    "STORAGE_BACKEND=postgres has a placeholder DATABASE_URL / SUPABASE_URI "
                    "(contains <project-ref>). Replace it with a real Session-mode URI, "
                    "or use ./start-services.sh --postgres-local."
                )
        if backend == "sqlite":
            # SQLite requires no external URI — just a writable path.
            db_path = self.sqlite_db_path.strip()
            if not db_path:
                raise ValueError(
                    "STORAGE_BACKEND=sqlite requires SQLITE_DB_PATH (or the default "
                    "'./data/run_state.db'). Set it in .env or the environment."
                )
            from pathlib import Path

            parent = Path(db_path).parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ValueError(
                    f"STORAGE_BACKEND=sqlite: cannot create parent directory for "
                    f"SQLITE_DB_PATH={db_path!r}: {exc}"
                ) from exc
        if backend == "elasticsearch" and not self.elasticsearch_url.strip():
            raise ValueError(
                "VECTOR_STORE_BACKEND=elasticsearch requires ELASTICSEARCH_URL. "
                "Set it in .env or the environment."
            )

    def default_database_provider(self) -> str:
        """Label for runs/stats when YAML omits ``database_provider``.

        Runtime selection remains ``storage_backend``. This only fills the
        engine metadata label (``mongodb`` | ``postgres`` | ``sqlite``) — never
        a product shorthand like ``supabase`` (Slice 37).
        """
        backend = normalize_storage_backend(self.storage_backend)
        if backend == "postgres":
            return "postgres"
        if backend == "sqlite":
            return "sqlite"
        return "mongodb"


settings = Settings()

logger.info(
    "settings loaded — server_url=%s storage_backend=%s vector_store_backend=%s",
    settings.server_url,
    settings.storage_backend,
    settings.vector_store_backend,
)
logger.debug(
    "settings detail — mongodb_uri=%s database_url=%s voyage_api_key=%s recover_on_boot=%s "
    "cors_origins=%s cors_allow_localhost_origin_regex=%s",
    "***" if settings.mongodb_uri else "(not set)",
    "***" if settings.database_url else "(not set)",
    "***" if settings.voyage_api_key else "(not set)",
    settings.recover_on_boot,
    settings.cors_origins,
    settings.cors_allow_localhost_origin_regex,
)
