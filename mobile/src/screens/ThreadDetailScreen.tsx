import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { Text, Chip, ActivityIndicator } from 'react-native-paper';
import { DiceFace, ThreadOccurrence, ThreadUpdate, ThreadDetail } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';
import NetworkErrorView from '../components/NetworkErrorView';

const FACE_META: Record<DiceFace, { label: string; color: string; darkColor: string }> = {
  RED:    { label: 'How',   color: '#D32F2F', darkColor: '#EF5350' },
  ORANGE: { label: 'What',  color: '#E65100', darkColor: '#FF9800' },
  YELLOW: { label: 'When',  color: '#F9A825', darkColor: '#FFEE58' },
  GREEN:  { label: 'Where', color: '#2E7D32', darkColor: '#66BB6A' },
  BLUE:   { label: 'Who',   color: '#1565C0', darkColor: '#42A5F5' },
  PURPLE: { label: 'Why',   color: '#6A1B9A', darkColor: '#AB47BC' },
};

const CHANGE_TYPE_META: Record<string, { label: string; color: string }> = {
  refinement:    { label: 'Refined',       color: '#1565C0' },
  contradiction: { label: 'Contradiction', color: '#D32F2F' },
  complexity:    { label: 'Complexity',    color: '#6A1B9A' },
};

interface Props {
  navigation: any;
  route: any;
}

export default function ThreadDetailScreen({ navigation, route }: Props) {
  const { theme, isDark } = useTheme();
  const { threadId } = route.params;
  const [data, setData] = useState<ThreadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    loadDetail();
  }, [threadId]);

  const loadDetail = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const result = await api.getThreadDetail(threadId);
      setData(result);
      navigation.setOptions({ title: result.thread?.title || 'Thread' });
    } catch (error) {
      console.error('Error loading thread detail:', error);
      setLoadError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDetail();
  };

  if (loadError && !data) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <NetworkErrorView onRetry={loadDetail} message="Could not load thread details." />
      </View>
    );
  }

  if (loading && !refreshing) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <ActivityIndicator size="small" />
      </View>
    );
  }

  if (!data) return null;

  const { thread, occurrences, updates, lectureTitles } = data;
  const face: DiceFace = (thread.face as DiceFace) || 'ORANGE';
  const meta = FACE_META[face];
  const accentColor = isDark ? meta.darkColor : meta.color;
  const lectureRefs: string[] = thread.lecture_refs || [];

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={theme.colors.onSurfaceVariant}
        />
      }
      contentContainerStyle={{ paddingBottom: 48 }}
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={[styles.faceBadge, { backgroundColor: accentColor }]}>
          <Text style={styles.faceBadgeText}>{face} - {meta.label}</Text>
        </View>
        <Text variant="headlineSmall" style={{ marginTop: 12 }}>
          {thread.title}
        </Text>
        {thread.summary ? (
          <Text
            variant="bodyMedium"
            style={{ color: theme.colors.onSurfaceVariant, marginTop: 6 }}
          >
            {thread.summary}
          </Text>
        ) : null}
        <View style={styles.chipRow}>
          <Chip compact textStyle={{ fontSize: 11 }}>
            {thread.status === 'foundational' ? 'Core' : 'Advanced'}
          </Chip>
          {(thread.complexity_level || 0) > 0 && (
            <Chip compact textStyle={{ fontSize: 11 }} style={{ marginLeft: 6 }}>
              Level {thread.complexity_level}
            </Chip>
          )}
        </View>
      </View>

      {/* Lectures section */}
      {lectureRefs.length > 0 && (
        <View style={styles.section}>
          <Text variant="titleSmall" style={styles.sectionTitle}>
            Appears in {lectureRefs.length} lecture{lectureRefs.length !== 1 ? 's' : ''}
          </Text>
          {lectureRefs.map((lid) => (
            <TouchableOpacity
              key={lid}
              style={[styles.lectureRow, { backgroundColor: theme.colors.surface }]}
              onPress={() => navigation.navigate('LectureDetail', {
                lectureId: lid,
                lectureTitle: lectureTitles[lid] || 'Lecture',
                courseId: data?.thread?.course_id,
              })}
            >
              <Text variant="bodyMedium">{lectureTitles[lid] || lid}</Text>
              <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
                View
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Evidence section */}
      {occurrences.length > 0 && (
        <View style={styles.section}>
          <Text variant="titleSmall" style={styles.sectionTitle}>
            Evidence ({occurrences.length})
          </Text>
          {occurrences.map((occ: ThreadOccurrence) => (
            <View
              key={occ.id}
              style={[styles.evidenceCard, { backgroundColor: theme.colors.surface }]}
            >
              <View style={styles.evidenceHeader}>
                <Text variant="labelMedium" style={{ flex: 1 }}>
                  {occ.lecture_title || lectureTitles[occ.lecture_id] || 'Unknown lecture'}
                </Text>
                <Text
                  variant="labelSmall"
                  style={{ color: theme.colors.onSurfaceVariant }}
                >
                  {Math.round(occ.confidence * 100)}%
                </Text>
              </View>
              <Text
                variant="bodySmall"
                style={{ color: theme.colors.onSurfaceVariant, marginTop: 4, fontStyle: 'italic' }}
              >
                "{occ.evidence}"
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Evolution section */}
      {updates.length > 0 && (
        <View style={styles.section}>
          <Text variant="titleSmall" style={styles.sectionTitle}>
            Evolution ({updates.length})
          </Text>
          {updates.map((upd: ThreadUpdate) => {
            const changeMeta = CHANGE_TYPE_META[upd.change_type] || {
              label: upd.change_type,
              color: '#666',
            };
            return (
              <View
                key={upd.id}
                style={[styles.updateCard, { backgroundColor: theme.colors.surface }]}
              >
                <View style={styles.updateHeader}>
                  <View
                    style={[
                      styles.changeTypeBadge,
                      { backgroundColor: changeMeta.color },
                    ]}
                  >
                    <Text style={styles.changeTypeBadgeText}>{changeMeta.label}</Text>
                  </View>
                  <Text
                    variant="labelSmall"
                    style={{ color: theme.colors.onSurfaceVariant, marginLeft: 8 }}
                  >
                    {upd.lecture_title || lectureTitles[upd.lecture_id] || 'Unknown'}
                  </Text>
                </View>
                <Text variant="bodySmall" style={{ marginTop: 6 }}>
                  {upd.summary}
                </Text>
                {upd.details && upd.details.length > 0 && (
                  <View style={{ marginTop: 4 }}>
                    {upd.details.map((d, i) => (
                      <Text
                        key={i}
                        variant="bodySmall"
                        style={{ color: theme.colors.onSurfaceVariant }}
                      >
                        - {d}
                      </Text>
                    ))}
                  </View>
                )}
              </View>
            );
          })}
        </View>
      )}

      {occurrences.length === 0 && updates.length === 0 && (
        <View style={styles.emptySection}>
          <Text
            variant="bodyMedium"
            style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}
          >
            No cross-lecture data yet. Re-generate a lecture to populate evidence and evolution.
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    padding: 16,
    paddingBottom: 12,
  },
  faceBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
  },
  faceBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  chipRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  section: {
    paddingHorizontal: 16,
    marginTop: 16,
  },
  sectionTitle: {
    marginBottom: 8,
  },
  lectureRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    marginBottom: 6,
  },
  evidenceCard: {
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  evidenceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  updateCard: {
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  updateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  changeTypeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  changeTypeBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
  },
  emptySection: {
    paddingHorizontal: 32,
    paddingTop: 40,
  },
});
