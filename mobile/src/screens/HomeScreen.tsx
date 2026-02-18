import React, { useState, useEffect } from 'react';
import { View, FlatList, RefreshControl } from 'react-native';
import {
  Appbar,
  Button,
  Card,
  Text,
  ActivityIndicator,
  Chip,
  TouchableRipple,
} from 'react-native-paper';
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
    navigation.navigate('CourseList', { selectForRecording: true });
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
    <Card
      style={{ marginBottom: 12 }}
      onPress={() => handleLecturePress(item)}
      mode="elevated"
    >
      <Card.Title
        title={item.title}
        titleVariant="titleMedium"
        subtitle={formatDate(item.created_at)}
        right={(props) => (
          <Chip
            {...props}
            icon="check"
            selectedColor={getStatusColor(item.status)}
            style={{ marginRight: 16, backgroundColor: theme.colors.surfaceVariant, borderWidth: 0 }}
          >
            {getStatusText(item.status)}
          </Chip>
        )}
      />
    </Card>
  );

  const renderEmpty = () => (
    <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
      <Text variant="displayMedium" style={{ marginBottom: 16 }}>🎙️</Text>
      <Text variant="titleLarge" style={{ marginBottom: 8 }}>No lectures yet</Text>
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
        Tap the record button to start your first lecture
      </Text>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header elevated>
        <Appbar.Content title="Pegasus" subtitle="Lecture Copilot" />
        <Appbar.Action
          icon="folder-multiple-outline"
          onPress={() => navigation.navigate('CourseList')}
        />
        <Appbar.Action
          icon={isDark ? 'weather-sunny' : 'weather-night'}
          onPress={toggleTheme}
        />
      </Appbar.Header>

      <View style={{ padding: 16 }}>
        <Card mode="contained">
          <Card.Content style={{ alignItems: 'center', paddingVertical: 24 }}>
            <Text variant="titleMedium" style={{ marginBottom: 16 }}>Ready to start?</Text>
            <Button
              mode="contained"
              onPress={handleRecord}
              icon="record-circle-outline"
              contentStyle={{ paddingVertical: 8, flexDirection: 'row-reverse' }}
              labelStyle={{ fontSize: 18 }}
            >
              Record a New Lecture
            </Button>
          </Card.Content>
        </Card>
      </View>

      <View style={{ flex: 1, paddingHorizontal: 16 }}>
        <Text variant="titleLarge" style={{ marginBottom: 16, marginTop: 16 }}>
          Recent Lectures
        </Text>
        {loading ? (
          <ActivityIndicator style={{ flex: 1 }} />
        ) : (
          <FlatList
            data={recentLectures}
            renderItem={renderLecture}
            keyExtractor={(item) => item.id}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={handleRefresh}
                tintColor={theme.colors.primary}
              />
            }
            ListEmptyComponent={renderEmpty}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={{ flexGrow: 1 }}
          />
        )}
      </View>
    </View>
  );
}

