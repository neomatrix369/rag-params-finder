from pydantic_settings import BaseSettings, SettingsConfigDict

from server.utils.logger import get_logger

logger = get_logger(__name__)


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

    # Voyage AI rate limits — free-tier defaults (no payment method).
    # Override via VOYAGE_RPM_LIMIT / VOYAGE_TPM_LIMIT env vars or .env.
    voyage_rpm_limit: int = 3
    voyage_tpm_limit: int = 10_000


settings = Settings()

logger.info(f"Settings loaded: server_url={settings.server_url}")
logger.debug(
    f"Settings detail: mongodb_uri={'***' if settings.mongodb_uri else '(not set)'}, "
    f"voyage_api_key={'***' if settings.voyage_api_key else '(not set)'}, "
    f"recover_on_boot={settings.recover_on_boot}"
)
