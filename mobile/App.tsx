import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'react-native';
import HomeScreen from './src/screens/HomeScreen';
import CourseListScreen from './src/screens/CourseListScreen';
import LectureListScreen from './src/screens/LectureListScreen';
import LectureDetailScreen from './src/screens/LectureDetailScreen';
import RecordLectureScreen from './src/screens/RecordLectureScreen';
import LectureModeScreen from './src/screens/LectureModeScreen';
import FlashcardViewerScreen from './src/screens/FlashcardViewerScreen';
import ExamViewerScreen from './src/screens/ExamViewerScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import SearchScreen from './src/screens/SearchScreen';
import FavoritesScreen from './src/screens/FavoritesScreen';
import StatisticsScreen from './src/screens/StatisticsScreen';
import DownloadsScreen from './src/screens/DownloadsScreen';
import GestureSettingsScreen from './src/screens/GestureSettingsScreen';
import WidgetsScreen from './src/screens/WidgetsScreen';
import { ThemeProvider, useTheme } from './src/theme';

const Stack = createNativeStackNavigator();

function AppNavigator() {
  const { theme, isDark } = useTheme();

  return (
    <>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName="Home"
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
            name="Home"
            component={HomeScreen}
            options={{
              headerShown: false,
            }}
          />
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
            name="LectureMode"
            component={LectureModeScreen}
            options={{
              title: 'Select Lecture Type',
              presentation: 'modal',
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
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{
              title: 'Settings',
            }}
          />
          <Stack.Screen
            name="Search"
            component={SearchScreen}
            options={{
              title: 'Search',
            }}
          />
          <Stack.Screen
            name="Favorites"
            component={FavoritesScreen}
            options={{
              title: 'Favorites',
            }}
          />
          <Stack.Screen
            name="Statistics"
            component={StatisticsScreen}
            options={{
              title: 'Statistics',
            }}
          />
          <Stack.Screen
            name="Downloads"
            component={DownloadsScreen}
            options={{
              title: 'Downloads',
            }}
          />
          <Stack.Screen
            name="GestureSettings"
            component={GestureSettingsScreen}
            options={{
              title: 'Gesture Controls',
            }}
          />
          <Stack.Screen
            name="Widgets"
            component={WidgetsScreen}
            options={{
              title: 'Widgets',
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
