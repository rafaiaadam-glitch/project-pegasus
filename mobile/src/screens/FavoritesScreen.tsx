import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  RefreshControl,
} from 'react-native';
import { useTheme } from '../theme';
import api from '../services/api';
import { Lecture } from '../types';
import { getFavorites, toggleFavorite } from '../services/bookmarks';

interface Props {
  navigation: any;
}

export default function FavoritesScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [favoriteLectures, setFavoriteLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const unsubscribe = navigation.addListener('focus', () => {
      loadFavorites();
    });

    return unsubscribe;
  }, [navigation]);

  const loadFavorites = async () => {
    try {
      setLoading(true);
      const favoriteIds = await getFavorites();

      // Load lecture details for each favorite
      const allLectures = await api.getLectures(undefined, 100, 0);
      const favorites = allLectures.lectures.filter(lecture =>
        favoriteIds.includes(lecture.id)
      );

      setFavoriteLectures(favorites);
    } catch (error) {
      console.error('Error loading favorites:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadFavorites();
  };

  const handleUnfavorite = async (lectureId: string) => {
    await toggleFavorite(lectureId);
    setFavoriteLectures(favoriteLectures.filter(l => l.id !== lectureId));
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

  const renderLecture = ({ item }: { item: Lecture }) => (
    <View style={styles.lectureCard}>
      <TouchableOpacity
        style={styles.lectureContent}
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
          {new Date(item.created_at).toLocaleDateString()}
        </Text>

        {item.duration_sec && (
          <Text style={styles.lectureDuration}>
            {Math.floor(item.duration_sec / 60)}m {item.duration_sec % 60}s
          </Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.favoriteButton}
        onPress={() => handleUnfavorite(item.id)}
      >
        <Text style={styles.favoriteIcon}>⭐</Text>
      </TouchableOpacity>
    </View>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyIcon}>⭐</Text>
      <Text style={styles.emptyTitle}>No Favorites Yet</Text>
      <Text style={styles.emptyText}>
        Star lectures to save them here for quick access
      </Text>
    </View>
  );

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      <FlatList
        data={favoriteLectures}
        renderItem={renderLecture}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
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
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.background,
    },
    listContent: {
      padding: 16,
      flexGrow: 1,
    },
    lectureCard: {
      flexDirection: 'row',
      backgroundColor: theme.surface,
      borderRadius: 12,
      marginBottom: 12,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
      overflow: 'hidden',
    },
    lectureContent: {
      flex: 1,
      padding: 16,
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
    favoriteButton: {
      width: 56,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.primary + '10',
    },
    favoriteIcon: {
      fontSize: 24,
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
    },
  });
