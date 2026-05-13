PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    display_name TEXT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    scan_mode TEXT NOT NULL DEFAULT 'manual_plus_basic_incremental',
    last_scan_at DATETIME NULL,
    last_scan_status TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS source_ignore_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    rule_type TEXT NOT NULL,
    rule_value TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    path TEXT NOT NULL UNIQUE,
    parent_path TEXT NOT NULL,
    name TEXT NOT NULL,
    stem TEXT NULL,
    extension TEXT NULL,
    file_type TEXT NOT NULL,
    file_kind TEXT NOT NULL DEFAULT 'other',
    auto_placement TEXT NOT NULL DEFAULT 'none',
    mime_type TEXT NULL,
    size_bytes INTEGER NULL,
    created_at_fs DATETIME NULL,
    modified_at_fs DATETIME NULL,
    discovered_at DATETIME NOT NULL,
    last_seen_at DATETIME NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    checksum_hint TEXT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS file_metadata (
    file_id INTEGER PRIMARY KEY,
    width INTEGER NULL,
    height INTEGER NULL,
    duration_ms INTEGER NULL,
    page_count INTEGER NULL,
    title TEXT NULL,
    author TEXT NULL,
    series TEXT NULL,
    codec_info TEXT NULL,
    extra_json TEXT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS file_tags (
    file_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (file_id, tag_id),
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS file_user_meta (
    file_id INTEGER PRIMARY KEY,
    color_tag TEXT NULL,
    status TEXT NULL,
    manual_placement TEXT NULL,
    rating INTEGER NULL,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    placement_updated_at DATETIME NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_type TEXT NULL,
    tag_id INTEGER NULL,
    color_tag TEXT NULL,
    source_id INTEGER NULL,
    parent_path TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    source_id INTEGER NULL,
    target_file_id INTEGER NULL,
    payload_json TEXT NULL,
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE SET NULL,
    FOREIGN KEY(target_file_id) REFERENCES files(id) ON DELETE SET NULL
);

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
);

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
);

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
);

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
);

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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS organize_plan_candidates (
    plan_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    PRIMARY KEY (plan_id, candidate_id),
    FOREIGN KEY(plan_id) REFERENCES organize_plans(id) ON DELETE CASCADE,
    FOREIGN KEY(candidate_id) REFERENCES organize_candidates(id) ON DELETE CASCADE
);

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
);

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
);

CREATE INDEX IF NOT EXISTS idx_files_source_id ON files(source_id);
CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
CREATE INDEX IF NOT EXISTS idx_files_parent_path ON files(parent_path);
CREATE INDEX IF NOT EXISTS idx_tags_normalized_name ON tags(normalized_name);
CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id ON file_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_file_user_meta_color_tag ON file_user_meta(color_tag);
CREATE INDEX IF NOT EXISTS idx_tasks_source_id ON tasks(source_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tool_runs_tool_key ON tool_runs(tool_key);
CREATE INDEX IF NOT EXISTS idx_tool_runs_status ON tool_runs(status);
CREATE INDEX IF NOT EXISTS idx_tool_runs_created_at ON tool_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_library_objects_object_type ON library_objects(object_type);
CREATE INDEX IF NOT EXISTS idx_library_objects_needs_review ON library_objects(needs_review);
CREATE INDEX IF NOT EXISTS idx_library_objects_last_scanned_at ON library_objects(last_scanned_at);
CREATE INDEX IF NOT EXISTS idx_library_object_members_object_id ON library_object_members(object_id);
CREATE INDEX IF NOT EXISTS idx_library_object_members_member_role ON library_object_members(member_role);
CREATE INDEX IF NOT EXISTS idx_organize_candidates_status ON organize_candidates(status);
CREATE INDEX IF NOT EXISTS idx_organize_candidates_source_file_id ON organize_candidates(source_file_id);
CREATE INDEX IF NOT EXISTS idx_organize_candidates_source_object_id ON organize_candidates(source_object_id);
CREATE INDEX IF NOT EXISTS idx_organize_plans_status ON organize_plans(status);
CREATE INDEX IF NOT EXISTS idx_organize_actions_plan_id ON organize_actions(plan_id);
CREATE INDEX IF NOT EXISTS idx_organize_actions_conflict_status ON organize_actions(conflict_status);
CREATE INDEX IF NOT EXISTS idx_organize_action_logs_plan_id ON organize_action_logs(plan_id);
CREATE INDEX IF NOT EXISTS idx_organize_action_logs_action_id ON organize_action_logs(action_id);
CREATE INDEX IF NOT EXISTS idx_organize_action_logs_created_at ON organize_action_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_organize_suggestions_candidate_id ON organize_suggestions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_organize_suggestions_status ON organize_suggestions(status);
CREATE INDEX IF NOT EXISTS idx_organize_suggestions_type ON organize_suggestions(suggestion_type);

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
);

CREATE INDEX IF NOT EXISTS idx_library_roots_is_enabled ON library_roots(is_enabled);
CREATE INDEX IF NOT EXISTS idx_library_roots_is_default ON library_roots(is_default);
