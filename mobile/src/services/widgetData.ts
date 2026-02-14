import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import { getStatistics, getDueCards, getStudyStreak } from './statistics';

const WIDGET_DATA_KEY = 'pegasus_widget_data';

export interface WidgetData {
  streak: number;
  dueCardsCount: number;
  totalStudyTime: number;
  todaySessions: number;
  averageScore: number;
  lastUpdated: string;
}

// Widget data file path (shared with widget extension)
const getWidgetDataPath = () => {
  return `${FileSystem.documentDirectory}widget_data.json`;
};

// Update widget data
export const updateWidgetData = async (): Promise<void> => {
  try {
    const [streak, dueCards, stats] = await Promise.all([
      getStudyStreak(),
      getDueCards(),
      getStatistics(),
    ]);

    // Calculate today's sessions
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todaySessions = stats.sessions.filter(session => {
      const sessionDate = new Date(session.startTime);
      sessionDate.setHours(0, 0, 0, 0);
      return sessionDate.getTime() === today.getTime();
    }).length;

    const widgetData: WidgetData = {
      streak,
      dueCardsCount: dueCards.length,
      totalStudyTime: stats.totalStudyTime,
      todaySessions,
      averageScore: stats.averageScore,
      lastUpdated: new Date().toISOString(),
    };

    // Save to AsyncStorage
    await AsyncStorage.setItem(WIDGET_DATA_KEY, JSON.stringify(widgetData));

    // Save to file system for widget extension access
    await FileSystem.writeAsStringAsync(
      getWidgetDataPath(),
      JSON.stringify(widgetData)
    );
  } catch (error) {
    console.error('Error updating widget data:', error);
  }
};

// Get widget data
export const getWidgetData = async (): Promise<WidgetData | null> => {
  try {
    const data = await AsyncStorage.getItem(WIDGET_DATA_KEY);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Error getting widget data:', error);
    return null;
  }
};

// Schedule periodic widget updates
export const scheduleWidgetUpdates = async (): Promise<void> => {
  // Update immediately
  await updateWidgetData();

  // Set up periodic updates (every hour)
  setInterval(async () => {
    await updateWidgetData();
  }, 60 * 60 * 1000); // 1 hour
};

// Format time for widget display
export const formatWidgetTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
};
