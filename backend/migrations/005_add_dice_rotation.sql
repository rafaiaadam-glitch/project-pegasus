-- Dice rotation state table
-- Stores the rotation state for each lecture's thread detection

CREATE TABLE IF NOT EXISTS dice_rotation_states (
    id TEXT PRIMARY KEY,
    lecture_id TEXT NOT NULL,
    course_id TEXT NOT NULL,

    -- Rotation metadata
    iterations_completed INTEGER NOT NULL,
    max_iterations INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'equilibrium', 'collapsed', 'max_iterations')),

    -- Facet scores (current state)
    score_how REAL NOT NULL DEFAULT 0.0,
    score_what REAL NOT NULL DEFAULT 0.0,
    score_when REAL NOT NULL DEFAULT 0.0,
    score_where REAL NOT NULL DEFAULT 0.0,
    score_who REAL NOT NULL DEFAULT 0.0,
    score_why REAL NOT NULL DEFAULT 0.0,

    -- Metrics
    entropy REAL NOT NULL DEFAULT 0.0,
    equilibrium_gap REAL NOT NULL DEFAULT 1.0,
    collapsed BOOLEAN NOT NULL DEFAULT FALSE,
    dominant_facet TEXT,
    dominant_score REAL,

    -- Full state (JSONB)
    full_state JSONB NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS dice_rotation_states_lecture_id_idx ON dice_rotation_states (lecture_id);
CREATE INDEX IF NOT EXISTS dice_rotation_states_course_id_idx ON dice_rotation_states (course_id);
CREATE INDEX IF NOT EXISTS dice_rotation_states_status_idx ON dice_rotation_states (status);
CREATE INDEX IF NOT EXISTS dice_rotation_states_dominant_facet_idx ON dice_rotation_states (dominant_facet);

-- Comments
COMMENT ON TABLE dice_rotation_states IS 'Stores dice rotation state for thread detection transparency';
COMMENT ON COLUMN dice_rotation_states.status IS 'Rotation completion status: in_progress, equilibrium, collapsed, or max_iterations';
COMMENT ON COLUMN dice_rotation_states.entropy IS 'Shannon entropy of facet score distribution (higher = more balanced)';
COMMENT ON COLUMN dice_rotation_states.equilibrium_gap IS 'Distance from perfect equilibrium (lower = more balanced)';
COMMENT ON COLUMN dice_rotation_states.full_state IS 'Complete rotation state including schedule and iteration history';
