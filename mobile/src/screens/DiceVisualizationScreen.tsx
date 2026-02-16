import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { DiceGrid, DiceFace } from '../components/DiceGrid';
import { API_URL } from '../config';

interface RotationState {
  schedule: DiceFace[][];
  activeIndex: number;
  scores: Record<DiceFace, number>;
  entropy: number;
  equilibriumGap: number;
  collapsed: boolean;
  status: string;
  iterationsCompleted: number;
  dominantFacet?: string;
  dominantScore?: number;
}

export default function DiceVisualizationScreen({ route, navigation }: any) {
  const { lectureId, lectureTitle } = route.params || {};

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rotationState, setRotationState] = useState<RotationState | null>(null);

  useEffect(() => {
    if (lectureId) {
      fetchDiceState();
    }
  }, [lectureId]);

  const fetchDiceState = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/lectures/${lectureId}/dice-state`);

      if (!response.ok) {
        throw new Error(`Failed to fetch dice state: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.hasRotationState) {
        setError('No rotation state available for this lecture');
        setLoading(false);
        return;
      }

      // Extract rotation state from fullState or use top-level fields
      const state = data.rotationState.fullState || data.rotationState;

      setRotationState({
        schedule: state.schedule || [],
        activeIndex: state.activeIndex || 0,
        scores: state.scores || {},
        entropy: state.entropy || 0,
        equilibriumGap: state.equilibriumGap || 1.0,
        collapsed: state.collapsed || false,
        status: data.rotationState.status || 'unknown',
        iterationsCompleted: data.rotationState.iterationsCompleted || 0,
        dominantFacet: data.rotationState.dominantFacet,
        dominantScore: data.rotationState.dominantScore,
      });

      setLoading(false);
    } catch (err: any) {
      console.error('Error fetching dice state:', err);
      setError(err.message || 'Failed to load dice state');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading dice rotation state...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>❌ {error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={fetchDiceState}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!rotationState) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.emptyText}>No rotation state available</Text>
      </View>
    );
  }

  const isEquilibrium = rotationState.equilibriumGap < 0.15;

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🎲 Dice Rotation State</Text>
        {lectureTitle && <Text style={styles.subtitle}>{lectureTitle}</Text>}
      </View>

      {/* Status Summary */}
      <View style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Status:</Text>
          <Text style={[styles.summaryValue, styles.statusValue]}>
            {rotationState.status.toUpperCase()}
          </Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Iterations:</Text>
          <Text style={styles.summaryValue}>{rotationState.iterationsCompleted}</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Entropy:</Text>
          <Text style={styles.summaryValue}>{rotationState.entropy.toFixed(3)}</Text>
        </View>
        <View style={styles.summaryRow}>
          <Text style={styles.summaryLabel}>Equilibrium Gap:</Text>
          <Text style={styles.summaryValue}>
            {rotationState.equilibriumGap.toFixed(3)}
          </Text>
        </View>
        {rotationState.dominantFacet && (
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Dominant Facet:</Text>
            <Text style={styles.summaryValue}>
              {rotationState.dominantFacet} (
              {((rotationState.dominantScore || 0) * 100).toFixed(0)}%)
            </Text>
          </View>
        )}
      </View>

      {/* Dice Grid Visualization */}
      <View style={styles.gridCard}>
        <Text style={styles.cardTitle}>Cognitive State Monitor</Text>
        <Text style={styles.cardDescription}>
          Each row shows a rotation state. Brighter dots = higher confidence.
          Active row is highlighted.
        </Text>

        <DiceGrid
          schedule={rotationState.schedule}
          activeIndex={rotationState.activeIndex}
          scores={rotationState.scores}
          collapsed={rotationState.collapsed}
          equilibrium={isEquilibrium}
        />
      </View>

      {/* Explanation */}
      <View style={styles.explanationCard}>
        <Text style={styles.cardTitle}>What This Shows</Text>
        <Text style={styles.explanationText}>
          The dot grid visualizes how the Thread Engine analyzed this lecture from
          multiple perspectives (facets).
        </Text>
        <Text style={styles.explanationText}>
          • <Text style={styles.bold}>Opacity</Text> = Confidence (bright = strong
          facet)
        </Text>
        <Text style={styles.explanationText}>
          • <Text style={styles.bold}>Active Row</Text> = Current rotation state
        </Text>
        <Text style={styles.explanationText}>
          • <Text style={styles.bold}>Bars Below</Text> = Overall facet strength
        </Text>
        {rotationState.collapsed && (
          <Text style={[styles.explanationText, styles.warningText]}>
            ⚠️ Collapsed state detected - one facet dominated the analysis
          </Text>
        )}
        {isEquilibrium && (
          <Text style={[styles.explanationText, styles.successText]}>
            ✅ Equilibrium reached - balanced across all facets
          </Text>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#666',
  },
  errorText: {
    fontSize: 16,
    color: '#FF3B30',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    backgroundColor: '#007AFF',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
  },
  summaryCard: {
    margin: 16,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    gap: 10,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600',
  },
  summaryValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '700',
  },
  statusValue: {
    color: '#007AFF',
  },
  gridCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  cardDescription: {
    fontSize: 13,
    color: '#666',
    marginBottom: 16,
    lineHeight: 18,
  },
  explanationCard: {
    margin: 16,
    marginTop: 0,
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    gap: 8,
  },
  explanationText: {
    fontSize: 13,
    color: '#666',
    lineHeight: 20,
  },
  bold: {
    fontWeight: '700',
    color: '#333',
  },
  warningText: {
    color: '#FF3B30',
    fontWeight: '600',
    marginTop: 8,
  },
  successText: {
    color: '#34C759',
    fontWeight: '600',
    marginTop: 8,
  },
});
