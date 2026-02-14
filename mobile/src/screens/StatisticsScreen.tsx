import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { useTheme } from '../theme';
import { getStatistics, getStudyStreak, Statistics } from '../services/statistics';

const { width } = Dimensions.get('window');

interface Props {
  navigation: any;
}

export default function StatisticsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [stats, setStats] = useState<Statistics | null>(null);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const [statistics, streakDays] = await Promise.all([
        getStatistics(),
        getStudyStreak(),
      ]);
      setStats(statistics);
      setStreak(streakDays);
    } catch (error) {
      console.error('Error loading statistics:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadStatistics();
  };

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const renderStatCard = (icon: string, label: string, value: string | number, color: string) => (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <Text style={styles.statIcon}>{icon}</Text>
      <View style={styles.statContent}>
        <Text style={styles.statValue}>{value}</Text>
        <Text style={styles.statLabel}>{label}</Text>
      </View>
    </View>
  );

  const styles = createStyles(theme);

  if (!stats) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading statistics...</Text>
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
      {/* Streak Banner */}
      <View style={styles.streakBanner}>
        <Text style={styles.streakIcon}>🔥</Text>
        <View style={styles.streakContent}>
          <Text style={styles.streakValue}>{streak} Day Streak</Text>
          <Text style={styles.streakText}>
            {streak === 0
              ? 'Start studying to begin your streak!'
              : streak === 1
              ? 'Keep it up!'
              : streak < 7
              ? 'Great momentum!'
              : 'Amazing dedication!'}
          </Text>
        </View>
      </View>

      {/* Overview Stats */}
      <Text style={styles.sectionTitle}>Overview</Text>
      <View style={styles.statsGrid}>
        {renderStatCard(
          '⏱️',
          'Total Study Time',
          formatDuration(stats.totalStudyTime),
          theme.primary
        )}
        {renderStatCard(
          '📚',
          'Study Sessions',
          stats.totalSessions.toString(),
          theme.success
        )}
        {renderStatCard(
          '🎴',
          'Cards Reviewed',
          stats.totalFlashcardsReviewed.toString(),
          theme.warning
        )}
        {renderStatCard(
          '📝',
          'Exams Taken',
          stats.totalExamsTaken.toString(),
          theme.error
        )}
      </View>

      {/* Performance */}
      <Text style={styles.sectionTitle}>Performance</Text>
      <View style={styles.performanceCard}>
        <View style={styles.performanceHeader}>
          <Text style={styles.performanceTitle}>Average Exam Score</Text>
          <Text style={styles.performanceValue}>
            {stats.averageScore > 0 ? `${Math.round(stats.averageScore)}%` : 'N/A'}
          </Text>
        </View>
        {stats.averageScore > 0 && (
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${stats.averageScore}%`,
                  backgroundColor:
                    stats.averageScore >= 80
                      ? theme.success
                      : stats.averageScore >= 60
                      ? theme.warning
                      : theme.error,
                },
              ]}
            />
          </View>
        )}
      </View>

      {/* Recent Activity */}
      {stats.sessions.length > 0 && (
        <>
          <Text style={styles.sectionTitle}>Recent Activity</Text>
          {stats.sessions.slice(-5).reverse().map((session) => (
            <View key={session.id} style={styles.activityCard}>
              <View style={styles.activityIcon}>
                <Text style={styles.activityIconText}>
                  {session.type === 'flashcards' ? '🎴' : '📝'}
                </Text>
              </View>
              <View style={styles.activityContent}>
                <Text style={styles.activityTitle}>
                  {session.type === 'flashcards' ? 'Flashcard Review' : 'Practice Exam'}
                </Text>
                <Text style={styles.activityDate}>
                  {new Date(session.startTime).toLocaleDateString()} •{' '}
                  {formatDuration(session.durationSeconds)}
                </Text>
              </View>
              {session.score !== undefined && (
                <Text style={styles.activityScore}>{Math.round(session.score)}%</Text>
              )}
            </View>
          ))}
        </>
      )}

      {/* Empty State */}
      {stats.totalSessions === 0 && (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>📊</Text>
          <Text style={styles.emptyTitle}>No Study Data Yet</Text>
          <Text style={styles.emptyText}>
            Start reviewing flashcards or taking practice exams to see your statistics here!
          </Text>
        </View>
      )}
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
    streakBanner: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: theme.primary + '15',
      borderRadius: 16,
      padding: 20,
      marginBottom: 24,
      borderWidth: 2,
      borderColor: theme.primary + '30',
    },
    streakIcon: {
      fontSize: 48,
      marginRight: 16,
    },
    streakContent: {
      flex: 1,
    },
    streakValue: {
      fontSize: 24,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 4,
    },
    streakText: {
      fontSize: 14,
      color: theme.textSecondary,
    },
    sectionTitle: {
      fontSize: 18,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 12,
      marginTop: 8,
    },
    statsGrid: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      marginHorizontal: -6,
      marginBottom: 16,
    },
    statCard: {
      width: (width - 48) / 2,
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      margin: 6,
      flexDirection: 'row',
      alignItems: 'center',
      borderLeftWidth: 4,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    statIcon: {
      fontSize: 32,
      marginRight: 12,
    },
    statContent: {
      flex: 1,
    },
    statValue: {
      fontSize: 20,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 2,
    },
    statLabel: {
      fontSize: 12,
      color: theme.textSecondary,
    },
    performanceCard: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      marginBottom: 16,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    performanceHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 12,
    },
    performanceTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.text,
    },
    performanceValue: {
      fontSize: 24,
      fontWeight: '700',
      color: theme.primary,
    },
    progressBar: {
      height: 8,
      backgroundColor: theme.border,
      borderRadius: 4,
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      borderRadius: 4,
    },
    activityCard: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 12,
      marginBottom: 8,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    activityIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: theme.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
    },
    activityIconText: {
      fontSize: 20,
    },
    activityContent: {
      flex: 1,
    },
    activityTitle: {
      fontSize: 15,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 2,
    },
    activityDate: {
      fontSize: 13,
      color: theme.textSecondary,
    },
    activityScore: {
      fontSize: 18,
      fontWeight: '700',
      color: theme.primary,
    },
    emptyContainer: {
      alignItems: 'center',
      paddingVertical: 60,
      paddingHorizontal: 40,
    },
    emptyIcon: {
      fontSize: 64,
      marginBottom: 16,
    },
    emptyTitle: {
      fontSize: 20,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 8,
    },
    emptyText: {
      fontSize: 15,
      color: theme.textSecondary,
      textAlign: 'center',
      lineHeight: 22,
    },
  });
