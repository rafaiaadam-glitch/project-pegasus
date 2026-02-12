import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'react-native';
import CourseListScreen from './src/screens/CourseListScreen';
import LectureListScreen from './src/screens/LectureListScreen';
import LectureDetailScreen from './src/screens/LectureDetailScreen';
import RecordLectureScreen from './src/screens/RecordLectureScreen';
import FlashcardViewerScreen from './src/screens/FlashcardViewerScreen';
import ExamViewerScreen from './src/screens/ExamViewerScreen';
import { ThemeProvider, useTheme } from './src/theme';

const Stack = createNativeStackNavigator();

function AppNavigator() {
  const { theme, isDark } = useTheme();

  return (
    <>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName="CourseList"
          screenOptions={{
            headerStyle: {
              backgroundColor: theme.surface,
            },
            headerTintColor: theme.primary,
            headerTitleStyle: {
              fontWeight: '600',
              color: theme.text,
            },
            headerShadowVisible: false,
          }}
        >
          <Stack.Screen
            name="CourseList"
            component={CourseListScreen}
            options={{
              headerShown: false, // CourseList has its own header
            }}
          />
          <Stack.Screen
            name="LectureList"
            component={LectureListScreen}
            options={{
              title: 'Lectures',
            }}
          />
          <Stack.Screen
            name="LectureDetail"
            component={LectureDetailScreen}
            options={{
              title: 'Lecture Details',
            }}
          />
          <Stack.Screen
            name="RecordLecture"
            component={RecordLectureScreen}
            options={{
              title: 'Add Lecture',
              presentation: 'modal',
            }}
          />
          <Stack.Screen
            name="FlashcardViewer"
            component={FlashcardViewerScreen}
            options={{
              title: 'Flashcards',
              presentation: 'modal',
            }}
          />
          <Stack.Screen
            name="ExamViewer"
            component={ExamViewerScreen}
            options={{
              title: 'Practice Exam',
              presentation: 'modal',
            }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppNavigator />
    </ThemeProvider>
  );
}
