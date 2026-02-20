import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  ScrollView,
  Alert,
  Platform,
  Animated,
  StyleSheet,
} from 'react-native';
import {
  TextInput,
  Button,
  Chip,
  Text,
  Card,
  ActivityIndicator,
  IconButton,
  Divider,
  ProgressBar,
} from 'react-native-paper';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Preset } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';
import { getLectureModeTitle, LectureMode } from '../types/lectureModes';

interface Props {
  navigation: any;
  route: any;
}

export default function RecordLectureScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { courseId, lectureMode = 'OPEN' } = route.params as { courseId: string; lectureMode?: LectureMode };
  const lectureModeTitle = getLectureModeTitle(lectureMode);
  const [title, setTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('exam-mode');
  
  // Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [uploadAttempts, setUploadAttempts] = useState(0);

  const isWeb = Platform.OS === 'web';

  // Recording state
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [hasMicPermission, setHasMicPermission] = useState<boolean | null>(null);

  // Animation for recording indicator
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    loadPresets();
    requestAudioPermissions();

    return () => {
      if (recording) {
        recording.stopAndUnloadAsync();
      }
    };
  }, []);

  const handleRecordingStatus = (status: Audio.RecordingStatus) => {
    if (typeof status.durationMillis === 'number') {
      setRecordingDuration(Math.floor(status.durationMillis / 1000));
    }
  };

  // Pulsing animation for recording dot
  useEffect(() => {
    if (isRecording && !isPaused) {
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      );
      pulse.start();
      return () => pulse.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isRecording, isPaused]);

  const loadPresets = async () => {
    try {
      const response = await api.getPresets();
      setPresets(response.presets);
    } catch (error) {
      console.error('Error loading presets:', error);
    }
  };

  const safeStopAndUnload = async (activeRecording: Audio.Recording) => {
    try {
      const status = await activeRecording.getStatusAsync();
      if (status.isRecording || status.canRecord) {
        await activeRecording.stopAndUnloadAsync();
      }
    } catch (error) {
      console.warn('Ignoring stop/unload error:', error);
    }
  };

  const requestAudioPermissions = async (): Promise<boolean> => {
    try {
      const current = await Audio.getPermissionsAsync();
      if (current.status === 'granted') {
        setHasMicPermission(true);
        return true;
      }

      const requested = await Audio.requestPermissionsAsync();
      const granted = requested.status === 'granted';
      setHasMicPermission(granted);

      if (!granted) {
        Alert.alert('Permission Required', 'Audio recording permission is required');
      }

      return granted;
    } catch (error) {
      console.error('[Permissions] Error requesting permissions:', error);
      setHasMicPermission(false);
      return false;
    }
  };

  const startRecording = async () => {
    if (isRecording) return;

    if (isWeb) {
      Alert.alert('Recording Not Available', 'Audio recording is only available on iOS and Android devices.');
      return;
    }

    try {
      const permissionGranted = await requestAudioPermissions();
      if (!permissionGranted) {
        Alert.alert(
          'Microphone Permission Required',
          'Please enable microphone access in your device settings to record lectures.',
          [{ text: 'OK' }]
        );
        return;
      }

      if (recording) {
        await safeStopAndUnload(recording);
      }

      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
          shouldDuckAndroid: true,
          playThroughEarpieceAndroid: false,
          staysActiveInBackground: false,
        });
      } catch (audioModeError) {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
      }

      const { recording: newRecording } = await Audio.Recording.createAsync(
        {
          isMeteringEnabled: true,
          android: {
            extension: '.m4a',
            outputFormat: Audio.AndroidOutputFormat.MPEG_4,
            audioEncoder: Audio.AndroidAudioEncoder.AAC,
            sampleRate: 22050,
            numberOfChannels: 1,
            bitRate: 64000, // 64kbps is plenty for speech
          },
          ios: {
            extension: '.m4a',
            audioQuality: Audio.IOSAudioQuality.MEDIUM,
            sampleRate: 22050,
            numberOfChannels: 1,
            bitRate: 64000,
            linearPCMBitDepth: 16,
            linearPCMIsBigEndian: false,
            linearPCMIsFloat: false,
          },
          web: {
            mimeType: 'audio/webm',
            bitsPerSecond: 64000,
          },
        },
        handleRecordingStatus,
        500
      );

      setSelectedFile(null);
      setRecording(newRecording);
      setIsRecording(true);
      setRecordingDuration(0);
      setIsPaused(false);

      if (!title) {
        setTitle(`Lecture ${new Date().toLocaleDateString()}`);
      }
    } catch (error: any) {
      Alert.alert(
        'Recording Error',
        `Failed to start recording: ${error?.message || 'Unknown error'}. Please ensure microphone permissions are granted and try again.`,
        [{ text: 'OK' }]
      );
      setIsRecording(false);
      setIsPaused(false);
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
    if (!recording) return;

    try {
      const status = await recording.getStatusAsync();
      if (!status.isRecording && !status.canRecord) {
        setIsRecording(false);
        setRecording(null);
        return;
      }

      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      if (uri) {
        setSelectedFile({
          uri,
          name: `recording_${Date.now()}.m4a`,
          mimeType: 'audio/mp4',
        });
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to stop recording');
      console.error(error);
    } finally {
      try {
        await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      } catch (audioModeError) {
        console.warn('[Recording] Failed to reset audio mode:', audioModeError);
      }
      setIsRecording(false);
      setRecording(null);
    }
  };

  const discardRecording = async () => {
    if (recording) {
      await safeStopAndUnload(recording);
      setRecording(null);
    }
    setIsRecording(false);
    setRecordingDuration(0);
    setSelectedFile(null);
    setIsPaused(false);
  };

  const MAX_FILE_SIZE_MB = 200;

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['audio/*', 'application/pdf'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets[0]) {
        const file = result.assets[0];

        // Validate file extension
        const allowedExtensions = ['m4a', 'mp3', 'wav', 'aac', 'ogg', 'flac', 'mp4', 'webm', 'pdf'];
        const ext = (file.name || file.uri || '').split('.').pop()?.toLowerCase();
        if (!ext || !allowedExtensions.includes(ext)) {
          Alert.alert(
            'Unsupported File Type',
            `Please select an audio file (${allowedExtensions.filter(e => e !== 'pdf').join(', ')}) or a PDF document.`
          );
          return;
        }

        const fileSizeMB = (file.size || 0) / (1024 * 1024);

        if (fileSizeMB > MAX_FILE_SIZE_MB) {
          Alert.alert(
            'File Too Large',
            `This file is ${fileSizeMB.toFixed(0)} MB. The maximum allowed size is ${MAX_FILE_SIZE_MB} MB. Please choose a smaller file.`
          );
          return;
        }

        setSelectedFile(file);
        if (!title) {
          const filename = file.name || 'Untitled Lecture';
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

    // Pre-upload connectivity check
    try {
      await api.healthCheck();
    } catch {
      Alert.alert('No Connection', 'Unable to reach the server. Please check your internet connection and try again.');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0.05);
      setUploadStatus('Preparing upload...');

      // Get safe filename
      const fileExt = selectedFile.uri.split('.').pop() || 'm4a';
      const safeName = `upload_${Date.now()}.${fileExt}`;
      const contentType = selectedFile.mimeType || (fileExt === 'pdf' ? 'application/pdf' : 'audio/mp4');

      // 1. Get Signed URL
      const { url, storagePath } = await api.getUploadUrl(safeName, contentType);
      
      // 2. Direct Upload to GCS
      setUploadStatus('Uploading directly to cloud...');
      await api.uploadToSignedUrl(url, selectedFile.uri, contentType, (progress) => {
        setUploadProgress(progress * 0.9);
      });

      setUploadProgress(0.92);
      setUploadStatus('Processing...');

      // 3. Ingest using reference
      const lectureId = `lecture-${Date.now()}`;
      const formData = new FormData();
      formData.append('course_id', courseId);
      formData.append('lecture_id', lectureId);
      formData.append('title', title);
      formData.append('preset_id', selectedPreset);
      formData.append('lecture_mode', lectureMode);
      formData.append('auto_transcribe', 'true');
      formData.append('storage_path', storagePath); // Pass reference instead of file

      setUploadProgress(0.97);
      setUploadStatus('Finalizing...');

      const result = await api.ingestLecture(formData);

      setUploadProgress(1.0);
      setUploadStatus('Processing started!');

      const returnedId = result?.lectureId || lectureId;

      setTimeout(() => {
        navigation.replace('LectureDetail', {
          lectureId: returnedId,
          lectureTitle: title,
          courseId,
        });
      }, 1000);

    } catch (error: any) {
      setUploading(false);
      setUploadProgress(0);
      const attempt = uploadAttempts + 1;
      setUploadAttempts(attempt);

      if (error.message?.includes('Mock')) {
        Alert.alert(
          'Demo Mode',
          'This is a demo. In production, your lecture would be uploaded and processed automatically!',
          [{ text: 'OK', onPress: () => navigation.goBack() }]
        );
      } else if (attempt < 3) {
        Alert.alert(
          'Upload Failed',
          `${error.message || 'Could not upload file.'}\n\nAttempt ${attempt} of 3.`,
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Retry', onPress: () => handleUpload() },
          ]
        );
      } else {
        Alert.alert('Upload Failed', 'Maximum retry attempts reached. Please check your connection and try again later.');
        setUploadAttempts(0);
      }
      console.error(error);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getPresetIcon = (id: string) => {
    if (id.includes('exam')) return 'school';
    if (id.includes('concept')) return 'sitemap';
    if (id.includes('beginner')) return 'compass-outline';
    if (id.includes('neuro')) return 'brain';
    if (id.includes('research')) return 'flask-outline';
    if (id.includes('seminar')) return 'account-voice';
    return 'text-box-outline';
  };

  const renderPresetItem = (preset: Preset) => {
    const isSelected = selectedPreset === preset.id;
    return (
      <Card
        key={preset.id}
        mode={isSelected ? 'contained' : 'outlined'}
        style={{
          marginRight: 12,
          minWidth: 100,
          backgroundColor: isSelected ? theme.colors.primaryContainer : theme.colors.surface,
          borderColor: isSelected ? theme.colors.primary : theme.colors.outline,
        }}
        onPress={() => setSelectedPreset(preset.id)}
        disabled={isRecording || uploading}
      >
        <Card.Content style={{ alignItems: 'center', paddingVertical: 12, paddingHorizontal: 8 }}>
          <View style={{ marginBottom: 8 }}>
             <MaterialCommunityIcons 
               name={getPresetIcon(preset.id)} 
               size={24} 
               color={isSelected ? theme.colors.primary : theme.colors.onSurfaceVariant} 
             />
          </View>
          <Text 
            variant="labelMedium" 
            style={{ 
              textAlign: 'center', 
              color: isSelected ? theme.colors.onPrimaryContainer : theme.colors.onSurface 
            }}
            numberOfLines={2}
          >
            {preset.name}
          </Text>
        </Card.Content>
      </Card>
    );
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 12 }}>
        <Chip 
          icon="tag-outline" 
          onPress={() => navigation.navigate('LectureMode', { courseId })}
          style={{ backgroundColor: theme.colors.secondaryContainer }}
        >
          Lecture Type: {lectureModeTitle}
        </Chip>
        <IconButton 
          icon="pencil-outline" 
          size={16} 
          onPress={() => navigation.navigate('LectureMode', { courseId })}
          style={{ margin: 0 }}
        />
      </View>

      <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8, marginTop: 8 }}>
        LECTURE TITLE
      </Text>
      <TextInput
        mode="outlined"
        placeholder="e.g., Neural Signaling"
        value={title}
        onChangeText={setTitle}
        autoCapitalize="words"
        editable={!isRecording && !uploading}
        style={{ marginBottom: 16 }}
      />

      <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8, marginTop: 8 }}>
        STYLE PRESET
      </Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 16 }}>
        {presets.map(renderPresetItem)}
      </ScrollView>

      {/* Recording Interface */}
      {!selectedFile && !isRecording && (
        <>
          <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 12, marginTop: 8 }}>
            RECORD AUDIO
          </Text>
          {hasMicPermission === false && (
            <Text variant="bodySmall" style={{ color: theme.colors.error, marginBottom: 8 }}>
              Microphone permission is required to record audio.
            </Text>
          )}

          <Card
            style={{ marginBottom: 16 }}
            mode="outlined"
            onPress={startRecording}
            disabled={uploading}
          >
            <Card.Content style={{ alignItems: 'center', paddingVertical: 32 }}>
              <View
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: 40,
                  backgroundColor: theme.colors.errorContainer,
                  justifyContent: 'center',
                  alignItems: 'center',
                  marginBottom: 16,
                }}
              >
                <MaterialCommunityIcons name="microphone" size={40} color={theme.colors.error} />
              </View>
              <Text variant="titleMedium" style={{ color: theme.colors.error }}>
                Tap to Start Recording
              </Text>
            </Card.Content>
          </Card>

          <View style={{ flexDirection: 'row', alignItems: 'center', marginVertical: 16 }}>
            <Divider style={{ flex: 1 }} />
            <Text variant="labelMedium" style={{ marginHorizontal: 16, color: theme.colors.onSurfaceVariant }}>
              OR
            </Text>
            <Divider style={{ flex: 1 }} />
          </View>

          <Card
            style={{ marginBottom: 16 }}
            mode="outlined"
            onPress={handlePickFile}
            disabled={uploading}
          >
            <Card.Title
              title="Upload Audio or PDF Notes"
              subtitle="Browse your files"
              left={(props) => <MaterialCommunityIcons name="folder-open-outline" size={32} color={theme.colors.primary} style={{ marginHorizontal: 8 }} />}
            />
          </Card>
        </>
      )}

      {/* Active Recording */}
      {isRecording && (
        <Card style={{ marginTop: 16 }} mode="elevated">
          <Card.Content style={{ paddingVertical: 24 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                <Animated.View
                  style={[
                    {
                      width: 12,
                      height: 12,
                      borderRadius: 6,
                      backgroundColor: isPaused ? theme.colors.tertiary : theme.colors.error,
                      marginRight: 8,
                    },
                    !isPaused && { transform: [{ scale: pulseAnim }] },
                  ]}
                />
                <Text variant="titleMedium" style={{ color: isPaused ? theme.colors.tertiary : theme.colors.error }}>
                  {isPaused ? 'Paused' : 'Recording'}
                </Text>
              </View>
              <Text variant="headlineSmall" style={{ fontVariant: ['tabular-nums'] }}>
                {formatDuration(recordingDuration)}
              </Text>
            </View>

            <View
              style={{
                height: 100,
                backgroundColor: theme.colors.surfaceVariant,
                borderRadius: 12,
                justifyContent: 'center',
                alignItems: 'center',
                marginBottom: 24,
                ...(isPaused && {
                  borderWidth: 2,
                  borderColor: theme.colors.tertiary,
                  borderStyle: 'dashed' as const,
                }),
              }}
            >
              <MaterialCommunityIcons 
                name={isPaused ? 'pause' : 'microphone'} 
                size={40} 
                color={theme.colors.onSurfaceVariant} 
              />
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 8 }}>
                {isPaused ? 'Recording paused' : 'Recording in progress...'}
              </Text>
            </View>

            <View style={{ flexDirection: 'row', justifyContent: 'space-around' }}>
              <Button mode="text" onPress={discardRecording} icon="close" textColor={theme.colors.error}>
                Cancel
              </Button>
              <Button
                mode="text"
                onPress={isPaused ? resumeRecording : pauseRecording}
                icon={isPaused ? 'play' : 'pause'}
              >
                {isPaused ? 'Resume' : 'Pause'}
              </Button>
              <Button mode="text" onPress={stopRecording} icon="stop">
                Done
              </Button>
            </View>
          </Card.Content>
        </Card>
      )}

      {/* Selected File & Upload Progress */}
      {selectedFile && !isRecording && (
        <Card style={{ marginTop: 16 }} mode="elevated">
          <Card.Title
            title={selectedFile.name}
            subtitle={
              selectedFile.size
                ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB${
                    selectedFile.mimeType !== 'application/pdf' && !selectedFile.name?.toLowerCase().endsWith('.pdf')
                      ? ` • ${formatDuration(recordingDuration || 0)}`
                      : ''
                  }`
                : undefined
            }
            left={() => (
              <MaterialCommunityIcons
                name={selectedFile.mimeType === 'application/pdf' || selectedFile.name?.toLowerCase().endsWith('.pdf') ? 'file-document-outline' : 'file-music-outline'}
                size={32}
                color={theme.colors.primary}
                style={{ marginHorizontal: 8 }}
              />
            )}
            right={() => (
              !uploading ? <IconButton icon="close" onPress={discardRecording} /> : null
            )}
          />
          {selectedFile.size && (selectedFile.size / 1024 / 1024) > 50 && (
            <Card.Content style={{ paddingTop: 0, paddingBottom: 8 }}>
              <Chip
                compact
                icon="alert-outline"
                style={{ alignSelf: 'flex-start', backgroundColor: theme.colors.tertiaryContainer }}
                textStyle={{ color: theme.colors.onTertiaryContainer, fontSize: 12 }}
              >
                Large file — upload may take longer
              </Chip>
            </Card.Content>
          )}
          {uploading && (
            <Card.Content>
              <ProgressBar progress={uploadProgress} color={theme.colors.primary} style={{ height: 8, borderRadius: 4, marginVertical: 12 }} />
              <Text style={{ textAlign: 'center', color: theme.colors.onSurfaceVariant }}>{uploadStatus}</Text>
              <Button
                mode="text"
                onPress={() => {
                  setUploading(false);
                  setUploadProgress(0);
                  setUploadStatus('');
                }}
                textColor={theme.colors.error}
                style={{ marginTop: 8 }}
              >
                Cancel Upload
              </Button>
            </Card.Content>
          )}
        </Card>
      )}

      {selectedFile && !isRecording && !uploading && (
        <Button
          mode="contained"
          onPress={handleUpload}
          icon="upload"
          style={{ marginTop: 16 }}
          contentStyle={{ paddingVertical: 8 }}
        >
          Upload & Process Lecture
        </Button>
      )}

      {!isRecording && !uploading && (
        <Text
          variant="bodySmall"
          style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginTop: 16 }}
        >
          After uploading, the lecture will be transcribed and processed automatically with
          your selected preset.
        </Text>
      )}
    </ScrollView>
  );
}
