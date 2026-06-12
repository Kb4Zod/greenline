"""Configuration. Everything overridable via GREENLINE_* env vars / .env.

The app name is config, not a constant — "Greenline" is a working codename
(decision 0008) and the eventual rename must not require a code hunt.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GREENLINE_", env_file=".env", extra="ignore"
    )

    app_name: str = "Greenline"
    data_dir: Path | None = None
    db_filename: str = "greenline.sqlite3"
    api_host: str = "127.0.0.1"
    api_port: int = 8537

    # Income: trailing average over the last N paychecks (decision 0004).
    income_trailing_n: int = 4
    # Days of grace before an expected paycheck counts as overdue.
    income_grace_days: int = 3
    # Headroom below this fraction of required cash reads as "tight".
    tight_buffer: float = 0.15

    def resolved_data_dir(self) -> Path:
        """Live data lives outside the repo tree (decision 0010)."""
        if self.data_dir is not None:
            return self.data_dir
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            return base / self.app_name
        return Path.home() / f".{self.app_name.lower()}"

    def db_path(self) -> Path:
        return self.resolved_data_dir() / self.db_filename
