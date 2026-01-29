 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/docs/architecture.md b/docs/architecture.md
index 55ec65bcc749ade573c995dcd34752a65c26e79b..3dbc334dc61720203eb3f7dbc025a5e4dcd50a9a 100644
--- a/docs/architecture.md
+++ b/docs/architecture.md
@@ -1,141 +1,227 @@
-# Pegasus Architecture
+# Pegasus Lecture Copilot Architecture
 
-This document describes the high-level architecture of **Project Pegasus**: an AI-powered learning engine that transforms unstructured inputs (lectures, audiobooks, notes) into structured, long-term learning threads and adaptive study guidance.
+This document describes the high-level architecture for **Pegasus Lecture Copilot**, the learning engine that turns lectures and notes into structured, long-term learning support.
 
-The architecture is **modular by design**, allowing components to be developed, swapped, or scaled independently.
+Pegasus is **modular by design** so components can evolve independently (e.g., swapping a transcription model without touching study planning).
 
 ---
 
 ## Architectural principles
 
 1. **Separation of concerns**
    - Ingestion ≠ understanding ≠ planning
 2. **Persistence over sessions**
-   - Knowledge accumulates; it is never reset per upload
-3. **Explainability**
-   - Every recommendation should be traceable to evidence
-4. **Overload-aware**
-   - Output is intentionally throttled and prioritised
-5. **LLM as component, not brain**
+   - Knowledge accumulates across lectures and courses
+3. **Explainability by default**
+   - Every recommendation links back to evidence in the source
+4. **Overload-aware outputs**
+   - Limit volume and prioritize what matters most
+5. **LLM as a component, not the brain**
    - LLMs transform data; they do not own state
 
 ---
 
-## High-level system flow
-
-[ Input ]
-|
-v
-[ Ingest ]
-|
-v
-[ Transcription ]
-|
-v
-[ Segmentation ]
-|
-v
-[ Concept Extraction ]
-|
-v
-[ Thread Engine ]
-|
-v
-[ Study Planner ]
-|
-v
-[ Outputs ]
-
+## High-level flow
+
+```
+[Input]
+   ↓
+[Ingest]
+   ↓
+[Transcription]
+   ↓
+[Segmentation]
+   ↓
+[Concept Extraction]
+   ↓
+[Thread Engine]
+   ↓
+[Study Planner]
+   ↓
+[Outputs]
+```
 
 Each stage produces **structured artifacts** that are stored and reused downstream.
 
 ---
 
 ## Core components
 
-### 1. Ingest Layer
+### 1) Ingest Layer
 
 **Responsibility**
 - Accept raw inputs and metadata
 
 **Inputs**
-- Audio files (mp3, wav, m4a)
+- Audio (mp3, wav, m4a)
 - Text (PDF, markdown, notes)
 - Metadata (course, date, source, author)
 
 **Outputs**
-- Normalised input record
+- Normalized input record
 - Pointer to raw asset storage
 
 **Notes**
+- Validation + storage registration only
 - No intelligence here
-- Pure validation + storage registration
 
 ---
 
-### 2. Transcription Layer
+### 2) Transcription Layer
 
 **Responsibility**
 - Convert audio → text
 
 **Inputs**
 - Audio file reference
 
 **Outputs**
 - Verbatim transcript
 - Timestamps (word or sentence level)
 - Confidence scores (if available)
 
 **Notes**
 - Deterministic and repeatable
-- Can be re-run with better models later
+- Can be re-run with improved models later
 
 ---
 
-### 3. Segmentation Layer
+### 3) Segmentation Layer
 
 **Responsibility**
 - Break transcript into meaningful chunks
 
 **Segmentation strategies**
-- Time-based (e.g. every 2–5 minutes)
+- Time-based (e.g., every 2–5 minutes)
 - Topic-shift detection
 - Speaker change (if applicable)
 
 **Outputs**
 - Ordered segments with:
   - text
   - timestamps
   - session reference
 
 **Why this matters**
 Segmentation is the boundary between *raw speech* and *meaningful cognition*.
 
 ---
 
-### 4. Concept Extraction Layer
+### 4) Concept Extraction Layer
 
 **Responsibility**
-- Identify what is being talked about
+- Identify what is being discussed
 
 **Extracted entities**
 - Concepts (terms, ideas, theories)
 - Definitions
 - Claims / arguments
 - Examples
-- Named authors or schools (esp. social sciences)
+- Named authors or schools
 
 **Outputs**
 Structured objects, e.g.:
 
 ```json
 {
   "concept": "Social Constructionism",
   "definition": "...",
   "confidence": 0.82,
   "source_segment_id": "seg_014"
 }
+```
+
+**Notes**
+- Outputs must be schema-driven for downstream stability
+
+---
+
+### 5) Thread Engine
+
+**Responsibility**
+- Maintain long-term concept continuity across sessions
+
+**Inputs**
+- Concept objects
+- Prior session threads
+
+**Outputs**
+- Updated threads (concept timelines)
+- New links between concepts
+- Change tracking (new vs repeated vs evolved)
+
+**Why this matters**
+Threads turn isolated notes into **persistent learning narratives**.
+
+---
+
+### 6) Study Planner
+
+**Responsibility**
+- Convert threads into actionable study guidance
+
+**Inputs**
+- Threads + concept importance signals
+- User goals (exam date, course priority)
+- Available time and pacing preferences
 
+**Outputs**
+- Recommended next steps
+- Time-boxed study blocks
+- “Why now” explanations
+- Optional stop-points to reduce overload
+
+---
+
+### 7) Outputs Layer
+
+**Responsibility**
+- Present structured learning artifacts to the user
+
+**Output formats**
+- Structured summaries
+- Skeleton outlines
+- Exam-style questions
+- Flashcards
+- Study plans and revision paths
+
+---
+
+## Storage and data model (high level)
+
+**Core entities**
+- **Source**: raw asset + metadata
+- **Session**: a lecture, chapter, or meeting
+- **Segment**: ordered transcript chunk
+- **Concept**: extracted topic with evidence
+- **Thread**: persistent concept narrative
+- **StudyAction**: recommended next step
 
+Each entity is **versioned and traceable** to its source segments.
 
 ---
+
+## Interfaces and integrations
+
+- **Transcription providers**: Whisper, cloud transcription APIs
+- **LLM providers**: structured extraction with schema validation
+- **Storage**: relational DB for structured entities + object storage for raw assets
+- **Optional retrieval**: vector DB for similarity and semantic search
+
+---
+
+## Non-functional requirements
+
+- **Explainability**: every output must reference evidence
+- **Observability**: logs and metrics for each pipeline stage
+- **Reprocessing**: ability to re-run extraction without data loss
+- **Privacy**: clear data retention and deletion workflows
+
+---
+
+## Future extensions
+
+- Live lecture support (near real-time segmentation + extraction)
+- Multi-course cross-linking (concepts across disciplines)
+- Adaptive assessments (question difficulty based on mastery)
+- Personalization (study plan tuned to user history)
 
EOF
)
