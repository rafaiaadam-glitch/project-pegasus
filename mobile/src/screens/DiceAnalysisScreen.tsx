import React, { useState, useEffect, useCallback } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { Card, Text, ActivityIndicator, Chip } from 'react-native-paper';
import api from '../services/api';
import { useTheme } from '../theme';
import { createDiceEngine, ThreadFacets, DiceFace } from 'core/thread_engine';

interface Props {
  navigation: any;
  route: any;
}

const FACET_META: Record<DiceFace, { label: string; color: string; darkColor: string }> = {
  RED:    { label: 'How',   color: '#D32F2F', darkColor: '#EF5350' },
  ORANGE: { label: 'What',  color: '#E65100', darkColor: '#FF9800' },
  YELLOW: { label: 'When',  color: '#F9A825', darkColor: '#FFEE58' },
  GREEN:  { label: 'Where', color: '#2E7D32', darkColor: '#66BB6A' },
  BLUE:   { label: 'Who',   color: '#1565C0', darkColor: '#42A5F5' },
  PURPLE: { label: 'Why',   color: '#6A1B9A', darkColor: '#AB47BC' },
};

const FACES: DiceFace[] = ['RED', 'ORANGE', 'YELLOW', 'GREEN', 'BLUE', 'PURPLE'];

const MAX_CHARS = 1500;

export default function DiceAnalysisScreen({ navigation, route }: Props) {
  const { theme, isDark } = useTheme();
  const { lectureId, lectureTitle } = route.params;

  const [status, setStatus] = useState('Loading transcript...');
  const [running, setRunning] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [facets, setFacets] = useState<ThreadFacets | null>(null);

  useEffect(() => {
    navigation.setOptions({ title: lectureTitle || 'Dice Analysis' });
  }, [lectureTitle]);

  const run = useCallback(async () => {
    try {
      setRunning(true);
      setError(null);

      setStatus('Fetching transcript...');
      const data = await api.getTranscript(lectureId);
      const fullText = data.text || '';
      if (!fullText.trim()) {
        setError('No transcript text available for this lecture.');
        setRunning(false);
        return;
      }

      const text = fullText.slice(0, MAX_CHARS);
      const segmentNote = fullText.length > MAX_CHARS
        ? ` (using first ${MAX_CHARS} chars of ${fullText.length})`
        : '';

      setStatus(`Running dice engine${segmentNote}...`);

      const engine = createDiceEngine(api.llmComplete.bind(api));
      const result = await engine.processTranscript(text, lectureId, { safeMode: true });

      setFacets(result);
      setStatus('Done');
    } catch (err: any) {
      console.error('Dice analysis error:', err);
      setError(err.message || 'Analysis failed');
    } finally {
      setRunning(false);
    }
  }, [lectureId]);

  useEffect(() => {
    run();
  }, [run]);

  if (error) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <Text style={{ fontSize: 48, marginBottom: 12 }}>&#x26A0;</Text>
        <Text variant="bodyLarge" style={{ color: theme.colors.error, textAlign: 'center', paddingHorizontal: 32 }}>
          {error}
        </Text>
      </View>
    );
  }

  if (running) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <ActivityIndicator size="large" />
        <Text variant="bodyLarge" style={{ marginTop: 16, color: theme.colors.onSurfaceVariant }}>
          {status}
        </Text>
      </View>
    );
  }

  if (!facets) return null;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={styles.list}
    >
      {FACES.map((face) => {
        const meta = FACET_META[face];
        const evidence = facets[face];
        const accentColor = isDark ? meta.darkColor : meta.color;

        return (
          <Card
            key={face}
            style={[styles.card, { borderLeftColor: accentColor, borderLeftWidth: 4 }]}
            mode="elevated"
          >
            <Card.Content>
              <View style={styles.headerRow}>
                <Chip
                  compact
                  style={{ backgroundColor: accentColor }}
                  textStyle={{ color: '#FFFFFF', fontWeight: '700' }}
                >
                  {face}
                </Chip>
                <Text variant="titleMedium" style={{ marginLeft: 8 }}>
                  {meta.label}
                </Text>
                <Text variant="labelSmall" style={{ marginLeft: 'auto', color: theme.colors.onSurfaceVariant }}>
                  {evidence.sourceCount} hits
                </Text>
              </View>

              {evidence.snippets.length === 0 ? (
                <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, fontStyle: 'italic', marginTop: 8 }}>
                  No evidence found
                </Text>
              ) : (
                evidence.snippets.map((snippet, i) => (
                  <Text
                    key={i}
                    variant="bodySmall"
                    style={{ color: theme.colors.onSurface, marginTop: i === 0 ? 10 : 6, lineHeight: 18 }}
                  >
                    {snippet}
                  </Text>
                ))
              )}
            </Card.Content>
          </Card>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  list: { padding: 16, paddingBottom: 32 },
  card: { marginBottom: 12 },
  headerRow: { flexDirection: 'row', alignItems: 'center' },
});
