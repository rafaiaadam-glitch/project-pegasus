import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  Dimensions,
} from 'react-native';
import {
  Card,
  Text,
  ProgressBar,
  List,
} from 'react-native-paper';
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

  if (!stats) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background, justifyContent: 'center', alignItems: 'center' }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          Loading statistics...
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
      {/* Streak Banner */}
      <Card style={{ marginBottom: 24 }} mode="elevated">
        <Card.Content style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 16 }}>
          <Text style={{ fontSize: 48, marginRight: 16 }}>🔥</Text>
          <View style={{ flex: 1 }}>
            <Text variant="headlineSmall" style={{ fontWeight: '700' }}>
              {streak} Day Streak
            </Text>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              {streak === 0
                ? 'Start studying to begin your streak!'
                : streak === 1
                ? 'Keep it up!'
                : streak < 7
                ? 'Great momentum!'
                : 'Amazing dedication!'}
            </Text>
          </View>
        </Card.Content>
      </Card>

      {/* Overview Stats */}
      <Text variant="titleLarge" style={{ marginBottom: 12, marginTop: 8 }}>Overview</Text>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6, marginBottom: 16 }}>
        {[
          { icon: '⏱️', label: 'Total Study Time', value: formatDuration(stats.totalStudyTime), color: theme.colors.primary },
          { icon: '📚', label: 'Study Sessions', value: stats.totalSessions.toString(), color: theme.colors.tertiary },
          { icon: '🎴', label: 'Cards Reviewed', value: stats.totalFlashcardsReviewed.toString(), color: theme.colors.secondary },
          { icon: '📝', label: 'Exams Taken', value: stats.totalExamsTaken.toString(), color: theme.colors.error },
        ].map((stat, idx) => (
          <Card
            key={idx}
            style={{ width: (width - 48) / 2, margin: 6, borderLeftWidth: 4, borderLeftColor: stat.color }}
            mode="elevated"
          >
            <Card.Content style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Text style={{ fontSize: 32, marginRight: 12 }}>{stat.icon}</Text>
              <View style={{ flex: 1 }}>
                <Text variant="titleLarge" style={{ fontWeight: '700' }}>{stat.value}</Text>
                <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                  {stat.label}
                </Text>
              </View>
            </Card.Content>
          </Card>
        ))}
      </View>

      {/* Performance */}
      <Text variant="titleLarge" style={{ marginBottom: 12, marginTop: 8 }}>Performance</Text>
      <Card style={{ marginBottom: 16 }} mode="elevated">
        <Card.Content>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Text variant="titleMedium">Average Exam Score</Text>
            <Text variant="headlineSmall" style={{ color: theme.colors.primary, fontWeight: '700' }}>
              {stats.averageScore > 0 ? `${Math.round(stats.averageScore)}%` : 'N/A'}
            </Text>
          </View>
          {stats.averageScore > 0 && (
            <ProgressBar
              progress={stats.averageScore / 100}
              color={
                stats.averageScore >= 80
                  ? theme.colors.primary
                  : stats.averageScore >= 60
                  ? theme.colors.tertiary
                  : theme.colors.error
              }
              style={{ borderRadius: 4 }}
            />
          )}
        </Card.Content>
      </Card>

      {/* Recent Activity */}
      {stats.sessions.length > 0 && (
        <>
          <Text variant="titleLarge" style={{ marginBottom: 12, marginTop: 8 }}>Recent Activity</Text>
          {stats.sessions.slice(-5).reverse().map((session) => (
            <List.Item
              key={session.id}
              title={session.type === 'flashcards' ? 'Flashcard Review' : 'Practice Exam'}
              description={`${new Date(session.startTime).toLocaleDateString()} • ${formatDuration(session.durationSeconds)}`}
              left={(props) => (
                <List.Icon {...props} icon={session.type === 'flashcards' ? 'cards-outline' : 'file-document-edit-outline'} />
              )}
              right={() =>
                session.score !== undefined ? (
                  <Text variant="titleMedium" style={{ color: theme.colors.primary, alignSelf: 'center' }}>
                    {Math.round(session.score)}%
                  </Text>
                ) : null
              }
              style={{ backgroundColor: theme.colors.surface, borderRadius: 12, marginBottom: 8 }}
            />
          ))}
        </>
      )}

      {/* Empty State */}
      {stats.totalSessions === 0 && (
        <View style={{ alignItems: 'center', paddingVertical: 60, paddingHorizontal: 40 }}>
          <Text style={{ fontSize: 64, marginBottom: 16 }}>📊</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Study Data Yet</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            Start reviewing flashcards or taking practice exams to see your statistics here!
          </Text>
        </View>
      )}
    </ScrollView>
  );
}
