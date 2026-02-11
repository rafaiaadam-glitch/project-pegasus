import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from 'react-native';
import { Lecture } from '../types';
import api from '../services/api';

interface Props {
  navigation: any;
  route: any;
}

export default function LectureListScreen({ navigation, route }: Props) {
  const { courseId, courseTitle } = route.params;
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: courseTitle || 'Lectures' });
    loadLectures();
  }, [courseId]);

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

  const renderEmpty = () => (
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

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading lectures...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={lectures}
        renderItem={renderLecture}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor="#007AFF"
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

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
  },
  listContent: {
    padding: 16,
    flexGrow: 1,
  },
  lectureCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
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
    color: '#000',
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
    color: '#8E8E93',
    marginBottom: 4,
  },
  lectureDuration: {
    fontSize: 13,
    color: '#8E8E93',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F2F2F7',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#8E8E93',
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
    color: '#000',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 15,
    color: '#8E8E93',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  addButton: {
    backgroundColor: '#007AFF',
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
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  floatingButtonText: {
    color: '#FFF',
    fontSize: 32,
    fontWeight: '300',
    lineHeight: 32,
  },
});
