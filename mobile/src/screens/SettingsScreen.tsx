import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
  Platform,
  Alert,
} from 'react-native';
import { useTheme } from '../theme';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface Props {
  navigation: any;
}

export default function SettingsScreen({ navigation }: Props) {
  const { theme, isDark, toggleTheme } = useTheme();
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [autoExport, setAutoExport] = useState(false);
  const [studyReminders, setStudyReminders] = useState(true);

  const handleClearCache = async () => {
    Alert.alert(
      'Clear Cache',
      'This will remove cached data. Your lectures and progress will not be affected.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            try {
              // Clear specific cache keys
              await AsyncStorage.removeItem('cached_lectures');
              Alert.alert('Success', 'Cache cleared successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to clear cache');
            }
          },
        },
      ]
    );
  };

  const handleExportData = () => {
    Alert.alert(
      'Export Data',
      'Export all your lectures, notes, and progress.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Export',
          onPress: () => {
            Alert.alert('Coming Soon', 'Data export will be available soon');
          },
        },
      ]
    );
  };

  const styles = createStyles(theme);

  const renderSection = (title: string) => (
    <Text style={styles.sectionTitle}>{title}</Text>
  );

  const renderSettingRow = (
    label: string,
    value: boolean,
    onToggle: (value: boolean) => void,
    description?: string
  ) => (
    <View style={styles.settingRow}>
      <View style={styles.settingText}>
        <Text style={styles.settingLabel}>{label}</Text>
        {description && (
          <Text style={styles.settingDescription}>{description}</Text>
        )}
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: theme.border, true: theme.primary + '80' }}
        thumbColor={value ? theme.primary : theme.textTertiary}
        ios_backgroundColor={theme.border}
      />
    </View>
  );

  const renderActionRow = (label: string, onPress: () => void, destructive?: boolean) => (
    <TouchableOpacity style={styles.actionRow} onPress={onPress}>
      <Text style={[styles.actionLabel, destructive && styles.destructiveLabel]}>
        {label}
      </Text>
      <Text style={styles.chevron}>›</Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        {/* App Info */}
        <View style={styles.appInfo}>
          <Text style={styles.appIcon}>🦅</Text>
          <Text style={styles.appName}>Pegasus</Text>
          <Text style={styles.appVersion}>Version 1.0.0</Text>
          <Text style={styles.appTagline}>Lecture Copilot</Text>
        </View>

        {/* Appearance */}
        {renderSection('Appearance')}
        <View style={styles.section}>
          {renderSettingRow(
            'Dark Mode',
            isDark,
            toggleTheme,
            'Use dark theme across the app'
          )}
        </View>

        {/* Notifications */}
        {renderSection('Notifications')}
        <View style={styles.section}>
          {renderSettingRow(
            'Enable Notifications',
            notificationsEnabled,
            setNotificationsEnabled,
            'Receive updates and alerts'
          )}
          {renderSettingRow(
            'Study Reminders',
            studyReminders,
            setStudyReminders,
            'Daily reminders to review flashcards'
          )}
        </View>

        {/* Study Preferences */}
        {renderSection('Study Preferences')}
        <View style={styles.section}>
          {renderSettingRow(
            'Auto-export after generation',
            autoExport,
            setAutoExport,
            'Automatically export artifacts after processing'
          )}
        </View>

        {/* Data & Storage */}
        {renderSection('Data & Storage')}
        <View style={styles.section}>
          {renderActionRow('Clear Cache', handleClearCache)}
          {renderActionRow('Export All Data', handleExportData)}
        </View>

        {/* About */}
        {renderSection('About')}
        <View style={styles.section}>
          {renderActionRow('Privacy Policy', () =>
            Alert.alert('Privacy Policy', 'Privacy policy details')
          )}
          {renderActionRow('Terms of Service', () =>
            Alert.alert('Terms of Service', 'Terms of service details')
          )}
          {renderActionRow('Licenses', () =>
            Alert.alert('Open Source Licenses', 'Third-party licenses')
          )}
        </View>

        {/* Debug */}
        {__DEV__ && (
          <>
            {renderSection('Developer')}
            <View style={styles.section}>
              {renderActionRow('View Logs', () =>
                Alert.alert('Logs', 'Development logs')
              )}
              {renderActionRow('Reset App', () =>
                Alert.alert('Reset', 'This would reset all app data'), true
              )}
            </View>
          </>
        )}

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Made with ❤️ for better learning
          </Text>
          <Text style={styles.footerText}>© 2026 Pegasus</Text>
        </View>
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
      paddingBottom: 40,
    },
    appInfo: {
      alignItems: 'center',
      paddingVertical: 40,
      paddingHorizontal: 20,
    },
    appIcon: {
      fontSize: 64,
      marginBottom: 12,
    },
    appName: {
      fontSize: 28,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 4,
    },
    appVersion: {
      fontSize: 14,
      color: theme.textTertiary,
      marginBottom: 8,
    },
    appTagline: {
      fontSize: 16,
      color: theme.textSecondary,
      fontWeight: '500',
    },
    sectionTitle: {
      fontSize: 13,
      fontWeight: '600',
      color: theme.textTertiary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      paddingHorizontal: 20,
      paddingTop: 24,
      paddingBottom: 8,
    },
    section: {
      backgroundColor: theme.surface,
      marginHorizontal: 20,
      borderRadius: 12,
      overflow: 'hidden',
    },
    settingRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingVertical: 12,
      paddingHorizontal: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    settingText: {
      flex: 1,
      marginRight: 12,
    },
    settingLabel: {
      fontSize: 16,
      fontWeight: '500',
      color: theme.text,
      marginBottom: 2,
    },
    settingDescription: {
      fontSize: 13,
      color: theme.textTertiary,
      marginTop: 2,
    },
    actionRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingVertical: 14,
      paddingHorizontal: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    actionLabel: {
      fontSize: 16,
      fontWeight: '500',
      color: theme.text,
    },
    destructiveLabel: {
      color: theme.error,
    },
    chevron: {
      fontSize: 24,
      color: theme.textTertiary,
      fontWeight: '300',
    },
    footer: {
      alignItems: 'center',
      paddingVertical: 32,
      paddingHorizontal: 20,
    },
    footerText: {
      fontSize: 13,
      color: theme.textTertiary,
      marginBottom: 4,
    },
  });
