import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  PanResponder,
  TouchableOpacity,
  Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme';

interface SwipeAction {
  icon: string;
  color: string;
  onPress: () => void;
  haptic?: boolean;
}

interface Props {
  children: React.ReactNode;
  leftActions?: SwipeAction[];
  rightActions?: SwipeAction[];
  swipeThreshold?: number;
  onSwipeStart?: () => void;
  onSwipeEnd?: () => void;
}

export default function SwipeableRow({
  children,
  leftActions = [],
  rightActions = [],
  swipeThreshold = 80,
  onSwipeStart,
  onSwipeEnd,
}: Props) {
  const { theme } = useTheme();
  const translateX = useRef(new Animated.Value(0)).current;
  const lastOffset = useRef(0);

  const triggerHaptic = async () => {
    if (Platform.OS !== 'web') {
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      } catch (error) {
        console.warn('Haptics not available:', error);
      }
    }
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (_, gestureState) => {
        return Math.abs(gestureState.dx) > 10;
      },
      onPanResponderGrant: () => {
        if (onSwipeStart) onSwipeStart();
      },
      onPanResponderMove: (_, gestureState) => {
        const newValue = lastOffset.current + gestureState.dx;
        const maxLeft = leftActions.length * 80;
        const maxRight = rightActions.length * -80;

        const clampedValue = Math.max(maxRight, Math.min(maxLeft, newValue));
        translateX.setValue(clampedValue);
      },
      onPanResponderRelease: (_, gestureState) => {
        const velocity = gestureState.vx;
        const offset = lastOffset.current + gestureState.dx;

        // Determine if action should be triggered
        let targetValue = 0;
        let triggeredAction: SwipeAction | null = null;

        if (offset > swipeThreshold && leftActions.length > 0) {
          const actionIndex = Math.min(
            Math.floor(offset / 80),
            leftActions.length - 1
          );
          triggeredAction = leftActions[actionIndex];
          targetValue = 0;
        } else if (offset < -swipeThreshold && rightActions.length > 0) {
          const actionIndex = Math.min(
            Math.floor(Math.abs(offset) / 80),
            rightActions.length - 1
          );
          triggeredAction = rightActions[actionIndex];
          targetValue = 0;
        }

        Animated.spring(translateX, {
          toValue: targetValue,
          useNativeDriver: true,
          velocity,
          tension: 40,
          friction: 8,
        }).start(() => {
          lastOffset.current = targetValue;
          if (onSwipeEnd) onSwipeEnd();

          if (triggeredAction) {
            if (triggeredAction.haptic !== false) {
              triggerHaptic();
            }
            triggeredAction.onPress();
          }
        });
      },
    })
  ).current;

  const renderActions = (actions: SwipeAction[], side: 'left' | 'right') => {
    if (actions.length === 0) return null;

    return (
      <View style={[styles.actionsContainer, side === 'left' ? styles.leftActions : styles.rightActions]}>
        {actions.map((action, index) => (
          <TouchableOpacity
            key={index}
            style={[styles.actionButton, { backgroundColor: action.color }]}
            onPress={() => {
              Animated.spring(translateX, {
                toValue: 0,
                useNativeDriver: true,
              }).start();
              lastOffset.current = 0;

              if (action.haptic !== false) {
                triggerHaptic();
              }
              action.onPress();
            }}
          >
            <Text style={styles.actionIcon}>{action.icon}</Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      {renderActions(leftActions, 'left')}
      {renderActions(rightActions, 'right')}

      <Animated.View
        style={[
          styles.content,
          {
            transform: [{ translateX }],
          },
        ]}
        {...panResponder.panHandlers}
      >
        {children}
      </Animated.View>
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      position: 'relative',
      marginBottom: 12,
    },
    content: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    actionsContainer: {
      position: 'absolute',
      top: 0,
      bottom: 0,
      flexDirection: 'row',
      alignItems: 'center',
    },
    leftActions: {
      left: 0,
    },
    rightActions: {
      right: 0,
    },
    actionButton: {
      width: 80,
      height: '100%',
      justifyContent: 'center',
      alignItems: 'center',
    },
    actionIcon: {
      fontSize: 28,
    },
  });
