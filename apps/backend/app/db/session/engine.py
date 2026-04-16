import sqlite3

from sqlalchemy import create_engine

from app.core.config.settings import settings


settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def initialize_database() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    sql = settings.baseline_sql_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(settings.database_path)
    try:
        connection.executescript(sql)
        connection.commit()
    finally:
        connection.close()
