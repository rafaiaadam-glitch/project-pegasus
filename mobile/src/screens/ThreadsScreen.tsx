import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  View,
  FlatList,
  RefreshControl,
  LayoutAnimation,
  UIManager,
  Platform,
} from 'react-native';
import {
  Text,
  Chip,
  ActivityIndicator,
  TouchableRipple,
} from 'react-native-paper';
import { Thread } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';

if (Platform.OS === 'android') {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

interface Props {
  navigation: any;
  route: any;
}

export default function ThreadsScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { courseId, courseTitle } = route.params;
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    navigation.setOptions({ title: courseTitle || 'Threads' });
    loadThreads();
  }, [courseId]);

  const loadThreads = async () => {
    try {
      setLoading(true);
      const data = await api.getCourseThreadTree(courseId);
      setThreads(data.threads || []);
    } catch (error) {
      console.error('Error loading threads:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadThreads();
  };

  const toggleExpand = useCallback((threadId: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) {
        next.delete(threadId);
      } else {
        next.add(threadId);
      }
      return next;
    });
  }, []);

  const visibleThreads = useMemo(() => {
    if (threads.length === 0) return [];

    const childrenMap = new Map<string, Thread[]>();
    const roots: Thread[] = [];

    for (const t of threads) {
      if (!t.parent_id) {
        roots.push(t);
      } else {
        const siblings = childrenMap.get(t.parent_id) || [];
        siblings.push(t);
        childrenMap.set(t.parent_id, siblings);
      }
    }

    const result: Thread[] = [];
    const walk = (nodes: Thread[]) => {
      for (const node of nodes) {
        result.push(node);
        if (expandedIds.has(node.id)) {
          const children = childrenMap.get(node.id);
          if (children) walk(children);
        }
      }
    };
    walk(roots);
    return result;
  }, [threads, expandedIds]);

  const renderThread = ({ item }: { item: Thread }) => {
    const depth = item.depth || 0;
    const hasChildren = (item.child_count || 0) > 0;
    const isExpanded = expandedIds.has(item.id);
    const isFoundational = item.status === 'foundational';
    const lectureCount = (item.lecture_refs || []).length;

    return (
      <TouchableRipple
        onPress={hasChildren ? () => toggleExpand(item.id) : undefined}
        style={{
          flexDirection: 'row',
          alignItems: 'flex-start',
          paddingVertical: 12,
          paddingRight: 16,
          paddingLeft: 16 + depth * 20,
          backgroundColor: theme.colors.surface,
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'flex-start', flex: 1 }}>
          <View
            style={{
              width: 3,
              height: 32,
              borderRadius: 1.5,
              marginRight: 12,
              marginTop: 2,
              backgroundColor: isFoundational ? theme.colors.primary : theme.colors.tertiary,
            }}
          />
          <View style={{ flex: 1 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 2 }}>
              <Text variant="bodyLarge" numberOfLines={1} style={{ flex: 1 }}>
                {item.title}
              </Text>
              {hasChildren && (
                <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginLeft: 8 }}>
                  {isExpanded ? '\u25BE' : '\u25B8'}
                </Text>
              )}
            </View>
            {item.summary ? (
              <Text variant="bodySmall" numberOfLines={1} style={{ color: theme.colors.onSurfaceVariant, marginBottom: 4 }}>
                {item.summary}
              </Text>
            ) : null}
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Chip compact textStyle={{ fontSize: 10 }}>
                {isFoundational ? 'Core' : 'Advanced'}
              </Chip>
              <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                {lectureCount} lecture{lectureCount !== 1 ? 's' : ''}
              </Text>
              {(item.complexity_level || 0) > 0 && (
                <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
                  L{item.complexity_level}
                </Text>
              )}
            </View>
          </View>
        </View>
      </TouchableRipple>
    );
  };

  const renderEmpty = () => (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 48, paddingTop: 80 }}>
      <Text style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>&#x1F9F5;</Text>
      <Text variant="titleMedium" style={{ marginBottom: 6 }}>No threads yet</Text>
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
        Threads appear after generating study materials from lectures
      </Text>
    </View>
  );

  const renderHeader = () => (
    <View style={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 8 }}>
      <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
        {threads.length} thread{threads.length !== 1 ? 's' : ''}
      </Text>
    </View>
  );

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator size="small" />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <FlatList
        data={visibleThreads}
        renderItem={renderThread}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ flexGrow: 1 }}
        ListHeaderComponent={threads.length > 0 ? renderHeader : null}
        ItemSeparatorComponent={() => (
          <View style={{ height: 0.5, backgroundColor: theme.colors.outlineVariant, marginLeft: 52 }} />
        )}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.onSurfaceVariant}
          />
        }
        ListEmptyComponent={renderEmpty}
      />
    </View>
  );
}
