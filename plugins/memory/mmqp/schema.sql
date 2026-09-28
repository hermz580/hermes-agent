PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    parent_session_id TEXT DEFAULT '',
    modality TEXT NOT NULL DEFAULT 'text',
    source_kind TEXT NOT NULL DEFAULT 'chat_turn',
    user_content TEXT DEFAULT '',
    assistant_content TEXT DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes(episode_id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    signal_name TEXT NOT NULL,
    value_num REAL,
    value_text TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    confidence REAL NOT NULL DEFAULT 1.0,
    provenance TEXT NOT NULL DEFAULT 'observed',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    current_version_id TEXT,
    state TEXT NOT NULL CHECK(state IN ('observation','candidate','canonical','disputed','superseded')),
    category TEXT NOT NULL DEFAULT 'general',
    semantic_importance REAL NOT NULL DEFAULT 0.5,
    emotional_salience REAL NOT NULL DEFAULT 0.0,
    repetition_weight REAL NOT NULL DEFAULT 0.0,
    correction_weight REAL NOT NULL DEFAULT 0.0,
    confidence REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_versions (
    version_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_episode_id TEXT REFERENCES episodes(episode_id),
    created_by TEXT NOT NULL DEFAULT 'mmqp',
    reason TEXT NOT NULL DEFAULT '',
    valid_from TEXT,
    valid_to TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(memory_id, version_no)
);

CREATE TABLE IF NOT EXISTS provenance_links (
    link_id TEXT PRIMARY KEY,
    from_type TEXT NOT NULL,
    from_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    to_type TEXT NOT NULL,
    to_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS council_annotations (
    annotation_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE,
    persona TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS promotion_events (
    event_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    authorized_by TEXT NOT NULL,
    authorization_source TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retrieval_events (
    retrieval_id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    memory_id TEXT NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE,
    score REAL NOT NULL DEFAULT 0.0,
    session_id TEXT DEFAULT '',
    used_by TEXT DEFAULT '',
    helpful INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_episode_session ON episodes(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_episode ON signals(episode_id);
CREATE INDEX IF NOT EXISTS idx_memory_state ON memories(state, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_version_memory ON memory_versions(memory_id, version_no DESC);
CREATE INDEX IF NOT EXISTS idx_council_memory ON council_annotations(memory_id, persona);
CREATE INDEX IF NOT EXISTS idx_retrieval_memory ON retrieval_events(memory_id, created_at DESC);
