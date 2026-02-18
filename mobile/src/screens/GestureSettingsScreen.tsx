import React, { useState } from 'react';
import { View, ScrollView, Switch } from 'react-native';
import {
  Card,
  List,
  Text,
  Divider,
} from 'react-native-paper';
import { useTheme } from '../theme';
import AsyncStorage from '@react-native-async-storage/async-storage';

const GESTURE_SETTINGS_KEY = 'pegasus_gesture_settings';

interface GestureSettings {
  swipeToDelete: boolean;
  swipeToFavorite: boolean;
  longPressMenu: boolean;
  hapticFeedback: boolean;
  doubleTapActions: boolean;
  pullToRefresh: boolean;
}

const defaultSettings: GestureSettings = {
  swipeToDelete: true,
  swipeToFavorite: true,
  longPressMenu: true,
  hapticFeedback: true,
  doubleTapActions: true,
  pullToRefresh: true,
};

interface Props {
  navigation: any;
}

export default function GestureSettingsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [settings, setSettings] = useState<GestureSettings>(defaultSettings);

  React.useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await AsyncStorage.getItem(GESTURE_SETTINGS_KEY);
      if (data) {
        setSettings({ ...defaultSettings, ...JSON.parse(data) });
      }
    } catch (error) {
      console.error('Error loading gesture settings:', error);
    }
  };

  const updateSetting = async (key: keyof GestureSettings, value: boolean) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);

    try {
      await AsyncStorage.setItem(GESTURE_SETTINGS_KEY, JSON.stringify(newSettings));
    } catch (error) {
      console.error('Error saving gesture settings:', error);
    }
  };

  const renderSettingItem = (
    key: keyof GestureSettings,
    label: string,
    description: string,
    icon: string
  ) => (
    <List.Item
      title={label}
      description={description}
      left={(props) => <List.Icon {...props} icon={icon} />}
      right={() => (
        <Switch
          value={settings[key]}
          onValueChange={(value) => updateSetting(key, value)}
          trackColor={{ false: theme.colors.outline, true: theme.colors.primary + '80' }}
          thumbColor={settings[key] ? theme.colors.primary : theme.colors.onSurfaceVariant}
        />
      )}
    />
  );

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <View style={{ padding: 16, paddingBottom: 40 }}>
        {/* Info Banner */}
        <Card style={{ marginBottom: 24 }} mode="elevated">
          <Card.Content style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Text style={{ fontSize: 32, marginRight: 12 }}>👆</Text>
            <View style={{ flex: 1 }}>
              <Text variant="titleMedium">Gesture Controls</Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
                Customize how you interact with the app using gestures
              </Text>
            </View>
          </Card.Content>
        </Card>

        {/* Swipe Gestures */}
        <List.Section>
          <List.Subheader>Swipe Gestures</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, borderRadius: 12, overflow: 'hidden' }}>
            {renderSettingItem('swipeToDelete', 'Swipe to Delete', 'Swipe left on lectures to delete', 'delete-sweep-outline')}
            <Divider />
            {renderSettingItem('swipeToFavorite', 'Swipe to Favorite', 'Swipe right on lectures to favorite', 'star-outline')}
          </View>
        </List.Section>

        {/* Tap Gestures */}
        <List.Section>
          <List.Subheader>Tap Gestures</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, borderRadius: 12, overflow: 'hidden' }}>
            {renderSettingItem('longPressMenu', 'Long Press Menu', 'Hold down to show context menu', 'gesture-tap-hold')}
            <Divider />
            {renderSettingItem('doubleTapActions', 'Double Tap Actions', 'Double tap for quick actions', 'gesture-double-tap')}
          </View>
        </List.Section>

        {/* Other */}
        <List.Section>
          <List.Subheader>Other</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, borderRadius: 12, overflow: 'hidden' }}>
            {renderSettingItem('pullToRefresh', 'Pull to Refresh', 'Pull down to refresh content', 'refresh')}
            <Divider />
            {renderSettingItem('hapticFeedback', 'Haptic Feedback', 'Vibrate on gesture actions', 'vibrate')}
          </View>
        </List.Section>

        {/* Gesture Guide */}
        <Card style={{ marginTop: 8 }} mode="elevated">
          <Card.Content>
            <Text variant="titleMedium" style={{ marginBottom: 16 }}>Gesture Guide</Text>

            {[
              { gesture: 'Swipe Right', action: 'Favorite lecture' },
              { gesture: 'Swipe Left', action: 'Delete lecture' },
              { gesture: 'Long Press', action: 'Show context menu' },
              { gesture: 'Double Tap', action: 'Quick favorite' },
              { gesture: 'Pull Down', action: 'Refresh content' },
            ].map((item, idx) => (
              <View
                key={idx}
                style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 }}
              >
                <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                  {item.gesture}
                </Text>
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                  {item.action}
                </Text>
              </View>
            ))}
          </Card.Content>
        </Card>
      </View>
    </ScrollView>
  );
}
