import { Lecture, Thread } from "./models.js";
import { computePriority } from "./scoring.js";

export type DailyStudyItem = {
  thread_id: string;
  title: string;
  priority: number;
  gravity: number;
  confidence: number;
  reason: string;
};

// The daily plan keeps choices focused and ordered by urgency.
export const getDailyStudyPlan = (threads: Thread[]): DailyStudyItem[] =>
  threads
    .map((thread) => {
      const priority = computePriority(thread);
      return {
        thread_id: thread.thread_id,
        title: thread.title,
        priority,
        gravity: thread.gravity_score,
        confidence: thread.confidence_score,
        reason: priority > 0.5 ? "High-risk gap" : "Keep momentum",
      };
    })
    .sort((a, b) => b.priority - a.priority);

export type LectureUploadRequest = {
  module_id: string;
  title: string;
  date: string;
  duration: number;
  consent_confirmed: boolean;
};

// Consent is mandatory before lecture processing to meet ethical constraints.
export const validateLectureUpload = (
  request: LectureUploadRequest,
): LectureUploadRequest => {
  if (!request.consent_confirmed) {
    throw new Error("Lecture recording requires explicit consent.");
  }
  return request;
};

// Freeze lectures to maintain immutability after processing.
export const lockLecture = (lecture: Lecture): Lecture =>
  Object.freeze({ ...lecture });
