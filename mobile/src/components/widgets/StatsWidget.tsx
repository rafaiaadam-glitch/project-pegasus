import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../theme';
import { formatWidgetTime } from '../../services/widgetData';

interface Props {
  totalStudyTime: number;
  todaySessions: number;
  averageScore: number;
}

export default function StatsWidget({
  totalStudyTime,
  todaySessions,
  averageScore,
}: Props) {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  const renderStat = (icon: string, label: string, value: string, color: string) => (
    <View style={styles.statItem}>
      <View style={[styles.statIcon, { backgroundColor: color + '20' }]}>
        <Text style={styles.statIconText}>{icon}</Text>
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Study Statistics</Text>

      <View style={styles.statsGrid}>
        {renderStat(
          '⏱️',
          'Total Time',
          formatWidgetTime(totalStudyTime),
          theme.primary
        )}
        {renderStat(
          '📚',
          'Today',
          `${todaySessions} ${todaySessions === 1 ? 'session' : 'sessions'}`,
          theme.success
        )}
        {renderStat(
          '📊',
          'Avg Score',
          averageScore > 0 ? `${Math.round(averageScore)}%` : 'N/A',
          theme.warning
        )}
      </View>
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: 16,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.1,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
      elevation: 4,
    },
    title: {
      fontSize: 16,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 16,
    },
    statsGrid: {
      flexDirection: 'row',
      justifyContent: 'space-between',
    },
    statItem: {
      flex: 1,
      alignItems: 'center',
    },
    statIcon: {
      width: 48,
      height: 48,
      borderRadius: 24,
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 8,
    },
    statIconText: {
      fontSize: 24,
    },
    statValue: {
      fontSize: 16,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 4,
    },
    statLabel: {
      fontSize: 11,
      fontWeight: '500',
      color: theme.textTertiary,
      textAlign: 'center',
    },
  });
