import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  Platform,
} from 'react-native';
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
    // Navigate to flashcard review
    Alert.alert('Review Cards', 'Navigate to flashcard review screen');
  };

  const styles = createStyles(theme);

  if (!widgetData) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading widgets...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={theme.primary}
        />
      }
    >
      {/* Info Banner */}
      <View style={styles.infoBanner}>
        <Text style={styles.infoBannerIcon}>📱</Text>
        <View style={styles.infoBannerContent}>
          <Text style={styles.infoBannerTitle}>Home Screen Widgets</Text>
          <Text style={styles.infoBannerText}>
            {Platform.OS === 'web'
              ? 'Widgets are available on iOS and Android devices'
              : 'Add these widgets to your home screen for quick access to your study stats'}
          </Text>
        </View>
      </View>

      {/* Widget Previews */}
      <Text style={styles.sectionTitle}>Available Widgets</Text>

      {/* Streak Widget - Small */}
      <View style={styles.widgetPreview}>
        <View style={styles.widgetHeader}>
          <Text style={styles.widgetName}>Study Streak</Text>
          <Text style={styles.widgetSize}>Small</Text>
        </View>
        <StreakWidget streak={widgetData.streak} size="small" />
      </View>

      {/* Streak Widget - Medium */}
      <View style={styles.widgetPreview}>
        <View style={styles.widgetHeader}>
          <Text style={styles.widgetName}>Study Streak</Text>
          <Text style={styles.widgetSize}>Medium</Text>
        </View>
        <StreakWidget streak={widgetData.streak} size="medium" />
      </View>

      {/* Due Cards Widget */}
      <View style={styles.widgetPreview}>
        <View style={styles.widgetHeader}>
          <Text style={styles.widgetName}>Due Cards</Text>
          <Text style={styles.widgetSize}>Medium</Text>
        </View>
        <DueCardsWidget
          dueCount={widgetData.dueCardsCount}
          onPress={handleDueCardsPress}
        />
      </View>

      {/* Stats Widget */}
      <View style={styles.widgetPreview}>
        <View style={styles.widgetHeader}>
          <Text style={styles.widgetName}>Study Statistics</Text>
          <Text style={styles.widgetSize}>Large</Text>
        </View>
        <StatsWidget
          totalStudyTime={widgetData.totalStudyTime}
          todaySessions={widgetData.todaySessions}
          averageScore={widgetData.averageScore}
        />
      </View>

      {/* Instructions */}
      {Platform.OS !== 'web' && (
        <View style={styles.instructions}>
          <Text style={styles.instructionsTitle}>How to Add Widgets</Text>

          {Platform.OS === 'ios' ? (
            <>
              <Text style={styles.instructionStep}>1. Long press on your home screen</Text>
              <Text style={styles.instructionStep}>2. Tap the "+" button</Text>
              <Text style={styles.instructionStep}>3. Search for "Pegasus"</Text>
              <Text style={styles.instructionStep}>4. Choose a widget size</Text>
              <Text style={styles.instructionStep}>5. Tap "Add Widget"</Text>
            </>
          ) : (
            <>
              <Text style={styles.instructionStep}>1. Long press on your home screen</Text>
              <Text style={styles.instructionStep}>2. Tap "Widgets"</Text>
              <Text style={styles.instructionStep}>3. Search for "Pegasus"</Text>
              <Text style={styles.instructionStep}>4. Drag widget to home screen</Text>
            </>
          )}
        </View>
      )}

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Last updated: {new Date(widgetData.lastUpdated).toLocaleString()}
        </Text>
      </View>
    </ScrollView>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    content: {
      padding: 16,
      paddingBottom: 40,
    },
    loadingText: {
      textAlign: 'center',
      marginTop: 40,
      fontSize: 16,
      color: theme.textSecondary,
    },
    infoBanner: {
      flexDirection: 'row',
      backgroundColor: theme.primary + '15',
      borderRadius: 12,
      padding: 16,
      marginBottom: 24,
      borderWidth: 1,
      borderColor: theme.primary + '30',
    },
    infoBannerIcon: {
      fontSize: 32,
      marginRight: 12,
    },
    infoBannerContent: {
      flex: 1,
    },
    infoBannerTitle: {
      fontSize: 16,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 4,
    },
    infoBannerText: {
      fontSize: 14,
      color: theme.textSecondary,
      lineHeight: 20,
    },
    sectionTitle: {
      fontSize: 18,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 16,
    },
    widgetPreview: {
      marginBottom: 24,
    },
    widgetHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 8,
    },
    widgetName: {
      fontSize: 15,
      fontWeight: '600',
      color: theme.text,
    },
    widgetSize: {
      fontSize: 12,
      fontWeight: '600',
      color: theme.textTertiary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
    },
    instructions: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      marginTop: 8,
    },
    instructionsTitle: {
      fontSize: 16,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 12,
    },
    instructionStep: {
      fontSize: 14,
      color: theme.textSecondary,
      marginBottom: 8,
      lineHeight: 20,
    },
    footer: {
      marginTop: 24,
      paddingTop: 16,
      borderTopWidth: 1,
      borderTopColor: theme.border,
      alignItems: 'center',
    },
    footerText: {
      fontSize: 12,
      color: theme.textTertiary,
    },
  });
