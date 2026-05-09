import sqlite3

from sqlalchemy import create_engine

from app.core.classification import classify_file
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
        _ensure_classification_columns(connection)
        _backfill_file_classification(connection)
        connection.commit()
    finally:
        connection.close()


def _ensure_classification_columns(connection: sqlite3.Connection) -> None:
    file_columns = _table_columns(connection, "files")
    if "file_kind" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN file_kind TEXT NOT NULL DEFAULT 'other'")
    if "auto_placement" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN auto_placement TEXT NOT NULL DEFAULT 'none'")

    user_meta_columns = _table_columns(connection, "file_user_meta")
    if "manual_placement" not in user_meta_columns:
        connection.execute("ALTER TABLE file_user_meta ADD COLUMN manual_placement TEXT NULL")
    if "placement_updated_at" not in user_meta_columns:
        connection.execute("ALTER TABLE file_user_meta ADD COLUMN placement_updated_at DATETIME NULL")

    connection.execute("CREATE INDEX IF NOT EXISTS idx_files_file_kind ON files(file_kind)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_files_auto_placement ON files(auto_placement)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_file_user_meta_manual_placement ON file_user_meta(manual_placement)"
    )


def _backfill_file_classification(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, extension, path
        FROM files
        WHERE file_kind IS NULL
           OR auto_placement IS NULL
           OR file_kind = 'other'
           OR auto_placement = 'none'
        """
    ).fetchall()
    for file_id, extension, path in rows:
        classification = classify_file(extension, path)
        connection.execute(
            "UPDATE files SET file_kind = ?, auto_placement = ? WHERE id = ?",
            (classification.file_kind, classification.auto_placement, file_id),
        )


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}
