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

  // --- Signed URL & Upload ---

  async getUploadUrl(filename: string, contentType: string): Promise<{ url: string; storagePath: string }> {
    return this.request('/upload/signed-url', {
      method: 'POST',
      body: JSON.stringify({ filename, content_type: contentType }),
    });
  }

  async uploadToSignedUrl(url: string, fileUri: string, contentType: string, onProgress?: (progress: number) => void): Promise<void> {
    // 1. Create a Blob from the URI
    const response = await fetch(fileUri);
    const blob = await response.blob();

    // 2. Upload using XHR
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', url);
      xhr.setRequestHeader('Content-Type', contentType);

      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            onProgress(event.loaded / event.total);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
        } else {
          reject(new Error(`Upload failed: ${xhr.status} ${xhr.responseText}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));
      xhr.send(blob);
    });
  }

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

  async ingestLectureWithProgress(formData: FormData, onProgress: (progress: number) => void): Promise<any> {
    // Legacy XHR method for multipart uploads (subject to 32MB limit)
    const url = `${this.baseUrl}/lectures/ingest`;
    const writeToken = process.env.EXPO_PUBLIC_WRITE_API_TOKEN;

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      if (writeToken) xhr.setRequestHeader('Authorization', `Bearer ${writeToken}`);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(event.loaded / event.total);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            resolve({});
          }
        } else {
          let detail = `HTTP ${xhr.status}`;
          try { detail = JSON.parse(xhr.responseText).detail || detail; } catch {}
          reject(new Error(detail));
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));
      xhr.ontimeout = () => reject(new Error('Upload timed out'));
      xhr.timeout = 300000; // 5 min timeout

      xhr.send(formData);
    });
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

  async getTranscript(lectureId: string): Promise<{ lectureId: string; text: string; segments: any[]; segmentCount: number }> {
    return this.request(`/lectures/${lectureId}/transcript`);
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

  async replayJob(jobId: string): Promise<any> {
    return this.request(`/jobs/${jobId}/replay`, { method: 'POST' });
  }

  async deleteLecture(lectureId: string): Promise<any> {
    return this.request(`/lectures/${lectureId}`, { method: 'DELETE' });
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

  // Chat
  async sendChatMessage(message: string, history: any[], context?: any): Promise<{ response: string }> {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history, context }),
    });
  }

  // Action Items
  async getActionItems(limit = 20, offset = 0): Promise<{ actionItems: any[] }> {
    return this.request(`/action-items?limit=${limit}&offset=${offset}`);
  }

  // LLM Completion (proxy for dice engine)
  async llmComplete(
    messages: Array<{ role: string; content: string }>,
    options?: { provider?: string; model?: string },
  ): Promise<string> {
    const result = await this.request<{ content: string }>('/api/llm/complete', {
      method: 'POST',
      body: JSON.stringify({ messages, ...options }),
    });
    return result.content;
  }
}

export default new ApiClient();
