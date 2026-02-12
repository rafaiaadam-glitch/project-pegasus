import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import { Preset } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

export default function RecordLectureScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { courseId } = route.params;
  const [title, setTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('exam-mode');
  const [uploading, setUploading] = useState(false);

  const isWeb = Platform.OS === 'web';

  // Recording state
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    loadPresets();
    requestAudioPermissions();

    return () => {
      if (recording) {
        recording.stopAndUnloadAsync();
      }
    };
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording && !isPaused) {
      interval = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording, isPaused]);

  const loadPresets = async () => {
    try {
      const response = await api.getPresets();
      setPresets(response.presets);
    } catch (error) {
      console.error('Error loading presets:', error);
    }
  };

  const requestAudioPermissions = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Audio recording permission is required');
      }
    } catch (error) {
      console.error('Error requesting permissions:', error);
    }
  };

  const startRecording = async () => {
    if (isWeb) {
      Alert.alert(
        'Recording Not Available',
        'Audio recording is only available on iOS and Android devices.'
      );
      return;
    }

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      setRecording(newRecording);
      setIsRecording(true);
      setRecordingDuration(0);
      setIsPaused(false);

      if (!title) {
        setTitle(`Lecture ${new Date().toLocaleDateString()}`);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to start recording');
      console.error(error);
    }
  };

  const pauseRecording = async () => {
    if (recording) {
      try {
        await recording.pauseAsync();
        setIsPaused(true);
      } catch (error) {
        console.error('Error pausing recording:', error);
      }
    }
  };

  const resumeRecording = async () => {
    if (recording) {
      try {
        await recording.startAsync();
        setIsPaused(false);
      } catch (error) {
        console.error('Error resuming recording:', error);
      }
    }
  };

  const stopRecording = async () => {
    if (recording) {
      try {
        await recording.stopAndUnloadAsync();
        const uri = recording.getURI();

        setSelectedFile({
          uri,
          name: `recording_${Date.now()}.m4a`,
          mimeType: 'audio/m4a',
        });

        setIsRecording(false);
        setRecording(null);
      } catch (error) {
        Alert.alert('Error', 'Failed to stop recording');
        console.error(error);
      }
    }
  };

  const discardRecording = () => {
    if (recording) {
      recording.stopAndUnloadAsync();
      setRecording(null);
    }
    setIsRecording(false);
    setRecordingDuration(0);
    setSelectedFile(null);
    setIsPaused(false);
  };

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'audio/*',
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets[0]) {
        setSelectedFile(result.assets[0]);
        if (!title) {
          const filename = result.assets[0].name || 'Untitled Lecture';
          setTitle(filename.replace(/\.[^/.]+$/, ''));
        }
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to pick file');
      console.error(error);
    }
  };

  const handleUpload = async () => {
    if (!title.trim()) {
      Alert.alert('Error', 'Please enter a lecture title');
      return;
    }

    if (!selectedFile) {
      Alert.alert('Error', 'Please record or select an audio file');
      return;
    }

    try {
      setUploading(true);

      const formData = new FormData();
      formData.append('file', {
        uri: selectedFile.uri,
        type: selectedFile.mimeType || 'audio/m4a',
        name: selectedFile.name,
      } as any);
      formData.append('course_id', courseId);
      formData.append('title', title);
      formData.append('preset_id', selectedPreset);

      const result = await api.ingestLecture(formData);

      Alert.alert('Success', 'Lecture uploaded successfully!', [
        {
          text: 'OK',
          onPress: () => navigation.goBack(),
        },
      ]);
    } catch (error: any) {
      if (error.message?.includes('Mock')) {
        Alert.alert(
          'Demo Mode',
          'This is a demo. In production, your lecture would be uploaded and processed automatically!',
          [{ text: 'OK', onPress: () => navigation.goBack() }]
        );
      } else {
        Alert.alert('Error', 'Failed to upload. Make sure the backend is running.');
      }
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const styles = createStyles(theme);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.sectionTitle}>Lecture Title</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g., Neural Signaling"
        value={title}
        onChangeText={setTitle}
        autoCapitalize="words"
        editable={!isRecording}
      />

      <Text style={styles.sectionTitle}>Style Preset</Text>
      <View style={styles.presetContainer}>
        {presets.map((preset) => (
          <TouchableOpacity
            key={preset.id}
            style={[
              styles.presetBadge,
              selectedPreset === preset.id && styles.presetBadgeActive,
            ]}
            onPress={() => setSelectedPreset(preset.id)}
            disabled={isRecording}
          >
            <Text
              style={[
                styles.presetText,
                selectedPreset === preset.id && styles.presetTextActive,
              ]}
            >
              {preset.name}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Recording Interface */}
      {!selectedFile && !isRecording && (
        <>
          <Text style={styles.sectionTitle}>Record Audio</Text>
          <TouchableOpacity style={styles.recordStartButton} onPress={startRecording}>
            <View style={styles.recordIconLarge}>
              <View style={styles.recordIconInner} />
            </View>
            <Text style={styles.recordStartText}>Tap to Start Recording</Text>
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity style={styles.filePickerButton} onPress={handlePickFile}>
            <Text style={styles.filePickerIcon}>📁</Text>
            <View style={styles.filePickerContent}>
              <Text style={styles.filePickerTitle}>Upload Audio File</Text>
              <Text style={styles.filePickerSubtitle}>Browse your files</Text>
            </View>
          </TouchableOpacity>
        </>
      )}

      {/* Active Recording */}
      {isRecording && (
        <View style={styles.recordingPanel}>
          <View style={styles.recordingHeader}>
            <View style={styles.recordingIndicator}>
              <View style={styles.recordingDot} />
              <Text style={styles.recordingText}>
                {isPaused ? 'Paused' : 'Recording'}
              </Text>
            </View>
            <Text style={styles.durationText}>{formatDuration(recordingDuration)}</Text>
          </View>

          <View style={styles.waveformPlaceholder}>
            <Text style={styles.waveformText}>🎙️ Audio Waveform</Text>
          </View>

          <View style={styles.recordingControls}>
            <TouchableOpacity style={styles.controlButton} onPress={discardRecording}>
              <Text style={styles.controlButtonText}>✕</Text>
              <Text style={styles.controlLabel}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.controlButton, styles.pauseButton]}
              onPress={isPaused ? resumeRecording : pauseRecording}
            >
              <Text style={styles.controlButtonText}>{isPaused ? '▶' : '⏸'}</Text>
              <Text style={styles.controlLabel}>{isPaused ? 'Resume' : 'Pause'}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.controlButton, styles.stopButton]}
              onPress={stopRecording}
            >
              <Text style={styles.controlButtonText}>⏹</Text>
              <Text style={styles.controlLabel}>Done</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Selected File */}
      {selectedFile && !isRecording && (
        <View style={styles.selectedFilePanel}>
          <View style={styles.fileHeader}>
            <Text style={styles.fileIcon}>🎵</Text>
            <View style={styles.fileInfo}>
              <Text style={styles.fileName}>{selectedFile.name}</Text>
              {selectedFile.size && (
                <Text style={styles.fileSize}>
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB •{' '}
                  {formatDuration(recordingDuration || 0)}
                </Text>
              )}
            </View>
            <TouchableOpacity onPress={discardRecording}>
              <Text style={styles.removeButton}>✕</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {selectedFile && !isRecording && (
        <TouchableOpacity
          style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
          onPress={handleUpload}
          disabled={uploading}
        >
          {uploading ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.uploadButtonText}>Upload & Process Lecture</Text>
          )}
        </TouchableOpacity>
      )}

      {!isRecording && (
        <Text style={styles.hint}>
          After uploading, the lecture will be transcribed and processed automatically with
          your selected preset.
        </Text>
      )}
    </ScrollView>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    content: {
      padding: 20,
      paddingBottom: 40,
    },
    sectionTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.textTertiary,
      textTransform: 'uppercase',
      marginBottom: 12,
      marginTop: 24,
    },
    input: {
      backgroundColor: theme.surface,
      padding: 16,
      borderRadius: 12,
      fontSize: 16,
      color: theme.text,
      borderWidth: 1,
      borderColor: theme.border,
    },
  presetContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  presetBadge: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
  },
  presetBadgeActive: {
    backgroundColor: theme.primary,
    borderColor: theme.primary,
  },
  presetText: {
    fontSize: 14,
    color: theme.primary,
    fontWeight: '500',
  },
  presetTextActive: {
    color: '#FFF',
  },
  recordStartButton: {
    backgroundColor: theme.surface,
    padding: 40,
    borderRadius: 20,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.error,
    borderStyle: 'dashed',
  },
  recordIconLarge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: theme.surface,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: theme.shadowColor,
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
    marginBottom: 16,
  },
  recordIconInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: theme.error,
  },
  recordStartText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.error,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 24,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: theme.border,
  },
  dividerText: {
    marginHorizontal: 16,
    fontSize: 13,
    color: theme.textTertiary,
    fontWeight: '600',
  },
  filePickerButton: {
    backgroundColor: theme.surface,
    padding: 20,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.border,
    borderStyle: 'dashed',
  },
  filePickerIcon: {
    fontSize: 32,
    marginRight: 16,
  },
  filePickerContent: {
    flex: 1,
  },
  filePickerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 4,
  },
  filePickerSubtitle: {
    fontSize: 13,
    color: theme.textTertiary,
  },
  recordingPanel: {
    backgroundColor: theme.surface,
    borderRadius: 20,
    padding: 24,
    marginTop: 24,
  },
  recordingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  recordingDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#FF3B30',
    marginRight: 8,
  },
  recordingText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FF3B30',
  },
  durationText: {
    fontSize: 24,
    fontWeight: '700',
    color: theme.text,
    fontVariant: ['tabular-nums'],
  },
  waveformPlaceholder: {
    height: 100,
    backgroundColor: theme.inputBackground,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  waveformText: {
    fontSize: 16,
    color: theme.textTertiary,
  },
  recordingControls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  controlButton: {
    alignItems: 'center',
  },
  pauseButton: {},
  stopButton: {},
  controlButtonText: {
    fontSize: 32,
    marginBottom: 8,
  },
  controlLabel: {
    fontSize: 13,
    color: theme.textTertiary,
    fontWeight: '500',
  },
  selectedFilePanel: {
    backgroundColor: theme.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 24,
  },
  fileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  fileIcon: {
    fontSize: 32,
    marginRight: 12,
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 15,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 4,
  },
  fileSize: {
    fontSize: 13,
    color: theme.textTertiary,
  },
  removeButton: {
    fontSize: 24,
    color: theme.textTertiary,
    padding: 8,
  },
  uploadButton: {
    backgroundColor: theme.primary,
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 24,
  },
  uploadButtonDisabled: {
    opacity: 0.6,
  },
  uploadButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
  hint: {
    fontSize: 13,
    color: theme.textTertiary,
    textAlign: 'center',
    marginTop: 16,
    lineHeight: 20,
  },
  });
