import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { CombinedLightTheme, CombinedDarkTheme } from './paperTheme';
import { MD3Theme } from 'react-native-paper';

type ThemeMode = 'light' | 'dark' | 'auto';

interface ThemeContextType {
  theme: MD3Theme;
  mode: ThemeMode;
  isDark: boolean;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const THEME_STORAGE_KEY = '@pegasus_theme_mode';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const systemColorScheme = useColorScheme();
  const [mode, setMode] = useState<ThemeMode>('auto');

  // Load saved theme preference on mount
  useEffect(() => {
    const loadThemePreference = async () => {
      try {
        const savedMode = await AsyncStorage.getItem(THEME_STORAGE_KEY);
        if (savedMode === 'light' || savedMode === 'dark' || savedMode === 'auto') {
          setMode(savedMode);
        }
      } catch (error) {
        console.error('Failed to load theme preference:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadThemePreference();
  }, []);

  if (isLoading) {
    return null;
  }

  const setThemeMode = async (newMode: ThemeMode) => {
    try {
      await AsyncStorage.setItem(THEME_STORAGE_KEY, newMode);
      setMode(newMode);
    } catch (error) {
      console.error('Failed to save theme preference:', error);
    }
  };

  const toggleTheme = () => {
    const newMode = mode === 'dark' ? 'light' : 'dark';
    setThemeMode(newMode);
  };

  // Determine if dark mode should be active
  const isDark = mode === 'dark' || (mode === 'auto' && systemColorScheme === 'dark');
  const theme = isDark ? CombinedDarkTheme : CombinedLightTheme;

  return (
    <ThemeContext.Provider
      value={{
        theme,
        mode,
        isDark,
        setThemeMode,
        toggleTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
