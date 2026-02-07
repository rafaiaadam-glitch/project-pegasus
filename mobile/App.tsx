import { StatusBar } from "expo-status-bar";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useEffect, useState } from "react";
import * as Clipboard from "expo-clipboard";
import { useState } from "react";
import * as DocumentPicker from "expo-document-picker";
import {
  ActivityIndicator,
  Alert,
  Linking,
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEYS = {
  courseId: "pegasus.courseId",
  lectureId: "pegasus.lectureId",
  presetId: "pegasus.presetId",
  title: "pegasus.title",
};

export default function App() {
  const [courseId, setCourseId] = useState("course-001");
  const [lectureId, setLectureId] = useState("lecture-001");
  const [presetId, setPresetId] = useState("exam-mode");
  const [title, setTitle] = useState("Lecture 1");
  const [artifacts, setArtifacts] = useState<Record<string, unknown> | null>(null);
  const [exportRecords, setExportRecords] = useState<
    { export_type: string; storage_path: string }[]
  >([]);
  const [summaryStatus, setSummaryStatus] = useState<{
    lecture?: { id?: string; title?: string; status?: string };
    artifactCount: number;
    exportCount: number;
    artifactTypes: string[];
    exportTypes: string[];
  } | null>(null);
  const [selectedThread, setSelectedThread] = useState<{
    id?: string;
    title?: string;
    summary?: string;
    status?: string;
    complexity_level?: number;
    lecture_refs?: string[];
  } | null>(null);
  const [jobs, setJobs] = useState<
    {
      id: string;
      jobType: string;
      status: string;
      error?: string | null;
    }[]
  >([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadPrefs = async () => {
      try {
        const storedCourse = await AsyncStorage.getItem(STORAGE_KEYS.courseId);
        const storedLecture = await AsyncStorage.getItem(STORAGE_KEYS.lectureId);
        const storedPreset = await AsyncStorage.getItem(STORAGE_KEYS.presetId);
        const storedTitle = await AsyncStorage.getItem(STORAGE_KEYS.title);
        if (storedCourse) setCourseId(storedCourse);
        if (storedLecture) setLectureId(storedLecture);
        if (storedPreset) setPresetId(storedPreset);
        if (storedTitle) setTitle(storedTitle);
      } catch (error) {
        Alert.alert("Error", `Failed to load saved IDs: ${error}`);
      }
    };
    loadPrefs();
  }, []);

  useEffect(() => {
    const persist = async () => {
      try {
        await AsyncStorage.multiSet([
          [STORAGE_KEYS.courseId, courseId],
          [STORAGE_KEYS.lectureId, lectureId],
          [STORAGE_KEYS.presetId, presetId],
          [STORAGE_KEYS.title, title],
        ]);
      } catch (error) {
        Alert.alert("Error", `Failed to save IDs: ${error}`);
      }
    };
    persist();
  }, [courseId, lectureId, presetId, title]);

  useEffect(() => {
    if (jobs.length === 0) {
      return;
    }
    const activeJobs = jobs.filter(
      (job) => job.status !== "completed" && job.status !== "failed"
    );
    if (activeJobs.length === 0) {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const updates = await Promise.all(
          activeJobs.map(async (job) => {
            const resp = await fetch(`${API_BASE_URL}/jobs/${job.id}`);
            if (!resp.ok) {
              const detail = await resp.text();
              return {
                ...job,
                status: "failed",
                error: detail || "Failed to load job status",
              };
            }
            const data = await resp.json();
            return {
              ...job,
              status: data.status ?? job.status,
              error: data.error ?? null,
            };
          })
        );
        setJobs((prev) => {
          const byId = new Map(prev.map((job) => [job.id, job]));
          updates.forEach((job) => {
            byId.set(job.id, { ...byId.get(job.id), ...job });
          });
          return Array.from(byId.values());
        });
      } catch (error) {
        Alert.alert("Error", `Failed to poll job status: ${error}`);
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [jobs]);

  const upsertJob = (job: { id: string; jobType?: string; status?: string }) => {
    setJobs((prev) => {
      const byId = new Map(prev.map((item) => [item.id, item]));
      const existing = byId.get(job.id);
      byId.set(job.id, {
        id: job.id,
        jobType: job.jobType ?? existing?.jobType ?? "unknown",
        status: job.status ?? existing?.status ?? "queued",
        error: existing?.error ?? null,
      });
      return Array.from(byId.values());
    });
  };

  const uploadAudio = async () => {
    setLoading(true);
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "audio/*",
        copyToCacheDirectory: true,
      });
      if (result.canceled || result.assets.length === 0) {
        return;
      }
      const asset = result.assets[0];
      const formData = new FormData();
      formData.append("course_id", courseId);
      formData.append("lecture_id", lectureId);
      formData.append("preset_id", presetId);
      formData.append("title", title);
      formData.append("duration_sec", "0");
      formData.append("source_type", "upload");
      formData.append("audio", {
        uri: asset.uri,
        name: asset.name ?? `${lectureId}.audio`,
        type: asset.mimeType ?? "audio/mpeg",
      } as unknown as Blob);

      const resp = await fetch(`${API_BASE_URL}/lectures/ingest`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Upload failed");
      }
      const data = await resp.json();
      Alert.alert("Upload complete", `Audio stored at: ${data.audioPath}`);
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const [loading, setLoading] = useState(false);

  const runGenerate = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/lectures/${lectureId}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ course_id: courseId, preset_id: presetId }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Generation failed");
      }
      const data = await resp.json();
      upsertJob({ id: data.jobId, jobType: data.jobType, status: data.status });
      Alert.alert("Generation started", `Job ID: ${data.jobId}`);
      Alert.alert("Generation started", "Artifacts are now available.");
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const runTranscribe = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/lectures/${lectureId}/transcribe`, {
        method: "POST",
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Transcription failed");
      }
      const data = await resp.json();
      upsertJob({ id: data.jobId, jobType: data.jobType, status: data.status });
      Alert.alert("Transcription queued", `Job ID: ${data.jobId}`);
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const runExport = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/lectures/${lectureId}/export`, {
        method: "POST",
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Export failed");
      }
      const data = await resp.json();
      upsertJob({ id: data.jobId, jobType: data.jobType, status: data.status });
      Alert.alert("Export queued", `Job ID: ${data.jobId}`);
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const loadArtifacts = async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `${API_BASE_URL}/lectures/${lectureId}/artifacts`
      );
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Failed to load artifacts");
      }
      const data = await resp.json();
      setArtifacts(data.artifacts);
      setExportRecords(data.exportRecords ?? []);
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `${API_BASE_URL}/lectures/${lectureId}/summary`
      );
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Failed to load lecture summary");
      }
      const data = await resp.json();
      setSummaryStatus({
        lecture: data.lecture,
        artifactCount: data.artifactCount ?? 0,
        exportCount: data.exportCount ?? 0,
        artifactTypes: data.artifactTypes ?? [],
        exportTypes: data.exportTypes ?? [],
      });
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (url: string) => {
    await Clipboard.setStringAsync(url);
    Alert.alert("Copied", "Export link copied to clipboard.");
  };

  const openExport = async (exportType: string) => {
    const url = `${API_BASE_URL}/exports/${lectureId}/${exportType}`;
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || "Export unavailable");
      }
      let targetUrl = url;
      const contentType = resp.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const data = await resp.json();
        if (data?.downloadUrl) {
          targetUrl = data.downloadUrl;
        }
      }

      const canOpen = await Linking.canOpenURL(targetUrl);
      if (!canOpen) {
        await copyToClipboard(targetUrl);
        return;
      }
      try {
        await Linking.openURL(targetUrl);
        Alert.alert("Opened", `Opened ${exportType.toUpperCase()} export.`);
      } catch (error) {
        await copyToClipboard(targetUrl);
      }
    } catch (error) {
      Alert.alert("Error", `${error}`);
    }
  const openExport = async (exportType: string) => {
    const url = `${API_BASE_URL}/exports/${lectureId}/${exportType}`;
    const canOpen = await Linking.canOpenURL(url);
    if (!canOpen) {
      Alert.alert("Unavailable", "Cannot open export link on this device.");
      return;
    }
    await Linking.openURL(url);
  };

  const summary = (artifacts?.summary ?? null) as
    | { overview?: string; sections?: { title?: string; bullets?: string[] }[] }
    | null;
  const outline = (artifacts?.outline ?? null) as
    | { structure?: { title?: string; children?: { title?: string }[] }[] }
    | null;
  const flashcards = (artifacts?.flashcards ?? null) as
    | { cards?: { front?: string; back?: string }[] }
    | null;
  const examQuestions = (artifacts?.examQuestions ?? null) as
    | { questions?: { question?: string; answer?: string }[] }
    | null;
  const threads = (artifacts?.threads ?? null) as
    | {
        id?: string;
        title?: string;
        summary?: string;
        status?: string;
        complexity_level?: number;
        lecture_refs?: string[];
      }[]
    | null;

  const renderSummary = () => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>Summary</Text>
      <Text style={styles.previewBody}>
        {summary?.overview ?? "Run generation to see summary."}
      </Text>
      {summary?.sections?.map((section, idx) => (
        <View key={`${section.title}-${idx}`} style={styles.previewSection}>
          <Text style={styles.previewSubtitle}>{section.title ?? "Section"}</Text>
          {(section.bullets ?? []).map((bullet, bIdx) => (
            <Text key={`${bullet}-${bIdx}`} style={styles.previewBody}>
              • {bullet}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );

  const renderOutline = () => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>Outline</Text>
      {outline?.structure?.length ? (
        outline.structure.map((node, idx) => (
          <View key={`${node.title}-${idx}`} style={styles.previewSection}>
            <Text style={styles.previewSubtitle}>{node.title ?? "Topic"}</Text>
            {(node.children ?? []).map((child, cIdx) => (
              <Text key={`${child.title}-${cIdx}`} style={styles.previewBody}>
                • {child.title ?? "Subtopic"}
              </Text>
            ))}
          </View>
        ))
      ) : (
        <Text style={styles.previewBody}>Run generation to see outline.</Text>
      )}
    </View>
  );

  const renderFlashcards = () => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>Flashcards</Text>
      {flashcards?.cards?.length ? (
        flashcards.cards.slice(0, 5).map((card, idx) => (
          <View key={`${card.front}-${idx}`} style={styles.previewSection}>
            <Text style={styles.previewSubtitle}>{card.front ?? "Card"}</Text>
            <Text style={styles.previewBody}>{card.back ?? ""}</Text>
          </View>
        ))
      ) : (
        <Text style={styles.previewBody}>Run generation to see flashcards.</Text>
      )}
    </View>
  );

  const renderQuestions = () => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>Exam Questions</Text>
      {examQuestions?.questions?.length ? (
        examQuestions.questions.slice(0, 5).map((item, idx) => (
          <View key={`${item.question}-${idx}`} style={styles.previewSection}>
            <Text style={styles.previewSubtitle}>{item.question ?? "Question"}</Text>
            <Text style={styles.previewBody}>{item.answer ?? ""}</Text>
          </View>
        ))
      ) : (
        <Text style={styles.previewBody}>Run generation to see questions.</Text>
      )}
    </View>
  );

  const renderThreads = () => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>Thread Summary</Text>
      {threads?.length ? (
        threads.slice(0, 5).map((thread, idx) => (
          <TouchableOpacity
            key={`${thread.title}-${idx}`}
            style={styles.threadCard}
            onPress={() => setSelectedThread(thread)}
          >
          <View key={`${thread.title}-${idx}`} style={styles.previewSection}>
            <Text style={styles.previewSubtitle}>
              {thread.title ?? "Thread"}
            </Text>
            <Text style={styles.previewBody}>
              {thread.summary ?? "No summary available."}
            </Text>
            <Text style={styles.previewBody}>
              Status: {thread.status ?? "unknown"} • Complexity:{" "}
              {thread.complexity_level ?? "n/a"}
            </Text>
            <Text style={styles.threadHint}>Tap for details</Text>
          </TouchableOpacity>
          </View>
        ))
      ) : (
        <Text style={styles.previewBody}>No thread records yet.</Text>
      )}
  const renderArtifactPreview = (
    label: string,
    value: unknown,
    fallback: string
  ) => (
    <View style={styles.previewCard}>
      <Text style={styles.previewTitle}>{label}</Text>
      <Text style={styles.previewBody}>
        {value ? JSON.stringify(value, null, 2) : fallback}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Pegasus Lecture Copilot</Text>
        <Text style={styles.subtitle}>MVP Flow</Text>

        <View style={styles.card}>
          <Text style={styles.label}>Course ID</Text>
          <TextInput
            value={courseId}
            onChangeText={setCourseId}
            style={styles.input}
          />
          <Text style={styles.label}>Lecture ID</Text>
          <TextInput
            value={lectureId}
            onChangeText={setLectureId}
            style={styles.input}
          />
          <Text style={styles.label}>Preset</Text>
          <TextInput
            value={presetId}
            onChangeText={setPresetId}
            style={styles.input}
          />
          <Text style={styles.label}>Lecture Title</Text>
          <TextInput value={title} onChangeText={setTitle} style={styles.input} />
        </View>

        <TouchableOpacity style={styles.button} onPress={uploadAudio}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Upload Audio</Text>
          )}
        </TouchableOpacity>

        </View>

        <TouchableOpacity style={styles.button} onPress={runGenerate}>
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Generate Artifacts</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={runTranscribe}>
          <Text style={styles.secondaryButtonText}>Queue Transcription</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={runExport}>
          <Text style={styles.secondaryButtonText}>Queue Export</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={loadSummary}>
          <Text style={styles.secondaryButtonText}>Load Lecture Status</Text>
        </TouchableOpacity>

        {summaryStatus && (
          <View style={styles.statusCard}>
            <Text style={styles.sectionTitle}>Lecture Status</Text>
            <Text style={styles.previewBody}>
              {summaryStatus.lecture?.title ?? "Lecture"} •{" "}
              {summaryStatus.lecture?.status ?? "unknown"}
            </Text>
            <View style={styles.statusRow}>
              <Text style={styles.statusLabel}>Artifacts</Text>
              <Text style={styles.statusValue}>
                {summaryStatus.artifactCount}
              </Text>
            </View>
            <Text style={styles.previewBody}>
              Types:{" "}
              {summaryStatus.artifactTypes.length
                ? summaryStatus.artifactTypes.join(", ")
                : "None yet"}
            </Text>
            <View style={styles.statusRow}>
              <Text style={styles.statusLabel}>Exports</Text>
              <Text style={styles.statusValue}>{summaryStatus.exportCount}</Text>
            </View>
            <Text style={styles.previewBody}>
              Types:{" "}
              {summaryStatus.exportTypes.length
                ? summaryStatus.exportTypes.join(", ")
                : "None yet"}
            </Text>
            <Text style={styles.statusHint}>
              Exports available:{" "}
              {summaryStatus.exportTypes.length
                ? summaryStatus.exportTypes.join(", ").toUpperCase()
                : "No exports ready"}
            </Text>
          </View>
        )}

        {jobs.length > 0 && (
          <View style={styles.statusCard}>
            <Text style={styles.sectionTitle}>Job Status</Text>
            {jobs.map((job) => (
              <View key={job.id} style={styles.jobRow}>
                <View style={styles.jobMeta}>
                  <Text style={styles.jobType}>
                    {job.jobType.toUpperCase()}
                  </Text>
                  <Text style={styles.jobId}>ID: {job.id}</Text>
                </View>
                <Text
                  style={[
                    styles.jobStatus,
                    job.status === "failed" && styles.jobStatusFailed,
                    job.status === "completed" && styles.jobStatusSuccess,
                  ]}
                >
                  {job.status}
                </Text>
                {job.error ? (
                  <Text style={styles.jobError}>{job.error}</Text>
                ) : null}
              </View>
            ))}
          </View>
        )}

        <TouchableOpacity style={styles.secondaryButton} onPress={loadArtifacts}>
          <Text style={styles.secondaryButtonText}>Review Artifacts</Text>
        </TouchableOpacity>

        {artifacts && (
          <View style={styles.reviewSection}>
            <Text style={styles.sectionTitle}>Artifact Review</Text>
            {renderSummary()}
            {renderOutline()}
            {renderFlashcards()}
            {renderQuestions()}
            {renderThreads()}
          </View>
        )}

        {selectedThread && (
          <View style={styles.detailCard}>
            <View style={styles.detailHeader}>
              <Text style={styles.sectionTitle}>Thread Detail</Text>
              <TouchableOpacity onPress={() => setSelectedThread(null)}>
                <Text style={styles.detailClose}>Close</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.previewSubtitle}>
              {selectedThread.title ?? "Thread"}
            </Text>
            <Text style={styles.previewBody}>
              {selectedThread.summary ?? "No summary available."}
            </Text>
            <Text style={styles.previewBody}>
              Status: {selectedThread.status ?? "unknown"} • Complexity:{" "}
              {selectedThread.complexity_level ?? "n/a"}
            </Text>
            <Text style={styles.previewBody}>
              Lecture refs:{" "}
              {selectedThread.lecture_refs?.length
                ? selectedThread.lecture_refs.join(", ")
                : "None"}
            </Text>
            {renderArtifactPreview(
              "Summary",
              artifacts.summary,
              "Run generation to see summary."
            )}
            {renderArtifactPreview(
              "Outline",
              artifacts.outline,
              "Run generation to see outline."
            )}
            {renderArtifactPreview(
              "Flashcards",
              artifacts.flashcards,
              "Run generation to see flashcards."
            )}
            {renderArtifactPreview(
              "Exam Questions",
              artifacts.examQuestions,
              "Run generation to see questions."
            )}
          </View>
        )}

        {exportRecords.length > 0 && (
          <View style={styles.reviewSection}>
            <Text style={styles.sectionTitle}>Exports</Text>
            {exportRecords.map((record) => (
              <TouchableOpacity
                key={record.export_type}
                style={styles.linkButton}
                onPress={() => openExport(record.export_type)}
              >
                <Text style={styles.linkText}>
                  Download {record.export_type.toUpperCase()}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        )}
        {summaryStatus && exportRecords.length === 0 && (
          <View style={styles.reviewSection}>
            <Text style={styles.sectionTitle}>Exports</Text>
            <Text style={styles.previewBody}>
              {summaryStatus.exportTypes.length
                ? `Exports ready: ${summaryStatus.exportTypes
                    .join(", ")
                    .toUpperCase()}`
                : "No exports ready yet."}
            </Text>
          </View>
        )}

        <View style={styles.hint}>
          <Text style={styles.hintText}>
            Ensure the FastAPI server is running and transcripts exist in
            storage/transcripts.
          </Text>
        </View>
      </ScrollView>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  content: {
    padding: 24,
    gap: 16,
  },
  title: {
    color: "#f8fafc",
    fontSize: 28,
    fontWeight: "700",
  },
  subtitle: {
    color: "#cbd5f5",
    fontSize: 16,
  },
  card: {
    backgroundColor: "#111827",
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  label: {
    color: "#e2e8f0",
    fontSize: 14,
  },
  input: {
    backgroundColor: "#1f2937",
    color: "#f8fafc",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  button: {
    backgroundColor: "#2563eb",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  secondaryButton: {
    borderColor: "#60a5fa",
    borderWidth: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  secondaryButtonText: {
    color: "#93c5fd",
    fontSize: 16,
    fontWeight: "600",
  },
  reviewSection: {
    gap: 12,
  },
  statusCard: {
    backgroundColor: "#0b1120",
    borderRadius: 12,
    padding: 12,
    gap: 8,
    borderColor: "#1d4ed8",
    borderWidth: 1,
  },
  statusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  statusLabel: {
    color: "#93c5fd",
    fontSize: 13,
    fontWeight: "600",
  },
  statusValue: {
    color: "#f8fafc",
    fontSize: 13,
    fontWeight: "600",
  },
  statusHint: {
    color: "#93c5fd",
    fontSize: 12,
  },
  jobRow: {
    backgroundColor: "#111827",
    borderRadius: 10,
    padding: 10,
    gap: 6,
  },
  jobMeta: {
    gap: 2,
  },
  jobType: {
    color: "#e2e8f0",
    fontSize: 13,
    fontWeight: "600",
  },
  jobId: {
    color: "#94a3b8",
    fontSize: 11,
  },
  jobStatus: {
    color: "#f8fafc",
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
  },
  jobStatusFailed: {
    color: "#fca5a5",
  },
  jobStatusSuccess: {
    color: "#86efac",
  },
  jobError: {
    color: "#fca5a5",
    fontSize: 11,
  },
  sectionTitle: {
    color: "#f8fafc",
    fontSize: 18,
    fontWeight: "600",
  },
  previewCard: {
    backgroundColor: "#111827",
    borderRadius: 12,
    padding: 12,
  },
  previewTitle: {
    color: "#e2e8f0",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 8,
  },
  previewBody: {
    color: "#cbd5f5",
    fontSize: 12,
  },
  previewSection: {
    marginTop: 10,
    gap: 4,
  },
  threadCard: {
    marginTop: 10,
    gap: 4,
    padding: 10,
    borderRadius: 10,
    backgroundColor: "#0f172a",
    borderColor: "#1e3a8a",
    borderWidth: 1,
  },
  threadHint: {
    color: "#93c5fd",
    fontSize: 12,
    marginTop: 6,
  },
  detailCard: {
    backgroundColor: "#0b1120",
    borderRadius: 12,
    padding: 12,
    gap: 8,
    borderColor: "#2563eb",
    borderWidth: 1,
  },
  detailHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  detailClose: {
    color: "#93c5fd",
    fontSize: 13,
    fontWeight: "600",
  },
  previewSubtitle: {
    color: "#e2e8f0",
    fontSize: 13,
    fontWeight: "600",
  },
  linkButton: {
    borderColor: "#38bdf8",
    borderWidth: 1,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: "center",
  },
  linkText: {
    color: "#7dd3fc",
    fontSize: 15,
    fontWeight: "600",
  },
  hint: {
    backgroundColor: "#0b1120",
    padding: 12,
    borderRadius: 10,
  },
  hintText: {
    color: "#94a3b8",
    fontSize: 13,
  },
});
