import React, { useState, useEffect, useMemo } from 'react';
import { View, FlatList, RefreshControl, Alert } from 'react-native';
import {
  Appbar,
  Searchbar,
  Card,
  Text,
  ActivityIndicator,
  IconButton,
  FAB,
  Dialog,
  Portal,
  TextInput,
  Button,
} from 'react-native-paper';
import { Swipeable } from 'react-native-gesture-handler';
import { TouchableOpacity, Animated } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
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
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const canGoBack = navigation.canGoBack?.() ?? false;

  const selectForRecording = route.params?.selectForRecording;

  useEffect(() => {
    loadCourses();
  }, []);

  const filteredCourses = useMemo(() => {
    if (!searchQuery.trim()) return courses;
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
      Alert.alert('Error', 'Unable to load courses.');
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

  const handleCreateCourse = async () => {
    const title = newTitle.trim();
    if (!title) return;

    try {
      setCreating(true);
      const course = await api.createCourse({
        title,
        description: newDescription.trim() || undefined,
      });
      setCourses((prev) => [course, ...prev]);
      setShowCreateDialog(false);
      setNewTitle('');
      setNewDescription('');

      // If in recording flow, go straight to recording with new course
      if (selectForRecording) {
        navigation.navigate('LectureMode', { courseId: course.id, courseTitle: course.title });
      }
    } catch (error) {
      Alert.alert('Error', 'Could not create course.');
      console.error(error);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteCourse = (course: Course) => {
    Alert.alert(
      'Delete Course',
      `Delete "${course.title}" and all its lectures? This cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteCourse(course.id);
              setCourses((prev) => prev.filter((c) => c.id !== course.id));
            } catch (err) {
              Alert.alert('Error', 'Failed to delete course.');
              console.error(err);
            }
          },
        },
      ]
    );
  };

  const handleCoursePress = (course: Course) => {
    if (selectForRecording) {
      navigation.navigate('LectureMode', { courseId: course.id, courseTitle: course.title });
    } else {
      navigation.navigate('LectureList', { courseId: course.id, courseTitle: course.title });
    }
  };

  const handleBackPress = () => {
    if (navigation.canGoBack?.()) {
      navigation.goBack();
    } else {
      navigation.navigate('Home');
    }
  };

  const renderRightActions = (item: Course) => (
    _progress: Animated.AnimatedInterpolation<number>,
    _dragX: Animated.AnimatedInterpolation<number>,
  ) => (
    <TouchableOpacity
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        width: 80,
        backgroundColor: theme.colors.error,
        borderRadius: 12,
        marginBottom: 12,
        marginLeft: 8,
      }}
      onPress={() => handleDeleteCourse(item)}
    >
      <MaterialCommunityIcons name="delete-outline" size={24} color="#fff" />
      <Text style={{ color: '#fff', fontSize: 12, marginTop: 4 }}>Delete</Text>
    </TouchableOpacity>
  );

  const renderCourse = ({ item }: { item: Course }) => (
    <Swipeable renderRightActions={renderRightActions(item)} overshootRight={false}>
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
    </Swipeable>
  );

  const renderEmpty = () => {
    if (searchQuery.trim()) {
      return (
        <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
          <Text variant="displayMedium" style={{ marginBottom: 16 }}>🔍</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Results</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            No courses match "{searchQuery}"
          </Text>
        </View>
      );
    }

    return (
      <View style={{ alignItems: 'center', paddingVertical: 60, flex: 1, justifyContent: 'center' }}>
        <MaterialCommunityIcons name="folder-plus-outline" size={64} color={theme.colors.primary} style={{ marginBottom: 16 }} />
        <Text variant="titleLarge" style={{ marginBottom: 8, color: theme.colors.onSurface }}>No Courses Yet</Text>
        <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', paddingHorizontal: 32 }}>
          Create a course to start recording and generating study materials.
        </Text>
        <Button
          mode="contained"
          onPress={() => setShowCreateDialog(true)}
          style={{ marginTop: 20 }}
          icon="plus"
        >
          Create Course
        </Button>
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
        <Appbar.Content
          title={selectForRecording ? 'Select Course' : 'Courses'}
          subtitle={selectForRecording ? 'Choose a course to record into' : undefined}
        />
        <Appbar.Action icon="plus" onPress={() => setShowCreateDialog(true)} />
      </Appbar.Header>

      {courses.length > 3 && (
        <Searchbar
          placeholder="Search courses..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          style={{ marginHorizontal: 16, marginVertical: 12 }}
        />
      )}

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

      {courses.length > 0 && (
        <FAB
          icon="plus"
          label="New Course"
          onPress={() => setShowCreateDialog(true)}
          style={{
            position: 'absolute',
            right: 16,
            bottom: 16,
            backgroundColor: theme.colors.primary,
          }}
          color={theme.colors.onPrimary}
        />
      )}

      {/* Create Course Dialog */}
      <Portal>
        <Dialog visible={showCreateDialog} onDismiss={() => !creating && setShowCreateDialog(false)}>
          <Dialog.Title>New Course</Dialog.Title>
          <Dialog.Content>
            <TextInput
              label="Course Name"
              value={newTitle}
              onChangeText={setNewTitle}
              mode="outlined"
              autoFocus
              style={{ marginBottom: 12 }}
              placeholder="e.g. Data Structures, Biology 101"
            />
            <TextInput
              label="Description (optional)"
              value={newDescription}
              onChangeText={setNewDescription}
              mode="outlined"
              multiline
              numberOfLines={2}
              placeholder="Brief description of the course"
            />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowCreateDialog(false)} disabled={creating}>Cancel</Button>
            <Button
              onPress={handleCreateCourse}
              loading={creating}
              disabled={creating || !newTitle.trim()}
              mode="contained"
            >
              Create
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
}
