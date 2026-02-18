import { Platform } from 'react-native';
import * as Haptics from 'expo-haptics';

export enum HapticType {
  Light = 'light',
  Medium = 'medium',
  Heavy = 'heavy',
  Success = 'success',
  Warning = 'warning',
  Error = 'error',
}

// Trigger haptic feedback
export const triggerHaptic = async (type: HapticType = HapticType.Medium): Promise<void> => {
  if (Platform.OS === 'web') return;

  try {
    switch (type) {
      case HapticType.Light:
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        break;
      case HapticType.Medium:
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
        break;
      case HapticType.Heavy:
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        break;
      case HapticType.Success:
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        break;
      case HapticType.Warning:
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        break;
      case HapticType.Error:
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        break;
    }
  } catch (error) {
    console.warn('Haptics not available:', error);
  }
};

// Gesture direction detection
export interface GestureDirection {
  horizontal: 'left' | 'right' | 'none';
  vertical: 'up' | 'down' | 'none';
}

export const detectGestureDirection = (
  dx: number,
  dy: number,
  threshold: number = 10
): GestureDirection => {
  const horizontal = Math.abs(dx) > threshold
    ? dx > 0 ? 'right' : 'left'
    : 'none';

  const vertical = Math.abs(dy) > threshold
    ? dy > 0 ? 'down' : 'up'
    : 'none';

  return { horizontal, vertical };
};

// Gesture velocity detection for quick actions
export const isQuickGesture = (velocity: number, threshold: number = 0.5): boolean => {
  return Math.abs(velocity) > threshold;
};

// Double tap detection helper
export class DoubleTapDetector {
  private lastTap: number = 0;
  private readonly delay: number;

  constructor(delay: number = 300) {
    this.delay = delay;
  }

  detect(callback: () => void): void {
    const now = Date.now();
    if (now - this.lastTap < this.delay) {
      callback();
      this.lastTap = 0;
    } else {
      this.lastTap = now;
    }
  }

  reset(): void {
    this.lastTap = 0;
  }
}

// Swipe threshold calculator based on screen size
export const calculateSwipeThreshold = (screenWidth: number): number => {
  return Math.min(100, screenWidth * 0.25);
};

// Gesture shortcuts configuration
export interface GestureShortcut {
  id: string;
  gesture: 'swipe-left' | 'swipe-right' | 'swipe-up' | 'swipe-down' | 'double-tap' | 'long-press';
  action: () => void;
  haptic?: HapticType;
  enabled: boolean;
}

export class GestureShortcutManager {
  private shortcuts: Map<string, GestureShortcut> = new Map();

  register(shortcut: GestureShortcut): void {
    this.shortcuts.set(shortcut.id, shortcut);
  }

  unregister(id: string): void {
    this.shortcuts.delete(id);
  }

  getShortcut(id: string): GestureShortcut | undefined {
    return this.shortcuts.get(id);
  }

  getAllShortcuts(): GestureShortcut[] {
    return Array.from(this.shortcuts.values());
  }

  executeShortcut(id: string): void {
    const shortcut = this.shortcuts.get(id);
    if (shortcut && shortcut.enabled) {
      if (shortcut.haptic) {
        triggerHaptic(shortcut.haptic);
      }
      shortcut.action();
    }
  }

  clear(): void {
    this.shortcuts.clear();
  }
}

// Global gesture manager instance
export const globalGestureManager = new GestureShortcutManager();
