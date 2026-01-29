import { Lecture, Thread } from "./models.js";
import { getDailyStudyPlan, LectureUploadRequest, validateLectureUpload } from "./api.js";
import { processLecture, upsertThread } from "./pipeline.js";

export type EndpointResult<T> = {
  status: number;
  body: T;
};

export const postLectureUpload = (
  request: LectureUploadRequest,
): EndpointResult<LectureUploadRequest> => ({
  status: 202,
  body: validateLectureUpload(request),
});

export const postLectureProcess = (
  payload: Parameters<typeof processLecture>[0],
): EndpointResult<Lecture> => ({
  status: 201,
  body: processLecture(payload),
});

export const postThreadUpsert = (
  payload: Parameters<typeof upsertThread>[0],
): EndpointResult<Thread> => ({
  status: 200,
  body: upsertThread(payload),
});

export const getDailyStudy = (
  threads: Thread[],
): EndpointResult<ReturnType<typeof getDailyStudyPlan>> => ({
  status: 200,
  body: getDailyStudyPlan(threads),
});
