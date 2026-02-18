
import { MD3LightTheme, MD3DarkTheme } from 'react-native-paper';
import { lightColors, darkColors } from './colors';

export const CombinedLightTheme = {
  ...MD3LightTheme,
  // Top-level access for screens using theme.primary, theme.background, etc.
  ...lightColors,
  colors: {
    ...MD3LightTheme.colors,
    ...lightColors,
  },
};

export const CombinedDarkTheme = {
  ...MD3DarkTheme,
  // Top-level access for screens using theme.primary, theme.background, etc.
  ...darkColors,
  colors: {
    ...MD3DarkTheme.colors,
    ...darkColors,
  },
};
