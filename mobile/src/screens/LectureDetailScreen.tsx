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
  Snackbar,
} from 'react-native-paper';
import api from '../services/api';
import { useTheme } from '../theme';
import NetworkErrorView from '../components/NetworkErrorView';

import * as ExportUtils from '../services/exportUtils';

const humanizeError = (error: string | undefined): string => {
  if (!error) return 'Something went wrong. Please try again.';
  const e = error.toLowerCase();
  if (e.includes('timeout') || e.includes('timed out')) return 'The request timed out. Please try again.';
  if (e.includes('json') || e.includes('parse')) return 'Received an unexpected response. Please retry.';
  if (e.includes('rate') || e.includes('429')) return 'Too many requests. Please wait a moment and retry.';
  if (e.includes('network') || e.includes('fetch') || e.includes('econnrefused')) return 'Network error. Please check your connection.';
  if (error.length > 120) return error.slice(0, 117) + '...';
  return error;
};

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
  const [exportingType, setExportingType] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generatingStage, setGeneratingStage] = useState('');
  const [loadError, setLoadError] = useState(false);
  const [retryingStage, setRetryingStage] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState<{ visible: boolean; message: string }>({ visible: false, message: '' });

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
        { delay: 90000, msg: 'Still processing — large lectures take longer...' },
        { delay: 240000, msg: 'Taking longer than usual — please wait...' },
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
      Alert.alert('Generation Failed', humanizeError(error.message));
    } finally {
      setGenerating(false);
      setGeneratingStage('');
    }
  };

  const handleExport = async (type: 'all' | 'summary' | 'flashcards' | 'questions') => {
    // Guard: check if the relevant artifact exists
    const arts = artifacts?.artifacts;
    const missingMap: Record<string, boolean> = {
      all: !arts,
      summary: !arts?.summary,
      flashcards: !arts?.flashcards,
      questions: !arts?.['exam-questions'],
    };
    if (missingMap[type]) {
      setSnackbar({ visible: true, message: `No ${type === 'all' ? 'artifacts' : type} available to export. Generate study materials first.` });
      return;
    }

    try {
      setExporting(true);
      setExportingType(type);

      switch (type) {
        case 'all':
          await ExportUtils.exportAllArtifacts(
            arts,
            lectureTitle,
            route.params.courseTitle
          );
          break;
        case 'summary':
          await ExportUtils.exportSummary(
            arts.summary,
            lectureTitle,
            route.params.courseTitle
          );
          break;
        case 'flashcards':
          await ExportUtils.exportFlashcards(
            arts.flashcards,
            lectureTitle
          );
          break;
        case 'questions':
          await ExportUtils.exportExamQuestions(
            arts['exam-questions'],
            lectureTitle,
            route.params.courseTitle
          );
          break;
      }
      setShowExportMenu(false);
      setSnackbar({ visible: true, message: 'Export successful!' });
    } catch (error: any) {
      setSnackbar({ visible: true, message: error.message || 'Could not export file' });
      console.error('Export error:', error);
    } finally {
      setExporting(false);
      setExportingType(null);
    }
  };

  const handleRetryStage = async (stageKey: string) => {
    try {
      setRetryingStage(stageKey);
      const jobs = await api.getLectureJobs(lectureId);
      const failedJob = jobs.jobs?.find(
        (j: any) => (j.jobType || j.job_type) === stageKey && j.status === 'failed'
      );
      if (failedJob) {
        await api.replayJob(failedJob.id);
        loadData();
      } else {
        setSnackbar({ visible: true, message: 'Could not find a failed job to retry.' });
      }
    } catch (err: any) {
      setSnackbar({ visible: true, message: err.message || 'Could not retry this stage.' });
    } finally {
      setRetryingStage(null);
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
                      {retryingStage === stage.key || isProcessing ? (
                        <ActivityIndicator size="small" />
                      ) : (
                        <Text style={{ fontSize: 20 }}>
                          {isCompleted ? '✓' : isFailed ? '✕' : stage.icon}
                        </Text>
                      )}
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
                        {humanizeError(stageData.error)}
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
            onPress={() => navigation.navigate('SummaryViewer', { summary: arts.summary, lectureTitle })}
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
                {arts.outline.outline?.length || arts.outline.sections?.length || 0} sections
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
        {artifacts?.artifactRecords?.length > 0 && (
          <Button
            mode="outlined"
            onPress={() => {
              Alert.alert(
                'Regenerate Artifacts',
                'This will replace existing study materials. Continue?',
                [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Regenerate', onPress: handleGenerate },
                ]
              );
            }}
            loading={generating}
            disabled={generating}
            icon="refresh"
            style={{ flex: 1 }}
          >
            {generating ? (generatingStage || 'Starting...') : 'Regenerate'}
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
          disabled={exporting || !artifacts?.artifacts}
          icon="export-variant"
          style={{ flex: 1 }}
        >
          {exporting ? 'Exporting...' : 'Export'}
        </Button>
      </View>
      {!artifacts?.artifacts && (
        <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', paddingHorizontal: 16, paddingBottom: 4 }}>
          Generate study materials to enable export.
        </Text>
      )}

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
        <Dialog visible={showExportMenu} onDismiss={() => !exporting && setShowExportMenu(false)}>
          <Dialog.Title>Export Options</Dialog.Title>
          <Dialog.Content>
            <List.Item
              title="Export All"
              description="Complete study guide with all artifacts"
              left={(props) => <List.Icon {...props} icon="package-variant" />}
              right={() => exportingType === 'all' ? <ActivityIndicator size="small" /> : null}
              onPress={() => handleExport('all')}
              disabled={exporting}
            />
            <List.Item
              title="Summary Only"
              description="Markdown file with lecture summary"
              left={(props) => <List.Icon {...props} icon="file-document-outline" />}
              right={() => exportingType === 'summary' ? <ActivityIndicator size="small" /> : null}
              onPress={() => handleExport('summary')}
              disabled={exporting}
            />
            <List.Item
              title="Flashcards (Anki CSV)"
              description="Import into Anki or other apps"
              left={(props) => <List.Icon {...props} icon="cards-outline" />}
              right={() => exportingType === 'flashcards' ? <ActivityIndicator size="small" /> : null}
              onPress={() => handleExport('flashcards')}
              disabled={exporting}
            />
            <List.Item
              title="Exam Questions"
              description="Practice questions with answers"
              left={(props) => <List.Icon {...props} icon="help-circle-outline" />}
              right={() => exportingType === 'questions' ? <ActivityIndicator size="small" /> : null}
              onPress={() => handleExport('questions')}
              disabled={exporting}
            />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowExportMenu(false)} disabled={exporting}>Cancel</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>

      <Snackbar
        visible={snackbar.visible}
        onDismiss={() => setSnackbar({ visible: false, message: '' })}
        duration={4000}
        action={{ label: 'Dismiss', onPress: () => setSnackbar({ visible: false, message: '' }) }}
      >
        {snackbar.message}
      </Snackbar>
    </View>
  );
}
