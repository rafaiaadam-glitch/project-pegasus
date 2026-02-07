import { StatusBar } from "expo-status-bar";
import { useState } from "react";
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

export default function App() {
  const [courseId, setCourseId] = useState("course-001");
  const [lectureId, setLectureId] = useState("lecture-001");
  const [presetId, setPresetId] = useState("exam-mode");
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
      Alert.alert("Export queued", `Job ID: ${data.jobId}`);
    } catch (error) {
      Alert.alert("Error", `${error}`);
    } finally {
      setLoading(false);
    }
  };

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
