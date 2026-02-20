import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, Button } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../theme';

interface Props {
  message?: string;
  onRetry: () => void;
}

export default function NetworkErrorView({ message, onRetry }: Props) {
  const { theme } = useTheme();

  return (
    <View style={styles.container}>
      <MaterialCommunityIcons
        name="wifi-off"
        size={48}
        color={theme.colors.onSurfaceVariant}
        style={styles.icon}
      />
      <Text variant="titleMedium" style={[styles.title, { color: theme.colors.onSurface }]}>
        Connection Error
      </Text>
      <Text variant="bodyMedium" style={[styles.message, { color: theme.colors.onSurfaceVariant }]}>
        {message || 'Could not connect to the server. Please check your connection and try again.'}
      </Text>
      <Button mode="contained" onPress={onRetry} style={styles.button}>
        Retry
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  icon: {
    marginBottom: 16,
  },
  title: {
    fontWeight: '600',
    marginBottom: 8,
  },
  message: {
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  button: {
    minWidth: 120,
  },
});
