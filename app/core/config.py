from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Downloadable Files API"
    app_version: str = "1.0.0"
    download_directory: Path = PROJECT_ROOT / "downloadable_files"


@lru_cache
def get_settings() -> Settings:
    return Settings()
