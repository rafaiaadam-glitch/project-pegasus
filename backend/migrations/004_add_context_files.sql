-- Context files table
-- Stores syllabus and notes uploaded by students for Thread Engine context

CREATE TABLE IF NOT EXISTS context_files (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,

    -- File metadata
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_type TEXT NOT NULL,

    -- Classification
    tag TEXT NOT NULL CHECK (tag IN ('SYLLABUS', 'NOTES')),

    -- Extracted content
    extracted_text TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS context_files_course_id_idx ON context_files (course_id);
CREATE INDEX IF NOT EXISTS context_files_tag_idx ON context_files (tag);
CREATE INDEX IF NOT EXISTS context_files_created_at_idx ON context_files (created_at DESC);

-- Comment
COMMENT ON TABLE context_files IS 'Syllabus and notes files uploaded for Thread Engine context';
COMMENT ON COLUMN context_files.tag IS 'SYLLABUS for course outline, NOTES for supporting materials';
COMMENT ON COLUMN context_files.extracted_text IS 'Extracted text content from PDF/DOCX/TXT files';
