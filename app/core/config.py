import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _optional_path(value: str | None, default: Path) -> Path:
    return Path(value).expanduser() if value else default


def _split_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        )
    return tuple(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Downloadable Files API"
    app_version: str = "2.4.0"
    environment: str = "development"
    download_directory: Path = PROJECT_ROOT / "media" / "downloadable_files"
    database_path: Path = PROJECT_ROOT / "data" / "app.db"
    seed_database_path: Path | None = PROJECT_ROOT / "data" / "app_seed.db"
    templates_directory: Path = PROJECT_ROOT / "app" / "templates"
    static_directory: Path = PROJECT_ROOT / "app" / "static"
    admin_username: str = ""
    admin_password: str = ""
    session_secret: str = "development-only-session-secret"
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    max_upload_bytes: int = 25 * 1024 * 1024
    discord_webhook_url: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_app_password: str = ""
    notification_email_to: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment.casefold() == "production"

    @property
    def admin_enabled(self) -> bool:
        return bool(self.admin_username and self.admin_password)

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            download_directory=_optional_path(
                os.getenv("DOWNLOAD_DIRECTORY"),
                PROJECT_ROOT / "media" / "downloadable_files",
            ),
            database_path=_optional_path(
                os.getenv("DATABASE_PATH"),
                PROJECT_ROOT / "data" / "app.db",
            ),
            seed_database_path=_optional_path(
                os.getenv("SEED_DATABASE_PATH"),
                PROJECT_ROOT / "data" / "app_seed.db",
            ),
            admin_username=os.getenv("ADMIN_USERNAME", ""),
            admin_password=os.getenv("ADMIN_PASSWORD", ""),
            session_secret=os.getenv(
                "SESSION_SECRET",
                "development-only-session-secret",
            ),
            cors_allowed_origins=_split_origins(
                os.getenv("CORS_ALLOWED_ORIGINS")
            ),
            max_upload_bytes=int(
                os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))
            ),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_app_password=os.getenv("SMTP_APP_PASSWORD", ""),
            notification_email_to=os.getenv("NOTIFICATION_EMAIL_TO", ""),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
