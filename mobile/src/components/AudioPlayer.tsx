import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
  Alert,
} from 'react-native';
import { useTheme } from '../theme';

// Lazy load expo-av for native platforms only
let Audio: any = null;
if (Platform.OS !== 'web') {
  try {
    const ExpoAV = require('expo-av');
    Audio = ExpoAV.Audio;
  } catch (error) {
    console.warn('expo-av not available');
  }
}

interface Props {
  audioUrl: string;
  onTimeUpdate?: (currentTime: number) => void;
  onSegmentChange?: (segmentIndex: number) => void;
  segments?: Array<{ start: number; end: number; text: string }>;
}

export default function AudioPlayer({
  audioUrl,
  onTimeUpdate,
  onSegmentChange,
  segments = [],
}: Props) {
  const { theme } = useTheme();
  const [sound, setSound] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentSegment, setCurrentSegment] = useState(-1);
  const updateInterval = useRef<any>(null);

  useEffect(() => {
    if (Platform.OS === 'web') {
      Alert.alert('Audio Playback', 'Audio playback is only available on iOS and Android');
      return;
    }

    loadAudio();
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
      if (updateInterval.current) {
        clearInterval(updateInterval.current);
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    if (onTimeUpdate) {
      onTimeUpdate(position);
    }

    // Find current segment
    const segmentIndex = segments.findIndex(
      (seg) => position >= seg.start && position < seg.end
    );

    if (segmentIndex !== currentSegment && segmentIndex !== -1) {
      setCurrentSegment(segmentIndex);
      if (onSegmentChange) {
        onSegmentChange(segmentIndex);
      }
    }
  }, [position]);

  const loadAudio = async () => {
    if (!Audio) return;

    try {
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
      });

      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        { shouldPlay: false },
        onPlaybackStatusUpdate
      );

      setSound(newSound);
    } catch (error) {
      console.error('Error loading audio:', error);
      Alert.alert('Error', 'Failed to load audio');
    }
  };

  const onPlaybackStatusUpdate = (status: any) => {
    if (status.isLoaded) {
      setPosition(status.positionMillis / 1000);
      setDuration(status.durationMillis / 1000);
      setIsPlaying(status.isPlaying);

      if (status.didJustFinish) {
        setIsPlaying(false);
        setPosition(0);
      }
    }
  };

  const togglePlayPause = async () => {
    if (!sound) return;

    try {
      if (isPlaying) {
        await sound.pauseAsync();
      } else {
        await sound.playAsync();
      }
    } catch (error) {
      console.error('Error toggling playback:', error);
    }
  };

  const seekTo = async (seconds: number) => {
    if (!sound) return;

    try {
      await sound.setPositionAsync(seconds * 1000);
    } catch (error) {
      console.error('Error seeking:', error);
    }
  };

  const skip = async (seconds: number) => {
    const newPosition = Math.max(0, Math.min(duration, position + seconds));
    await seekTo(newPosition);
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (Platform.OS === 'web') {
    return null;
  }

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <TouchableOpacity
          style={styles.progressBar}
          onPress={(e) => {
            const { locationX } = e.nativeEvent;
            const percentage = locationX / 300; // Approximate width
            seekTo(duration * percentage);
          }}
        >
          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                { width: `${(position / duration) * 100 || 0}%` },
              ]}
            />
          </View>
        </TouchableOpacity>
        <View style={styles.timeLabels}>
          <Text style={styles.timeText}>{formatTime(position)}</Text>
          <Text style={styles.timeText}>{formatTime(duration)}</Text>
        </View>
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => skip(-15)}
        >
          <Text style={styles.controlIcon}>⏪</Text>
          <Text style={styles.controlLabel}>15s</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.playButton}
          onPress={togglePlayPause}
        >
          <Text style={styles.playIcon}>{isPlaying ? '⏸' : '▶️'}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => skip(15)}
        >
          <Text style={styles.controlIcon}>⏩</Text>
          <Text style={styles.controlLabel}>15s</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 16,
      marginVertical: 12,
    },
    progressContainer: {
      marginBottom: 16,
    },
    progressBar: {
      height: 40,
      justifyContent: 'center',
    },
    progressTrack: {
      height: 4,
      backgroundColor: theme.border,
      borderRadius: 2,
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      backgroundColor: theme.primary,
      borderRadius: 2,
    },
    timeLabels: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginTop: 8,
    },
    timeText: {
      fontSize: 12,
      color: theme.textSecondary,
      fontVariant: ['tabular-nums'],
    },
    controls: {
      flexDirection: 'row',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 24,
    },
    controlButton: {
      alignItems: 'center',
      padding: 8,
    },
    controlIcon: {
      fontSize: 24,
    },
    controlLabel: {
      fontSize: 10,
      color: theme.textSecondary,
      marginTop: 2,
    },
    playButton: {
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: theme.primary,
      justifyContent: 'center',
      alignItems: 'center',
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.3,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
      elevation: 8,
    },
    playIcon: {
      fontSize: 28,
    },
  });
