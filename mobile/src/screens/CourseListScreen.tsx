import React, { useState, useEffect, useMemo } from 'react';
import { View, FlatList, RefreshControl, Alert } from 'react-native';
import {
  Appbar,
  Searchbar,
  Card,
  Text,
  ActivityIndicator,
  IconButton,
} from 'react-native-paper';
import { Course } from '../types';
import api from '../services/api';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

export default function CourseListScreen({ navigation, route }: Props) {
  const { theme, isDark, toggleTheme } = useTheme();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const canGoBack = navigation.canGoBack?.() ?? false;

  useEffect(() => {
    loadCourses();
  }, []);

  const filteredCourses = useMemo(() => {
    if (!searchQuery.trim()) {
      return courses;
    }

    const query = searchQuery.toLowerCase();
    return courses.filter(
      (course) =>
        course.title.toLowerCase().includes(query) ||
        course.description?.toLowerCase().includes(query)
    );
  }, [courses, searchQuery]);

  const loadCourses = async () => {
    try {
      setLoading(true);
      const response = await api.getCourses();
      setCourses(response.courses);
    } catch (error) {
      Alert.alert('Error', 'Unable to load courses. Please check your internet connection and try again.');
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadCourses();
  };

  const selectForRecording = route.params?.selectForRecording;

  const handleCoursePress = (course: Course) => {
    if (selectForRecording) {
      navigation.navigate('LectureMode', { courseId: course.id, courseTitle: course.title });
    } else {
      navigation.navigate('LectureList', { courseId: course.id, courseTitle: course.title });
    }
  };

  const handleBackPress = () => {
    const parentNavigation = navigation.getParent?.();

    if (navigation.canGoBack?.()) {
      navigation.goBack();
      return;
    }

    if (parentNavigation?.canGoBack?.()) {
      parentNavigation.goBack();
      return;
    }

    if (parentNavigation?.navigate) {
      parentNavigation.navigate('Home');
      return;
    }

    if (navigation.navigate) {
      navigation.navigate('Home');
      return;
    }

    navigation.reset?.({
      index: 0,
      routes: [{ name: 'Home' }],
    });
    navigation.getParent?.()?.goBack?.();
    navigation.navigate('Home');
  };

  const renderCourse = ({ item }: { item: Course }) => (
    <Card
      style={{ marginBottom: 12 }}
      onPress={() => handleCoursePress(item)}
      mode="elevated"
    >
      <Card.Title
        title={item.title}
        titleVariant="titleMedium"
        subtitle={item.description || undefined}
        subtitleNumberOfLines={2}
        right={(props) => (
          <IconButton {...props} icon="chevron-right" />
        )}
      />
      <Card.Content style={{ paddingTop: 0 }}>
        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
          Created {new Date(item.created_at).toLocaleDateString()}
        </Text>
      </Card.Content>
    </Card>
  );

  const renderEmpty = () => {
    if (searchQuery.trim()) {
      return (
        <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
          <Text variant="displayMedium" style={{ marginBottom: 16 }}>🔍</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Results Found</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            No courses match "{searchQuery}"
          </Text>
        </View>
      );
    }

    return (
      <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
        <Text variant="displayMedium" style={{ marginBottom: 16 }}>📚</Text>
        <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Courses Yet</Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
          Courses will appear here once you start using PLC.
        </Text>
        <Text variant="labelMedium" style={{ color: theme.colors.primary, textAlign: 'center', marginTop: 16 }}>
          Tap + to create your first course
        </Text>
      </View>
    );
  };

  if (loading && !refreshing) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator size="large" />
        <Text variant="bodyLarge" style={{ marginTop: 12, color: theme.colors.onSurfaceVariant }}>
          Loading courses...
        </Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header elevated>
        {canGoBack && <Appbar.BackAction onPress={handleBackPress} />}
        <Appbar.Content title="Courses" subtitle="Pegasus Lecture Copilot" />
        <Appbar.Action
          icon={isDark ? 'weather-sunny' : 'weather-night'}
          onPress={toggleTheme}
        />
      </Appbar.Header>

      <Searchbar
        placeholder="Search courses..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        style={{ marginHorizontal: 16, marginVertical: 12 }}
      />

      <FlatList
        data={filteredCourses}
        renderItem={renderCourse}
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
      />
    </View>
  );
}
