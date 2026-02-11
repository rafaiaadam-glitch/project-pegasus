import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

type Tab = 'Transcript' | 'Artifacts';
type PresetMode = 'exam-mode' | 'neurodivergent-friendly-mode' | 'research-mode';
type FlowAction =
  | 'Queue transcription'
  | 'Generate artifacts'
  | 'Queue export'
  | 'Review artifacts'
  | 'Download exports';

type PersistedContext = {
  apiBaseUrl: string;
  courseId: string;
  lectureId: string;
  presetId: PresetMode;
};

type TranscriptSegment = {
  start?: number;
  end?: number;
  text?: string;
};

type LectureProgress = {
  overallStatus?: string;
  currentStage?: string;
  progressPercent?: number;
};

const STORAGE_KEY = 'pegasus.mobile.context.v1';

const PRESET_OPTIONS: Array<{ label: string; value: PresetMode }> = [
  { label: 'Exam', value: 'exam-mode' },
  { label: 'ADHD', value: 'neurodivergent-friendly-mode' },
  { label: 'Research', value: 'research-mode' },
];

const DEFAULT_CONTEXT: PersistedContext = {
  apiBaseUrl: 'http://localhost:8000',
  courseId: 'bio-101',
  lectureId: 'lec-04',
  presetId: 'exam-mode',
};

const FLOW_ACTIONS: FlowAction[] = [
  'Queue transcription',
  'Generate artifacts',
  'Queue export',
  'Review artifacts',
  'Download exports',
];

function toPresetLabel(value: PresetMode): string {
  return PRESET_OPTIONS.find((item) => item.value === value)?.label ?? 'Exam';
}

function toStatusText(prefix: string, details: unknown): string {
  if (typeof details === 'string') {
    return `${prefix}: ${details}`;
  }

  if (details && typeof details === 'object') {
    const id = (details as { id?: unknown; jobId?: unknown }).jobId ?? (details as { id?: unknown }).id;
    const status = (details as { status?: unknown }).status;
    if (typeof id === 'string' && typeof status === 'string') {
      return `${prefix}: ${status} (${id})`;
    }
    return `${prefix}: request completed`;
  }

  return prefix;
}

function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

async function requestJson(apiBaseUrl: string, path: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(`${normalizeBaseUrl(apiBaseUrl)}${path}`, {
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const bodyText = await response.text();
  let parsed: unknown = bodyText;

  if (bodyText) {
    try {
      parsed = JSON.parse(bodyText);
    } catch {
      parsed = bodyText;
    }
  }

  if (!response.ok) {
    const errorMessage =
      typeof parsed === 'string'
        ? parsed
        : (parsed as { detail?: string })?.detail ?? `HTTP ${response.status}`;
    throw new Error(errorMessage);
  }

  return parsed;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('Artifacts');
  const [context, setContext] = useState<PersistedContext>(DEFAULT_CONTEXT);
  const [statusMessage, setStatusMessage] = useState('Ready');
  const [isBusy, setIsBusy] = useState(false);
  const [artifactsPreview, setArtifactsPreview] = useState<string[]>([]);
  const [jobsPreview, setJobsPreview] = useState<string[]>([]);
  const [transcriptText, setTranscriptText] = useState('');
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegment[]>([]);
  const [lectureProgress, setLectureProgress] = useState<LectureProgress>({});

  useEffect(() => {
    let mounted = true;

    async function loadPersistedContext() {
      try {
        const raw = await AsyncStorage.getItem(STORAGE_KEY);
        if (!mounted || !raw) {
          return;
        }

        const parsed = JSON.parse(raw) as Partial<PersistedContext>;
        if (parsed.courseId && parsed.lectureId && parsed.presetId) {
          setContext({
            apiBaseUrl: typeof parsed.apiBaseUrl === 'string' ? parsed.apiBaseUrl : DEFAULT_CONTEXT.apiBaseUrl,
            courseId: parsed.courseId,
            lectureId: parsed.lectureId,
            presetId: parsed.presetId,
          });
          setStatusMessage('Loaded saved lecture context');
        }
      } catch {
        setStatusMessage('Using default lecture context');
      }
    }

    loadPersistedContext();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(context)).catch(() => {
      setStatusMessage('Unable to persist context locally');
    });
  }, [context]);

  const presetLabel = useMemo(() => toPresetLabel(context.presetId), [context.presetId]);

  const loadRecentJobs = async () => {
    const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/jobs?limit=5`);
    const rows = Array.isArray((payload as { jobs?: unknown[] })?.jobs)
      ? ((payload as { jobs: unknown[] }).jobs ?? [])
      : Array.isArray(payload)
        ? payload
        : [];

    const preview = rows
      .map((item) => {
        const status = (item as { status?: unknown }).status;
        const jobType = (item as { jobType?: unknown; job_type?: unknown }).jobType
          ?? (item as { job_type?: unknown }).job_type;
        if (typeof status !== 'string') {
          return null;
        }
        return typeof jobType === 'string' ? `${jobType}: ${status}` : status;
      })
      .filter((line): line is string => Boolean(line));

    setJobsPreview(preview);
  };

  const loadTranscript = async () => {
    if (!context.lectureId.trim()) {
      setStatusMessage('Lecture ID is required before loading transcript');
      return;
    }

    setIsBusy(true);
    setStatusMessage('Loading transcript…');

    try {
      const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/transcript?segment_limit=20`);
      const text = typeof (payload as { text?: unknown }).text === 'string'
        ? (payload as { text: string }).text
        : '';
      const segments = Array.isArray((payload as { segments?: unknown[] }).segments)
        ? ((payload as { segments: unknown[] }).segments as TranscriptSegment[])
        : [];

      setTranscriptText(text);
      setTranscriptSegments(segments);
      setStatusMessage(`Transcript loaded (${segments.length} segments)`);
      await loadLectureProgress();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed';
      setStatusMessage(`Load transcript failed: ${message}`);
    } finally {
      setIsBusy(false);
    }
  };


  const loadLectureProgress = async () => {
    if (!context.lectureId.trim()) {
      setStatusMessage('Lecture ID is required before loading progress');
      return;
    }

    try {
      const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/progress`);
      setLectureProgress({
        overallStatus: typeof (payload as { overallStatus?: unknown }).overallStatus === 'string'
          ? (payload as { overallStatus: string }).overallStatus
          : undefined,
        currentStage: typeof (payload as { currentStage?: unknown }).currentStage === 'string'
          ? (payload as { currentStage: string }).currentStage
          : undefined,
        progressPercent: typeof (payload as { progressPercent?: unknown }).progressPercent === 'number'
          ? (payload as { progressPercent: number }).progressPercent
          : undefined,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed';
      setStatusMessage(`Load progress failed: ${message}`);
    }
  };

  const runFlowAction = async (action: FlowAction) => {
    if (!context.lectureId.trim()) {
      setStatusMessage('Lecture ID is required before running workflow actions');
      return;
    }

    if (!context.courseId.trim() && action === 'Generate artifacts') {
      setStatusMessage('Course ID is required to generate artifacts');
      return;
    }

    if (!normalizeBaseUrl(context.apiBaseUrl)) {
      setStatusMessage('API base URL is required');
      return;
    }

    setIsBusy(true);
    setStatusMessage(`${action}…`);

    try {
      switch (action) {
        case 'Queue transcription': {
          const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/transcribe`, {
            method: 'POST',
          });
          setStatusMessage(toStatusText('Transcription queued', payload));
          await loadRecentJobs();
          break;
        }
        case 'Generate artifacts': {
          const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/generate`, {
            method: 'POST',
            body: JSON.stringify({
              course_id: context.courseId,
              preset_id: context.presetId,
            }),
          });
          setStatusMessage(toStatusText('Artifact generation queued', payload));
          await loadRecentJobs();
          break;
        }
        case 'Queue export': {
          const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/export`, {
            method: 'POST',
          });
          setStatusMessage(toStatusText('Export queued', payload));
          await loadRecentJobs();
          break;
        }
        case 'Review artifacts': {
          const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/artifacts?limit=5`);
          const rows = Array.isArray((payload as { artifacts?: unknown[] })?.artifacts)
            ? ((payload as { artifacts: unknown[] }).artifacts ?? [])
            : Array.isArray(payload)
              ? payload
              : [];

          const preview = rows
            .map((item) => {
              const artifactType = (item as { artifact_type?: unknown; artifactType?: unknown }).artifact_type
                ?? (item as { artifactType?: unknown }).artifactType;
              const generatedAt = (item as { generated_at?: unknown; generatedAt?: unknown }).generated_at
                ?? (item as { generatedAt?: unknown }).generatedAt;
              if (typeof artifactType !== 'string') {
                return null;
              }
              return typeof generatedAt === 'string'
                ? `${artifactType} • ${generatedAt}`
                : artifactType;
            })
            .filter((line): line is string => Boolean(line));

          setArtifactsPreview(preview);
          setActiveTab('Artifacts');
          setStatusMessage(`Loaded ${preview.length} artifacts`);
          break;
        }
        case 'Download exports': {
          const payload = await requestJson(context.apiBaseUrl, `/lectures/${context.lectureId}/summary`);
          setStatusMessage(toStatusText('Fetched lecture export summary', payload));
          break;
        }
        default:
          setStatusMessage('Unsupported action');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed';
      setStatusMessage(`${action} failed: ${message}`);
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.navBar}>
        <Text style={styles.navTitle}>{context.courseId.toUpperCase()}</Text>
        <Text style={styles.navSubtitle}>{context.lectureId} • {presetLabel} Mode</Text>
      </View>

      <View style={styles.tabContainer}>
        <View style={styles.segmentBackground}>
          <TouchableOpacity
            style={[styles.segment, activeTab === 'Artifacts' && styles.segmentActive]}
            onPress={() => setActiveTab('Artifacts')}
          >
            <Text style={[styles.segmentText, activeTab === 'Artifacts' && styles.segmentTextActive]}>Study Guide</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.segment, activeTab === 'Transcript' && styles.segmentActive]}
            onPress={() => setActiveTab('Transcript')}
          >
            <Text style={[styles.segmentText, activeTab === 'Transcript' && styles.segmentTextActive]}>Transcript</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.scrollArea} showsVerticalScrollIndicator={false}>
        <View style={styles.card}>
          <Text style={styles.cardTag}>LECTURE CONTEXT</Text>
          <TextInput
            style={styles.input}
            value={context.apiBaseUrl}
            onChangeText={(apiBaseUrl) => setContext((prev) => ({ ...prev, apiBaseUrl }))}
            placeholder="http://localhost:8000"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TextInput
            style={styles.input}
            value={context.courseId}
            onChangeText={(courseId) => setContext((prev) => ({ ...prev, courseId }))}
            placeholder="course-id"
            autoCapitalize="none"
          />
          <TextInput
            style={styles.input}
            value={context.lectureId}
            onChangeText={(lectureId) => setContext((prev) => ({ ...prev, lectureId }))}
            placeholder="lecture-id"
            autoCapitalize="none"
          />

          <Text style={styles.label}>Style Preset</Text>
          <View style={styles.presetRow}>
            {PRESET_OPTIONS.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[styles.pBadge, context.presetId === option.value && styles.pBadgeActive]}
                onPress={() => setContext((prev) => ({ ...prev, presetId: option.value }))}
              >
                <Text style={[styles.pBadgeText, context.presetId === option.value && styles.pBadgeTextActive]}>{option.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTag}>WORKFLOW</Text>
          <Text style={styles.cardTitle}>Course → Preset → Process → Review → Export</Text>
          <View style={styles.actionsList}>
            {FLOW_ACTIONS.map((action) => (
              <TouchableOpacity
                key={action}
                style={[styles.actionButton, isBusy && styles.actionButtonDisabled]}
                onPress={() => runFlowAction(action)}
                disabled={isBusy}
              >
                <Text style={styles.actionButtonText}>{action}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <View style={styles.statusRow}>
            {isBusy ? <ActivityIndicator size="small" color="#007AFF" /> : null}
            <Text style={styles.statusText}>Status: {statusMessage}</Text>
          </View>
        </View>

        {jobsPreview.length > 0 ? (
          <View style={styles.card}>
            <Text style={styles.cardTag}>RECENT JOBS</Text>
            {jobsPreview.map((line) => (
              <Text key={line} style={styles.previewRow}>• {line}</Text>
            ))}
          </View>
        ) : null}

        {activeTab === 'Artifacts' ? (
          <View style={styles.card}>
            <Text style={styles.cardTag}>ARTIFACT PREVIEW</Text>
            {artifactsPreview.length > 0 ? (
              artifactsPreview.map((line) => (
                <Text key={line} style={styles.previewRow}>• {line}</Text>
              ))
            ) : (
              <Text style={styles.emptyState}>Tap “Review artifacts” to fetch latest generated artifacts.</Text>
            )}
          </View>
        ) : (
          <View style={styles.card}>
            <Text style={styles.cardTag}>TRANSCRIPT</Text>
            <View style={styles.actionsList}>
              <TouchableOpacity
                style={[styles.actionButton, isBusy && styles.actionButtonDisabled]}
                onPress={loadTranscript}
                disabled={isBusy}
              >
                <Text style={styles.actionButtonText}>Load transcript</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionButton, isBusy && styles.actionButtonDisabled]}
                onPress={loadLectureProgress}
                disabled={isBusy}
              >
                <Text style={styles.actionButtonText}>Refresh progress</Text>
              </TouchableOpacity>
            </View>
            {lectureProgress.overallStatus ? (
              <Text style={styles.progressText}>
                Progress: {lectureProgress.overallStatus} · Stage: {lectureProgress.currentStage ?? 'n/a'} · {lectureProgress.progressPercent ?? 0}%
              </Text>
            ) : null}
            {transcriptText ? <Text style={styles.transcriptText}>{transcriptText}</Text> : null}
            {transcriptSegments.length > 0 ? (
              <View style={styles.segmentList}>
                {transcriptSegments.slice(0, 5).map((segment, index) => (
                  <Text key={`${segment.start ?? 's'}-${index}`} style={styles.segmentRow}>
                    • [{segment.start ?? 0}s - {segment.end ?? 0}s] {segment.text ?? ''}
                  </Text>
                ))}
              </View>
            ) : (
              <Text style={styles.emptyState}>Load transcript to view text and timestamp segments.</Text>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  navBar: { padding: 20, alignItems: 'center', borderBottomWidth: 0.5, borderColor: '#E5E5E5' },
  navTitle: { fontSize: 17, fontWeight: '600', color: '#000' },
  navSubtitle: { fontSize: 13, color: '#8E8E93', marginTop: 2 },
  tabContainer: { padding: 16, backgroundColor: '#F2F2F7' },
  segmentBackground: { flexDirection: 'row', backgroundColor: '#E3E3E8', borderRadius: 8, padding: 2 },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  segmentActive: { backgroundColor: '#FFF', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  segmentText: { fontSize: 13, color: '#8E8E93', fontWeight: '500' },
  segmentTextActive: { color: '#000', fontWeight: '600' },
  scrollArea: { flex: 1, padding: 20 },
  card: {
    backgroundColor: '#FFF',
    padding: 20,
    borderRadius: 16,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
    borderWidth: 1,
    borderColor: '#F2F2F7',
  },
  cardTag: { fontSize: 10, fontWeight: '700', color: '#007AFF', letterSpacing: 1, marginBottom: 8 },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#000', marginBottom: 12 },
  label: { fontSize: 12, fontWeight: '600', color: '#8E8E93', textTransform: 'uppercase', marginBottom: 12, marginTop: 6 },
  input: {
    borderWidth: 1,
    borderColor: '#DCDCE3',
    borderRadius: 10,
    fontSize: 15,
    color: '#1C1C1E',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
    backgroundColor: '#FAFAFC',
  },
  presetRow: { flexDirection: 'row', gap: 10, marginBottom: 4 },
  pBadge: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, backgroundColor: '#F2F2F7' },
  pBadgeActive: { backgroundColor: '#007AFF' },
  pBadgeText: { fontSize: 14, color: '#007AFF', fontWeight: '500' },
  pBadgeTextActive: { color: '#FFF' },
  actionsList: { gap: 10 },
  actionButton: {
    backgroundColor: '#F2F2F7',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  actionButtonDisabled: { opacity: 0.5 },
  actionButtonText: { color: '#1C1C1E', fontWeight: '600', fontSize: 14 },
  statusRow: { marginTop: 14, flexDirection: 'row', alignItems: 'center', gap: 8 },
  statusText: { color: '#3A3A3C', fontSize: 13, flex: 1 },
  emptyState: { color: '#3A3A3C', fontSize: 14, lineHeight: 20, marginTop: 10 },
  previewRow: { color: '#1C1C1E', fontSize: 14, marginBottom: 6 },
  transcriptText: { marginTop: 12, color: '#1C1C1E', fontSize: 14, lineHeight: 20 },
  segmentList: { marginTop: 12, gap: 8 },
  segmentRow: { color: '#3A3A3C', fontSize: 13, lineHeight: 18 },
  progressText: { marginTop: 10, color: '#3A3A3C', fontSize: 13 },
});
