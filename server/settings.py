from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from server.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

# Matches http(s) localhost / loopback on any port — covers Vite port drift (5174+)
# without widening CORS to arbitrary hosts (see Starlette cors regex docs).
LOCALHOST_CORS_ORIGIN_REGEX: str = r"^https?://" r"(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


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
    # Override via CORS_ORIGINS env var, e.g. "http://localhost:5173,http://localhost:3000".
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

    # Tiebreaker metric for ranking configurations when max_score is tied.
    # Options:
    #   - "query_avg" (weighted, per-query average — fairer)
    #   - "chunk_avg" (unweighted, per-chunk — legacy)
    # Default: "query_avg" (recommended for fairness).
    # Override via TIEBREAKER_METRIC env var.
    tiebreaker_metric: str = "query_avg"

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


settings = Settings()

logger.info("settings loaded — server_url=%s", settings.server_url)
logger.debug(
    "settings detail — mongodb_uri=%s voyage_api_key=%s recover_on_boot=%s "
    "cors_origins=%s cors_allow_localhost_origin_regex=%s",
    "***" if settings.mongodb_uri else "(not set)",
    "***" if settings.voyage_api_key else "(not set)",
    settings.recover_on_boot,
    settings.cors_origins,
    settings.cors_allow_localhost_origin_regex,
)
