import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  ScrollView,
  Alert,
  Platform,
  Animated,
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
} from 'react-native-paper';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
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
  const [uploading, setUploading] = useState(false);

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
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
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

  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['audio/*', 'application/pdf'],
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

      const lectureId = `lecture-${Date.now()}`;
      const formData = new FormData();
      const audioPayload = {
        uri: selectedFile.uri,
        type: selectedFile.mimeType || 'audio/m4a',
        name: selectedFile.name,
      } as any;

      formData.append('audio', audioPayload);
      formData.append('file', audioPayload);
      formData.append('course_id', courseId);
      formData.append('lecture_id', lectureId);
      formData.append('title', title);
      formData.append('preset_id', selectedPreset);
      formData.append('lecture_mode', lectureMode);
      formData.append('auto_transcribe', 'true');

      const result = await api.ingestLecture(formData);
      const returnedId = result?.lectureId || lectureId;

      navigation.replace('LectureDetail', {
        lectureId: returnedId,
        lectureTitle: title,
        courseId,
      });
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

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
    >
      <Chip icon="tag-outline" style={{ alignSelf: 'flex-start', marginBottom: 12 }}>
        Lecture Type: {lectureModeTitle}
      </Chip>

      <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8, marginTop: 8 }}>
        LECTURE TITLE
      </Text>
      <TextInput
        mode="outlined"
        placeholder="e.g., Neural Signaling"
        value={title}
        onChangeText={setTitle}
        autoCapitalize="words"
        editable={!isRecording}
        style={{ marginBottom: 16 }}
      />

      <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8, marginTop: 8 }}>
        STYLE PRESET
      </Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
        {presets.map((preset) => (
          <Chip
            key={preset.id}
            selected={selectedPreset === preset.id}
            onPress={() => setSelectedPreset(preset.id)}
            disabled={isRecording}
            showSelectedOverlay
          >
            {preset.name}
          </Chip>
        ))}
      </View>

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
                <View
                  style={{
                    width: 60,
                    height: 60,
                    borderRadius: 30,
                    backgroundColor: theme.colors.error,
                  }}
                />
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
          >
            <Card.Title
              title="Upload Audio or PDF Notes"
              subtitle="Browse your files"
              left={(props) => <Text {...props} style={{ fontSize: 32 }}>📁</Text>}
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
              <Text style={{ fontSize: 16 }}>{isPaused ? '⏸️' : '🎙️'}</Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
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

      {/* Selected File */}
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
              <Text style={{ fontSize: 32 }}>
                {selectedFile.mimeType === 'application/pdf' || selectedFile.name?.toLowerCase().endsWith('.pdf') ? '📄' : '🎵'}
              </Text>
            )}
            right={() => (
              <IconButton icon="close" onPress={discardRecording} />
            )}
          />
        </Card>
      )}

      {selectedFile && !isRecording && (
        <Button
          mode="contained"
          onPress={handleUpload}
          disabled={uploading}
          loading={uploading}
          icon="upload"
          style={{ marginTop: 16 }}
          contentStyle={{ paddingVertical: 8 }}
        >
          Upload & Process Lecture
        </Button>
      )}

      {!isRecording && (
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
