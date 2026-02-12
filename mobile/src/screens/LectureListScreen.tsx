import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Alert,
  TextInput,
  ScrollView,
} from 'react-native';
import { Lecture } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureListScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { courseId, courseTitle } = route.params;
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    navigation.setOptions({ title: courseTitle || 'Lectures' });
    loadLectures();
  }, [courseId]);

  // Filter lectures based on search and status
  const filteredLectures = useMemo(() => {
    let filtered = lectures;

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter((lecture) => lecture.status === statusFilter);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((lecture) =>
        lecture.title.toLowerCase().includes(query)
      );
    }

    return filtered;
  }, [lectures, searchQuery, statusFilter]);

  const loadLectures = async () => {
    try {
      setLoading(true);
      const response = await api.getCourseLectures(courseId);
      setLectures(response.lectures);
    } catch (error) {
      Alert.alert('Error', 'Failed to load lectures');
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadLectures();
  };

  const handleLecturePress = (lecture: Lecture) => {
    navigation.navigate('LectureDetail', {
      lectureId: lecture.id,
      lectureTitle: lecture.title,
      courseId,
    });
  };

  const handleAddLecture = () => {
    navigation.navigate('RecordLecture', { courseId });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'generated':
        return '#34C759';
      case 'processing':
        return '#FF9500';
      case 'failed':
        return '#FF3B30';
      default:
        return '#8E8E93';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'generated':
        return 'Ready';
      case 'processing':
        return 'Processing';
      case 'failed':
        return 'Failed';
      case 'uploaded':
        return 'Uploaded';
      default:
        return status;
    }
  };

  const renderLecture = ({ item }: { item: Lecture }) => (
    <TouchableOpacity
      style={styles.lectureCard}
      onPress={() => handleLecturePress(item)}
    >
      <View style={styles.lectureHeader}>
        <Text style={styles.lectureTitle}>{item.title}</Text>
        <View
          style={[
            styles.statusBadge,
            { backgroundColor: getStatusColor(item.status) + '20' },
          ]}
        >
          <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
            {getStatusText(item.status)}
          </Text>
        </View>
      </View>

      <Text style={styles.lectureDate}>
        {new Date(item.created_at).toLocaleDateString()} •{' '}
        {new Date(item.created_at).toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        })}
      </Text>

      {item.duration_sec && (
        <Text style={styles.lectureDuration}>
          Duration: {Math.floor(item.duration_sec / 60)}m {item.duration_sec % 60}s
        </Text>
      )}
    </TouchableOpacity>
  );

  const renderEmpty = () => {
    if (searchQuery.trim() || statusFilter !== 'all') {
      return (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🔍</Text>
          <Text style={styles.emptyTitle}>No Results Found</Text>
          <Text style={styles.emptyText}>
            Try adjusting your search or filters
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyIcon}>🎤</Text>
        <Text style={styles.emptyTitle}>No Lectures Yet</Text>
        <Text style={styles.emptyText}>
          Start by recording or uploading your first lecture
        </Text>
        <TouchableOpacity style={styles.addButton} onPress={handleAddLecture}>
          <Text style={styles.addButtonText}>+ Add Lecture</Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderFilterChip = (label: string, value: string) => {
    const isActive = statusFilter === value;
    return (
      <TouchableOpacity
        key={value}
        style={[styles.filterChip, isActive && styles.filterChipActive]}
        onPress={() => setStatusFilter(value)}
      >
        <Text style={[styles.filterChipText, isActive && styles.filterChipTextActive]}>
          {label}
        </Text>
      </TouchableOpacity>
    );
  };

  const renderHeader = () => (
    <TouchableOpacity style={styles.recordPrompt} onPress={handleAddLecture}>
      <View style={styles.recordPromptIcon}>
        <Text style={styles.recordPromptIconText}>🎙️</Text>
      </View>
      <View style={styles.recordPromptContent}>
        <Text style={styles.recordPromptTitle}>Record New Lecture</Text>
        <Text style={styles.recordPromptSubtitle}>
          Tap to start recording or upload audio →
        </Text>
      </View>
    </TouchableOpacity>
  );

  const styles = createStyles(theme);

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={styles.loadingText}>Loading lectures...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            placeholder="Search lectures..."
            placeholderTextColor="#8E8E93"
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
            autoCorrect={false}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Text style={styles.clearButton}>✕</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Filter Chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.filterContainer}
        contentContainerStyle={styles.filterContent}
      >
        {renderFilterChip('All', 'all')}
        {renderFilterChip('Ready', 'generated')}
        {renderFilterChip('Processing', 'processing')}
        {renderFilterChip('Uploaded', 'uploaded')}
        {renderFilterChip('Failed', 'failed')}
      </ScrollView>

      <FlatList
        data={filteredLectures}
        renderItem={renderLecture}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={lectures.length > 0 ? renderHeader : null}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.primary}
          />
        }
        ListEmptyComponent={renderEmpty}
      />

      {lectures.length > 0 && (
        <TouchableOpacity
          style={styles.floatingButton}
          onPress={handleAddLecture}
        >
          <Text style={styles.floatingButtonText}>+</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    searchContainer: {
      backgroundColor: theme.surface,
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    searchBar: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: theme.inputBackground,
      borderRadius: 10,
      paddingHorizontal: 12,
      height: 40,
    },
    searchIcon: {
      fontSize: 16,
      marginRight: 8,
    },
    searchInput: {
      flex: 1,
      fontSize: 16,
      color: theme.text,
    },
    clearButton: {
      fontSize: 18,
      color: theme.textTertiary,
      paddingHorizontal: 8,
    },
    filterContainer: {
      backgroundColor: theme.surface,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    filterContent: {
      paddingHorizontal: 16,
      paddingVertical: 12,
      gap: 8,
    },
    filterChip: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: theme.inputBackground,
      marginRight: 8,
    },
    filterChipActive: {
      backgroundColor: theme.primary,
    },
    filterChipText: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.textTertiary,
    },
    filterChipTextActive: {
      color: '#FFF',
    },
    listContent: {
      padding: 16,
      flexGrow: 1,
    },
    lectureCard: {
      backgroundColor: theme.surface,
      padding: 16,
      borderRadius: 12,
      marginBottom: 12,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    lectureHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: 8,
    },
    lectureTitle: {
      fontSize: 17,
      fontWeight: '600',
      color: theme.text,
      flex: 1,
      marginRight: 8,
    },
    statusBadge: {
      paddingHorizontal: 10,
      paddingVertical: 4,
      borderRadius: 12,
    },
    statusText: {
      fontSize: 12,
      fontWeight: '600',
    },
    lectureDate: {
      fontSize: 13,
      color: theme.textTertiary,
      marginBottom: 4,
    },
    lectureDuration: {
      fontSize: 13,
      color: theme.textTertiary,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.background,
    },
    loadingText: {
      marginTop: 12,
      fontSize: 16,
      color: theme.textTertiary,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      paddingHorizontal: 40,
      paddingTop: 60,
    },
    emptyIcon: {
      fontSize: 64,
      marginBottom: 16,
    },
    emptyTitle: {
      fontSize: 20,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 8,
    },
    emptyText: {
      fontSize: 15,
      color: theme.textTertiary,
      textAlign: 'center',
      lineHeight: 22,
      marginBottom: 24,
    },
    addButton: {
      backgroundColor: theme.primary,
      paddingHorizontal: 32,
      paddingVertical: 14,
      borderRadius: 24,
    },
    addButtonText: {
      color: '#FFF',
      fontSize: 16,
      fontWeight: '600',
    },
    floatingButton: {
      position: 'absolute',
      right: 20,
      bottom: 30,
      width: 64,
      height: 64,
      borderRadius: 32,
      backgroundColor: theme.primary,
      justifyContent: 'center',
      alignItems: 'center',
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.4,
      shadowRadius: 12,
      shadowOffset: { width: 0, height: 6 },
      elevation: 10,
      borderWidth: 3,
      borderColor: theme.background,
    },
    floatingButtonText: {
      color: '#FFF',
      fontSize: 36,
      fontWeight: '400',
      lineHeight: 36,
    },
    recordPrompt: {
      backgroundColor: theme.primary + '15',
      borderRadius: 16,
      padding: 20,
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 16,
      borderWidth: 2,
      borderColor: theme.primary + '30',
      borderStyle: 'dashed',
    },
    recordPromptIcon: {
      width: 56,
      height: 56,
      borderRadius: 28,
      backgroundColor: theme.primary,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 16,
    },
    recordPromptIconText: {
      fontSize: 28,
    },
    recordPromptContent: {
      flex: 1,
    },
    recordPromptTitle: {
      fontSize: 17,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 4,
    },
    recordPromptSubtitle: {
      fontSize: 14,
      color: theme.textSecondary,
    },
  });
