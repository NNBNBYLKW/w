from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKBENCH_", case_sensitive=False)

    app_name: str = "Windows Local Asset Workbench Backend"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_origin: str = "http://127.0.0.1:5173"
    frontend_origin_alt: str = "http://localhost:5173"

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "workbench.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def baseline_sql_path(self) -> Path:
        return self.base_dir / "app" / "db" / "migrations" / "0001_initial_core.sql"

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_origin, self.frontend_origin_alt]


settings = Settings()
