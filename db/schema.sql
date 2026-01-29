-- Core schema for Pegasus Lecture Copilot.
-- Threads are primary; lectures are immutable secondary inputs.

CREATE TABLE modules (
  module_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  learning_outcomes TEXT NOT NULL
);

CREATE TABLE lectures (
  lecture_id TEXT PRIMARY KEY,
  module_id TEXT NOT NULL REFERENCES modules(module_id),
  title TEXT NOT NULL,
  date TEXT NOT NULL,
  duration INTEGER NOT NULL,
  transcript TEXT NOT NULL,
  consent_confirmed BOOLEAN NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE lecture_segments (
  segment_id TEXT PRIMARY KEY,
  lecture_id TEXT NOT NULL REFERENCES lectures(lecture_id),
  start_time INTEGER NOT NULL,
  end_time INTEGER NOT NULL,
  text TEXT NOT NULL
);

CREATE TABLE exam_signals (
  signal_id TEXT PRIMARY KEY,
  lecture_id TEXT NOT NULL REFERENCES lectures(lecture_id),
  segment_id TEXT NOT NULL REFERENCES lecture_segments(segment_id),
  type TEXT NOT NULL,
  weight REAL NOT NULL
);

CREATE TABLE threads (
  thread_id TEXT PRIMARY KEY,
  module_id TEXT NOT NULL REFERENCES modules(module_id),
  title TEXT NOT NULL,
  gravity_score REAL NOT NULL,
  confidence_score REAL NOT NULL
);

CREATE TABLE thread_appearances (
  appearance_id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(thread_id),
  lecture_id TEXT NOT NULL REFERENCES lectures(lecture_id),
  segment_id TEXT NOT NULL REFERENCES lecture_segments(segment_id),
  label TEXT NOT NULL,
  summary TEXT NOT NULL,
  detected_at TEXT NOT NULL
);

CREATE TABLE thread_layers (
  thread_id TEXT PRIMARY KEY REFERENCES threads(thread_id),
  conscious_summary TEXT NOT NULL,
  subconscious_summary TEXT NOT NULL,
  unconscious_summary TEXT NOT NULL,
  conscious_connections TEXT NOT NULL,
  subconscious_connections TEXT NOT NULL,
  unconscious_connections TEXT NOT NULL,
  conscious_critique TEXT NOT NULL,
  subconscious_critique TEXT NOT NULL,
  unconscious_critique TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE thread_sources (
  source_id TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES threads(thread_id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  verified BOOLEAN NOT NULL
);

CREATE TABLE thread_safeguards (
  thread_id TEXT PRIMARY KEY REFERENCES threads(thread_id),
  red_mode BOOLEAN NOT NULL,
  reason TEXT,
  last_triggered TEXT
);
