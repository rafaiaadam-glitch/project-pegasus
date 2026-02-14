import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../theme';

interface Props {
  streak: number;
  size?: 'small' | 'medium';
}

export default function StreakWidget({ streak, size = 'small' }: Props) {
  const { theme } = useTheme();
  const styles = createStyles(theme, size);

  const getMessage = () => {
    if (streak === 0) return 'Start your streak!';
    if (streak === 1) return 'Keep it going!';
    if (streak < 7) return 'Great momentum!';
    if (streak < 30) return 'On fire! 🔥';
    return 'Legendary! 🏆';
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Study Streak</Text>
        <Text style={styles.flame}>🔥</Text>
      </View>

      <View style={styles.content}>
        <Text style={styles.streakNumber}>{streak}</Text>
        <Text style={styles.streakLabel}>
          {streak === 1 ? 'Day' : 'Days'}
        </Text>
      </View>

      <Text style={styles.message}>{getMessage()}</Text>
    </View>
  );
}

const createStyles = (theme: any, size: 'small' | 'medium') =>
  StyleSheet.create({
    container: {
      backgroundColor: theme.surface,
      borderRadius: 16,
      padding: size === 'small' ? 12 : 16,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.1,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 4 },
      elevation: 4,
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: size === 'small' ? 8 : 12,
    },
    title: {
      fontSize: size === 'small' ? 12 : 14,
      fontWeight: '600',
      color: theme.textSecondary,
    },
    flame: {
      fontSize: size === 'small' ? 16 : 20,
    },
    content: {
      alignItems: 'center',
      marginBottom: size === 'small' ? 8 : 12,
    },
    streakNumber: {
      fontSize: size === 'small' ? 36 : 48,
      fontWeight: '700',
      color: theme.primary,
      lineHeight: size === 'small' ? 40 : 52,
    },
    streakLabel: {
      fontSize: size === 'small' ? 14 : 16,
      fontWeight: '500',
      color: theme.textTertiary,
    },
    message: {
      fontSize: size === 'small' ? 11 : 13,
      fontWeight: '500',
      color: theme.textSecondary,
      textAlign: 'center',
    },
  });
