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

logger.info(f"Settings loaded: server_url={settings.server_url}")
logger.debug(
    f"Settings detail: mongodb_uri={'***' if settings.mongodb_uri else '(not set)'}, "
    f"voyage_api_key={'***' if settings.voyage_api_key else '(not set)'}, "
    f"recover_on_boot={settings.recover_on_boot}, "
    f"cors_origins={settings.cors_origins}, "
    f"cors_allow_localhost_origin_regex={settings.cors_allow_localhost_origin_regex}"
)
