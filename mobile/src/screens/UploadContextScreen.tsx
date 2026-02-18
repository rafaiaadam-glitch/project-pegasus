import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import { API_URL } from '../config';

type FileTag = 'SYLLABUS' | 'NOTES';

type UploadedFile = {
  id: string;
  name: string;
  size: number;
  type: string;
  tag: FileTag;
  status: 'idle' | 'uploading' | 'done' | 'error';
  error?: string;
};

const MAX_MB = 30;
const MAX_BYTES = MAX_MB * 1024 * 1024;

function prettyBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export default function UploadContextScreen({ route, navigation }: any) {
  const { courseId, courseTitle } = route.params || {};

  const [items, setItems] = useState<UploadedFile[]>([]);
  const [selectedTag, setSelectedTag] = useState<FileTag>('SYLLABUS');

  const pickAndUploadFiles = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'text/plain', 'text/markdown',
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        multiple: true,
        copyToCacheDirectory: true,
      });

      if (result.canceled) return;

      const files = result.assets || [];
      if (files.length === 0) return;

      // Validate file sizes
      const tooBig = files.find(f => f.size && f.size > MAX_BYTES);
      if (tooBig) {
        Alert.alert('File Too Large', `Maximum file size is ${MAX_MB}MB: ${tooBig.name}`);
        return;
      }

      // Add to UI list as "uploading"
      const temp: UploadedFile[] = files.map(f => ({
        id: `temp-${Date.now()}-${Math.random()}`,
        name: f.name,
        size: f.size || 0,
        type: f.mimeType || 'unknown',
        tag: selectedTag,
        status: 'uploading',
      }));

      setItems(prev => [...temp, ...prev]);

      // Upload files
      const formData = new FormData();
      formData.append('tag', selectedTag);
      formData.append('course_id', courseId || 'default');

      files.forEach((file) => {
        formData.append('files', {
          uri: file.uri,
          name: file.name,
          type: file.mimeType || 'application/octet-stream',
        } as any);
      });

      const response = await fetch(`${API_URL}/context/upload`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      const uploaded = data.uploaded || [];

      // Mark files as done
      setItems(prev =>
        prev.map(item => {
          if (item.status !== 'uploading') return item;
          const match = uploaded.find((u: any) => u.name === item.name);
          return match ? { ...item, id: match.id, status: 'done' } : item;
        })
      );

      Alert.alert('Success', `Uploaded ${uploaded.length} file(s) successfully!`);
    } catch (error: any) {
      console.error('Upload error:', error);

      // Mark uploading files as error
      setItems(prev =>
        prev.map(item =>
          item.status === 'uploading'
            ? { ...item, status: 'error', error: error.message || 'Upload failed' }
            : item
        )
      );

      Alert.alert('Upload Failed', error.message || 'Could not upload files');
    }
  };

  const totals = {
    done: items.filter(i => i.status === 'done').length,
    uploading: items.filter(i => i.status === 'uploading').length,
    total: items.length,
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Upload Context Files</Text>
        <Text style={styles.subtitle}>
          {courseTitle || 'Course files'}
        </Text>
        <Text style={styles.description}>
          Add your syllabus and notes. Pegasus will use them to enhance thread detection
          and generate better study materials.
        </Text>
      </View>

      <View style={styles.controls}>
        <View style={styles.tagSelector}>
          <TouchableOpacity
            style={[
              styles.tagButton,
              selectedTag === 'SYLLABUS' && styles.tagButtonActive,
            ]}
            onPress={() => setSelectedTag('SYLLABUS')}
          >
            <Text
              style={[
                styles.tagButtonText,
                selectedTag === 'SYLLABUS' && styles.tagButtonTextActive,
              ]}
            >
              📋 Syllabus
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.tagButton,
              selectedTag === 'NOTES' && styles.tagButtonActive,
            ]}
            onPress={() => setSelectedTag('NOTES')}
          >
            <Text
              style={[
                styles.tagButtonText,
                selectedTag === 'NOTES' && styles.tagButtonTextActive,
              ]}
            >
              📝 Notes
            </Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.uploadButton} onPress={pickAndUploadFiles}>
          <Text style={styles.uploadButtonText}>📤 Choose Files</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.info}>
        <Text style={styles.infoText}>
          Allowed: PDF, DOCX, TXT, MD • Max {MAX_MB}MB per file
        </Text>
        <Text style={styles.infoText}>
          Uploaded: {totals.done}/{totals.total}
        </Text>
      </View>

      <View style={styles.fileList}>
        {items.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>
              No files yet. Upload your syllabus first, then any notes/readings.
            </Text>
          </View>
        ) : (
          items.map((file, index) => (
            <View key={`${file.id}-${index}`} style={styles.fileItem}>
              <View style={styles.fileInfo}>
                <Text style={styles.fileName} numberOfLines={1}>
                  {file.name}
                </Text>
                <Text style={styles.fileDetails}>
                  {file.tag} • {prettyBytes(file.size)}
                </Text>
              </View>

              <View style={styles.fileStatus}>
                {file.status === 'uploading' && (
                  <ActivityIndicator size="small" color="#007AFF" />
                )}
                {file.status === 'done' && (
                  <Text style={styles.statusDone}>✅</Text>
                )}
                {file.status === 'error' && (
                  <Text style={styles.statusError}>❌</Text>
                )}
              </View>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    padding: 20,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 12,
  },
  description: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    gap: 12,
  },
  tagSelector: {
    flexDirection: 'row',
    gap: 8,
    flex: 1,
  },
  tagButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: 'white',
  },
  tagButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  tagButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  tagButtonTextActive: {
    color: 'white',
  },
  uploadButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#007AFF',
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  info: {
    padding: 16,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  infoText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  fileList: {
    padding: 16,
    gap: 12,
  },
  emptyState: {
    padding: 32,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#ddd',
    borderStyle: 'dashed',
    backgroundColor: 'white',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
  },
  fileItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    gap: 12,
  },
  fileInfo: {
    flex: 1,
    minWidth: 0,
  },
  fileName: {
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 4,
  },
  fileDetails: {
    fontSize: 12,
    color: '#666',
  },
  fileStatus: {
    minWidth: 30,
    alignItems: 'center',
  },
  statusDone: {
    fontSize: 18,
  },
  statusError: {
    fontSize: 18,
  },
});
