import React, { useState } from 'react';
import { View } from 'react-native';
import { Card, Text, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../theme';
import { LECTURE_MODE_OPTIONS, LectureMode } from '../types/lectureModes';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureModeScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const [selectedMode, setSelectedMode] = useState<LectureMode>('OPEN');
  const courseId = route.params?.courseId;

  if (!courseId) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center', alignItems: 'center', padding: 20 }}>
        <Text variant="titleMedium" style={{ marginBottom: 12 }}>No course selected</Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginBottom: 20 }}>
          Please select or create a course first.
        </Text>
        <Button mode="contained" onPress={() => navigation.goBack()}>Go Back</Button>
      </View>
    );
  }

  const handleContinue = () => {
    navigation.navigate('RecordLecture', {
      courseId,
      lectureMode: selectedMode,
    });
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background, paddingHorizontal: 20, paddingTop: 24, paddingBottom: 24 }}>
      <Text variant="headlineMedium" style={{ marginBottom: 8 }}>Select Lecture Type</Text>
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 20 }}>
        Different lecture types activate different reasoning dimensions.
      </Text>

      <View style={{ gap: 12 }}>
        {LECTURE_MODE_OPTIONS.map((mode) => {
          const isSelected = selectedMode === mode.id;

          return (
            <Card
              key={mode.id}
              mode="outlined"
              onPress={() => setSelectedMode(mode.id)}
              style={isSelected ? { borderColor: theme.colors.primary, borderWidth: 2 } : undefined}
              accessibilityRole="button"
              accessibilityLabel={`Select ${mode.title}`}
            >
              <Card.Content>
                <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                  <MaterialCommunityIcons 
                    name={mode.icon as any} 
                    size={24} 
                    color={isSelected ? theme.colors.primary : theme.colors.onSurface} 
                    style={{ marginRight: 12 }} 
                  />
                  <Text variant="titleMedium" style={{ fontWeight: isSelected ? '700' : '400' }}>
                    {mode.title}
                  </Text>
                </View>
                <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, paddingLeft: 36 }}>
                  {mode.description}
                </Text>
              </Card.Content>
            </Card>
          );
        })}
      </View>

      <View style={{ marginTop: 'auto' }}>
        <Button
          mode="contained"
          onPress={handleContinue}
          contentStyle={{ paddingVertical: 8 }}
          labelStyle={{ fontSize: 16 }}
        >
          Continue to Record
        </Button>
      </View>
    </View>
  );
}
