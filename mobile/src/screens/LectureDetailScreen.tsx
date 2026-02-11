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
} from 'react-native';
import api from '../services/api';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureDetailScreen({ navigation, route }: Props) {
  const { lectureId, lectureTitle } = route.params;
  const [activeTab, setActiveTab] = useState<'artifacts' | 'progress'>('artifacts');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);

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

  const renderProgressBar = () => {
    if (!progress) return null;

    return (
      <View style={styles.progressSection}>
        <View style={styles.progressHeader}>
          <Text style={styles.progressTitle}>Processing Status</Text>
          <Text style={styles.progressPercent}>{progress.progressPercent}%</Text>
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

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F2F2F7' },
  tabContainer: { padding: 16, backgroundColor: '#F2F2F7' },
  segmentBackground: {
    flexDirection: 'row',
    backgroundColor: '#E3E3E8',
    borderRadius: 8,
    padding: 2,
  },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  segmentActive: {
    backgroundColor: '#FFF',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  segmentText: { fontSize: 13, color: '#8E8E93', fontWeight: '500' },
  segmentTextActive: { color: '#000', fontWeight: '600' },
  scrollArea: { flex: 1, padding: 20 },
  progressSection: { marginBottom: 24 },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  progressTitle: { fontSize: 16, fontWeight: '600', color: '#000' },
  progressPercent: { fontSize: 16, fontWeight: '700', color: '#007AFF' },
  progressBarContainer: {
    height: 8,
    backgroundColor: '#E5E5EA',
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressBarFill: { height: '100%', backgroundColor: '#007AFF' },
  progressStage: { fontSize: 13, color: '#8E8E93' },
  card: {
    backgroundColor: '#FFF',
    padding: 20,
    borderRadius: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  cardTag: {
    fontSize: 10,
    fontWeight: '700',
    color: '#007AFF',
    letterSpacing: 1,
    marginBottom: 8,
  },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#000', marginBottom: 8 },
  cardBody: { fontSize: 15, lineHeight: 22, color: '#3A3A3C', marginBottom: 12 },
  viewButton: { fontSize: 15, fontWeight: '600', color: '#007AFF', marginTop: 8 },
  stageCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  stageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stageName: { fontSize: 16, fontWeight: '600', color: '#000' },
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
    backgroundColor: '#F2F2F7',
  },
  loadingText: { marginTop: 12, fontSize: 16, color: '#8E8E93' },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 15, color: '#8E8E93' },
});
