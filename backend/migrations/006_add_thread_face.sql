-- Add face column to threads table for dice protocol alignment
-- Valid values: RED (How), ORANGE (What), YELLOW (When), GREEN (Where), BLUE (Who), PURPLE (Why)

ALTER TABLE threads ADD COLUMN IF NOT EXISTS face TEXT;
