// API Client for Pegasus Backend
import { Platform } from 'react-native';
import { Course, Lecture, Preset, Artifact, Job, LectureProgress } from '../types';

const getApiBaseUrl = () => {
  const productionUrl = process.env.EXPO_PUBLIC_API_URL;
  if (productionUrl) return productionUrl;

  if (Platform.OS === 'android') return 'http://10.0.2.2:8000';
  if (Platform.OS === 'ios') return 'http://localhost:8000';
  return 'http://192.168.1.78:8000';
};

export const API_URL = getApiBaseUrl();
const API_BASE_URL = API_URL;

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const writeToken = process.env.EXPO_PUBLIC_WRITE_API_TOKEN;
    if (writeToken) headers['Authorization'] = `Bearer ${writeToken}`;
    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const response = await fetch(url, {
        ...options,
        headers: { ...this.getAuthHeaders(), ...options.headers },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  // Health
  async healthCheck(): Promise<{ status: string }> {
    return this.request('/health');
  }

  // Courses
  async getCourses(limit = 50, offset = 0): Promise<{ courses: Course[] }> {
    return this.request(`/courses?limit=${limit}&offset=${offset}`);
  }

  async getCourse(courseId: string): Promise<Course> {
    return this.request(`/courses/${courseId}`);
  }

  async createCourse(data: { title: string; description?: string }): Promise<Course> {
    return this.request('/courses', { method: 'POST', body: JSON.stringify(data) });
  }

  // Lectures
  async getLectures(courseId?: string, limit = 50, offset = 0): Promise<{ lectures: Lecture[] }> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (courseId) params.append('course_id', courseId);
    return this.request(`/lectures?${params}`);
  }

  async getCourseLectures(courseId: string, limit = 50, offset = 0): Promise<{ lectures: Lecture[] }> {
    return this.request(`/courses/${courseId}/lectures?limit=${limit}&offset=${offset}`);
  }

  async getLecture(lectureId: string): Promise<Lecture> {
    return this.request(`/lectures/${lectureId}`);
  }

  async getLectureProgress(lectureId: string): Promise<LectureProgress> {
    return this.request(`/lectures/${lectureId}/progress`);
  }

  async getLectureSummary(lectureId: string): Promise<any> {
    return this.request(`/lectures/${lectureId}/summary`);
  }

  // Presets
  async getPresets(): Promise<{ presets: Preset[] }> {
    return this.request('/presets');
  }

  async getPreset(presetId: string): Promise<Preset> {
    return this.request(`/presets/${presetId}`);
  }

  // Artifacts
  async getLectureArtifacts(lectureId: string, artifactType?: string, presetId?: string): Promise<any> {
    const params = new URLSearchParams();
    if (artifactType) params.append('artifact_type', artifactType);
    if (presetId) params.append('preset_id', presetId);
    const query = params.toString();
    return this.request(`/lectures/${lectureId}/artifacts${query ? '?' + query : ''}`);
  }

  // Jobs
  async getLectureJobs(lectureId: string): Promise<{ jobs: Job[] }> {
    return this.request(`/lectures/${lectureId}/jobs`);
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request(`/jobs/${jobId}`);
  }

  // Processing Actions
  async ingestLecture(formData: FormData): Promise<any> {
    const url = `${this.baseUrl}/lectures/ingest`;
    const headers: Record<string, string> = {};
    const writeToken = process.env.EXPO_PUBLIC_WRITE_API_TOKEN;
    if (writeToken) headers['Authorization'] = `Bearer ${writeToken}`;

    const response = await fetch(url, { method: 'POST', headers, body: formData });
    if (!response.ok) {
      const errorText = await response.text();
      let detail = `HTTP ${response.status}`;
      try { detail = JSON.parse(errorText).detail || detail; } catch {}
      throw new Error(detail);
    }
    return response.json();
  }

  async transcribeLecture(lectureId: string): Promise<any> {
    const languageCode = process.env.EXPO_PUBLIC_STT_LANGUAGE || 'en-US';
    return this.request(
      `/lectures/${lectureId}/transcribe?provider=google&language_code=${encodeURIComponent(languageCode)}`,
      { method: 'POST' }
    );
  }

  async generateArtifacts(lectureId: string, data: { course_id?: string; preset_id?: string }): Promise<any> {
    return this.request(`/lectures/${lectureId}/generate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async exportLecture(lectureId: string, exportType = 'markdown'): Promise<any> {
    return this.request(`/lectures/${lectureId}/export`, {
      method: 'POST',
      body: JSON.stringify({ export_type: exportType }),
    });
  }

  // Threads
  async getCourseThreads(courseId: string, limit = 50, offset = 0): Promise<any> {
    return this.request(`/courses/${courseId}/threads?limit=${limit}&offset=${offset}`);
  }

  async getCourseThreadTree(courseId: string): Promise<any> {
    return this.request(`/courses/${courseId}/thread-tree`);
  }

  async getThreadChildren(threadId: string): Promise<any> {
    return this.request(`/threads/${threadId}/children`);
  }
}

export default new ApiClient();
