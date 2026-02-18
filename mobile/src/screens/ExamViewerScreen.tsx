import React, { useState } from 'react';
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
  RadioButton,
  Chip,
  TouchableRipple,
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
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);

  const currentQuestion = questions[currentIndex];
  const progress = (currentIndex + 1) / questions.length;

  const handleAnswer = (answer: string) => {
    setAnswers({ ...answers, [currentIndex]: answer });
  };

  const nextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
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
      <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }}>
        <View style={{ padding: 24, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.outlineVariant }}>
          <Text variant="headlineMedium" style={{ textAlign: 'center', marginBottom: 24 }}>
            Practice Complete!
          </Text>
          <View style={{ flexDirection: 'row', justifyContent: 'space-around' }}>
            {[
              { value: answeredCount, label: 'Answered' },
              { value: questions.length, label: 'Total' },
              { value: `${completionRate.toFixed(0)}%`, label: 'Complete' },
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
          {questions.map((q: any, idx: number) => (
            <Card key={idx} style={{ marginBottom: 12 }} mode="elevated">
              <Card.Content>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                  <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                    Question {idx + 1}
                  </Text>
                  <Chip
                    compact
                    selectedColor={answers[idx] ? theme.colors.primary : theme.colors.onSurfaceVariant}
                  >
                    {answers[idx] ? '✓ Answered' : '○ Skipped'}
                  </Chip>
                </View>
                <Text variant="bodyMedium" style={{ marginBottom: 8 }}>
                  {q.question}
                </Text>
                {answers[idx] && (
                  <Text variant="bodySmall" style={{ color: theme.colors.primary, fontStyle: 'italic' }}>
                    Your answer: {answers[idx]}
                  </Text>
                )}
              </Card.Content>
            </Card>
          ))}
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
          const isAnswered = !!answers[idx];

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
                  : isAnswered
                  ? theme.colors.primaryContainer
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
                    : isAnswered
                    ? theme.colors.onPrimaryContainer
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
              {currentQuestion.question}
            </Text>

            {currentQuestion.type === 'multiple-choice' && currentQuestion.options && (
              <RadioButton.Group
                onValueChange={handleAnswer}
                value={answers[currentIndex] || ''}
              >
                {currentQuestion.options.map((option: string, idx: number) => {
                  const optionLetter = String.fromCharCode(65 + idx);
                  const isSelected = answers[currentIndex] === optionLetter;

                  return (
                    <TouchableRipple
                      key={idx}
                      onPress={() => handleAnswer(optionLetter)}
                      style={{
                        flexDirection: 'row',
                        alignItems: 'center',
                        padding: 16,
                        backgroundColor: isSelected ? theme.colors.primaryContainer : theme.colors.surfaceVariant,
                        borderRadius: 12,
                        borderWidth: 2,
                        borderColor: isSelected ? theme.colors.primary : 'transparent',
                        marginBottom: 12,
                      }}
                    >
                      <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
                        <View
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 16,
                            backgroundColor: isSelected ? theme.colors.primary : theme.colors.surface,
                            justifyContent: 'center',
                            alignItems: 'center',
                            marginRight: 12,
                          }}
                        >
                          <Text
                            variant="labelLarge"
                            style={{ color: isSelected ? theme.colors.onPrimary : theme.colors.onSurfaceVariant }}
                          >
                            {optionLetter}
                          </Text>
                        </View>
                        <Text
                          variant="bodyMedium"
                          style={{ flex: 1, fontWeight: isSelected ? '600' : '400' }}
                        >
                          {option}
                        </Text>
                      </View>
                    </TouchableRipple>
                  );
                })}
              </RadioButton.Group>
            )}

            {(currentQuestion.type === 'short-answer' ||
              currentQuestion.type === 'essay') && (
              <View style={{ padding: 20, backgroundColor: theme.colors.surfaceVariant, borderRadius: 12, alignItems: 'center' }}>
                <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginBottom: 16 }}>
                  {currentQuestion.type === 'essay'
                    ? 'In an actual exam, you would write your essay answer here.'
                    : 'In an actual exam, you would write your short answer here.'}
                </Text>
                <Button
                  mode={answers[currentIndex] ? 'contained' : 'outlined'}
                  onPress={() =>
                    handleAnswer(answers[currentIndex] ? '' : 'answered')
                  }
                >
                  {answers[currentIndex] ? '✓ Marked as Answered' : 'Mark as Answered'}
                </Button>
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
