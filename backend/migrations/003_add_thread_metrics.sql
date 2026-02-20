-- Thread detection metrics table
-- Tracks quality and performance of thread detection for monitoring and optimization

CREATE TABLE IF NOT EXISTS thread_metrics (
    id TEXT PRIMARY KEY,
    lecture_id TEXT NOT NULL,
    course_id TEXT NOT NULL,

    -- Timestamp
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Thread counts
    new_threads_detected INTEGER NOT NULL DEFAULT 0,
    existing_threads_updated INTEGER NOT NULL DEFAULT 0,
    total_threads_after INTEGER NOT NULL DEFAULT 0,

    -- Quality metrics
    avg_complexity_level DECIMAL(3,2),
    complexity_distribution JSONB,
    change_type_distribution JSONB,

    -- Evidence quality
    avg_evidence_length DECIMAL(6,1),
    threads_with_evidence INTEGER NOT NULL DEFAULT 0,

    -- Performance metrics
    detection_method TEXT NOT NULL, -- 'openai', 'fallback'
    api_response_time_ms DECIMAL(10,2),
    token_usage JSONB, -- {input: N, output: M}
    retry_count INTEGER NOT NULL DEFAULT 0,

    -- Model info
    model_name TEXT,
    llm_provider TEXT,

    -- Status
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,

    -- Quality score (calculated)
    quality_score DECIMAL(5,2),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS thread_metrics_lecture_id_idx ON thread_metrics (lecture_id);
CREATE INDEX IF NOT EXISTS thread_metrics_course_id_idx ON thread_metrics (course_id);
CREATE INDEX IF NOT EXISTS thread_metrics_detected_at_idx ON thread_metrics (detected_at DESC);
CREATE INDEX IF NOT EXISTS thread_metrics_detection_method_idx ON thread_metrics (detection_method);
CREATE INDEX IF NOT EXISTS thread_metrics_success_idx ON thread_metrics (success);
CREATE INDEX IF NOT EXISTS thread_metrics_quality_score_idx ON thread_metrics (quality_score DESC);

-- Add comment
COMMENT ON TABLE thread_metrics IS 'Tracks quality and performance metrics for thread detection runs';
