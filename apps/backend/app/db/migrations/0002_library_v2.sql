PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'created',
    source_kind TEXT NOT NULL,
    import_method TEXT NOT NULL DEFAULT 'copy',
    file_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    error_summary TEXT NULL
);

CREATE TABLE IF NOT EXISTS inbox_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_batch_id INTEGER NOT NULL,
    file_id INTEGER NULL,
    source_path TEXT NOT NULL,
    inbox_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'imported',
    detected_file_kind TEXT NULL,
    detected_placement TEXT NULL,
    detected_object_type TEXT NULL,
    final_object_type TEXT NULL,
    target_library_root_id INTEGER NULL,
    organize_candidate_id INTEGER NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(import_batch_id) REFERENCES import_batches(id),
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE SET NULL,
    FOREIGN KEY(target_library_root_id) REFERENCES library_roots(id),
    FOREIGN KEY(organize_candidate_id) REFERENCES organize_candidates(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS operation_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NULL,
    status TEXT NOT NULL DEFAULT 'started',
    before_json TEXT NULL,
    after_json TEXT NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL,
    finished_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS file_path_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    old_path TEXT NULL,
    new_path TEXT NOT NULL,
    reason TEXT NOT NULL,
    operation_journal_id INTEGER NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(file_id) REFERENCES files(id),
    FOREIGN KEY(operation_journal_id) REFERENCES operation_journal(id)
);

CREATE TABLE IF NOT EXISTS import_object_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_batch_id INTEGER NOT NULL,
    source_root_path TEXT NOT NULL,
    inbox_root_path TEXT NOT NULL,
    suggested_object_type TEXT NULL,
    final_object_type TEXT NULL,
    confidence TEXT NULL,
    status TEXT NOT NULL DEFAULT 'detected',
    primary_file_id INTEGER NULL,
    launch_file_id INTEGER NULL,
    member_count INTEGER NOT NULL DEFAULT 0,
    reason_json TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(import_batch_id) REFERENCES import_batches(id),
    FOREIGN KEY(primary_file_id) REFERENCES files(id),
    FOREIGN KEY(launch_file_id) REFERENCES files(id)
);

CREATE TABLE IF NOT EXISTS import_object_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_object_candidate_id INTEGER NOT NULL,
    inbox_item_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'unknown_child',
    confidence TEXT NULL,
    reason TEXT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(import_object_candidate_id) REFERENCES import_object_candidates(id),
    FOREIGN KEY(inbox_item_id) REFERENCES inbox_items(id)
);

CREATE INDEX IF NOT EXISTS idx_import_batches_status ON import_batches(status);
CREATE INDEX IF NOT EXISTS idx_inbox_items_import_batch_id ON inbox_items(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_inbox_items_file_id ON inbox_items(file_id);
CREATE INDEX IF NOT EXISTS idx_inbox_items_status ON inbox_items(status);
CREATE INDEX IF NOT EXISTS idx_inbox_items_organize_candidate_id ON inbox_items(organize_candidate_id);
CREATE INDEX IF NOT EXISTS idx_operation_journal_operation_id ON operation_journal(operation_id);
CREATE INDEX IF NOT EXISTS idx_operation_journal_status ON operation_journal(status);
CREATE INDEX IF NOT EXISTS idx_operation_journal_created_at ON operation_journal(created_at);
CREATE INDEX IF NOT EXISTS idx_file_path_history_file_id ON file_path_history(file_id);
CREATE INDEX IF NOT EXISTS idx_import_object_candidates_import_batch_id ON import_object_candidates(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_import_object_candidates_status ON import_object_candidates(status);
CREATE INDEX IF NOT EXISTS idx_import_object_members_candidate_id ON import_object_members(import_object_candidate_id);
CREATE INDEX IF NOT EXISTS idx_import_object_members_inbox_item_id ON import_object_members(inbox_item_id);
