import React, { useState, useEffect, useMemo } from 'react';
import { View, FlatList, RefreshControl, ScrollView, Alert } from 'react-native';
import {
  Searchbar,
  Card,
  Text,
  Chip,
  FAB,
  ActivityIndicator,
} from 'react-native-paper';
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

  const filteredLectures = useMemo(() => {
    let filtered = lectures;

    if (statusFilter !== 'all') {
      filtered = filtered.filter((lecture) => lecture.status === statusFilter);
    }

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
      courseTitle,
    });
  };

  const handleAddLecture = () => {
    navigation.navigate('RecordLecture', { courseId });
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
        subtitle={`${new Date(item.created_at).toLocaleDateString()} • ${new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
        right={(props) => (
          <Chip
            {...props}
            selectedColor={getStatusColor(item.status)}
            style={{ marginRight: 16, backgroundColor: theme.colors.surfaceVariant, borderWidth: 0 }}
          >
            {getStatusText(item.status)}
          </Chip>
        )}
      />
      {item.duration_sec ? (
        <Card.Content style={{ paddingTop: 0 }}>
          <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
            Duration: {Math.floor(item.duration_sec / 60)}m {item.duration_sec % 60}s
          </Text>
        </Card.Content>
      ) : null}
    </Card>
  );

  const renderEmpty = () => {
    if (searchQuery.trim() || statusFilter !== 'all') {
      return (
        <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
          <Text variant="displayMedium" style={{ marginBottom: 16 }}>🔍</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Results Found</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            Try adjusting your search or filters
          </Text>
        </View>
      );
    }

    return (
      <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
        <Text variant="displayMedium" style={{ marginBottom: 16 }}>🎤</Text>
        <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Lectures Yet</Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginBottom: 24 }}>
          Start by recording or uploading your first lecture
        </Text>
      </View>
    );
  };

  const renderHeader = () => (
    <View>
      <Card
        style={{ marginBottom: 16 }}
        onPress={handleAddLecture}
        mode="outlined"
      >
        <Card.Title
          title="Record New Lecture"
          subtitle="Tap to start recording or upload audio"
          left={(props) => (
            <View
              {...props}
              style={{
                width: 48,
                height: 48,
                borderRadius: 24,
                backgroundColor: theme.colors.primary,
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Text style={{ fontSize: 24 }}>🎙️</Text>
            </View>
          )}
        />
      </Card>

      <Card
        style={{ marginBottom: 16 }}
        onPress={() => navigation.navigate('Threads', { courseId, courseTitle })}
        mode="elevated"
      >
        <Card.Title
          title="Conceptual Threads"
          subtitle="View concept map across lectures"
          left={(props) => (
            <View
              {...props}
              style={{
                width: 48,
                height: 48,
                borderRadius: 24,
                backgroundColor: theme.colors.primaryContainer,
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <Text style={{ fontSize: 24 }}>&#x1F9F5;</Text>
            </View>
          )}
        />
      </Card>
    </View>
  );

  const filterChips = [
    { label: 'All', value: 'all' },
    { label: 'Ready', value: 'generated' },
    { label: 'Processing', value: 'processing' },
    { label: 'Uploaded', value: 'uploaded' },
    { label: 'Failed', value: 'failed' },
  ];

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator size="large" />
        <Text variant="bodyLarge" style={{ marginTop: 12, color: theme.colors.onSurfaceVariant }}>
          Loading lectures...
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Searchbar
        placeholder="Search lectures..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={{ marginHorizontal: 16, marginTop: 12 }}
      />

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0 }}
        contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 12, gap: 8 }}
      >
        {filterChips.map((chip) => (
          <Chip
            key={chip.value}
            selected={statusFilter === chip.value}
            onPress={() => setStatusFilter(chip.value)}
            showSelectedOverlay
            style={{ marginRight: 4 }}
          >
            {chip.label}
          </Chip>
        ))}
      </ScrollView>

      <FlatList
        data={filteredLectures}
        renderItem={renderLecture}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16, flexGrow: 1 }}
        ListHeaderComponent={lectures.length > 0 ? renderHeader : null}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.primary}
          />
        }
        ListEmptyComponent={renderEmpty}
      />

      {lectures.length > 0 && (
        <FAB
          icon="plus"
          onPress={handleAddLecture}
          style={{ position: 'absolute', right: 16, bottom: 16 }}
        />
      )}
    </View>
  );
}
