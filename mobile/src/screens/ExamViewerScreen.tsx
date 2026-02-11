import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';

interface Props {
  navigation: any;
  route: any;
}

export default function ExamViewerScreen({ navigation, route }: Props) {
  const { questions } = route.params;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;

  const handleAnswer = (answer: string) => {
    setAnswers({ ...answers, [currentIndex]: answer });
  };

  const nextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      // Last question - show results
      Alert.alert(
        'Complete Practice Exam?',
        `You've answered ${Object.keys(answers).length} of ${questions.length} questions.`,
        [
          { text: 'Review', style: 'cancel' },
          {
            text: 'Finish',
            onPress: () => setShowResults(true),
          },
        ]
      );
    }
  };

  const prevQuestion = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const goToQuestion = (index: number) => {
    setCurrentIndex(index);
  };

  const restartExam = () => {
    setAnswers({});
    setCurrentIndex(0);
    setShowResults(false);
  };

  if (showResults) {
    const answeredCount = Object.keys(answers).length;
    const completionRate = (answeredCount / questions.length) * 100;

    return (
      <ScrollView style={styles.container}>
        <View style={styles.resultsHeader}>
          <Text style={styles.resultsTitle}>Practice Complete!</Text>
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{answeredCount}</Text>
              <Text style={styles.statLabel}>Answered</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{questions.length}</Text>
              <Text style={styles.statLabel}>Total</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{completionRate.toFixed(0)}%</Text>
              <Text style={styles.statLabel}>Complete</Text>
            </View>
          </View>
        </View>

        <View style={styles.reviewSection}>
          <Text style={styles.sectionTitle}>Your Answers</Text>
          {questions.map((q: any, idx: number) => (
            <View key={idx} style={styles.reviewCard}>
              <View style={styles.reviewHeader}>
                <Text style={styles.reviewNumber}>Question {idx + 1}</Text>
                <Text
                  style={[
                    styles.reviewStatus,
                    answers[idx]
                      ? styles.reviewStatusAnswered
                      : styles.reviewStatusSkipped,
                  ]}
                >
                  {answers[idx] ? '✓ Answered' : '○ Skipped'}
                </Text>
              </View>
              <Text style={styles.reviewQuestion}>{q.question}</Text>
              {answers[idx] && (
                <Text style={styles.reviewAnswer}>Your answer: {answers[idx]}</Text>
              )}
            </View>
          ))}
        </View>

        <TouchableOpacity style={styles.restartButton} onPress={restartExam}>
          <Text style={styles.restartButtonText}>Practice Again</Text>
        </TouchableOpacity>
      </ScrollView>
    );
  }

  return (
    <View style={styles.container}>
      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${progress}%` }]} />
        </View>
        <Text style={styles.progressText}>
          Question {currentIndex + 1} of {questions.length}
        </Text>
      </View>

      {/* Question Navigator */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.questionNav}
        contentContainerStyle={styles.questionNavContent}
      >
        {questions.map((_: any, idx: number) => (
          <TouchableOpacity
            key={idx}
            style={[
              styles.questionDot,
              currentIndex === idx && styles.questionDotActive,
              answers[idx] && styles.questionDotAnswered,
            ]}
            onPress={() => goToQuestion(idx)}
          >
            <Text
              style={[
                styles.questionDotText,
                currentIndex === idx && styles.questionDotTextActive,
              ]}
            >
              {idx + 1}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Question Content */}
      <ScrollView style={styles.questionContainer}>
        <View style={styles.questionCard}>
          <View style={styles.questionHeader}>
            <Text style={styles.questionType}>{currentQuestion.type || 'Question'}</Text>
            {currentQuestion.points && (
              <Text style={styles.questionPoints}>{currentQuestion.points} pts</Text>
            )}
          </View>

          <Text style={styles.questionText}>{currentQuestion.question}</Text>

          {currentQuestion.type === 'multiple-choice' && currentQuestion.options && (
            <View style={styles.optionsContainer}>
              {currentQuestion.options.map((option: string, idx: number) => {
                const optionLetter = String.fromCharCode(65 + idx); // A, B, C, D
                const isSelected = answers[currentIndex] === optionLetter;

                return (
                  <TouchableOpacity
                    key={idx}
                    style={[styles.option, isSelected && styles.optionSelected]}
                    onPress={() => handleAnswer(optionLetter)}
                  >
                    <View
                      style={[
                        styles.optionCircle,
                        isSelected && styles.optionCircleSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.optionLetter,
                          isSelected && styles.optionLetterSelected,
                        ]}
                      >
                        {optionLetter}
                      </Text>
                    </View>
                    <Text
                      style={[
                        styles.optionText,
                        isSelected && styles.optionTextSelected,
                      ]}
                    >
                      {option}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}

          {(currentQuestion.type === 'short-answer' ||
            currentQuestion.type === 'essay') && (
            <View style={styles.textAnswerContainer}>
              <Text style={styles.textAnswerHint}>
                {currentQuestion.type === 'essay'
                  ? '📝 In an actual exam, you would write your essay answer here.'
                  : '✍️ In an actual exam, you would write your short answer here.'}
              </Text>
              <TouchableOpacity
                style={[
                  styles.markAnsweredButton,
                  answers[currentIndex] && styles.markAnsweredButtonActive,
                ]}
                onPress={() =>
                  handleAnswer(answers[currentIndex] ? '' : 'answered')
                }
              >
                <Text style={styles.markAnsweredText}>
                  {answers[currentIndex] ? '✓ Marked as Answered' : 'Mark as Answered'}
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Navigation Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.navButton, currentIndex === 0 && styles.navButtonDisabled]}
          onPress={prevQuestion}
          disabled={currentIndex === 0}
        >
          <Text style={styles.navButtonText}>← Back</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navButtonPrimary} onPress={nextQuestion}>
          <Text style={styles.navButtonPrimaryText}>
            {currentIndex === questions.length - 1 ? 'Finish' : 'Next →'}
          </Text>
        </TouchableOpacity>
      </View>
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
    backgroundColor: '#34C759',
  },
  progressText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8E8E93',
    textAlign: 'center',
  },
  questionNav: {
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  questionNavContent: {
    padding: 12,
    gap: 8,
  },
  questionDot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#E5E5EA',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 4,
  },
  questionDotActive: {
    backgroundColor: '#007AFF',
  },
  questionDotAnswered: {
    backgroundColor: '#34C759',
  },
  questionDotText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#8E8E93',
  },
  questionDotTextActive: {
    color: '#FFF',
  },
  questionContainer: {
    flex: 1,
  },
  questionCard: {
    margin: 20,
    padding: 24,
    backgroundColor: '#FFF',
    borderRadius: 16,
  },
  questionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  questionType: {
    fontSize: 12,
    fontWeight: '700',
    color: '#007AFF',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  questionPoints: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8E8E93',
  },
  questionText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#000',
    lineHeight: 28,
    marginBottom: 24,
  },
  optionsContainer: {
    gap: 12,
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  optionSelected: {
    backgroundColor: '#E3F2FD',
    borderColor: '#007AFF',
  },
  optionCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#FFF',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  optionCircleSelected: {
    backgroundColor: '#007AFF',
  },
  optionLetter: {
    fontSize: 14,
    fontWeight: '700',
    color: '#8E8E93',
  },
  optionLetterSelected: {
    color: '#FFF',
  },
  optionText: {
    flex: 1,
    fontSize: 15,
    color: '#000',
    lineHeight: 22,
  },
  optionTextSelected: {
    fontWeight: '600',
  },
  textAnswerContainer: {
    padding: 20,
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
    alignItems: 'center',
  },
  textAnswerHint: {
    fontSize: 14,
    color: '#8E8E93',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  markAnsweredButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#FFF',
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  markAnsweredButtonActive: {
    backgroundColor: '#007AFF',
  },
  markAnsweredText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: '#FFF',
    borderTopWidth: 1,
    borderTopColor: '#E5E5EA',
  },
  navButton: {
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 12,
    backgroundColor: '#F2F2F7',
  },
  navButtonDisabled: {
    opacity: 0.3,
  },
  navButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
  },
  navButtonPrimary: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
    backgroundColor: '#007AFF',
  },
  navButtonPrimaryText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  },
  resultsHeader: {
    padding: 24,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5EA',
  },
  resultsTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#000',
    textAlign: 'center',
    marginBottom: 24,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statCard: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 36,
    fontWeight: '700',
    color: '#007AFF',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 13,
    color: '#8E8E93',
    fontWeight: '600',
  },
  reviewSection: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#000',
    marginBottom: 16,
  },
  reviewCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  reviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  reviewNumber: {
    fontSize: 14,
    fontWeight: '700',
    color: '#007AFF',
  },
  reviewStatus: {
    fontSize: 13,
    fontWeight: '600',
  },
  reviewStatusAnswered: {
    color: '#34C759',
  },
  reviewStatusSkipped: {
    color: '#8E8E93',
  },
  reviewQuestion: {
    fontSize: 15,
    color: '#000',
    lineHeight: 22,
    marginBottom: 8,
  },
  reviewAnswer: {
    fontSize: 14,
    color: '#007AFF',
    fontStyle: 'italic',
  },
  restartButton: {
    margin: 20,
    padding: 18,
    backgroundColor: '#007AFF',
    borderRadius: 12,
    alignItems: 'center',
  },
  restartButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  },
});
