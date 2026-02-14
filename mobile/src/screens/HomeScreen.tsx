import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  RefreshControl,
  Platform,
} from 'react-native';
import { Lecture } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
}

export default function HomeScreen({ navigation }: Props) {
  const { theme, isDark, toggleTheme } = useTheme();
  const [recentLectures, setRecentLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadRecentLectures();
  }, []);

  const loadRecentLectures = async () => {
    try {
      setLoading(true);
      // Get all lectures from all courses
      const response = await api.getLectures(undefined, 10, 0);
      setRecentLectures(response.lectures);
    } catch (error) {
      console.error('Error loading recent lectures:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadRecentLectures();
  };

  const handleRecord = () => {
    const params = { courseId: 'course-bio-101' };

    if (navigation?.navigate) {
      navigation.navigate('LectureMode', params);
      return;
    }

    // Defensive fallback for unexpected navigator wiring.
    navigation?.push?.('LectureMode', params);
  };

  const handleLecturePress = (lecture: Lecture) => {
    navigation.navigate('LectureDetail', {
      lectureId: lecture.id,
      lectureTitle: lecture.title,
      courseId: lecture.course_id,
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'generated':
        return theme.success;
      case 'processing':
        return theme.warning;
      case 'failed':
        return theme.error;
      default:
        return theme.textTertiary;
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
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
      <Text style={styles.lectureDate}>{formatDate(item.created_at)}</Text>
      {item.duration_sec && (
        <Text style={styles.lectureDuration}>
          {Math.floor(item.duration_sec / 60)}m {item.duration_sec % 60}s
        </Text>
      )}
    </TouchableOpacity>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyIcon}>🎙️</Text>
      <Text style={styles.emptyTitle}>No lectures yet</Text>
      <Text style={styles.emptyText}>
        Tap the record button to start your first lecture
      </Text>
    </View>
  );

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Pegasus</Text>
          <Text style={styles.headerSubtitle}>Lecture Copilot</Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={styles.iconButton}
            onPress={() => navigation.navigate('CourseList')}
          >
            <Text style={styles.iconButtonText}>📚</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconButton} onPress={toggleTheme}>
            <Text style={styles.iconButtonText}>{isDark ? '☀️' : '🌙'}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Main Record Button */}
      <View style={styles.recordSection}>
        <TouchableOpacity
          style={styles.recordButton}
          onPress={handleRecord}
          accessibilityRole="button"
          accessibilityLabel="Tap to record"
          testID="home-record-button"
          activeOpacity={0.85}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <View style={styles.recordButtonInner}>
            <View style={styles.recordButtonDot} />
          </View>
        </TouchableOpacity>
        <Text style={styles.recordButtonLabel}>Tap to record</Text>
        <TouchableOpacity
          style={styles.recordCtaButton}
          onPress={handleRecord}
          accessibilityRole="button"
          accessibilityLabel="Select lecture type"
          testID="home-record-cta"
          activeOpacity={0.85}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.recordCtaText}>Select Lecture Type</Text>
        </TouchableOpacity>
      </View>

      {/* Recent Lectures */}
      <View style={styles.lecturesSection}>
        <Text style={styles.sectionTitle}>Recent Lectures</Text>
        <FlatList
          data={recentLectures}
          renderItem={renderLecture}
          keyExtractor={(item) => item.id}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={theme.primary}
            />
          }
          ListEmptyComponent={renderEmpty}
          showsVerticalScrollIndicator={false}
        />
      </View>
    </View>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingTop: Platform.OS === 'ios' ? 60 : 20,
      paddingBottom: 20,
      backgroundColor: theme.background,
    },
    headerTitle: {
      fontSize: 32,
      fontWeight: '700',
      color: theme.text,
    },
    headerSubtitle: {
      fontSize: 14,
      color: theme.textTertiary,
      marginTop: 2,
    },
    headerActions: {
      flexDirection: 'row',
      gap: 12,
    },
    iconButton: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: theme.surface,
      justifyContent: 'center',
      alignItems: 'center',
    },
    iconButtonText: {
      fontSize: 20,
    },
    recordSection: {
      alignItems: 'center',
      paddingVertical: 40,
    },
    recordButton: {
      width: 120,
      height: 120,
      borderRadius: 60,
      backgroundColor: theme.surface,
      justifyContent: 'center',
      alignItems: 'center',
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.2,
      shadowRadius: 20,
      shadowOffset: { width: 0, height: 10 },
      elevation: 10,
    },
    recordButtonInner: {
      width: 100,
      height: 100,
      borderRadius: 50,
      backgroundColor: '#FF3B30',
      justifyContent: 'center',
      alignItems: 'center',
    },
    recordButtonDot: {
      width: 30,
      height: 30,
      borderRadius: 15,
      backgroundColor: '#FFF',
    },
    recordButtonLabel: {
      marginTop: 16,
      fontSize: 16,
      fontWeight: '600',
      color: theme.textSecondary,
    },
    recordCtaButton: {
      marginTop: 12,
      backgroundColor: theme.surface,
      borderWidth: 1,
      borderColor: theme.border,
      borderRadius: 12,
      paddingHorizontal: 14,
      paddingVertical: 10,
    },
    recordCtaText: {
      color: theme.text,
      fontSize: 14,
      fontWeight: '600',
    },
    lecturesSection: {
      flex: 1,
      paddingHorizontal: 20,
    },
    sectionTitle: {
      fontSize: 20,
      fontWeight: '700',
      color: theme.text,
      marginBottom: 16,
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
      fontSize: 16,
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
      fontSize: 11,
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
    emptyContainer: {
      alignItems: 'center',
      paddingVertical: 60,
    },
    emptyIcon: {
      fontSize: 64,
      marginBottom: 16,
    },
    emptyTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 8,
    },
    emptyText: {
      fontSize: 14,
      color: theme.textTertiary,
      textAlign: 'center',
      lineHeight: 20,
    },
  });
