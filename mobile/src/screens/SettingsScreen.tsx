import React, { useState, useEffect, useCallback } from 'react';
import { View, ScrollView, Alert, Switch, Linking, Image } from 'react-native';
import {
  List,
  Text,
  Button,
  Divider,
  ActivityIndicator,
  ProgressBar,
  RadioButton,
} from 'react-native-paper';
import { useTheme } from '../theme';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { logout, getStoredUser, AuthUser } from '../services/auth';
import api from '../services/api';
import { TokenBalance } from '../types';

const LLM_MODELS = [
  { label: 'GPT-4o Mini', value: 'gpt-4o-mini', desc: 'OpenAI — fast & affordable' },
  { label: 'Gemini 2.5 Flash', value: 'gemini-2.5-flash', desc: 'Google — fast & cheap' },
  { label: 'Gemini 2.5 Pro', value: 'gemini-2.5-pro', desc: 'Google — high quality' },
] as const;

const LLM_STORAGE_KEY = '@pegasus/default-llm';

interface Props {
  navigation: any;
}

export default function SettingsScreen({ navigation }: Props) {
  const { theme, isDark, toggleTheme } = useTheme();
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [studyReminders, setStudyReminders] = useState(true);
  const [defaultModel, setDefaultModel] = useState('gpt-4o-mini');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [creditsSummary, setCreditsSummary] = useState<any>(null);
  const [creditsLoading, setCreditsLoading] = useState(false);
  const [tokenBalance, setTokenBalance] = useState<TokenBalance | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(LLM_STORAGE_KEY).then((val) => {
      if (val) setDefaultModel(val);
    });
  }, []);

  const handleModelChange = async (value: string) => {
    setDefaultModel(value);
    await AsyncStorage.setItem(LLM_STORAGE_KEY, value);
  };

  useEffect(() => {
    (async () => {
      const u = await getStoredUser();
      setUser(u);
      if (u) {
        setCreditsLoading(true);
        try {
          const [summary, balance] = await Promise.all([
            api.getCreditsSummary(),
            api.getTokenBalance(),
          ]);
          setCreditsSummary(summary);
          setTokenBalance(balance);
        } catch {
          // Not critical
        } finally {
          setCreditsLoading(false);
        }
      }
    })();
  }, []);

  const handleLogout = () => {
    Alert.alert('Log Out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
          // Force reload — simplest approach
          if (navigation.getParent()) {
            navigation.getParent()?.reset({ index: 0, routes: [] });
          }
          // Fallback: just go back
          navigation.popToTop();
        },
      },
    ]);
  };

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

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

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <View style={{ paddingBottom: 40 }}>
        {/* App Info */}
        <View style={{ alignItems: 'center', paddingVertical: 40, paddingHorizontal: 20 }}>
          <Image
            source={require('../../assets/pegasus-logo.png')}
            style={{ width: 80, height: 80, borderRadius: 20, marginBottom: 12 }}
          />
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

        {/* AI Model */}
        <List.Section>
          <List.Subheader>AI Model</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            {LLM_MODELS.map((m, i) => (
              <React.Fragment key={m.value}>
                {i > 0 && <Divider />}
                <List.Item
                  title={m.label}
                  description={m.desc}
                  onPress={() => handleModelChange(m.value)}
                  right={() => (
                    <RadioButton
                      value={m.value}
                      status={defaultModel === m.value ? 'checked' : 'unchecked'}
                      onPress={() => handleModelChange(m.value)}
                      color={theme.colors.primary}
                    />
                  )}
                />
              </React.Fragment>
            ))}
          </View>
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
          </View>
        </List.Section>

        {/* Account */}
        {user && (
          <List.Section>
            <List.Subheader>Account</List.Subheader>
            <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
              <List.Item
                title={user.displayName || user.email}
                description={user.email}
                left={(props) => <List.Icon {...props} icon="account-circle" />}
              />
              <Divider />
              <List.Item
                title="Log Out"
                titleStyle={{ color: theme.colors.error }}
                left={(props) => <List.Icon {...props} icon="logout" color={theme.colors.error} />}
                onPress={handleLogout}
              />
            </View>
          </List.Section>
        )}

        {/* Token Balance */}
        {user && (
          <List.Section>
            <List.Subheader>Token Balance</List.Subheader>
            <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden', padding: 16 }}>
              {creditsLoading ? (
                <ActivityIndicator size="small" />
              ) : tokenBalance ? (
                <>
                  {/* Free tokens with progress bar */}
                  <View style={{ marginBottom: 12 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>Free Monthly</Text>
                      <Text variant="labelSmall">
                        {formatTokens(tokenBalance.freeBalance)} / {formatTokens(tokenBalance.freeMonthlyAllowance)}
                      </Text>
                    </View>
                    <ProgressBar
                      progress={Math.min(tokenBalance.freeBalance / tokenBalance.freeMonthlyAllowance, 1)}
                      style={{ borderRadius: 4, height: 6 }}
                      color={tokenBalance.freeBalance < tokenBalance.freeMonthlyAllowance * 0.1 ? theme.colors.error : theme.colors.primary}
                    />
                    {tokenBalance.freeResetsAt && (
                      <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 2 }}>
                        Resets {new Date(new Date(tokenBalance.freeResetsAt).getTime() + 30 * 86400000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </Text>
                    )}
                  </View>

                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                    <View>
                      <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>Purchased</Text>
                      <Text variant="titleMedium">{formatTokens(tokenBalance.purchasedBalance)}</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>Total Available</Text>
                      <Text variant="titleMedium" style={{ color: theme.colors.primary, fontWeight: '700' }}>
                        {formatTokens(tokenBalance.totalBalance)}
                      </Text>
                    </View>
                  </View>

                  {creditsSummary && (
                    <>
                      <Divider style={{ marginBottom: 8 }} />
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                          {creditsSummary.generationCount} generations
                        </Text>
                        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                          {formatTokens(creditsSummary.totalTokens)} tokens used total
                        </Text>
                      </View>
                    </>
                  )}

                  <Button
                    mode="contained"
                    onPress={() => navigation.navigate('PurchaseTokens')}
                    style={{ marginTop: 12 }}
                    icon="cart"
                  >
                    Buy Tokens
                  </Button>
                </>
              ) : (
                <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                  No usage data yet. Generate study materials to see your usage.
                </Text>
              )}
            </View>
          </List.Section>
        )}

        {/* About */}
        <List.Section>
          <List.Subheader>About</List.Subheader>
          <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
            <List.Item
              title="Privacy Policy"
              right={(props) => <List.Icon {...props} icon="open-in-new" />}
              onPress={() => Linking.openURL('https://pegasus-app.com/privacy')}
            />
            <Divider />
            <List.Item
              title="Terms of Service"
              right={(props) => <List.Icon {...props} icon="open-in-new" />}
              onPress={() => Linking.openURL('https://pegasus-app.com/terms')}
            />
          </View>
        </List.Section>

        {/* Debug - only in dev */}
        {__DEV__ && (
          <List.Section>
            <List.Subheader>Developer</List.Subheader>
            <View style={{ backgroundColor: theme.colors.surface, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden' }}>
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
            Made with care for better learning
          </Text>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            2026 Pegasus
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}
