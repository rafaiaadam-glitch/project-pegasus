// Lecture captures a single time-bounded event and is immutable after processing.
export type Lecture = {
  lecture_id: string;
  module_id: string;
  title: string;
  date: string;
  duration: number;
  transcript: string;
  segments: LectureSegment[];
  detected_threads: ThreadAppearance[];
  exam_signals: ExamSignal[];
  consent_confirmed: boolean;
};

export type LectureSegment = {
  segment_id: string;
  lecture_id: string;
  start_time: number;
  end_time: number;
  text: string;
  detected_signals: ExamSignal[];
};

// Thread is the primary object; it accumulates across lectures and drives study logic.
export type Thread = {
  thread_id: string;
  title: string;
  module_id: string;
  gravity_score: number;
  confidence_score: number;
  appearances: ThreadAppearance[];
  layers: ThreadLayers;
  exam_signals: ExamSignal[];
  sources: SourceReference[];
  safeguards: ThreadSafeguards;
};

// ThreadAppearance records how a lecture contributes to a thread's evolution.
export type ThreadAppearance = {
  lecture_id: string;
  segment_id: string;
  label: "definition" | "example" | "expansion" | "critique" | "application";
  summary: string;
  detected_at: string;
};

// Layers enforce bounded depth to prevent cognitive overload.
export type ThreadLayers = {
  conscious: ThreadLayerContent;
  subconscious: ThreadLayerContent;
  unconscious: ThreadLayerContent;
};

export type ThreadLayerContent = {
  summary: string;
  connections: string[];
  critique_prompts: string[];
  last_updated: string;
};

// Exam signals are only derived from verified lecture input.
export type ExamSignal = {
  type: "emphasis" | "repetition" | "explicit_cue";
  weight: number;
  source_segment_id: string;
};

// Sources are only used when verified to avoid hallucinated citations.
export type SourceReference = {
  source_id: string;
  type: "slide" | "pdf" | "link";
  title: string;
  url?: string;
  verified: boolean;
};

// Safeguards capture stress-related collapses and rationale.
export type ThreadSafeguards = {
  red_mode: boolean;
  reason?: string;
  last_triggered?: string;
};
