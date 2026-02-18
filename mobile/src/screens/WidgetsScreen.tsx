import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  Alert,
  Platform,
} from 'react-native';
import {
  Card,
  Text,
} from 'react-native-paper';
import { useTheme } from '../theme';
import {
  getWidgetData,
  updateWidgetData,
  WidgetData,
  scheduleWidgetUpdates,
} from '../services/widgetData';
import StreakWidget from '../components/widgets/StreakWidget';
import DueCardsWidget from '../components/widgets/DueCardsWidget';
import StatsWidget from '../components/widgets/StatsWidget';

interface Props {
  navigation: any;
}

export default function WidgetsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [widgetData, setWidgetData] = useState<WidgetData | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadWidgetData();
    scheduleWidgetUpdates();
  }, []);

  const loadWidgetData = async () => {
    try {
      const data = await getWidgetData();
      setWidgetData(data);
    } catch (error) {
      console.error('Error loading widget data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await updateWidgetData();
    await loadWidgetData();
  };

  const handleDueCardsPress = () => {
    Alert.alert('Review Cards', 'Navigate to flashcard review screen');
  };

  if (!widgetData) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center', alignItems: 'center' }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          Loading widgets...
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={theme.colors.primary}
        />
      }
    >
      {/* Info Banner */}
      <Card style={{ marginBottom: 24 }} mode="elevated">
        <Card.Content style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Text style={{ fontSize: 32, marginRight: 12 }}>📱</Text>
          <View style={{ flex: 1 }}>
            <Text variant="titleMedium">Home Screen Widgets</Text>
            <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
              {Platform.OS === 'web'
                ? 'Widgets are available on iOS and Android devices'
                : 'Add these widgets to your home screen for quick access to your study stats'}
            </Text>
          </View>
        </Card.Content>
      </Card>

      {/* Widget Previews */}
      <Text variant="titleLarge" style={{ marginBottom: 16 }}>Available Widgets</Text>

      {/* Streak Widget - Small */}
      <Card style={{ marginBottom: 16 }} mode="outlined">
        <Card.Title
          title="Study Streak"
          titleVariant="titleSmall"
          right={() => <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 16 }}>SMALL</Text>}
        />
        <Card.Content>
          <StreakWidget streak={widgetData.streak} size="small" />
        </Card.Content>
      </Card>

      {/* Streak Widget - Medium */}
      <Card style={{ marginBottom: 16 }} mode="outlined">
        <Card.Title
          title="Study Streak"
          titleVariant="titleSmall"
          right={() => <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 16 }}>MEDIUM</Text>}
        />
        <Card.Content>
          <StreakWidget streak={widgetData.streak} size="medium" />
        </Card.Content>
      </Card>

      {/* Due Cards Widget */}
      <Card style={{ marginBottom: 16 }} mode="outlined">
        <Card.Title
          title="Due Cards"
          titleVariant="titleSmall"
          right={() => <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 16 }}>MEDIUM</Text>}
        />
        <Card.Content>
          <DueCardsWidget
            dueCount={widgetData.dueCardsCount}
            onPress={handleDueCardsPress}
          />
        </Card.Content>
      </Card>

      {/* Stats Widget */}
      <Card style={{ marginBottom: 16 }} mode="outlined">
        <Card.Title
          title="Study Statistics"
          titleVariant="titleSmall"
          right={() => <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginRight: 16 }}>LARGE</Text>}
        />
        <Card.Content>
          <StatsWidget
            totalStudyTime={widgetData.totalStudyTime}
            todaySessions={widgetData.todaySessions}
            averageScore={widgetData.averageScore}
          />
        </Card.Content>
      </Card>

      {/* Instructions */}
      {Platform.OS !== 'web' && (
        <Card style={{ marginTop: 8 }} mode="elevated">
          <Card.Content>
            <Text variant="titleMedium" style={{ marginBottom: 12 }}>How to Add Widgets</Text>

            {(Platform.OS === 'ios'
              ? [
                  '1. Long press on your home screen',
                  '2. Tap the "+" button',
                  '3. Search for "Pegasus"',
                  '4. Choose a widget size',
                  '5. Tap "Add Widget"',
                ]
              : [
                  '1. Long press on your home screen',
                  '2. Tap "Widgets"',
                  '3. Search for "Pegasus"',
                  '4. Drag widget to home screen',
                ]
            ).map((step, idx) => (
              <Text
                key={idx}
                variant="bodyMedium"
                style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}
              >
                {step}
              </Text>
            ))}
          </Card.Content>
        </Card>
      )}

      <View style={{ marginTop: 24, paddingTop: 16, borderTopWidth: 1, borderTopColor: theme.colors.outlineVariant, alignItems: 'center' }}>
        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
          Last updated: {new Date(widgetData.lastUpdated).toLocaleString()}
        </Text>
      </View>
    </ScrollView>
  );
}
