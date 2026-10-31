from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Maison Connectée"
    app_version: str = "0.1.0"
    environment: str = "development"
    allow_public_registration: bool = False
    jwt_secret: str = ""
    data_dir: Path = BASE_DIR
    accounts_db_path: Path | None = None
    domotique_db_path: Path | None = None
    backup_dir: Path | None = None
    backup_interval_hours: int = Field(default=24, ge=1, le=168)
    backup_retention_count: int = Field(default=14, ge=1, le=365)
    usb_backup_mount_path: Path | None = None

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def accounts_db_file(self) -> Path:
        return self.accounts_db_path or self.data_dir / "comptes.db"

    @property
    def domotique_db_file(self) -> Path:
        return self.domotique_db_path or self.data_dir / "systeme_historique.db"

    @property
    def backup_dir_path(self) -> Path:
        return self.backup_dir or self.data_dir / "backups"

    def preparer_stockage(self) -> None:
        """Crée les répertoires de stockage sans toucher aux bases existantes."""
        for chemin in (self.accounts_db_file, self.domotique_db_file):
            chemin.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
