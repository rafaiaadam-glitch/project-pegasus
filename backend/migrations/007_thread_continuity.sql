-- 007_thread_continuity.sql: Add thread occurrences, updates, and evolution notes

-- Add evolution_notes column to threads
ALTER TABLE threads ADD COLUMN IF NOT EXISTS evolution_notes JSONB;

-- Thread occurrences: evidence quotes linking threads to lectures
CREATE TABLE IF NOT EXISTS thread_occurrences (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    course_id   TEXT NOT NULL,
    lecture_id  TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    evidence    TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 0.0,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thread_occurrences_thread_id
    ON thread_occurrences(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_occurrences_lecture_id
    ON thread_occurrences(lecture_id);

-- Thread updates: evolution records (refinement, contradiction, complexity)
CREATE TABLE IF NOT EXISTS thread_updates (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    course_id   TEXT NOT NULL,
    lecture_id  TEXT NOT NULL,
    change_type TEXT NOT NULL,
    summary     TEXT NOT NULL,
    details     JSONB,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thread_updates_thread_id
    ON thread_updates(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_updates_lecture_id
    ON thread_updates(lecture_id);

-- Backfill null faces to ORANGE
UPDATE threads SET face = 'ORANGE' WHERE face IS NULL;
