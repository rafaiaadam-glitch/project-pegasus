import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Modal,
  Platform,
} from 'react-native';
import api from '../services/api';
import { useTheme } from '../theme';

// Lazy load export utils only on native platforms
const ExportUtils = Platform.OS !== 'web' ? require('../services/exportUtils') : null;

interface Props {
  navigation: any;
  route: any;
}

export default function LectureDetailScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { lectureId, lectureTitle } = route.params;
  const [activeTab, setActiveTab] = useState<'artifacts' | 'progress'>('artifacts');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: lectureTitle || 'Lecture Details' });
    loadData();
  }, [lectureId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [summaryData, artifactsData, progressData] = await Promise.all([
        api.getLectureSummary(lectureId),
        api.getLectureArtifacts(lectureId),
        api.getLectureProgress(lectureId),
      ]);
      setSummary(summaryData);
      setArtifacts(artifactsData);
      setProgress(progressData);
    } catch (error) {
      console.error('Error loading lecture data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleExport = async (type: 'all' | 'summary' | 'flashcards' | 'questions') => {
    try {
      setExporting(true);
      setShowExportMenu(false);

      // Export only works on native platforms (iOS/Android)
      if (Platform.OS === 'web' || !ExportUtils) {
        Alert.alert(
          'Export Not Available',
          'File export is only available on iOS and Android devices. Please use the mobile app to export files.'
        );
        return;
      }

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

  const renderProgressBar = () => {
    if (!progress) return null;

    const stages = [
      { key: 'transcription', icon: '📝', label: 'Transcribe' },
      { key: 'generation', icon: '🧠', label: 'Generate' },
      { key: 'export', icon: '📦', label: 'Export' },
    ];

    return (
      <View style={styles.progressSection}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressTitle}>Pipeline Progress</Text>
          <Text style={styles.progressPercent}>{progress.progressPercent}%</Text>
        </View>

        {/* Visual Pipeline */}
        <View style={styles.pipelineContainer}>
          {stages.map((stage, index) => {
            const stageData = progress.stages?.[stage.key];
            const isCompleted = stageData?.status === 'completed';
            const isProcessing = stageData?.status === 'processing';
            const isFailed = stageData?.status === 'failed';
            const isActive = progress.currentStage === stage.key;

            return (
              <React.Fragment key={stage.key}>
                <View style={styles.pipelineStage}>
                  <View
                    style={[
                      styles.pipelineIcon,
                      isCompleted && styles.pipelineIconCompleted,
                      isProcessing && styles.pipelineIconProcessing,
                      isFailed && styles.pipelineIconFailed,
                    ]}
                  >
                    <Text style={styles.pipelineIconText}>
                      {isCompleted ? '✓' : isFailed ? '✕' : stage.icon}
                    </Text>
                  </View>
                  <Text
                    style={[
                      styles.pipelineLabel,
                      (isCompleted || isProcessing) && styles.pipelineLabelActive,
                    ]}
                  >
                    {stage.label}
                  </Text>
                  {isActive && <Text style={styles.pipelineActiveIndicator}>●</Text>}
                </View>
                {index < stages.length - 1 && (
                  <View
                    style={[
                      styles.pipelineConnector,
                      isCompleted && styles.pipelineConnectorCompleted,
                    ]}
                  />
                )}
              </React.Fragment>
            );
          })}
        </View>

        <View style={styles.progressBarContainer}>
          <View
            style={[
              styles.progressBarFill,
              { width: `${progress.progressPercent}%` },
            ]}
          />
        </View>
        <Text style={styles.progressStage}>
          {progress.currentStage ? `Current: ${progress.currentStage}` : 'Completed'}
        </Text>
      </View>
    );
  };

  const renderArtifacts = () => {
    if (!artifacts || !artifacts.artifacts) {
      return (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>📄</Text>
          <Text style={styles.emptyText}>No artifacts generated yet</Text>
        </View>
      );
    }

    const { artifacts: arts } = artifacts;

    return (
      <View>
        {arts.summary && (
          <View style={styles.card}>
            <Text style={styles.cardTag}>SUMMARY</Text>
            <Text style={styles.cardTitle}>Lecture Summary</Text>
            <Text style={styles.cardBody}>{arts.summary.overview}</Text>
          </View>
        )}

        {arts.outline && (
          <View style={styles.card}>
            <Text style={styles.cardTag}>OUTLINE</Text>
            <Text style={styles.cardTitle}>Lecture Outline</Text>
            <Text style={styles.cardBody}>
              {arts.outline.sections?.length || 0} sections
            </Text>
          </View>
        )}

        {arts.flashcards && (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              navigation.navigate('FlashcardViewer', {
                cards: arts.flashcards.cards,
              })
            }
          >
            <Text style={styles.cardTag}>FLASHCARDS</Text>
            <Text style={styles.cardTitle}>Study Flashcards</Text>
            <Text style={styles.cardBody}>
              {arts.flashcards.cards?.length || 0} flashcards
            </Text>
            <Text style={styles.viewButton}>View Flashcards →</Text>
          </TouchableOpacity>
        )}

        {arts['exam-questions'] && (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              navigation.navigate('ExamViewer', {
                questions: arts['exam-questions'].questions,
              })
            }
          >
            <Text style={styles.cardTag}>EXAM PREP</Text>
            <Text style={styles.cardTitle}>Practice Questions</Text>
            <Text style={styles.cardBody}>
              {arts['exam-questions'].questions?.length || 0} questions
            </Text>
            <Text style={styles.viewButton}>Start Practice →</Text>
          </TouchableOpacity>
        )}

        {arts.threads && arts.threads.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTag}>🧵 THREADS</Text>
            <Text style={styles.cardTitle}>Conceptual Threads</Text>
            <Text style={styles.cardBody}>
              {arts.threads.length} concepts tracked across lectures
            </Text>
          </View>
        )}
      </View>
    );
  };

  const renderProgressDetails = () => {
    if (!progress) {
      return (
        <View style={styles.emptyState}>
          <Text style={styles.emptyText}>No progress data available</Text>
        </View>
      );
    }

    const stages = ['transcription', 'generation', 'export'];

    return (
      <View>
        {stages.map((stage) => {
          const stageData = progress.stages?.[stage];
          if (!stageData) return null;

          return (
            <View key={stage} style={styles.stageCard}>
              <View style={styles.stageHeader}>
                <Text style={styles.stageName}>
                  {stage.charAt(0).toUpperCase() + stage.slice(1)}
                </Text>
                <View
                  style={[
                    styles.stageStatus,
                    {
                      backgroundColor:
                        stageData.status === 'completed'
                          ? '#34C759'
                          : stageData.status === 'failed'
                          ? '#FF3B30'
                          : stageData.status === 'processing'
                          ? '#FF9500'
                          : '#8E8E93',
                    },
                  ]}
                >
                  <Text style={styles.stageStatusText}>
                    {stageData.status}
                  </Text>
                </View>
              </View>
            </View>
          );
        })}
      </View>
    );
  };

  const styles = createStyles(theme);

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Export Button */}
      <View style={styles.exportButtonContainer}>
        <TouchableOpacity
          style={styles.exportButton}
          onPress={() => setShowExportMenu(true)}
          disabled={exporting || !artifacts}
        >
          <Text style={styles.exportButtonText}>
            {exporting ? '⏳' : '📤'} Export
          </Text>
        </TouchableOpacity>
      </View>

      {/* Tab Switcher */}
      <View style={styles.tabContainer}>
        <View style={styles.segmentBackground}>
          <TouchableOpacity
            style={[styles.segment, activeTab === 'artifacts' && styles.segmentActive]}
            onPress={() => setActiveTab('artifacts')}
          >
            <Text
              style={[styles.segmentText, activeTab === 'artifacts' && styles.segmentTextActive]}
            >
              Study Guide
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.segment, activeTab === 'progress' && styles.segmentActive]}
            onPress={() => setActiveTab('progress')}
          >
            <Text
              style={[styles.segmentText, activeTab === 'progress' && styles.segmentTextActive]}
            >
              Progress
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollArea}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        {renderProgressBar()}

        {activeTab === 'artifacts' ? renderArtifacts() : renderProgressDetails()}
      </ScrollView>

      {/* Export Menu Modal */}
      <Modal
        visible={showExportMenu}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowExportMenu(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowExportMenu(false)}
        >
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Export Options</Text>

            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleExport('all')}
            >
              <Text style={styles.modalOptionIcon}>📦</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Export All</Text>
                <Text style={styles.modalOptionSubtitle}>
                  Complete study guide with all artifacts
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleExport('summary')}
            >
              <Text style={styles.modalOptionIcon}>📄</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Summary Only</Text>
                <Text style={styles.modalOptionSubtitle}>
                  Markdown file with lecture summary
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleExport('flashcards')}
            >
              <Text style={styles.modalOptionIcon}>🎴</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Flashcards (Anki CSV)</Text>
                <Text style={styles.modalOptionSubtitle}>
                  Import into Anki or other apps
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleExport('questions')}
            >
              <Text style={styles.modalOptionIcon}>❓</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Exam Questions</Text>
                <Text style={styles.modalOptionSubtitle}>
                  Practice questions with answers
                </Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalCancelButton}
              onPress={() => setShowExportMenu(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const createStyles = (theme: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.background },
  tabContainer: { padding: 16, backgroundColor: theme.background },
  segmentBackground: {
    flexDirection: 'row',
    backgroundColor: theme.surfaceSecondary,
    borderRadius: 8,
    padding: 2,
  },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  segmentActive: {
    backgroundColor: theme.surface,
    shadowColor: theme.shadowColor,
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  segmentText: { fontSize: 13, color: theme.textTertiary, fontWeight: '500' },
  segmentTextActive: { color: theme.text, fontWeight: '600' },
  scrollArea: { flex: 1, padding: 20 },
  progressSection: { marginBottom: 24 },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  progressTitle: { fontSize: 16, fontWeight: '600', color: theme.text },
  progressPercent: { fontSize: 16, fontWeight: '700', color: theme.primary },
  pipelineContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
    paddingHorizontal: 8,
  },
  pipelineStage: {
    alignItems: 'center',
    flex: 1,
  },
  pipelineIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: theme.surfaceSecondary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
    borderWidth: 2,
    borderColor: theme.border,
  },
  pipelineIconCompleted: {
    backgroundColor: theme.success + '20',
    borderColor: theme.success,
  },
  pipelineIconProcessing: {
    backgroundColor: theme.warning + '20',
    borderColor: theme.warning,
  },
  pipelineIconFailed: {
    backgroundColor: theme.error + '20',
    borderColor: theme.error,
  },
  pipelineIconText: {
    fontSize: 20,
  },
  pipelineLabel: {
    fontSize: 12,
    color: theme.textTertiary,
    fontWeight: '500',
    textAlign: 'center',
  },
  pipelineLabelActive: {
    color: theme.text,
    fontWeight: '600',
  },
  pipelineActiveIndicator: {
    fontSize: 8,
    color: theme.primary,
    marginTop: 4,
  },
  pipelineConnector: {
    height: 2,
    flex: 0.5,
    backgroundColor: theme.border,
    marginBottom: 32,
  },
  pipelineConnectorCompleted: {
    backgroundColor: theme.success,
  },
  progressBarContainer: {
    height: 8,
    backgroundColor: theme.border,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressBarFill: { height: '100%', backgroundColor: theme.primary },
  progressStage: { fontSize: 13, color: theme.textTertiary },
  card: {
    backgroundColor: theme.surface,
    padding: 20,
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: theme.shadowColor,
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  cardTag: {
    fontSize: 10,
    fontWeight: '700',
    color: theme.primary,
    letterSpacing: 1,
    marginBottom: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '700', color: theme.text, marginBottom: 8 },
  cardBody: { fontSize: 15, lineHeight: 22, color: theme.textSecondary, marginBottom: 12 },
  viewButton: { fontSize: 15, fontWeight: '600', color: theme.primary, marginTop: 8 },
  stageCard: {
    backgroundColor: theme.surface,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  stageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stageName: { fontSize: 16, fontWeight: '600', color: theme.text },
  stageStatus: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  stageStatusText: { fontSize: 12, fontWeight: '600', color: '#FFF' },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.background,
  },
  loadingText: { marginTop: 12, fontSize: 16, color: theme.textTertiary },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 15, color: theme.textTertiary },
  exportButtonContainer: {
    padding: 16,
    paddingBottom: 8,
    backgroundColor: theme.background,
    borderBottomWidth: 1,
    borderBottomColor: theme.border,
  },
  exportButton: {
    backgroundColor: theme.primary,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 10,
    alignItems: 'center',
    shadowColor: theme.shadowColor,
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 3,
  },
  exportButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFF',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: theme.surface,
    borderRadius: 20,
    padding: 20,
    width: '100%',
    maxWidth: 400,
    shadowColor: theme.shadowColor,
    shadowOpacity: 0.25,
    shadowRadius: 20,
    elevation: 10,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: theme.text,
    marginBottom: 20,
    textAlign: 'center',
  },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.inputBackground,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  modalOptionIcon: {
    fontSize: 28,
    marginRight: 16,
  },
  modalOptionText: {
    flex: 1,
  },
  modalOptionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.text,
    marginBottom: 4,
  },
  modalOptionSubtitle: {
    fontSize: 13,
    color: theme.textTertiary,
  },
  modalCancelButton: {
    marginTop: 8,
    paddingVertical: 14,
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FF3B30',
  },
});
