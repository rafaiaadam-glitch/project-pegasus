// API Client for Pegasus Backend
import { Course, Lecture, Preset, Artifact, Job, LectureProgress } from '../types';
import * as MockData from './mockData';

// Configure this to point to your backend
// For local development: http://localhost:8000
// For production: your deployed backend URL
const API_BASE_URL = __DEV__
  ? 'http://localhost:8000'
  : 'https://your-production-api.com';

// Set to true to use mock data (no backend required)
const USE_MOCK_DATA = true;

class ApiClient {
  private baseUrl: string;
  private useMock: boolean;

  constructor(baseUrl: string = API_BASE_URL, useMock: boolean = USE_MOCK_DATA) {
    this.baseUrl = baseUrl;
    this.useMock = useMock;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
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

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    return this.request('/health');
  }

  // Courses
  async getCourses(limit = 50, offset = 0): Promise<{ courses: Course[] }> {
    if (this.useMock) {
      return Promise.resolve(MockData.getMockCourses());
    }
    return this.request(`/courses?limit=${limit}&offset=${offset}`);
  }

  async getCourse(courseId: string): Promise<Course> {
    if (this.useMock) {
      const courses = MockData.getMockCourses();
      const course = courses.courses.find(c => c.id === courseId);
      if (!course) throw new Error('Course not found');
      return Promise.resolve(course);
    }
    return this.request(`/courses/${courseId}`);
  }

  async createCourse(data: { title: string; description?: string }): Promise<Course> {
    // Note: This endpoint may not exist in backend yet
    return this.request('/courses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Lectures
  async getLectures(courseId?: string, limit = 50, offset = 0): Promise<{ lectures: Lecture[] }> {
    if (this.useMock) {
      if (courseId) {
        return Promise.resolve(MockData.getMockLectures(courseId));
      }
      // Return all lectures when no courseId is specified
      const allLectures = Object.values(MockData.mockLectures).flat();
      return Promise.resolve({ lectures: allLectures });
    }
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (courseId) params.append('course_id', courseId);
    return this.request(`/lectures?${params}`);
  }

  async getCourseLectures(courseId: string, limit = 50, offset = 0): Promise<{ lectures: Lecture[] }> {
    if (this.useMock) {
      return Promise.resolve(MockData.getMockLectures(courseId));
    }
    return this.request(`/courses/${courseId}/lectures?limit=${limit}&offset=${offset}`);
  }

  async getLecture(lectureId: string): Promise<Lecture> {
    if (this.useMock) {
      const allLectures = Object.values(MockData.mockLectures).flat();
      const lecture = allLectures.find(l => l.id === lectureId);
      if (!lecture) throw new Error('Lecture not found');
      return Promise.resolve(lecture);
    }
    return this.request(`/lectures/${lectureId}`);
  }

  async getLectureProgress(lectureId: string): Promise<LectureProgress> {
    if (this.useMock) {
      const progress = MockData.getMockProgress(lectureId);
      if (!progress) throw new Error('Progress not found');
      return Promise.resolve(progress);
    }
    return this.request(`/lectures/${lectureId}/progress`);
  }

  async getLectureSummary(lectureId: string): Promise<any> {
    if (this.useMock) {
      return Promise.resolve(MockData.getMockSummary(lectureId));
    }
    return this.request(`/lectures/${lectureId}/summary`);
  }

  // Presets
  async getPresets(): Promise<{ presets: Preset[] }> {
    if (this.useMock) {
      return Promise.resolve(MockData.getMockPresets());
    }
    return this.request('/presets');
  }

  async getPreset(presetId: string): Promise<Preset> {
    if (this.useMock) {
      const presets = MockData.getMockPresets();
      const preset = presets.presets.find(p => p.id === presetId);
      if (!preset) throw new Error('Preset not found');
      return Promise.resolve(preset);
    }
    return this.request(`/presets/${presetId}`);
  }

  // Artifacts
  async getLectureArtifacts(
    lectureId: string,
    artifactType?: string,
    presetId?: string
  ): Promise<any> {
    if (this.useMock) {
      return Promise.resolve(MockData.getMockArtifacts(lectureId));
    }
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
    const response = await fetch(url, {
      method: 'POST',
      body: formData, // Don't set Content-Type for multipart/form-data
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  async transcribeLecture(lectureId: string): Promise<any> {
    return this.request(`/lectures/${lectureId}/transcribe`, {
      method: 'POST',
    });
  }

  async generateArtifacts(
    lectureId: string,
    data: { course_id?: string; preset_id?: string; openai_model?: string }
  ): Promise<any> {
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
}

// Export singleton instance
export default new ApiClient();
