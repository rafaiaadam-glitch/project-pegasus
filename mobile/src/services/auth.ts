import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import * as AppleAuthentication from 'expo-apple-authentication';
import { API_URL } from './api';

// Google Sign-In native module — only available in custom dev client, not Expo Go
let GoogleSignin: any = null;
try {
  GoogleSignin = require('@react-native-google-signin/google-signin').GoogleSignin;
} catch {
  // Native module not available
}

const AUTH_TOKEN_KEY = '@pegasus/auth-token';
const AUTH_USER_KEY = '@pegasus/auth-user';

export interface AuthUser {
  id: string;
  email: string;
  displayName?: string;
}

interface AuthResponse {
  token: string;
  user: AuthUser;
}

export async function signInWithApple(): Promise<AuthResponse> {
  const credential = await AppleAuthentication.signInAsync({
    requestedScopes: [
      AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
      AppleAuthentication.AppleAuthenticationScope.EMAIL,
    ],
  });

  if (!credential.identityToken) {
    throw new Error('Apple Sign-In failed: no identity token received.');
  }

  // Apple only provides the name on the first sign-in
  const fullName = credential.fullName
    ? [credential.fullName.givenName, credential.fullName.familyName]
        .filter(Boolean)
        .join(' ')
    : undefined;

  const response = await fetch(`${API_URL}/auth/apple`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      identity_token: credential.identityToken,
      full_name: fullName || null,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Apple sign-in failed' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  const data: AuthResponse = await response.json();
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, data.token);
  await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
  return data;
}

export async function signInWithGoogle(): Promise<AuthResponse> {
  if (!GoogleSignin) {
    throw new Error('Google Sign-In is not available. Please use a custom dev client build.');
  }
  await GoogleSignin.hasPlayServices();
  const signInResult = await GoogleSignin.signIn();
  const idToken = signInResult.data?.idToken;

  if (!idToken) {
    throw new Error('Google Sign-In failed: no ID token received.');
  }

  const response = await fetch(`${API_URL}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Google sign-in failed' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  const data: AuthResponse = await response.json();
  await AsyncStorage.setItem(AUTH_TOKEN_KEY, data.token);
  await AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
  return data;
}

export async function isAppleSignInAvailable(): Promise<boolean> {
  if (Platform.OS !== 'ios') return false;
  return AppleAuthentication.isAvailableAsync();
}

export function isGoogleSignInAvailable(): boolean {
  return GoogleSignin !== null;
}

export async function getStoredToken(): Promise<string | null> {
  return AsyncStorage.getItem(AUTH_TOKEN_KEY);
}

export async function getStoredUser(): Promise<AuthUser | null> {
  const raw = await AsyncStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await AsyncStorage.multiRemove([AUTH_TOKEN_KEY, AUTH_USER_KEY]);
}

export async function isAuthenticated(): Promise<boolean> {
  const token = await getStoredToken();
  return !!token;
}
