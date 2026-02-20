import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  View,
  SectionList,
  RefreshControl,
  StyleSheet,
} from 'react-native';
import {
  Text,
  Chip,
  ActivityIndicator,
} from 'react-native-paper';
import { Thread, DiceFace } from '../types';
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

const FACE_ORDER: DiceFace[] = ['RED', 'ORANGE', 'YELLOW', 'GREEN', 'BLUE', 'PURPLE'];

interface Props {
  navigation: any;
  route: any;
}

interface FaceSection {
  face: DiceFace;
  data: Thread[];
}

export default function ThreadsScreen({ navigation, route }: Props) {
  const { theme, isDark } = useTheme();
  const { courseId, courseTitle } = route.params;
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: courseTitle || 'Threads' });
    loadThreads();
  }, [courseId]);

  const loadThreads = async () => {
    try {
      setLoading(true);
      setLoadError(false);
      const data = await api.getCourseThreads(courseId);
      setThreads(data.threads || []);
    } catch (error) {
      console.error('Error loading threads:', error);
      setLoadError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadThreads();
  };

  const sections: FaceSection[] = useMemo(() => {
    if (threads.length === 0) return [];

    const grouped = new Map<DiceFace, Thread[]>();
    for (const face of FACE_ORDER) {
      grouped.set(face, []);
    }

    for (const t of threads) {
      const face: DiceFace = (t.face && FACE_ORDER.includes(t.face)) ? t.face : 'ORANGE';
      grouped.get(face)!.push(t);
    }

    // Only include sections that have threads
    return FACE_ORDER
      .filter((face) => grouped.get(face)!.length > 0)
      .map((face) => ({ face, data: grouped.get(face)! }));
  }, [threads]);

  const renderSectionHeader = ({ section }: { section: FaceSection }) => {
    const meta = FACE_META[section.face];
    const accentColor = isDark ? meta.darkColor : meta.color;

    return (
      <View style={[styles.sectionHeader, { backgroundColor: theme.colors.background }]}>
        <View style={[styles.faceBadge, { backgroundColor: accentColor }]}>
          <Text style={styles.faceBadgeText}>{section.face}</Text>
        </View>
        <Text variant="titleSmall" style={{ marginLeft: 10 }}>
          {meta.label}
        </Text>
        <Text variant="labelSmall" style={{ marginLeft: 'auto', color: theme.colors.onSurfaceVariant }}>
          {section.data.length}
        </Text>
      </View>
    );
  };

  const renderThread = ({ item }: { item: Thread }) => {
    const face: DiceFace = (item.face && FACE_ORDER.includes(item.face)) ? item.face : 'ORANGE';
    const meta = FACE_META[face];
    const accentColor = isDark ? meta.darkColor : meta.color;
    const lectureCount = (item.lecture_refs || []).length;

    return (
      <View style={[styles.threadRow, { backgroundColor: theme.colors.surface }]}>
        <View style={[styles.colorBar, { backgroundColor: accentColor }]} />
        <View style={styles.threadContent}>
          <Text variant="bodyLarge" numberOfLines={1}>
            {item.title}
          </Text>
          {item.summary ? (
            <Text
              variant="bodySmall"
              numberOfLines={2}
              style={{ color: theme.colors.onSurfaceVariant, marginTop: 2 }}
            >
              {item.summary}
            </Text>
          ) : null}
          <View style={styles.chipRow}>
            <Chip compact textStyle={{ fontSize: 10 }}>
              {item.status === 'foundational' ? 'Core' : 'Advanced'}
            </Chip>
            {(item.complexity_level || 0) > 0 && (
              <Chip compact textStyle={{ fontSize: 10 }} style={{ marginLeft: 6 }}>
                L{item.complexity_level}
              </Chip>
            )}
            <Text
              variant="labelSmall"
              style={{ color: theme.colors.onSurfaceVariant, marginLeft: 8 }}
            >
              {lectureCount} lecture{lectureCount !== 1 ? 's' : ''}
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>&#x1F3B2;</Text>
      <Text variant="titleMedium" style={{ marginBottom: 6 }}>No threads yet</Text>
      <Text
        variant="bodyMedium"
        style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}
      >
        Threads appear after generating study materials from lectures
      </Text>
    </View>
  );

  const renderListHeader = () => (
    <View style={styles.listHeader}>
      <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
        {threads.length} keyword{threads.length !== 1 ? 's' : ''} across {sections.length} face{sections.length !== 1 ? 's' : ''}
      </Text>
    </View>
  );

  if (loadError && threads.length === 0) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <NetworkErrorView onRetry={loadThreads} message="Could not load threads. Please check your connection and try again." />
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

  if (threads.length === 0) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        {renderEmpty()}
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id}
        renderSectionHeader={renderSectionHeader}
        renderItem={renderThread}
        ListHeaderComponent={renderListHeader}
        ItemSeparatorComponent={() => (
          <View
            style={{
              height: StyleSheet.hairlineWidth,
              backgroundColor: theme.colors.outlineVariant,
              marginLeft: 19,
            }}
          />
        )}
        stickySectionHeadersEnabled={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.onSurfaceVariant}
          />
        }
        contentContainerStyle={{ paddingBottom: 32 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 8,
  },
  faceBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  faceBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  threadRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 12,
    paddingRight: 16,
  },
  colorBar: {
    width: 3,
    height: 32,
    borderRadius: 1.5,
    marginLeft: 16,
    marginRight: 12,
    marginTop: 4,
  },
  threadContent: {
    flex: 1,
  },
  chipRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 48,
    paddingTop: 80,
  },
  listHeader: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
});
