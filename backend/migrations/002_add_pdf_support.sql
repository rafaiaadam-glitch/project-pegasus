-- Add source_type column to differentiate audio from PDF uploads
ALTER TABLE lectures ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'audio';

-- Update existing lectures to have source_type='audio'
UPDATE lectures SET source_type = 'audio' WHERE source_type IS NULL;

-- Add constraint to ensure valid source types
ALTER TABLE lectures ADD CONSTRAINT lectures_source_type_check
  CHECK (source_type IN ('audio', 'pdf'));

-- Add index for filtering by source type
CREATE INDEX IF NOT EXISTS lectures_source_type_idx ON lectures (source_type);
