import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  Alert,
} from 'react-native';
import {
  SegmentedButtons,
  Card,
  Text,
  Button,
  ProgressBar,
  ActivityIndicator,
  Chip,
  Dialog,
  Portal,
  List,
  IconButton,
} from 'react-native-paper';
import api from '../services/api';
import { useTheme } from '../theme';
import NetworkErrorView from '../components/NetworkErrorView';

import * as ExportUtils from '../services/exportUtils';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { lectureId, lectureTitle } = route.params;
  const [activeTab, setActiveTab] = useState('artifacts');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatingStage, setGeneratingStage] = useState('');
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    navigation.setOptions({
      title: lectureTitle || 'Lecture Details',
      headerRight: () => (
        <IconButton
          icon="share-variant"
          onPress={() => setShowExportMenu(true)}
        />
      ),
    });
    loadData();
  }, [lectureId]);

  useEffect(() => {
    const status = summary?.lecture?.status;
    if (status === 'uploaded' || status === 'transcribing') {
      const timer = setInterval(() => loadData(), 3000);
      return () => clearInterval(timer);
    }
  }, [summary?.lecture?.status]);

  const loadData = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const [summaryData, artifactsData, progressData] = await Promise.all([
        api.getLectureSummary(lectureId),
        api.getLectureArtifacts(lectureId),
        api.getLectureProgress(lectureId),
      ]);
      setSummary(summaryData);
      setArtifacts(artifactsData);
      setProgress(progressData);
    } catch (err) {
      console.error('Error loading lecture data:', err);
      setLoadError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setGeneratingStage('Sending to AI...');
      const courseId = summary?.lecture?.course_id || route.params?.courseId;
      const presetId = summary?.lecture?.preset_id || 'exam-mode';

      const stages = [
        { delay: 2000, msg: 'AI is thinking deeply...' },
        { delay: 10000, msg: 'Reasoning through concepts...' },
        { delay: 25000, msg: 'Building flashcards & exam questions...' },
        { delay: 45000, msg: 'Almost done — finalizing study guide...' },
      ];
      const timers = stages.map(({ delay, msg }) =>
        setTimeout(() => setGeneratingStage(msg), delay)
      );

      await api.generateArtifacts(lectureId, { course_id: courseId, preset_id: presetId });
      timers.forEach(clearTimeout);

      setGeneratingStage('Done!');
      await loadData();
      setActiveTab('artifacts');
    } catch (error: any) {
      Alert.alert('Generation Failed', error.message || 'Could not generate artifacts');
    } finally {
      setGenerating(false);
      setGeneratingStage('');
    }
  };

  const handleExport = async (type: 'all' | 'summary' | 'flashcards' | 'questions') => {
    try {
      setExporting(true);
      setShowExportMenu(false);

      switch (type) {
        case 'all':
          if (artifacts?.artifacts) {
            await ExportUtils.exportAllArtifacts(
              artifacts.artifacts,
              lectureTitle,
              route.params.courseTitle
            );
            Alert.alert('Success', 'All artifacts exported successfully!');
          }
          break;
        case 'summary':
          if (artifacts?.artifacts?.summary) {
            await ExportUtils.exportSummary(
              artifacts.artifacts.summary,
              lectureTitle,
              route.params.courseTitle
            );
            Alert.alert('Success', 'Summary exported successfully!');
          }
          break;
        case 'flashcards':
          if (artifacts?.artifacts?.flashcards) {
            await ExportUtils.exportFlashcards(
              artifacts.artifacts.flashcards,
              lectureTitle
            );
            Alert.alert('Success', 'Flashcards exported as Anki CSV!');
          }
          break;
        case 'questions':
          if (artifacts?.artifacts['exam-questions']) {
            await ExportUtils.exportExamQuestions(
              artifacts.artifacts['exam-questions'],
              lectureTitle,
              route.params.courseTitle
            );
            Alert.alert('Success', 'Exam questions exported successfully!');
          }
          break;
      }
    } catch (error: any) {
      Alert.alert('Export Failed', error.message || 'Could not export file');
      console.error('Export error:', error);
    } finally {
      setExporting(false);
    }
  };

  const handleRetryStage = async (stageKey: string) => {
    try {
      const jobs = await api.getLectureJobs(lectureId);
      const failedJob = jobs.jobs?.find(
        (j: any) => j.job_type === stageKey && j.status === 'failed'
      );
      if (failedJob) {
        await api.replayJob(failedJob.id);
        Alert.alert('Retry Started', `Retrying ${stageKey}...`);
        loadData();
      } else {
        Alert.alert('No Failed Job', 'Could not find a failed job to retry.');
      }
    } catch (err: any) {
      Alert.alert('Retry Failed', err.message || 'Could not retry this stage.');
    }
  };

  const renderProgressBar = () => {
    if (!progress) return null;

    const stages = [
      { key: 'transcription', icon: '📝', label: 'Transcribe' },
      { key: 'generation', icon: '🧠', label: 'Generate' },
      { key: 'export', icon: '📦', label: 'Export' },
    ];

    return (
      <Card style={{ marginBottom: 16 }} mode="elevated">
        <Card.Content>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Text variant="titleMedium">Pipeline Progress</Text>
            <Text variant="titleMedium" style={{ color: theme.colors.primary, fontWeight: '700' }}>
              {progress.progressPercent}%
            </Text>
          </View>

          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, paddingHorizontal: 8 }}>
            {stages.map((stage, index) => {
              const stageData = progress.stages?.[stage.key];
              const isCompleted = stageData?.status === 'completed';
              const isProcessing = stageData?.status === 'processing';
              const isFailed = stageData?.status === 'failed';

              const borderColor = isCompleted
                ? theme.colors.primary
                : isFailed
                ? theme.colors.error
                : isProcessing
                ? theme.colors.tertiary
                : theme.colors.outlineVariant;

              return (
                <React.Fragment key={stage.key}>
                  <View style={{ alignItems: 'center', flex: 1 }}>
                    <View
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 24,
                        backgroundColor: theme.colors.surfaceVariant,
                        justifyContent: 'center',
                        alignItems: 'center',
                        marginBottom: 8,
                        borderWidth: 2,
                        borderColor,
                      }}
                    >
                      <Text style={{ fontSize: 20 }}>
                        {isCompleted ? '✓' : isFailed ? '✕' : stage.icon}
                      </Text>
                    </View>
                    <Text
                      variant="labelSmall"
                      style={{ color: isCompleted || isProcessing ? theme.colors.onSurface : theme.colors.onSurfaceVariant }}
                    >
                      {stage.label}
                    </Text>
                    {isFailed && stageData?.error && (
                      <Text
                        variant="labelSmall"
                        style={{ color: theme.colors.error, textAlign: 'center', marginTop: 4, fontSize: 10 }}
                        numberOfLines={2}
                      >
                        {stageData.error}
                      </Text>
                    )}
                    {isFailed && (
                      <Chip
                        compact
                        onPress={() => handleRetryStage(stage.key)}
                        style={{ marginTop: 4, backgroundColor: theme.colors.errorContainer }}
                        textStyle={{ fontSize: 10, color: theme.colors.error }}
                      >
                        Retry
                      </Chip>
                    )}
                  </View>
                  {index < stages.length - 1 && (
                    <View
                      style={{
                        height: 2,
                        flex: 0.5,
                        backgroundColor: isCompleted ? theme.colors.primary : theme.colors.outlineVariant,
                        marginBottom: 32,
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </View>

          <ProgressBar progress={progress.progressPercent / 100} style={{ marginBottom: 8, borderRadius: 4 }} />
          <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
            {progress.currentStage ? `Current: ${progress.currentStage}` : 'Completed'}
          </Text>
        </Card.Content>
      </Card>
    );
  };

  const renderArtifacts = () => {
    if (!artifacts || !artifacts.artifacts) {
      return (
        <View style={{ alignItems: 'center', paddingVertical: 60 }}>
          <Text style={{ fontSize: 48, marginBottom: 12 }}>📄</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
            No artifacts generated yet
          </Text>
        </View>
      );
    }

    const { artifacts: arts } = artifacts;

    return (
      <View>
        {arts.summary && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() => navigation.navigate('SummaryViewer', { summary: arts.summary })}
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>SUMMARY</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Lecture Summary</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }} numberOfLines={3}>
                {arts.summary.overview}
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                View Full Summary →
              </Text>
            </Card.Content>
          </Card>
        )}

        {arts.outline && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() => navigation.navigate('OutlineViewer', { outline: arts.outline })}
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>OUTLINE</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Lecture Outline</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                {arts.outline.sections?.length || 0} sections
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                View Outline →
              </Text>
            </Card.Content>
          </Card>
        )}

        {arts['key-terms'] && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() => navigation.navigate('KeyTermsViewer', { keyTerms: arts['key-terms'] })}
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>KEY TERMS</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Key Terms</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                {arts['key-terms'].terms?.length || 0} terms
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                View Key Terms →
              </Text>
            </Card.Content>
          </Card>
        )}

        {arts.flashcards && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() =>
              navigation.navigate('FlashcardViewer', { cards: arts.flashcards.cards })
            }
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>FLASHCARDS</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Study Flashcards</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                {arts.flashcards.cards?.length || 0} flashcards
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                View Flashcards →
              </Text>
            </Card.Content>
          </Card>
        )}

        {arts['exam-questions'] && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() =>
              navigation.navigate('ExamViewer', { questions: arts['exam-questions'].questions })
            }
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>EXAM PREP</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Practice Questions</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                {arts['exam-questions'].questions?.length || 0} questions
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                Start Practice →
              </Text>
            </Card.Content>
          </Card>
        )}

        {arts.threads && arts.threads.length > 0 && (
          <Card
            style={{ marginBottom: 16 }}
            onPress={() => {
              const courseId = summary?.lecture?.course_id || route.params?.courseId;
              navigation.navigate('Threads', {
                courseId,
                courseTitle: route.params?.courseTitle,
              });
            }}
            mode="elevated"
          >
            <Card.Content>
              <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 8 }}>THREADS</Chip>
              <Text variant="titleMedium" style={{ marginBottom: 8 }}>Conceptual Threads</Text>
              <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 8 }}>
                {arts.threads.length} concepts tracked across lectures
              </Text>
              <Text variant="labelLarge" style={{ color: theme.colors.primary }}>
                View Threads →
              </Text>
            </Card.Content>
          </Card>
        )}
      </View>
    );
  };

  const renderProgressDetails = () => {
    if (!progress) {
      return (
        <View style={{ alignItems: 'center', paddingVertical: 60 }}>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
            No progress data available
          </Text>
        </View>
      );
    }

    const stageNames = ['transcription', 'generation', 'export'];

    return (
      <View>
        {stageNames.map((stage) => {
          const stageData = progress.stages?.[stage];
          if (!stageData) return null;

          const statusColor =
            stageData.status === 'completed'
              ? theme.colors.primary
              : stageData.status === 'failed'
              ? theme.colors.error
              : stageData.status === 'processing'
              ? theme.colors.tertiary
              : theme.colors.onSurfaceVariant;

          return (
            <Card key={stage} style={{ marginBottom: 12 }} mode="elevated">
              <Card.Content style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text variant="titleSmall">
                  {stage.charAt(0).toUpperCase() + stage.slice(1)}
                </Text>
                <Chip compact selectedColor={statusColor} style={{ backgroundColor: theme.colors.surfaceVariant }}>
                  {stageData.status}
                </Chip>
              </Card.Content>
            </Card>
          );
        })}
      </View>
    );
  };

  if (loadError && !summary) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
        <NetworkErrorView onRetry={loadData} message="Could not load lecture data. Please check your connection and try again." />
      </View>
    );
  }

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator size="large" />
        <Text variant="bodyLarge" style={{ marginTop: 12, color: theme.colors.onSurfaceVariant }}>
          Loading...
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {/* Action Buttons */}
      <View style={{ flexDirection: 'row', padding: 16, paddingBottom: 8, gap: 8 }}>
        {summary?.lecture?.status === 'transcribed' && !artifacts?.artifactRecords?.length && (
          <Button
            mode="contained"
            onPress={handleGenerate}
            loading={generating}
            disabled={generating}
            icon="brain"
            style={{ flex: 1 }}
          >
            {generating ? (generatingStage || 'Starting...') : 'Generate'}
          </Button>
        )}
        {(summary?.lecture?.status === 'transcribed' || artifacts?.artifactRecords?.length > 0) && (
          <Button
            mode="outlined"
            onPress={() => navigation.navigate('DiceAnalysis', { lectureId, lectureTitle })}
            icon="cube-outline"
            style={{ flex: 1 }}
          >
            Dice Analysis
          </Button>
        )}
        <Button
          mode="outlined"
          onPress={() => setShowExportMenu(true)}
          disabled={exporting || !artifacts}
          icon="export-variant"
          style={{ flex: 1 }}
        >
          {exporting ? 'Exporting...' : 'Export'}
        </Button>
      </View>

      {/* Transcription-in-progress banner */}
      {(summary?.lecture?.status === 'uploaded' || summary?.lecture?.status === 'transcribing') && (
        <View style={{ backgroundColor: theme.colors.tertiaryContainer, paddingVertical: 8, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <ActivityIndicator size="small" />
          <Text variant="labelMedium" style={{ color: theme.colors.onTertiaryContainer }}>
            {progress?.currentStage === 'transcription'
              ? 'Transcribing your lecture... this takes a few seconds'
              : progress?.currentStage === 'generation'
              ? 'Generating study materials...'
              : progress?.currentStage === 'export'
              ? 'Preparing exports...'
              : 'Processing your lecture...'}
          </Text>
        </View>
      )}

      {/* Tab Switcher */}
      <View style={{ paddingHorizontal: 16, paddingVertical: 12 }}>
        <SegmentedButtons
          value={activeTab}
          onValueChange={setActiveTab}
          buttons={[
            { value: 'artifacts', label: 'Study Guide' },
            { value: 'progress', label: 'Progress' },
          ]}
        />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: 16 }}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        {renderProgressBar()}
        {activeTab === 'artifacts' ? renderArtifacts() : renderProgressDetails()}
      </ScrollView>

      {/* Export Menu Dialog */}
      <Portal>
        <Dialog visible={showExportMenu} onDismiss={() => setShowExportMenu(false)}>
          <Dialog.Title>Export Options</Dialog.Title>
          <Dialog.Content>
            <List.Item
              title="Export All"
              description="Complete study guide with all artifacts"
              left={(props) => <List.Icon {...props} icon="package-variant" />}
              onPress={() => handleExport('all')}
            />
            <List.Item
              title="Summary Only"
              description="Markdown file with lecture summary"
              left={(props) => <List.Icon {...props} icon="file-document-outline" />}
              onPress={() => handleExport('summary')}
            />
            <List.Item
              title="Flashcards (Anki CSV)"
              description="Import into Anki or other apps"
              left={(props) => <List.Icon {...props} icon="cards-outline" />}
              onPress={() => handleExport('flashcards')}
            />
            <List.Item
              title="Exam Questions"
              description="Practice questions with answers"
              left={(props) => <List.Icon {...props} icon="help-circle-outline" />}
              onPress={() => handleExport('questions')}
            />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowExportMenu(false)}>Cancel</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
}
