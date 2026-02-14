import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import { Lecture } from '../types';
import api from './api';

const OFFLINE_DATA_KEY = 'pegasus_offline_data';
const DOWNLOAD_QUEUE_KEY = 'pegasus_download_queue';

export interface DownloadedLecture {
  lectureId: string;
  lectureData: Lecture;
  audioPath?: string;
  transcriptPath?: string;
  artifactsPath?: string;
  downloadedAt: string;
  size: number; // bytes
}

export interface DownloadProgress {
  lectureId: string;
  status: 'queued' | 'downloading' | 'completed' | 'failed';
  progress: number; // 0-100
  totalBytes: number;
  downloadedBytes: number;
  error?: string;
}

// Get offline storage directory
const getOfflineDir = () => {
  return `${FileSystem.documentDirectory}offline/`;
};

// Initialize offline storage
export const initOfflineStorage = async (): Promise<void> => {
  try {
    const dir = getOfflineDir();
    const dirInfo = await FileSystem.getInfoAsync(dir);

    if (!dirInfo.exists) {
      await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
    }
  } catch (error) {
    console.error('Error initializing offline storage:', error);
  }
};

// Get all downloaded lectures
export const getDownloadedLectures = async (): Promise<DownloadedLecture[]> => {
  try {
    const data = await AsyncStorage.getItem(OFFLINE_DATA_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Error getting downloaded lectures:', error);
    return [];
  }
};

// Check if lecture is downloaded
export const isLectureDownloaded = async (lectureId: string): Promise<boolean> => {
  const downloaded = await getDownloadedLectures();
  return downloaded.some(l => l.lectureId === lectureId);
};

// Get downloaded lecture
export const getDownloadedLecture = async (lectureId: string): Promise<DownloadedLecture | null> => {
  const downloaded = await getDownloadedLectures();
  return downloaded.find(l => l.lectureId === lectureId) || null;
};

// Download lecture
export const downloadLecture = async (
  lecture: Lecture,
  onProgress?: (progress: DownloadProgress) => void
): Promise<void> => {
  await initOfflineStorage();

  const lectureDir = `${getOfflineDir()}${lecture.id}/`;
  const progress: DownloadProgress = {
    lectureId: lecture.id,
    status: 'downloading',
    progress: 0,
    totalBytes: 0,
    downloadedBytes: 0,
  };

  try {
    // Create lecture directory
    await FileSystem.makeDirectoryAsync(lectureDir, { intermediates: true });

    // Download audio if available
    let audioPath: string | undefined;
    if (lecture.audio_url) {
      progress.status = 'downloading';
      progress.progress = 10;
      if (onProgress) onProgress(progress);

      const audioDestination = `${lectureDir}audio.mp3`;
      const downloadResult = await FileSystem.downloadAsync(
        lecture.audio_url,
        audioDestination
      );
      audioPath = downloadResult.uri;
    }

    // Download transcript
    progress.progress = 40;
    if (onProgress) onProgress(progress);

    let transcriptPath: string | undefined;
    try {
      const transcript = await api.getLectureDetail(lecture.id);
      const transcriptDestination = `${lectureDir}transcript.json`;
      await FileSystem.writeAsStringAsync(
        transcriptDestination,
        JSON.stringify(transcript)
      );
      transcriptPath = transcriptDestination;
    } catch (error) {
      console.warn('Could not download transcript:', error);
    }

    // Download artifacts
    progress.progress = 70;
    if (onProgress) onProgress(progress);

    let artifactsPath: string | undefined;
    try {
      const artifacts = await api.getLectureArtifacts(lecture.id);
      const artifactsDestination = `${lectureDir}artifacts.json`;
      await FileSystem.writeAsStringAsync(
        artifactsDestination,
        JSON.stringify(artifacts)
      );
      artifactsPath = artifactsDestination;
    } catch (error) {
      console.warn('Could not download artifacts:', error);
    }

    // Calculate total size
    const dirInfo = await FileSystem.getInfoAsync(lectureDir);
    const size = dirInfo.exists && 'size' in dirInfo ? dirInfo.size || 0 : 0;

    // Save to offline data
    const downloadedLecture: DownloadedLecture = {
      lectureId: lecture.id,
      lectureData: lecture,
      audioPath,
      transcriptPath,
      artifactsPath,
      downloadedAt: new Date().toISOString(),
      size,
    };

    const downloaded = await getDownloadedLectures();
    const index = downloaded.findIndex(l => l.lectureId === lecture.id);

    if (index > -1) {
      downloaded[index] = downloadedLecture;
    } else {
      downloaded.push(downloadedLecture);
    }

    await AsyncStorage.setItem(OFFLINE_DATA_KEY, JSON.stringify(downloaded));

    progress.status = 'completed';
    progress.progress = 100;
    if (onProgress) onProgress(progress);
  } catch (error) {
    console.error('Error downloading lecture:', error);
    progress.status = 'failed';
    progress.error = error instanceof Error ? error.message : 'Download failed';
    if (onProgress) onProgress(progress);
    throw error;
  }
};

// Delete downloaded lecture
export const deleteDownloadedLecture = async (lectureId: string): Promise<void> => {
  try {
    const lectureDir = `${getOfflineDir()}${lectureId}/`;
    const dirInfo = await FileSystem.getInfoAsync(lectureDir);

    if (dirInfo.exists) {
      await FileSystem.deleteAsync(lectureDir, { idempotent: true });
    }

    const downloaded = await getDownloadedLectures();
    const filtered = downloaded.filter(l => l.lectureId !== lectureId);
    await AsyncStorage.setItem(OFFLINE_DATA_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Error deleting downloaded lecture:', error);
    throw error;
  }
};

// Get total offline storage size
export const getOfflineStorageSize = async (): Promise<number> => {
  try {
    const downloaded = await getDownloadedLectures();
    return downloaded.reduce((total, lecture) => total + lecture.size, 0);
  } catch (error) {
    console.error('Error getting storage size:', error);
    return 0;
  }
};

// Format bytes to human readable
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

// Clear all offline data
export const clearAllOfflineData = async (): Promise<void> => {
  try {
    const dir = getOfflineDir();
    const dirInfo = await FileSystem.getInfoAsync(dir);

    if (dirInfo.exists) {
      await FileSystem.deleteAsync(dir, { idempotent: true });
    }

    await AsyncStorage.removeItem(OFFLINE_DATA_KEY);
    await AsyncStorage.removeItem(DOWNLOAD_QUEUE_KEY);
  } catch (error) {
    console.error('Error clearing offline data:', error);
    throw error;
  }
};

// Check network connectivity
export const isOnline = async (): Promise<boolean> => {
  try {
    // Simple network check - try to fetch from API
    const response = await fetch('https://www.google.com', {
      method: 'HEAD',
      cache: 'no-cache'
    });
    return response.ok;
  } catch {
    return false;
  }
};
