// API Types for Pegasus Lecture Copilot

export interface Course {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Lecture {
  id: string;
  course_id: string;
  title: string;
  preset_id: string;
  status: 'uploaded' | 'processing' | 'generated' | 'failed';
  duration_sec?: number;
  created_at: string;
  updated_at?: string;
}

export interface Preset {
  id: string;
  name: string;
  kind: 'exam' | 'concept-map' | 'beginner' | 'neurodivergent-friendly' | 'research';
  description?: string;
  outputProfile: Record<string, any>;
}

export interface Artifact {
  id: string;
  lecture_id: string;
  course_id: string;
  preset_id: string;
  artifact_type: 'summary' | 'outline' | 'key-terms' | 'flashcards' | 'exam-questions' | 'threads';
  storage_path: string;
  created_at: string;
}

export interface Thread {
  id: string;
  courseId: string;
  title: string;
  summary: string;
  status: 'foundational' | 'advanced';
  complexityLevel: number;
  lectureRefs: string[];
  evolutionNotes?: any[];
}

export interface Job {
  id: string;
  lecture_id: string;
  job_type: 'transcription' | 'generation' | 'export';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface LectureProgress {
  lectureId: string;
  lectureStatus: string;
  overallStatus: 'not_started' | 'in_progress' | 'completed' | 'failed';
  stageCount: number;
  completedStageCount: number;
  progressPercent: number;
  currentStage?: string;
  hasFailedStage: boolean;
  stages: {
    transcription: StageStatus;
    generation: StageStatus;
    export: StageStatus;
  };
  links: {
    summary: string;
    progress: string;
    artifacts: string;
    jobs: string;
  };
}

export interface StageStatus {
  status: 'not_started' | 'queued' | 'processing' | 'completed' | 'failed';
  job?: Job;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
