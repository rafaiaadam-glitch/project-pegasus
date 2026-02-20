import React, { useState } from 'react';
import {
  View,
  Dimensions,
  Animated,
} from 'react-native';
import {
  Text,
  Button,
  ProgressBar,
  Card,
  TouchableRipple,
} from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

const { width, height } = Dimensions.get('window');

export default function FlashcardViewerScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { cards } = route.params;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [flipAnim] = useState(new Animated.Value(0));

  const currentCard = cards[currentIndex];
  const progress = (currentIndex + 1) / cards.length;

  const flipCard = () => {
    Animated.spring(flipAnim, {
      toValue: isFlipped ? 0 : 180,
      friction: 8,
      tension: 10,
      useNativeDriver: true,
    }).start();
    setIsFlipped(!isFlipped);
  };

  const nextCard = () => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setIsFlipped(false);
      flipAnim.setValue(0);
    }
  };

  const prevCard = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsFlipped(false);
      flipAnim.setValue(0);
    }
  };

  const frontInterpolate = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ['0deg', '180deg'],
  });

  const backInterpolate = flipAnim.interpolate({
    inputRange: [0, 180],
    outputRange: ['180deg', '360deg'],
  });

  const frontOpacity = flipAnim.interpolate({
    inputRange: [89, 90],
    outputRange: [1, 0],
  });

  const backOpacity = flipAnim.interpolate({
    inputRange: [89, 90],
    outputRange: [0, 1],
  });

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {/* Progress Bar */}
      <View style={{ padding: 20, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.outlineVariant }}>
        <ProgressBar progress={progress} style={{ marginBottom: 12, borderRadius: 3 }} />
        <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
          {currentIndex + 1} / {cards.length}
        </Text>
      </View>

      {/* Card Container */}
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 }}>
        <TouchableRipple
          onPress={flipCard}
          style={{ width: width - 40, height: height * 0.5 }}
          borderless
        >
          <View style={{ flex: 1 }}>
            {/* Front of Card */}
            <Animated.View
              style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                borderRadius: 24,
                backgroundColor: theme.colors.surface,
                backfaceVisibility: 'hidden',
                shadowColor: '#000',
                shadowOpacity: 0.1,
                shadowRadius: 20,
                shadowOffset: { width: 0, height: 4 },
                elevation: 8,
                opacity: frontOpacity,
                transform: [{ rotateY: frontInterpolate }],
                borderWidth: 1,
                borderColor: theme.colors.outlineVariant,
              }}
            >
              <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 }}>
                <Chip icon="help-circle-outline" style={{ marginBottom: 24, backgroundColor: theme.colors.secondaryContainer }}>
                  QUESTION
                </Chip>
                <Text variant="headlineSmall" style={{ textAlign: 'center', lineHeight: 36, fontWeight: '600' }}>
                  {currentCard.front}
                </Text>
                <Text variant="bodySmall" style={{ position: 'absolute', bottom: 32, color: theme.colors.onSurfaceVariant, fontStyle: 'italic' }}>
                  Tap card to flip
                </Text>
              </View>
            </Animated.View>

            {/* Back of Card */}
            <Animated.View
              style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                borderRadius: 24,
                backgroundColor: theme.colors.primaryContainer,
                backfaceVisibility: 'hidden',
                shadowColor: '#000',
                shadowOpacity: 0.1,
                shadowRadius: 20,
                shadowOffset: { width: 0, height: 4 },
                elevation: 8,
                opacity: backOpacity,
                transform: [{ rotateY: backInterpolate }],
                borderWidth: 1,
                borderColor: theme.colors.primary,
              }}
            >
              <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 }}>
                <Chip icon="lightbulb-on-outline" style={{ marginBottom: 24, backgroundColor: theme.colors.surface }}>
                  ANSWER
                </Chip>
                <Text variant="headlineSmall" style={{ textAlign: 'center', lineHeight: 36, color: theme.colors.onPrimaryContainer }}>
                  {currentCard.back}
                </Text>
                <Text variant="bodySmall" style={{ position: 'absolute', bottom: 32, color: theme.colors.onPrimaryContainer, fontStyle: 'italic' }}>
                  Tap to see question
                </Text>
              </View>
            </Animated.View>
          </View>
        </TouchableRipple>
      </View>

      {/* Navigation Controls */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', padding: 20, paddingBottom: 40 }}>
        <Button
          mode="elevated"
          onPress={prevCard}
          disabled={currentIndex === 0}
          icon="arrow-left"
          style={{ minWidth: 140 }}
        >
          Previous
        </Button>

        <Button
          mode="elevated"
          onPress={nextCard}
          disabled={currentIndex === cards.length - 1}
          icon="arrow-right"
          contentStyle={{ flexDirection: 'row-reverse' }}
          style={{ minWidth: 140 }}
        >
          Next
        </Button>
      </View>

      {/* Completion Message */}
      {currentIndex === cards.length - 1 && (
        <Card
          style={{
            position: 'absolute',
            bottom: 120,
            left: 20,
            right: 20,
            backgroundColor: theme.colors.primaryContainer,
          }}
          mode="contained"
        >
          <Card.Content style={{ alignItems: 'center' }}>
            <Text variant="titleSmall" style={{ color: theme.colors.onPrimaryContainer }}>
              🎉 Last card! You've reviewed {cards.length} flashcards
            </Text>
          </Card.Content>
        </Card>
      )}
    </View>
  );
}
