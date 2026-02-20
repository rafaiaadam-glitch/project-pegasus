import React, { useState, useMemo } from 'react';
import {
  View,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Text,
  Button,
  ProgressBar,
  Card,
  Chip,
  TouchableRipple,
  Divider,
} from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

export default function ExamViewerScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { questions } = route.params;
  const [currentIndex, setCurrentIndex] = useState(0);
  // MC/true-false: question index → selected choice index
  const [selectedChoices, setSelectedChoices] = useState<Record<number, number>>({});
  // Short-answer/essay: question index → marked as answered
  const [markedAnswered, setMarkedAnswered] = useState<Record<number, boolean>>({});
  const [showResults, setShowResults] = useState(false);

  if (!questions || questions.length === 0) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background, padding: 32 }}>
        <Text style={{ fontSize: 48, marginBottom: 12 }}>{'📝'}</Text>
        <Text variant="titleMedium" style={{ marginBottom: 8, textAlign: 'center' }}>No practice questions available</Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
          Generate study materials from a lecture to see practice questions here.
        </Text>
      </View>
    );
  }

  const currentQuestion = questions[currentIndex];
  const progress = (currentIndex + 1) / questions.length;
  const isMCType = currentQuestion.type === 'multiple-choice' || currentQuestion.type === 'true-false';
  const currentMCAnswered = isMCType && currentIndex in selectedChoices;

  const handleMCAnswer = (choiceIndex: number) => {
    if (currentIndex in selectedChoices) return; // lock after first answer
    setSelectedChoices({ ...selectedChoices, [currentIndex]: choiceIndex });
  };

  const toggleMarkAnswered = () => {
    setMarkedAnswered({
      ...markedAnswered,
      [currentIndex]: !markedAnswered[currentIndex],
    });
  };

  const nextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      const answered = Object.keys(selectedChoices).length +
        Object.values(markedAnswered).filter(Boolean).length;
      Alert.alert(
        'Complete Practice Exam?',
        `You've answered ${answered} of ${questions.length} questions.`,
        [
          { text: 'Review', style: 'cancel' },
          { text: 'Finish', onPress: () => setShowResults(true) },
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
    setSelectedChoices({});
    setMarkedAnswered({});
    setCurrentIndex(0);
    setShowResults(false);
  };

  const { correctCount, totalMC, answeredCount } = useMemo(() => {
    let correct = 0;
    let mcCount = 0;
    questions.forEach((q: any, idx: number) => {
      if (q.type === 'multiple-choice' || q.type === 'true-false') {
        mcCount++;
        if (idx in selectedChoices && selectedChoices[idx] === q.correctChoiceIndex) {
          correct++;
        }
      }
    });
    const answered = Object.keys(selectedChoices).length +
      Object.values(markedAnswered).filter(Boolean).length;
    return { correctCount: correct, totalMC: mcCount, answeredCount: answered };
  }, [questions, selectedChoices, markedAnswered]);

  if (showResults) {
    const scorePercent = totalMC > 0 ? (correctCount / totalMC) * 100 : 0;

    return (
      <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }}>
        <View style={{ padding: 24, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.outlineVariant }}>
          <Text variant="headlineMedium" style={{ textAlign: 'center', marginBottom: 24 }}>
            Practice Complete!
          </Text>
          <View style={{ flexDirection: 'row', justifyContent: 'space-around' }}>
            {[
              { value: `${correctCount}/${totalMC}`, label: 'Score' },
              { value: `${scorePercent.toFixed(0)}%`, label: 'Accuracy' },
              { value: answeredCount, label: 'Answered' },
            ].map((stat, idx) => (
              <View key={idx} style={{ alignItems: 'center' }}>
                <Text variant="displaySmall" style={{ color: theme.colors.primary, fontWeight: '700', marginBottom: 4 }}>
                  {stat.value}
                </Text>
                <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                  {stat.label}
                </Text>
              </View>
            ))}
          </View>
        </View>

        <View style={{ padding: 20 }}>
          <Text variant="titleLarge" style={{ marginBottom: 16 }}>Your Answers</Text>
          {questions.map((q: any, idx: number) => {
            const isMC = q.type === 'multiple-choice' || q.type === 'true-false';
            const wasAnswered = isMC ? idx in selectedChoices : !!markedAnswered[idx];
            const isCorrect = isMC && wasAnswered && selectedChoices[idx] === q.correctChoiceIndex;
            const correctAnswer = isMC && q.choices ? q.choices[q.correctChoiceIndex] : q.answer;

            return (
              <Card key={idx} style={{ marginBottom: 12 }} mode="elevated">
                <Card.Content>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                    <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                      Question {idx + 1}
                    </Text>
                    <Chip
                      compact
                      selectedColor={
                        !wasAnswered ? theme.colors.onSurfaceVariant :
                        isMC ? (isCorrect ? '#4CAF50' : '#F44336') :
                        theme.colors.primary
                      }
                    >
                      {!wasAnswered ? '○ Skipped' : isMC ? (isCorrect ? '✓ Correct' : '✗ Incorrect') : '✓ Answered'}
                    </Chip>
                  </View>
                  <Text variant="bodyMedium" style={{ marginBottom: 8 }}>
                    {q.prompt}
                  </Text>
                  {isMC && wasAnswered && (
                    <View>
                      <Text variant="bodySmall" style={{ color: isCorrect ? '#4CAF50' : '#F44336', fontStyle: 'italic' }}>
                        Your answer: {q.choices?.[selectedChoices[idx]]}
                      </Text>
                      {!isCorrect && (
                        <Text variant="bodySmall" style={{ color: '#4CAF50', fontStyle: 'italic' }}>
                          Correct answer: {correctAnswer}
                        </Text>
                      )}
                    </View>
                  )}
                  {q.explanation && (
                    <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
                      {q.explanation}
                    </Text>
                  )}
                </Card.Content>
              </Card>
            );
          })}
        </View>

        <Button
          mode="contained"
          onPress={restartExam}
          style={{ marginHorizontal: 20, marginBottom: 40 }}
          contentStyle={{ paddingVertical: 8 }}
        >
          Practice Again
        </Button>
      </ScrollView>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {/* Progress Bar */}
      <View style={{ padding: 20, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.outlineVariant }}>
        <ProgressBar progress={progress} style={{ marginBottom: 12, borderRadius: 3 }} />
        <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
          Question {currentIndex + 1} of {questions.length}
        </Text>
      </View>

      {/* Question Navigator */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.outlineVariant, flexGrow: 0 }}
        contentContainerStyle={{ padding: 12, gap: 8 }}
      >
        {questions.map((_: any, idx: number) => {
          const isActive = currentIndex === idx;
          const qIsMC = questions[idx].type === 'multiple-choice' || questions[idx].type === 'true-false';
          const wasAnswered = qIsMC ? idx in selectedChoices : !!markedAnswered[idx];
          const wasCorrect = qIsMC && wasAnswered && selectedChoices[idx] === questions[idx].correctChoiceIndex;

          return (
            <TouchableRipple
              key={idx}
              onPress={() => goToQuestion(idx)}
              style={{
                width: 36,
                height: 36,
                borderRadius: 18,
                backgroundColor: isActive
                  ? theme.colors.primary
                  : wasAnswered
                  ? (qIsMC ? (wasCorrect ? '#4CAF50' : '#F44336') : theme.colors.primaryContainer)
                  : theme.colors.surfaceVariant,
                justifyContent: 'center',
                alignItems: 'center',
                marginHorizontal: 4,
              }}
              borderless
            >
              <Text
                variant="labelMedium"
                style={{
                  color: isActive
                    ? theme.colors.onPrimary
                    : wasAnswered
                    ? '#FFFFFF'
                    : theme.colors.onSurfaceVariant,
                }}
              >
                {idx + 1}
              </Text>
            </TouchableRipple>
          );
        })}
      </ScrollView>

      {/* Question Content */}
      <ScrollView style={{ flex: 1 }}>
        <Card style={{ margin: 20 }} mode="elevated">
          <Card.Content>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 }}>
              <Chip compact>{currentQuestion.type || 'Question'}</Chip>
              {currentQuestion.points && (
                <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                  {currentQuestion.points} pts
                </Text>
              )}
            </View>

            <Text variant="titleMedium" style={{ lineHeight: 28, marginBottom: 24 }}>
              {currentQuestion.prompt}
            </Text>

            {isMCType && currentQuestion.choices && (
              <View>
                {currentQuestion.choices.map((choice: string, idx: number) => {
                  const optionLetter = String.fromCharCode(65 + idx);
                  const isSelected = selectedChoices[currentIndex] === idx;
                  const isCorrectChoice = idx === currentQuestion.correctChoiceIndex;
                  const showResult = currentMCAnswered;

                  let bgColor = theme.colors.surfaceVariant;
                  let borderColor = 'transparent';

                  if (showResult) {
                    if (isCorrectChoice) {
                      bgColor = '#E8F5E9';
                      borderColor = '#4CAF50';
                    } else if (isSelected) {
                      bgColor = '#FFEBEE';
                      borderColor = '#F44336';
                    }
                  } else if (isSelected) {
                    bgColor = theme.colors.primaryContainer;
                    borderColor = theme.colors.primary;
                  }

                  return (
                    <TouchableRipple
                      key={idx}
                      onPress={() => handleMCAnswer(idx)}
                      disabled={currentMCAnswered}
                      style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        padding: 16,
                        backgroundColor: bgColor,
                        borderRadius: 12,
                        borderWidth: 2,
                        borderColor: borderColor,
                        marginBottom: 12,
                        opacity: currentMCAnswered && !isSelected && !isCorrectChoice ? 0.6 : 1,
                      }}
                    >
                      <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
                        <View
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 16,
                            backgroundColor: showResult
                              ? (isCorrectChoice ? '#4CAF50' : isSelected ? '#F44336' : theme.colors.surface)
                              : (isSelected ? theme.colors.primary : theme.colors.surface),
                            justifyContent: 'center',
                            alignItems: 'center',
                            marginRight: 12,
                          }}
                        >
                          <Text
                            variant="labelLarge"
                            style={{
                              color: (showResult && (isCorrectChoice || isSelected)) || (!showResult && isSelected)
                                ? '#FFFFFF'
                                : theme.colors.onSurfaceVariant,
                            }}
                          >
                            {showResult && isCorrectChoice ? '✓' : showResult && isSelected ? '✗' : optionLetter}
                          </Text>
                        </View>
                        <Text
                          variant="bodyMedium"
                          style={{ flex: 1, fontWeight: isSelected || (showResult && isCorrectChoice) ? '600' : '400' }}
                        >
                          {choice}
                        </Text>
                      </View>
                    </TouchableRipple>
                  );
                })}

                {currentMCAnswered && currentQuestion.explanation && (
                  <View style={{
                    backgroundColor: theme.colors.surfaceVariant,
                    padding: 16,
                    borderRadius: 12,
                    marginTop: 4,
                  }}>
                    <Text variant="labelLarge" style={{ marginBottom: 4 }}>Explanation</Text>
                    <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                      {currentQuestion.explanation}
                    </Text>
                  </View>
                )}
              </View>
            )}

            {(currentQuestion.type === 'short-answer' ||
              currentQuestion.type === 'essay') && (
              <View style={{ padding: 20, backgroundColor: theme.colors.surfaceVariant, borderRadius: 12 }}>
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 16, fontStyle: 'italic' }}>
                  {currentQuestion.type === 'essay'
                    ? 'Draft your essay answer here (mental or written notes).'
                    : 'Draft your short answer here.'}
                </Text>

                <Button
                  mode={markedAnswered[currentIndex] ? 'contained' : 'outlined'}
                  onPress={toggleMarkAnswered}
                  style={{ marginBottom: 16 }}
                >
                  {markedAnswered[currentIndex] ? '✓ Marked as Answered' : 'Mark as Answered'}
                </Button>

                <Divider style={{ marginBottom: 16 }} />

                <Text variant="labelLarge" style={{ marginBottom: 8 }}>Ideal Answer Key:</Text>
                <View style={{ backgroundColor: theme.colors.surface, padding: 12, borderRadius: 8 }}>
                   <Text variant="bodyMedium">{currentQuestion.answer}</Text>
                </View>

                {currentQuestion.explanation && (
                  <View style={{ marginTop: 12 }}>
                    <Text variant="labelLarge" style={{ marginBottom: 4 }}>Explanation</Text>
                    <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
                      {currentQuestion.explanation}
                    </Text>
                  </View>
                )}
              </View>
            )}
          </Card.Content>
        </Card>
      </ScrollView>

      {/* Navigation Controls */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', padding: 20, backgroundColor: theme.colors.surface, borderTopWidth: 1, borderTopColor: theme.colors.outlineVariant }}>
        <Button
          mode="elevated"
          onPress={prevQuestion}
          disabled={currentIndex === 0}
          icon="arrow-left"
        >
          Back
        </Button>

        <Button
          mode="contained"
          onPress={nextQuestion}
          icon={currentIndex === questions.length - 1 ? 'check' : 'arrow-right'}
          contentStyle={{ flexDirection: 'row-reverse' }}
        >
          {currentIndex === questions.length - 1 ? 'Finish' : 'Next'}
        </Button>
      </View>
    </View>
  );
}
