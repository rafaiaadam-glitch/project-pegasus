import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { API_URL } from '../services/api'; //

// Progress stages for Gemini 3 Reasoning
type GenerationStage = 'IDLE' | 'UPLOADING' | 'TRANSCRIBING' | 'THINKING' | 'FINALIZING' | 'COMPLETE' | 'ERROR';

export const RecordLectureScreen = () => {
  const [stage, setStage] = useState<GenerationStage>('IDLE');
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation();

  // Helper to map stages to user-friendly messages
  const getStageMessage = () => {
    switch (stage) {
      case 'UPLOADING': return 'Uploading audio to Pegasus...';
      case 'TRANSCRIBING': return 'Converting speech to text...';
      case 'THINKING': return 'AI is thinking deeply (Gemini 3 Mode)...'; // Reasoning indicator
      case 'FINALIZING': return 'Building your study artifacts...';
      case 'COMPLETE': return 'Success! Your lecture is ready.';
      default: return 'Ready to record';
    }
  };

  const startIngestion = async () => {
    setStage('UPLOADING');
    setError(null);

    try {
      // 1. Upload & Transcribe
      // Trigger transcription pipeline in us-central1
      setStage('TRANSCRIBING');
      const response = await fetch(`${API_URL}/lectures/ingest`, { method: 'POST' });
      
      if (!response.ok) throw new Error('Ingestion failed');
      const { lectureId } = await response.json();

      // 2. Deep Reasoning Stage
      // Reasoning models take significantly longer than standard models
      setStage('THINKING'); 
      const genResponse = await fetch(`${API_URL}/lectures/${lectureId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset_id: 'exam-mode' }) //
      });

      if (!genResponse.ok) throw new Error('AI reasoning failed');

      setStage('COMPLETE');
      // Navigate to review once final artifacts exist
      setTimeout(() => navigation.navigate('LectureDetail', { lectureId }), 1500);

    } catch (err: any) {
      setStage('ERROR');
      setError(err.message || 'An unexpected error occurred');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>New Lecture</Text>
      
      <View style={styles.statusBox}>
        {stage !== 'IDLE' && stage !== 'COMPLETE' && stage !== 'ERROR' && (
          <ActivityIndicator size="large" color="#007AFF" style={styles.spinner} />
        )}
        <Text style={styles.statusText}>{getStageMessage()}</Text>
        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>

      <TouchableOpacity 
        style={[styles.button, stage !== 'IDLE' && styles.buttonDisabled]}
        onPress={startIngestion}
        disabled={stage !== 'IDLE'}
      >
        <Text style={styles.buttonText}>
          {stage === 'IDLE' ? 'Start Processing' : 'Processing...'}
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#F9F9F9', justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 30, textAlign: 'center' },
  statusBox: { height: 150, alignItems: 'center', justifyContent: 'center', marginBottom: 40 },
  spinner: { marginBottom: 20 },
  statusText: { fontSize: 18, color: '#333', textAlign: 'center' },
  errorText: { color: '#FF3B30', marginTop: 10, textAlign: 'center' },
  button: { backgroundColor: '#007AFF', padding: 18, borderRadius: 12, alignItems: 'center' },
  buttonDisabled: { backgroundColor: '#A2A2A2' },
  buttonText: { color: '#FFF', fontSize: 18, fontWeight: '600' }
});
