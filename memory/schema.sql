-- NEUTRON Memory Schema
-- SQLite database for episodic and semantic memory

-- Episodic memories (conversations, events)
CREATE TABLE IF NOT EXISTS episodic_memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    summary TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    emotion_valence REAL DEFAULT 0.5,
    emotion_arousal REAL DEFAULT 0.3,
    importance REAL DEFAULT 0.5,
    tags TEXT,  -- JSON array
    metadata TEXT,  -- JSON object
    embedding_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Semantic facts (learned knowledge)
CREATE TABLE IF NOT EXISTS semantic_facts (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    first_learned DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_confirmed DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    metadata TEXT  -- JSON object
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    turn_count INTEGER DEFAULT 0,
    topic TEXT,
    summary TEXT,
    emotion_trajectory TEXT,  -- JSON array
    participants INTEGER DEFAULT 1,
    metadata TEXT  -- JSON object
);

-- Conversation turns
CREATE TABLE IF NOT EXISTS conversation_turns (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    emotion_valence REAL,
    emotion_arousal REAL,
    intent TEXT,
    metadata TEXT,  -- JSON object
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- User preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    learned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0
);

-- Cloud sync tracking
CREATE TABLE IF NOT EXISTS sync_log (
    id TEXT PRIMARY KEY,
    sync_type TEXT NOT NULL,  -- 'full' or 'incremental'
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    items_synced INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error TEXT
);

-- Privacy log (for audit)
CREATE TABLE IF NOT EXISTS privacy_log (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,  -- 'forget', 'private_mode_on', 'private_mode_off'
    target_type TEXT,
    target_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

-- Important events (automatically captured significant moments)
CREATE TABLE IF NOT EXISTS important_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,  -- 'emotional', 'milestone', 'preference', 'request'
    content TEXT NOT NULL,
    summary TEXT,
    importance_score REAL DEFAULT 0.5,
    user_emotion TEXT,
    robot_emotion TEXT,
    context TEXT,  -- JSON: conversation context
    requires_followup BOOLEAN DEFAULT FALSE,
    followup_completed BOOLEAN DEFAULT FALSE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON object
);

-- User profile (learned information about the user)
CREATE TABLE IF NOT EXISTS user_profile (
    id TEXT PRIMARY KEY,
    name TEXT,
    preferred_name TEXT,  -- How they like to be called
    voice_signature TEXT,  -- For future voice recognition
    face_encoding TEXT,  -- For future face recognition
    emotional_baseline TEXT,  -- JSON: typical emotion patterns
    preferences TEXT,  -- JSON: learned preferences
    interests TEXT,  -- JSON array of topics
    communication_style TEXT,  -- 'casual', 'formal', 'friendly'
    interaction_count INTEGER DEFAULT 0,
    total_conversation_time_seconds INTEGER DEFAULT 0,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    trust_level REAL DEFAULT 0.5,  -- How much user trusts the robot
    metadata TEXT  -- JSON object
);

-- Interaction statistics
CREATE TABLE IF NOT EXISTS interaction_stats (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    total_interactions INTEGER DEFAULT 0,
    total_words_spoken INTEGER DEFAULT 0,
    avg_emotion_valence REAL DEFAULT 0.5,
    avg_emotion_arousal REAL DEFAULT 0.3,
    most_common_topic TEXT,
    most_common_emotion TEXT,
    feedback_positive INTEGER DEFAULT 0,
    feedback_negative INTEGER DEFAULT 0,
    metadata TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic_memories(timestamp);
CREATE INDEX IF NOT EXISTS idx_episodic_importance ON episodic_memories(importance);
CREATE INDEX IF NOT EXISTS idx_semantic_subject ON semantic_facts(subject);
CREATE INDEX IF NOT EXISTS idx_conversation_started ON conversations(started_at);
CREATE INDEX IF NOT EXISTS idx_turns_conversation ON conversation_turns(conversation_id);
CREATE INDEX IF NOT EXISTS idx_important_events_type ON important_events(event_type);
CREATE INDEX IF NOT EXISTS idx_important_events_importance ON important_events(importance_score);
CREATE INDEX IF NOT EXISTS idx_user_profile_name ON user_profile(name);
CREATE INDEX IF NOT EXISTS idx_interaction_stats_date ON interaction_stats(date);

