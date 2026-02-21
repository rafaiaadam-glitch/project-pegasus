import React, { useState, useEffect } from 'react';
import {
  View,
  Platform,
  StyleSheet,
  Alert,
} from 'react-native';
import { Text, Button, ActivityIndicator } from 'react-native-paper';
import * as AppleAuthentication from 'expo-apple-authentication';
import { useTheme } from '../theme';
import {
  signInWithApple,
  signInWithGoogle,
  isAppleSignInAvailable,
  isGoogleSignInAvailable,
} from '../services/auth';
import api from '../services/api';

interface Props {
  onAuthenticated: () => void;
}

export default function AuthScreen({ onAuthenticated }: Props) {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(false);
  const [appleAvailable, setAppleAvailable] = useState(false);
  const googleAvailable = isGoogleSignInAvailable();

  useEffect(() => {
    isAppleSignInAvailable().then(setAppleAvailable);
  }, []);

  const handleAppleSignIn = async () => {
    try {
      setLoading(true);
      await signInWithApple();
      await api.refreshAuthToken();
      onAuthenticated();
    } catch (error: any) {
      // User cancelled — AppleAuthentication throws ERR_CANCELED
      if (error.code === 'ERR_CANCELED') return;
      Alert.alert('Sign In Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      setLoading(true);
      await signInWithGoogle();
      await api.refreshAuthToken();
      onAuthenticated();
    } catch (error: any) {
      // User cancelled
      if (
        error.code === 'SIGN_IN_CANCELLED' ||
        error.code === 'ERR_CANCELED'
      )
        return;
      Alert.alert('Sign In Failed', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={styles.header}>
        <Text style={styles.emoji}>🦅</Text>
        <Text variant="headlineLarge" style={styles.title}>
          Pegasus
        </Text>
        <Text
          variant="bodyLarge"
          style={[styles.subtitle, { color: theme.colors.onSurfaceVariant }]}
        >
          Your lecture companion
        </Text>
      </View>

      <View style={styles.buttons}>
        {appleAvailable && (
          <AppleAuthentication.AppleAuthenticationButton
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={8}
            style={styles.appleButton}
            onPress={handleAppleSignIn}
          />
        )}

        {googleAvailable && (
          <Button
            mode="outlined"
            onPress={handleGoogleSignIn}
            disabled={loading}
            icon="google"
            style={styles.googleButton}
            labelStyle={styles.googleLabel}
            contentStyle={styles.googleContent}
          >
            Sign in with Google
          </Button>
        )}

        {loading && (
          <ActivityIndicator
            animating
            size="small"
            style={styles.spinner}
          />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 64,
  },
  emoji: {
    fontSize: 64,
    marginBottom: 12,
  },
  title: {
    fontWeight: '700',
  },
  subtitle: {
    marginTop: 4,
  },
  buttons: {
    gap: 16,
  },
  appleButton: {
    height: 50,
    width: '100%',
  },
  googleButton: {
    borderRadius: 8,
    borderWidth: 1,
  },
  googleLabel: {
    fontSize: 16,
  },
  googleContent: {
    height: 50,
  },
  spinner: {
    marginTop: 8,
  },
});
