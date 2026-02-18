import React, { useState } from 'react';
import { View, ScrollView, Alert, Switch } from 'react-native';
import {
  List,
  Text,
  Divider,
} from 'react-native-paper';
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

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <View style={{ paddingBottom: 40 }}>
        {/* App Info */}
        <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 20 }}>
          <Text style={{ fontSize: 64, marginBottom: 12 }}>🦅</Text>
          <Text variant="headlineMedium" style={{ marginBottom: 4 }}>Pegasus</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
            Version 1.0.0
          </Text>
          <Text variant="titleSmall" style={{ color: theme.colors.onSurfaceVariant }}>
            Lecture Copilot
          </Text>
        </View>

        {/* Appearance */}
        <List.Section>
          <List.Subheader>Appearance</List.Subheader>
          <List.Item
            title="Dark Mode"
            description="Use dark theme across the app"
            right={() => (
              <Switch
                value={isDark}
                onValueChange={toggleTheme}
                trackColor={{ false: theme.colors.outline, true: theme.colors.primary + '80' }}
                thumbColor={isDark ? theme.colors.primary : theme.colors.onSurfaceVariant}
              />
            )}
            style={{ backgroundColor: theme.colors.surface, paddingHorizontal: 16 }}
          />
        </List.Section>

        {/* Notifications */}
        <List.Section>
          <List.Subheader>Notifications</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            <List.Item
              title="Enable Notifications"
              description="Receive updates and alerts"
              right={() => (
                <Switch
                  value={notificationsEnabled}
                  onValueChange={setNotificationsEnabled}
                  trackColor={{ false: theme.colors.outline, true: theme.colors.primary + '80' }}
                  thumbColor={notificationsEnabled ? theme.colors.primary : theme.colors.onSurfaceVariant}
                />
              )}
            />
            <Divider />
            <List.Item
              title="Study Reminders"
              description="Daily reminders to review flashcards"
              right={() => (
                <Switch
                  value={studyReminders}
                  onValueChange={setStudyReminders}
                  trackColor={{ false: theme.colors.outline, true: theme.colors.primary + '80' }}
                  thumbColor={studyReminders ? theme.colors.primary : theme.colors.onSurfaceVariant}
                />
              )}
            />
          </View>
        </List.Section>

        {/* Study Preferences */}
        <List.Section>
          <List.Subheader>Study Preferences</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            <List.Item
              title="Auto-export after generation"
              description="Automatically export artifacts after processing"
              right={() => (
                <Switch
                  value={autoExport}
                  onValueChange={setAutoExport}
                  trackColor={{ false: theme.colors.outline, true: theme.colors.primary + '80' }}
                  thumbColor={autoExport ? theme.colors.primary : theme.colors.onSurfaceVariant}
                />
              )}
            />
          </View>
        </List.Section>

        {/* Data & Storage */}
        <List.Section>
          <List.Subheader>Data & Storage</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            <List.Item
              title="Clear Cache"
              left={(props) => <List.Icon {...props} icon="delete-outline" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={handleClearCache}
            />
            <Divider />
            <List.Item
              title="Export All Data"
              left={(props) => <List.Icon {...props} icon="export-variant" />}
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={handleExportData}
            />
          </View>
        </List.Section>

        {/* About */}
        <List.Section>
          <List.Subheader>About</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            <List.Item
              title="Privacy Policy"
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={() => Alert.alert('Privacy Policy', 'Privacy policy details')}
            />
            <Divider />
            <List.Item
              title="Terms of Service"
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={() => Alert.alert('Terms of Service', 'Terms of service details')}
            />
            <Divider />
            <List.Item
              title="Licenses"
              right={(props) => <List.Icon {...props} icon="chevron-right" />}
              onPress={() => Alert.alert('Open Source Licenses', 'Third-party licenses')}
            />
          </View>
        </List.Section>

        {/* Debug */}
        {__DEV__ && (
          <List.Section>
            <List.Subheader>Developer</List.Subheader>
            <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
              <List.Item
                title="View Logs"
                left={(props) => <List.Icon {...props} icon="console" />}
                right={(props) => <List.Icon {...props} icon="chevron-right" />}
                onPress={() => Alert.alert('Logs', 'Development logs')}
              />
              <Divider />
              <List.Item
                title="Reset App"
                titleStyle={{ color: theme.colors.error }}
                left={(props) => <List.Icon {...props} icon="restore" color={theme.colors.error} />}
                right={(props) => <List.Icon {...props} icon="chevron-right" />}
                onPress={() => Alert.alert('Reset', 'This would reset all app data')}
              />
            </View>
          </List.Section>
        )}

        <View style={{ alignItems: 'center', paddingVertical: 32, paddingHorizontal: 20 }}>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 4 }}>
            Made with ❤️ for better learning
          </Text>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            © 2026 Pegasus
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}
