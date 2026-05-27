import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from app.core.classification import classify_file
from app.core.config.settings import settings


settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_wal(dbapi_connection, _connection_record):
    dbapi_connection.execute("PRAGMA journal_mode=WAL")


def initialize_database() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    sql = settings.baseline_sql_path.read_text(encoding="utf-8")
    connection = sqlite3.connect(settings.database_path)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(sql)
        current = _get_schema_version(connection)
        if current < 1:
            _ensure_classification_columns(connection)
            _backfill_file_classification(connection)
        if current < 2:
            _ensure_tool_runs_table(connection)
            _ensure_library_object_tables(connection)
            _ensure_library_organize_tables(connection)
            _ensure_library_roots_table(connection)
        if current < 3:
            _ensure_library_v2_tables(connection)
            _ensure_library_v2_source(connection)
        if current < 4:
            _ensure_source_discovered_count(connection)
            _ensure_recovery_findings_table(connection)
        if current < 5:
            _ensure_performance_indexes(connection)
        _ensure_schema_version(connection)
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


def _ensure_tool_runs_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_key TEXT NOT NULL,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL,
            output_json TEXT NULL,
            log_text TEXT NULL,
            error_message TEXT NULL,
            started_at DATETIME NULL,
            finished_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tool_runs_tool_key ON tool_runs(tool_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tool_runs_status ON tool_runs(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tool_runs_created_at ON tool_runs(created_at)")


def _ensure_library_object_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS library_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_type TEXT NOT NULL,
            type_prefix TEXT NOT NULL,
            root_path TEXT NOT NULL UNIQUE,
            root_name TEXT NOT NULL,
            filesystem_title TEXT NULL,
            title TEXT NULL,
            original_title TEXT NULL,
            romanized_title TEXT NULL,
            localized_title_json TEXT NULL,
            sort_title TEXT NULL,
            year INTEGER NULL,
            tags_json TEXT NULL,
            cover_path TEXT NULL,
            primary_file_path TEXT NULL,
            metadata_source TEXT NOT NULL,
            needs_review INTEGER NOT NULL DEFAULT 0,
            review_reason TEXT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            last_scanned_at DATETIME NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS library_object_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL,
            file_id INTEGER NULL,
            relative_path TEXT NOT NULL,
            absolute_path TEXT NOT NULL,
            member_role TEXT NOT NULL,
            sort_index INTEGER NULL,
            hidden_from_global INTEGER NOT NULL DEFAULT 1,
            extension TEXT NULL,
            size_bytes INTEGER NULL,
            modified_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(object_id) REFERENCES library_objects(id) ON DELETE CASCADE,
            FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE SET NULL,
            UNIQUE(object_id, relative_path)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_metadata_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL UNIQUE,
            yaml_path TEXT NULL,
            schema_version INTEGER NULL,
            parsed_json TEXT NULL,
            parse_status TEXT NOT NULL,
            parse_error TEXT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(object_id) REFERENCES library_objects(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_library_objects_object_type ON library_objects(object_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_library_objects_needs_review ON library_objects(needs_review)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_library_objects_last_scanned_at ON library_objects(last_scanned_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_library_object_members_object_id ON library_object_members(object_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_library_object_members_member_role ON library_object_members(member_role)"
    )

    # Phase 8D-A1: add member_status column for soft-deactivate
    lom_columns = _table_columns(connection, "library_object_members")
    if "member_status" not in lom_columns:
        connection.execute(
            "ALTER TABLE library_object_members ADD COLUMN member_status TEXT NOT NULL DEFAULT 'active'"
        )


def _ensure_library_organize_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_type TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_file_id INTEGER NULL,
            source_object_id INTEGER NULL,
            source_path TEXT NOT NULL,
            display_name TEXT NOT NULL,
            detected_type TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL,
            ignored_at DATETIME NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(source_file_id) REFERENCES files(id) ON DELETE SET NULL,
            FOREIGN KEY(source_object_id) REFERENCES library_objects(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            plan_kind TEXT NOT NULL,
            summary TEXT NULL,
            summary_json TEXT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            confirmed_at DATETIME NULL,
            executed_at DATETIME NULL,
            execution_started_at DATETIME NULL,
            execution_finished_at DATETIME NULL,
            execution_summary_json TEXT NULL,
            template_key TEXT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            action_order INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            source_path TEXT NULL,
            target_path TEXT NULL,
            payload_json TEXT NULL,
            status TEXT NOT NULL,
            conflict_status TEXT NOT NULL,
            conflict_message TEXT NULL,
            reason TEXT NULL,
            before_path TEXT NULL,
            after_path TEXT NULL,
            executed_at DATETIME NULL,
            finished_at DATETIME NULL,
            error_message TEXT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(plan_id) REFERENCES organize_plans(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_plan_candidates (
            plan_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            PRIMARY KEY (plan_id, candidate_id),
            FOREIGN KEY(plan_id) REFERENCES organize_plans(id) ON DELETE CASCADE,
            FOREIGN KEY(candidate_id) REFERENCES organize_candidates(id) ON DELETE CASCADE
        )
        """
    )
    plan_columns = _table_columns(connection, "organize_plans")
    if "execution_started_at" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN execution_started_at DATETIME NULL")
    if "execution_finished_at" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN execution_finished_at DATETIME NULL")
    if "execution_summary_json" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN execution_summary_json TEXT NULL")

    action_columns = _table_columns(connection, "organize_actions")
    if "before_path" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN before_path TEXT NULL")
    if "after_path" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN after_path TEXT NULL")
    if "executed_at" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN executed_at DATETIME NULL")
    if "finished_at" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN finished_at DATETIME NULL")
    if "error_message" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN error_message TEXT NULL")
    if "reconcile_status" not in action_columns:
        connection.execute("ALTER TABLE organize_actions ADD COLUMN reconcile_status TEXT NOT NULL DEFAULT 'not_checked'")

    if "reconcile_status" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN reconcile_status TEXT NOT NULL DEFAULT 'not_required'")
    if "reconciled_at" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN reconciled_at DATETIME NULL")
    if "reconcile_summary_json" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN reconcile_summary_json TEXT NULL")
    if "parent_plan_id" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN parent_plan_id INTEGER REFERENCES organize_plans(id)")
    if "plan_origin" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN plan_origin TEXT NOT NULL DEFAULT 'generated_from_candidates'")
    if "template_key" not in plan_columns:
        connection.execute("ALTER TABLE organize_plans ADD COLUMN template_key TEXT NULL")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            action_id INTEGER NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            path_before TEXT NULL,
            path_after TEXT NULL,
            error_message TEXT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(plan_id) REFERENCES organize_plans(id) ON DELETE CASCADE,
            FOREIGN KEY(action_id) REFERENCES organize_actions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS organize_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NULL,
            plan_id INTEGER NULL,
            action_id INTEGER NULL,
            suggestion_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            confidence REAL NULL,
            reason TEXT NULL,
            provider TEXT NOT NULL DEFAULT 'rule_based',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME NOT NULL,
            accepted_at DATETIME NULL,
            rejected_at DATETIME NULL,
            FOREIGN KEY(candidate_id) REFERENCES organize_candidates(id) ON DELETE SET NULL,
            FOREIGN KEY(plan_id) REFERENCES organize_plans(id) ON DELETE SET NULL,
            FOREIGN KEY(action_id) REFERENCES organize_actions(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_candidates_status ON organize_candidates(status)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_organize_candidates_source_file_id ON organize_candidates(source_file_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_organize_candidates_source_object_id ON organize_candidates(source_object_id)"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_plans_status ON organize_plans(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_actions_plan_id ON organize_actions(plan_id)")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_organize_actions_conflict_status ON organize_actions(conflict_status)"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_action_logs_plan_id ON organize_action_logs(plan_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_action_logs_action_id ON organize_action_logs(action_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_action_logs_created_at ON organize_action_logs(created_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_suggestions_candidate_id ON organize_suggestions(candidate_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_suggestions_status ON organize_suggestions(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_organize_suggestions_type ON organize_suggestions(suggestion_type)")


def _ensure_library_roots_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS library_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_path TEXT NOT NULL UNIQUE,
            display_name TEXT NULL,
            root_kind TEXT NOT NULL DEFAULT 'managed',
            is_enabled INTEGER NOT NULL DEFAULT 1,
            is_default INTEGER NOT NULL DEFAULT 0,
            scan_policy TEXT NOT NULL DEFAULT 'manual',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_library_roots_is_enabled ON library_roots(is_enabled)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_library_roots_is_default ON library_roots(is_default)")

    plan_columns = _table_columns(connection, "organize_plans")
    if "target_library_root_id" not in plan_columns:
        connection.execute(
            "ALTER TABLE organize_plans ADD COLUMN target_library_root_id INTEGER REFERENCES library_roots(id)"
        )


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
        ("table", table_name),
    ).fetchone()
    if row is None:
        return set()
    return {str(col[1]) for col in connection.execute(
        "SELECT * FROM pragma_table_info(?)", (table_name,)
    ).fetchall()}


def _ensure_library_v2_tables(connection: sqlite3.Connection) -> None:
    v2_sql = settings.v2_baseline_sql_path.read_text(encoding="utf-8")
    connection.executescript(v2_sql)

    file_columns = _table_columns(connection, "files")
    if "storage_state" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN storage_state TEXT NOT NULL DEFAULT 'external'")
    if "managed_root_id" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN managed_root_id INTEGER REFERENCES library_roots(id)")
    if "original_path" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN original_path TEXT NULL")
    if "inbox_item_id" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN inbox_item_id INTEGER REFERENCES inbox_items(id) ON DELETE SET NULL")
    if "managed_at" not in file_columns:
        connection.execute("ALTER TABLE files ADD COLUMN managed_at DATETIME NULL")

    connection.execute("CREATE INDEX IF NOT EXISTS idx_files_storage_state ON files(storage_state)")

    # Phase 7C: import_object_candidates additions
    oc_columns = _table_columns(connection, "import_object_candidates")
    if "target_library_root_id" not in oc_columns:
        connection.execute(
            "ALTER TABLE import_object_candidates ADD COLUMN target_library_root_id INTEGER REFERENCES library_roots(id)"
        )
    if "organize_candidate_id" not in oc_columns:
        connection.execute(
            "ALTER TABLE import_object_candidates ADD COLUMN organize_candidate_id INTEGER REFERENCES organize_candidates(id) ON DELETE SET NULL"
        )
    if "organize_plan_id" not in oc_columns:
        connection.execute(
            "ALTER TABLE import_object_candidates ADD COLUMN organize_plan_id INTEGER REFERENCES organize_plans(id)"
        )

    # Phase 7C: organize_actions traceability
    action_columns = _table_columns(connection, "organize_actions")
    if "inbox_item_id" not in action_columns:
        connection.execute(
            "ALTER TABLE organize_actions ADD COLUMN inbox_item_id INTEGER REFERENCES inbox_items(id) ON DELETE SET NULL"
        )
    if "import_object_candidate_id" not in action_columns:
        connection.execute(
            "ALTER TABLE organize_actions ADD COLUMN import_object_candidate_id INTEGER REFERENCES import_object_candidates(id) ON DELETE SET NULL"
        )


def _ensure_performance_indexes(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_del_disc "
        "ON files(is_deleted, discovered_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_del_name "
        "ON files(is_deleted, name)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_del_mod "
        "ON files(is_deleted, modified_at_fs)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_del_src "
        "ON files(is_deleted, source_id)"
    )


CURRENT_SCHEMA_VERSION = 5


def _get_schema_version(connection: sqlite3.Connection) -> int:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER NOT NULL,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] if row and row[0] is not None else 0


def _ensure_schema_version(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    current = row[0] if row and row[0] is not None else 0
    if current < CURRENT_SCHEMA_VERSION:
        connection.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )


def _ensure_recovery_findings_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS recovery_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT NOT NULL,
            scanned_at TEXT NOT NULL DEFAULT (datetime('now')),
            finding_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            entity_type TEXT,
            entity_id INTEGER,
            path TEXT,
            message TEXT NOT NULL,
            suggested_action TEXT
        )
        """
    )


def _ensure_source_discovered_count(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "sources")
    if "discovered_count" not in columns:
        connection.execute("ALTER TABLE sources ADD COLUMN discovered_count INTEGER")


def _ensure_library_v2_source(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT id FROM sources WHERE path = ?", ("__workbench_managed_import__",)
    ).fetchone()
    if row is None:
        connection.execute(
            """
            INSERT INTO sources (path, display_name, is_enabled, scan_mode, last_scan_status, created_at, updated_at)
            VALUES (?, ?, 1, 'manual', 'not_applicable', datetime('now'), datetime('now'))
            """,
            ("__workbench_managed_import__", "Managed Import"),
        )
