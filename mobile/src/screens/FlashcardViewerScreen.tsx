import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Animated,
} from 'react-native';

interface Props {
  navigation: any;
  route: any;
}

const { width, height } = Dimensions.get('window');

export default function FlashcardViewerScreen({ navigation, route }: Props) {
  const { cards } = route.params;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [flipAnim] = useState(new Animated.Value(0));

  const currentCard = cards[currentIndex];
  const progress = ((currentIndex + 1) / cards.length) * 100;

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
    <View style={styles.container}>
      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>
          {currentIndex + 1} / {cards.length}
        </Text>
      </View>

      {/* Card Container */}
      <View style={styles.cardContainer}>
        <TouchableOpacity
          style={styles.cardTouchArea}
          onPress={flipCard}
          activeOpacity={0.9}
        >
          {/* Front of Card */}
          <Animated.View
            style={[
              styles.card,
              styles.cardFront,
              {
                opacity: frontOpacity,
                transform: [{ rotateY: frontInterpolate }],
              },
            ]}
          >
            <View style={styles.cardContent}>
              <Text style={styles.cardLabel}>QUESTION</Text>
              <Text style={styles.cardText}>{currentCard.front}</Text>
              <Text style={styles.tapHint}>Tap to reveal answer</Text>
            </View>
          </Animated.View>

          {/* Back of Card */}
          <Animated.View
            style={[
              styles.card,
              styles.cardBack,
              {
                opacity: backOpacity,
                transform: [{ rotateY: backInterpolate }],
              },
            ]}
          >
            <View style={styles.cardContent}>
              <Text style={[styles.cardLabel, styles.answerLabel]}>ANSWER</Text>
              <Text style={styles.cardText}>{currentCard.back}</Text>
              <Text style={styles.tapHint}>Tap to see question</Text>
            </View>
          </Animated.View>
        </TouchableOpacity>
      </View>

      {/* Navigation Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.navButton, currentIndex === 0 && styles.navButtonDisabled]}
          onPress={prevCard}
          disabled={currentIndex === 0}
        >
          <Text style={styles.navButtonText}>← Previous</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.navButton,
            currentIndex === cards.length - 1 && styles.navButtonDisabled,
          ]}
          onPress={nextCard}
          disabled={currentIndex === cards.length - 1}
        >
          <Text style={styles.navButtonText}>Next →</Text>
        </TouchableOpacity>
      </View>

      {/* Completion Message */}
      {currentIndex === cards.length - 1 && (
        <View style={styles.completionBanner}>
          <Text style={styles.completionText}>
            🎉 Last card! You've reviewed {cards.length} flashcards
          </Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  progressContainer: {
    padding: 20,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#E5E5EA',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 12,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
  },
  progressText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8E8E93',
    textAlign: 'center',
  },
  cardContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  cardTouchArea: {
    width: width - 40,
    height: height * 0.5,
  },
  card: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    borderRadius: 24,
    backgroundColor: '#FFF',
    backfaceVisibility: 'hidden',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  cardFront: {},
  cardBack: {
    backgroundColor: '#007AFF',
  },
  cardContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#8E8E93',
    letterSpacing: 1,
    marginBottom: 24,
  },
  answerLabel: {
    color: '#FFFFFF80',
  },
  cardText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#000',
    textAlign: 'center',
    lineHeight: 36,
  },
  tapHint: {
    position: 'absolute',
    bottom: 32,
    fontSize: 13,
    color: '#8E8E93',
    fontStyle: 'italic',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
    paddingBottom: 40,
  },
  navButton: {
    backgroundColor: '#FFF',
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 12,
    minWidth: 140,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  navButtonDisabled: {
    opacity: 0.3,
  },
  navButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  completionBanner: {
    position: 'absolute',
    bottom: 120,
    left: 20,
    right: 20,
    backgroundColor: '#34C759',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  completionText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#FFF',
  },
});
