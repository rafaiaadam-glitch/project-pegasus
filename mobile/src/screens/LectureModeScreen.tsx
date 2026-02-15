import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTheme } from '../theme';
import { LECTURE_MODE_OPTIONS, LectureMode } from '../types/lectureModes';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureModeScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const [selectedMode, setSelectedMode] = useState<LectureMode>('OPEN');
  const courseId = route.params?.courseId ?? 'course-bio-101';
  const styles = createStyles(theme);

  const handleContinue = () => {
    navigation.navigate('RecordLecture', {
      courseId,
      lectureMode: selectedMode,
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select Lecture Type</Text>
      <Text style={styles.subtitle}>
        Different lecture types activate different reasoning dimensions.
      </Text>

      <View style={styles.optionsContainer}>
        {LECTURE_MODE_OPTIONS.map((mode) => {
          const isSelected = selectedMode === mode.id;

          return (
            <TouchableOpacity
              key={mode.id}
              style={[styles.optionButton, isSelected && styles.optionButtonSelected]}
              onPress={() => setSelectedMode(mode.id)}
              accessibilityRole="button"
              accessibilityLabel={`Select ${mode.title}`}
            >
              <Text style={styles.optionTitle}>
                {mode.emoji} {mode.title}
              </Text>
              <Text style={styles.optionDescription}>{mode.description}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <TouchableOpacity style={styles.continueButton} onPress={handleContinue}>
        <Text style={styles.continueButtonText}>Continue to Record</Text>
      </TouchableOpacity>
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
      paddingHorizontal: 20,
      paddingTop: 24,
      paddingBottom: 24,
    },
    title: {
      fontSize: 30,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 8,
    },
    subtitle: {
      fontSize: 14,
      color: theme.textSecondary,
      marginBottom: 20,
      lineHeight: 20,
    },
    optionsContainer: {
      gap: 12,
    },
    optionButton: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      borderWidth: 1,
      borderColor: theme.border,
    },
    optionButtonSelected: {
      borderColor: theme.primary,
      borderWidth: 2,
    },
    optionTitle: {
      color: theme.text,
      fontSize: 17,
      fontWeight: '600',
      marginBottom: 4,
    },
    optionDescription: {
      color: theme.textSecondary,
      fontSize: 13,
      lineHeight: 18,
    },
    continueButton: {
      marginTop: 'auto',
      backgroundColor: theme.primary,
      borderRadius: 12,
      paddingVertical: 14,
      alignItems: 'center',
    },
    continueButtonText: {
      color: '#fff',
      fontSize: 16,
      fontWeight: '700',
    },
  });
