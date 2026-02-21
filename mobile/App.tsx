import React, { useState, useEffect, useCallback } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar, ActivityIndicator, View } from 'react-native';
import { PaperProvider } from 'react-native-paper';
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
import ThreadsScreen from './src/screens/ThreadsScreen';
import ThreadDetailScreen from './src/screens/ThreadDetailScreen';
import ChatScreen from './src/screens/ChatScreen';
import SummaryViewerScreen from './src/screens/SummaryViewerScreen';
import OutlineViewerScreen from './src/screens/OutlineViewerScreen';
import KeyTermsViewerScreen from './src/screens/KeyTermsViewerScreen';
import PurchaseTokensScreen from './src/screens/PurchaseTokensScreen';
import { ThemeProvider, useTheme } from './src/theme';
import ErrorBoundary from './src/components/ErrorBoundary';
import AuthScreen from './src/screens/AuthScreen';
import { isAuthenticated } from './src/services/auth';
import api from './src/services/api';
import { initializePurchases, destroyPurchases } from './src/services/purchases';

// Configure Google Sign-In — guarded because the native module is only
// available in a custom dev client build (not Expo Go).
try {
  const { GoogleSignin } = require('@react-native-google-signin/google-signin');
  GoogleSignin.configure({
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
  });
} catch {
  // Native module not available (running in Expo Go) — Google Sign-In disabled
}

const Stack = createNativeStackNavigator();

function AppStack() {
  const { theme } = useTheme();
  return (
    <Stack.Navigator
      id={undefined}
      initialRouteName="Home"
      screenOptions={{
        headerStyle: {
          backgroundColor: theme.colors.surface,
        },
        headerTintColor: theme.colors.primary,
        headerTitleStyle: {
          fontWeight: '600',
          color: theme.colors.text,
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
      <Stack.Screen
        name="Threads"
        component={ThreadsScreen}
        options={{
          title: 'Conceptual Threads',
        }}
      />
      <Stack.Screen
        name="ThreadDetail"
        component={ThreadDetailScreen}
        options={{
          title: 'Thread',
        }}
      />
      <Stack.Screen
        name="Chat"
        component={ChatScreen}
        options={{
          title: 'Pegasus Chat',
        }}
      />
      <Stack.Screen
        name="SummaryViewer"
        component={SummaryViewerScreen}
        options={{
          title: 'Summary',
        }}
      />
      <Stack.Screen
        name="OutlineViewer"
        component={OutlineViewerScreen}
        options={{
          title: 'Outline',
        }}
      />
      <Stack.Screen
        name="KeyTermsViewer"
        component={KeyTermsViewerScreen}
        options={{
          title: 'Key Terms',
        }}
      />
      <Stack.Screen
        name="PurchaseTokens"
        component={PurchaseTokensScreen}
        options={{
          title: 'Buy Tokens',
        }}
      />
    </Stack.Navigator>
  );
}

function AppNavigator() {
  const { theme, isDark } = useTheme();
  const [authChecked, setAuthChecked] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    (async () => {
      const loggedIn = await isAuthenticated();
      if (loggedIn) {
        await api.refreshAuthToken();
        initializePurchases(); // Initialize IAP after auth (non-blocking)
      }
      setAuthed(loggedIn);
      setAuthChecked(true);
    })();
    return () => {
      destroyPurchases();
    };
  }, []);

  const handleAuthenticated = useCallback(() => {
    setAuthed(true);
  }, []);

  if (!authChecked) {
    return (
      <PaperProvider theme={theme}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </PaperProvider>
    );
  }

  return (
    <PaperProvider theme={theme}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <ErrorBoundary>
        {authed ? (
          <NavigationContainer>
            <AppStack />
          </NavigationContainer>
        ) : (
          <AuthScreen onAuthenticated={handleAuthenticated} />
        )}
      </ErrorBoundary>
    </PaperProvider>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider>
        <AppNavigator />
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}

