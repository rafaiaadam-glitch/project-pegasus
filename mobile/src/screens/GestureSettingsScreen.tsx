import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Switch,
} from 'react-native';
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

  const renderSettingRow = (
    key: keyof GestureSettings,
    label: string,
    description: string,
    icon: string
  ) => (
    <View style={styles.settingRow}>
      <View style={styles.settingIcon}>
        <Text style={styles.settingIconText}>{icon}</Text>
      </View>
      <View style={styles.settingText}>
        <Text style={styles.settingLabel}>{label}</Text>
        <Text style={styles.settingDescription}>{description}</Text>
      </View>
      <Switch
        value={settings[key]}
        onValueChange={(value) => updateSetting(key, value)}
        trackColor={{ false: theme.border, true: theme.primary + '80' }}
        thumbColor={settings[key] ? theme.primary : theme.textTertiary}
        ios_backgroundColor={theme.border}
      />
    </View>
  );

  const styles = createStyles(theme);

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        {/* Info Banner */}
        <View style={styles.infoBanner}>
          <Text style={styles.infoBannerIcon}>👆</Text>
          <View style={styles.infoBannerContent}>
            <Text style={styles.infoBannerTitle}>Gesture Controls</Text>
            <Text style={styles.infoBannerText}>
              Customize how you interact with the app using gestures
            </Text>
          </View>
        </View>

        {/* Swipe Gestures */}
        <Text style={styles.sectionTitle}>Swipe Gestures</Text>
        <View style={styles.section}>
          {renderSettingRow(
            'swipeToDelete',
            'Swipe to Delete',
            'Swipe left on lectures to delete',
            '🗑️'
          )}
          {renderSettingRow(
            'swipeToFavorite',
            'Swipe to Favorite',
            'Swipe right on lectures to favorite',
            '⭐'
          )}
        </View>

        {/* Tap Gestures */}
        <Text style={styles.sectionTitle}>Tap Gestures</Text>
        <View style={styles.section}>
          {renderSettingRow(
            'longPressMenu',
            'Long Press Menu',
            'Hold down to show context menu',
            '📋'
          )}
          {renderSettingRow(
            'doubleTapActions',
            'Double Tap Actions',
            'Double tap for quick actions',
            '👆👆'
          )}
        </View>

        {/* Other Gestures */}
        <Text style={styles.sectionTitle}>Other</Text>
        <View style={styles.section}>
          {renderSettingRow(
            'pullToRefresh',
            'Pull to Refresh',
            'Pull down to refresh content',
            '🔄'
          )}
          {renderSettingRow(
            'hapticFeedback',
            'Haptic Feedback',
            'Vibrate on gesture actions',
            '📳'
          )}
        </View>

        {/* Gesture Guide */}
        <View style={styles.guideCard}>
          <Text style={styles.guideTitle}>💡 Gesture Guide</Text>

          <View style={styles.guideItem}>
            <Text style={styles.guideGesture}>Swipe Right →</Text>
            <Text style={styles.guideAction}>Favorite lecture</Text>
          </View>

          <View style={styles.guideItem}>
            <Text style={styles.guideGesture}>Swipe Left ←</Text>
            <Text style={styles.guideAction}>Delete lecture</Text>
          </View>

          <View style={styles.guideItem}>
            <Text style={styles.guideGesture}>Long Press</Text>
            <Text style={styles.guideAction}>Show context menu</Text>
          </View>

          <View style={styles.guideItem}>
            <Text style={styles.guideGesture}>Double Tap</Text>
            <Text style={styles.guideAction}>Quick favorite</Text>
          </View>

          <View style={styles.guideItem}>
            <Text style={styles.guideGesture}>Pull Down</Text>
            <Text style={styles.guideAction}>Refresh content</Text>
          </View>
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
      padding: 16,
      paddingBottom: 40,
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
      fontSize: 13,
      fontWeight: '600',
      color: theme.textTertiary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      paddingHorizontal: 4,
      marginBottom: 8,
    },
    section: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      marginBottom: 24,
      overflow: 'hidden',
    },
    settingRow: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    settingIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: theme.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
    },
    settingIconText: {
      fontSize: 20,
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
    },
    guideCard: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
    },
    guideTitle: {
      fontSize: 16,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 16,
    },
    guideItem: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingVertical: 8,
    },
    guideGesture: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.primary,
    },
    guideAction: {
      fontSize: 14,
      color: theme.textSecondary,
    },
  });
