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
  source_type?: 'audio' | 'pdf';
  status: 'uploaded' | 'processing' | 'generated' | 'failed';
  duration_sec?: number;
  audio_url?: string;
  summary?: string;
  created_at: string;
  updated_at?: string;
}

export interface Preset {
  id: string;
  name: string;
  kind: 'exam' | 'concept-map' | 'beginner' | 'neurodivergent-friendly' | 'neurodivergent' | 'research' | 'seminar';
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

export type DiceFace = 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'BLUE' | 'PURPLE';

export interface Thread {
  id: string;
  course_id: string;
  title: string;
  summary: string;
  status: 'foundational' | 'advanced';
  complexity_level: number;
  lecture_refs: string[];
  face?: DiceFace | null;
  created_at?: string;
}

export interface ThreadOccurrence {
  id: string;
  thread_id: string;
  course_id: string;
  lecture_id: string;
  evidence: string;
  confidence: number;
  lecture_title?: string;
  captured_at: string;
}

export interface ThreadUpdate {
  id: string;
  thread_id: string;
  course_id: string;
  lecture_id: string;
  change_type: 'refinement' | 'contradiction' | 'complexity';
  summary: string;
  details?: string[];
  lecture_title?: string;
  captured_at: string;
}

export interface ThreadDetail {
  thread: Thread;
  occurrences: ThreadOccurrence[];
  updates: ThreadUpdate[];
  lectureTitles: Record<string, string>;
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

export interface TokenBalance {
  freeBalance: number;
  purchasedBalance: number;
  totalBalance: number;
  freeResetsAt: string | null;
  freeMonthlyAllowance: number;
}

export interface TokenTransaction {
  id: string;
  transactionType: string;
  tokenAmount: number;
  balanceAfterFree: number;
  balanceAfterPurchased: number;
  referenceId?: string;
  description?: string;
  createdAt: string;
}

export interface Product {
  productId: string;
  tokens: number;
  priceUsd: number;
  label: string;
}

export interface PurchaseReceipt {
  id: string;
  platform: string;
  productId: string;
  transactionId: string;
  tokensGranted: number;
  priceUsd: number;
  status: string;
  createdAt: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
