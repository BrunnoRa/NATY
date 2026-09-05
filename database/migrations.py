from __future__ import annotations

from database.connection import Database


MIGRATIONS: list[tuple[int, str]] = [
    (1, """
    CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS projects(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, description TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS tasks(
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', project_id INTEGER,
      status TEXT NOT NULL DEFAULT 'pending', priority TEXT NOT NULL DEFAULT 'normal',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, due_at TEXT, estimated_minutes INTEGER,
      completed_at TEXT, postpone_count INTEGER NOT NULL DEFAULT 0, last_prompted_at TEXT,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
    CREATE INDEX IF NOT EXISTS idx_tasks_status_due ON tasks(status, due_at);
    CREATE TABLE IF NOT EXISTS reminders(
      id INTEGER PRIMARY KEY, text TEXT NOT NULL, remind_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, triggered_at TEXT, last_prompted_at TEXT);
    CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(status, remind_at);
    CREATE TABLE IF NOT EXISTS appointments(
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, starts_at TEXT NOT NULL, ends_at TEXT, location TEXT,
      notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'scheduled', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS lists(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, slug TEXT NOT NULL UNIQUE,
      obsidian_file TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS list_items(
      id INTEGER PRIMARY KEY, list_id INTEGER NOT NULL, text TEXT NOT NULL COLLATE NOCASE, quantity REAL,
      checked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT,
      FOREIGN KEY(list_id) REFERENCES lists(id) ON DELETE CASCADE);
    CREATE INDEX IF NOT EXISTS idx_list_items_list ON list_items(list_id, checked);
    CREATE TABLE IF NOT EXISTS notes(
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL, project_id INTEGER,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS memories(
      id INTEGER PRIMARY KEY, type TEXT NOT NULL, key TEXT NOT NULL COLLATE NOCASE, value TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 1.0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TEXT, UNIQUE(type, key));
    CREATE TABLE IF NOT EXISTS preferences(
      key TEXT PRIMARY KEY COLLATE NOCASE, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS activity_history(
      id INTEGER PRIMARY KEY, action TEXT NOT NULL, entity_type TEXT, entity_id INTEGER, summary TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS research_history(
      id INTEGER PRIMARY KEY, query TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      saved_to_obsidian INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS automation_rules(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, trigger_type TEXT NOT NULL, trigger_value TEXT NOT NULL,
      action_type TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, last_run_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """),
    (2, """
    CREATE TABLE IF NOT EXISTS obsidian_documents(
      id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, title TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '',
      frontmatter TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '', wikilinks TEXT NOT NULL DEFAULT '',
      mtime REAL NOT NULL, content_hash TEXT NOT NULL, indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      last_accessed TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS obsidian_fts USING fts5(path UNINDEXED, title, tags, body, tokenize='unicode61 remove_diacritics 2');
    CREATE TABLE IF NOT EXISTS knowledge_nodes(
      id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL, path TEXT, importance REAL NOT NULL DEFAULT 1.0,
      last_accessed TEXT, metadata_json TEXT NOT NULL DEFAULT '{}');
    CREATE TABLE IF NOT EXISTS knowledge_edges(
      source TEXT NOT NULL, target TEXT NOT NULL, relation TEXT NOT NULL,
      PRIMARY KEY(source, target, relation));
    CREATE TABLE IF NOT EXISTS connector_accounts(
      provider TEXT PRIMARY KEY, account_label TEXT, scopes TEXT NOT NULL DEFAULT '', connected_at TEXT,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS research_claims(
      id INTEGER PRIMARY KEY, research_id INTEGER NOT NULL, claim TEXT NOT NULL, source_url TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 0.5, observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(research_id) REFERENCES research_history(id) ON DELETE CASCADE);
    CREATE INDEX IF NOT EXISTS idx_obsidian_documents_mtime ON obsidian_documents(mtime);
    CREATE INDEX IF NOT EXISTS idx_knowledge_edges_source ON knowledge_edges(source);
    """),
    (3, """
    ALTER TABLE automation_rules ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}';
    ALTER TABLE automation_rules ADD COLUMN next_run_at TEXT;
    CREATE INDEX IF NOT EXISTS idx_automation_due ON automation_rules(enabled, next_run_at);
    """),
    (4, """
    CREATE TABLE IF NOT EXISTS sync_applied_events(
      event_id TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sync_entity_map(
      entity TEXT NOT NULL, sync_id TEXT NOT NULL, local_id TEXT NOT NULL,
      PRIMARY KEY(entity, sync_id), UNIQUE(entity, local_id));
    CREATE TABLE IF NOT EXISTS sync_entity_state(
      entity TEXT NOT NULL, sync_id TEXT NOT NULL, last_event_id TEXT NOT NULL,
      last_device_id TEXT NOT NULL, last_timestamp TEXT NOT NULL, payload_json TEXT NOT NULL,
      tombstone INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(entity, sync_id));
    CREATE TABLE IF NOT EXISTS sync_conflicts(
      conflict_id TEXT PRIMARY KEY, entity TEXT NOT NULL, sync_id TEXT NOT NULL,
      local_event_id TEXT NOT NULL, incoming_event_id TEXT NOT NULL,
      local_payload_json TEXT NOT NULL, incoming_payload_json TEXT NOT NULL,
      created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open');
    CREATE INDEX IF NOT EXISTS idx_sync_conflicts_status ON sync_conflicts(status, created_at);
    """),
    (5, """
    CREATE TABLE IF NOT EXISTS activity_events(
      id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, event_type TEXT NOT NULL,
      summary TEXT NOT NULL, project_id INTEGER, source TEXT NOT NULL DEFAULT 'naty',
      metadata_json TEXT NOT NULL DEFAULT '{}', session_id TEXT,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
    CREATE INDEX IF NOT EXISTS idx_activity_events_time ON activity_events(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_activity_events_type_time ON activity_events(event_type, timestamp DESC);
    """),
    (6, """
    CREATE TABLE IF NOT EXISTS workspaces(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE,
      aliases_json TEXT NOT NULL DEFAULT '[]', actions_json TEXT NOT NULL DEFAULT '[]',
      project_id INTEGER, focus_minutes INTEGER, enabled INTEGER NOT NULL DEFAULT 1,
      active INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
    CREATE INDEX IF NOT EXISTS idx_workspaces_enabled ON workspaces(enabled,name);
    """),
    (7, """
    CREATE TABLE IF NOT EXISTS notification_items(
      id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, category TEXT NOT NULL,
      priority TEXT NOT NULL, title TEXT NOT NULL, message TEXT NOT NULL,
      action_json TEXT NOT NULL DEFAULT '{}', read INTEGER NOT NULL DEFAULT 0,
      event_key TEXT);
    CREATE INDEX IF NOT EXISTS idx_notifications_read_time ON notification_items(read,timestamp DESC);
    CREATE TABLE IF NOT EXISTS proactivity_events(
      event_key TEXT PRIMARY KEY, last_shown TEXT NOT NULL, cooldown_minutes INTEGER NOT NULL);
    """),
    (8, """
    CREATE TABLE IF NOT EXISTS skill_gaps(
      id INTEGER PRIMARY KEY, request_text TEXT NOT NULL, normalized_key TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL DEFAULT 'suggested', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_skill_gaps_status ON skill_gaps(status,updated_at DESC);
    """),
]


def migrate(db: Database) -> None:
    with db.transaction() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for version, sql in MIGRATIONS:
            if version not in applied:
                conn.executescript(sql)
                conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
