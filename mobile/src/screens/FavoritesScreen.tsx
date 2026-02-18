import React, { useState, useEffect } from 'react';
import { View, FlatList, RefreshControl } from 'react-native';
import {
  Card,
  Text,
  Chip,
  IconButton,
} from 'react-native-paper';
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
        return theme.colors.primary;
      case 'processing':
        return theme.colors.tertiary;
      case 'failed':
        return theme.colors.error;
      default:
        return theme.colors.onSurfaceVariant;
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
    <Card
      style={{ marginBottom: 12 }}
      onPress={() => handleLecturePress(item)}
      mode="elevated"
    >
      <Card.Title
        title={item.title}
        titleVariant="titleMedium"
        subtitle={`${new Date(item.created_at).toLocaleDateString()}${
          item.duration_sec ? ` • ${Math.floor(item.duration_sec / 60)}m ${item.duration_sec % 60}s` : ''
        }`}
        right={(props) => (
          <IconButton
            {...props}
            icon="star"
            iconColor={theme.colors.primary}
            onPress={() => handleUnfavorite(item.id)}
          />
        )}
      />
      <Card.Content style={{ paddingTop: 0 }}>
        <Chip
          compact
          selectedColor={getStatusColor(item.status)}
          style={{ alignSelf: 'flex-start', backgroundColor: theme.colors.surfaceVariant, borderWidth: 0 }}
        >
          {getStatusText(item.status)}
        </Chip>
      </Card.Content>
    </Card>
  );

  const renderEmpty = () => (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40, paddingTop: 60 }}>
      <Text style={{ fontSize: 64, marginBottom: 16 }}>⭐</Text>
      <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Favorites Yet</Text>
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
        Star lectures to save them here for quick access
      </Text>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <FlatList
        data={favoriteLectures}
        renderItem={renderLecture}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16, flexGrow: 1 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.primary}
          />
        }
        ListEmptyComponent={renderEmpty}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
