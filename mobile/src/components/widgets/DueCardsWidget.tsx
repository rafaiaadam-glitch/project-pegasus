import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../../theme';

interface Props {
  dueCount: number;
  onPress?: () => void;
}

export default function DueCardsWidget({ dueCount, onPress }: Props) {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  const getMessage = () => {
    if (dueCount === 0) return 'All caught up! 🎉';
    if (dueCount === 1) return '1 card ready to review';
    if (dueCount < 5) return `${dueCount} cards to review`;
    if (dueCount < 10) return `${dueCount} cards waiting`;
    return `${dueCount} cards to review!`;
  };

  const getColor = () => {
    if (dueCount === 0) return theme.success;
    if (dueCount < 5) return theme.primary;
    if (dueCount < 10) return theme.warning;
    return theme.error;
  };

  return (
    <TouchableOpacity
      style={styles.container}
      onPress={onPress}
      disabled={!onPress}
      activeOpacity={0.7}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Due Today</Text>
        <Text style={styles.icon}>🎴</Text>
      </View>

      <View style={styles.content}>
        <View style={[styles.badge, { backgroundColor: getColor() + '20' }]}>
          <Text style={[styles.count, { color: getColor() }]}>
            {dueCount}
          </Text>
        </View>
        <Text style={styles.message}>{getMessage()}</Text>
      </View>

      {dueCount > 0 && onPress && (
        <View style={styles.footer}>
          <Text style={styles.action}>Start Review →</Text>
        </View>
      )}
    </TouchableOpacity>
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
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 12,
    },
    title: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.textSecondary,
    },
    icon: {
      fontSize: 20,
    },
    content: {
      alignItems: 'center',
      paddingVertical: 12,
    },
    badge: {
      width: 80,
      height: 80,
      borderRadius: 40,
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 12,
    },
    count: {
      fontSize: 36,
      fontWeight: '700',
    },
    message: {
      fontSize: 14,
      fontWeight: '500',
      color: theme.text,
      textAlign: 'center',
    },
    footer: {
      marginTop: 12,
      paddingTop: 12,
      borderTopWidth: 1,
      borderTopColor: theme.border,
      alignItems: 'center',
    },
    action: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.primary,
    },
  });
