// Color definitions for light and dark themes

export interface ThemeColors {
  // Backgrounds
  background: string;
  surface: string;
  surfaceSecondary: string;

  // Text
  text: string;
  textSecondary: string;
  textTertiary: string;

  // Primary
  primary: string;
  primaryLight: string;

  // Status colors
  success: string;
  warning: string;
  error: string;
  info: string;

  // Borders
  border: string;
  borderLight: string;

  // Shadows (for card elevation)
  shadowColor: string;

  // Input
  inputBackground: string;
  placeholder: string;
}

export const lightColors: ThemeColors = {
  // Backgrounds
  background: '#F2F2F7',
  surface: '#FFFFFF',
  surfaceSecondary: '#F2F2F7',

  // Text
  text: '#000000',
  textSecondary: '#3A3A3C',
  textTertiary: '#8E8E93',

  // Primary - Gray/Monochrome Theme
  primary: '#636366', // System Gray
  primaryLight: '#63636620',

  // Status colors
  success: '#34C759',
  warning: '#FF9500',
  error: '#FF3B30',
  info: '#8E8E93',

  // Borders
  border: '#E5E5EA',
  borderLight: '#E5E5E5',

  // Shadows
  shadowColor: '#000000',

  // Input
  inputBackground: '#F2F2F7',
  placeholder: '#8E8E93',
};

export const darkColors: ThemeColors = {
  // Backgrounds
  background: '#000000',
  surface: '#1C1C1E',
  surfaceSecondary: '#2C2C2E',

  // Text
  text: '#FFFFFF',
  textSecondary: '#EBEBF5',
  textTertiary: '#8E8E93',

  // Primary - Gray/Monochrome Theme (Lighter for Dark Mode)
  primary: '#AEAEB2', // System Gray 2
  primaryLight: '#AEAEB220',

  // Status colors
  success: '#30D158',
  warning: '#FF9F0A',
  error: '#FF453A',
  info: '#8E8E93',

  // Borders
  border: '#38383A',
  borderLight: '#48484A',

  // Shadows
  shadowColor: '#000000',

  // Input
  inputBackground: '#2C2C2E',
  placeholder: '#8E8E93',
};
