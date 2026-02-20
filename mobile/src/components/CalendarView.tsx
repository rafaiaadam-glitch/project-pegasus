import React, { useState, useEffect } from 'react';
import { View, SectionList, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Card, Chip } from 'react-native-paper';
import { useTheme } from '../theme';
import api from '../services/api';
import { Lecture } from '../types';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface Props {
  navigation: any;
}

interface Section {
  title: string;
  data: Lecture[];
}

export default function CalendarView({ navigation }: Props) {
  const { theme } = useTheme();
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLectures();
  }, []);

  const loadLectures = async () => {
    try {
      setLoading(true);
      const response = await api.getLectures(undefined, 100); // Fetch up to 100 recent lectures
      const lectures = response.lectures;

      // Group by date
      const grouped: Record<string, Lecture[]> = {};
      lectures.forEach(lecture => {
        const date = new Date(lecture.created_at).toLocaleDateString(undefined, {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });
        if (!grouped[date]) grouped[date] = [];
        grouped[date].push(lecture);
      });

      const sectionsArray = Object.keys(grouped).map(date => ({
        title: date,
        data: grouped[date]
      }));

      setSections(sectionsArray);
    } catch (error) {
      console.error('Failed to load lectures for calendar:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'generated': return theme.colors.primary;
      case 'processing': return theme.colors.tertiary;
      case 'failed': return theme.colors.error;
      default: return theme.colors.onSurfaceVariant;
    }
  };

  const renderItem = ({ item }: { item: Lecture }) => (
    <TouchableOpacity 
      style={[styles.itemContainer, { backgroundColor: theme.colors.surface }]}
      onPress={() => navigation.navigate('LectureDetail', { lectureId: item.id, lectureTitle: item.title })}
    >
      <View style={styles.timeContainer}>
        <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant }}>
          {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>
      <View style={[styles.cardContainer, { borderLeftColor: getStatusColor(item.status) }]}>
        <Text variant="titleMedium" numberOfLines={1} style={{ fontWeight: '600', color: theme.colors.onSurface }}>
          {item.title}
        </Text>
        <View style={styles.row}>
          <MaterialCommunityIcons name="clock-outline" size={14} color={theme.colors.onSurfaceVariant} />
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginLeft: 4 }}>
            {Math.floor((item.duration_sec || 0) / 60)} min
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderSectionHeader = ({ section: { title } }: { section: { title: string } }) => (
    <View style={[styles.sectionHeader, { backgroundColor: theme.colors.background }]}>
      <Text variant="titleSmall" style={{ color: theme.colors.primary, fontWeight: 'bold' }}>
        {title.toUpperCase()}
      </Text>
    </View>
  );

  if (loading) {
    return <ActivityIndicator style={{ marginTop: 20 }} />;
  }

  if (sections.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>No lectures found.</Text>
      </View>
    );
  }

  return (
    <SectionList
      sections={sections}
      keyExtractor={(item) => item.id}
      renderItem={renderItem}
      renderSectionHeader={renderSectionHeader}
      contentContainerStyle={{ paddingBottom: 100 }}
      stickySectionHeadersEnabled={false}
    />
  );
}

const styles = StyleSheet.create({
  sectionHeader: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginTop: 8,
  },
  itemContainer: {
    flexDirection: 'row',
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 12,
    elevation: 1,
  },
  timeContainer: {
    width: 60,
    justifyContent: 'center',
  },
  cardContainer: {
    flex: 1,
    paddingLeft: 12,
    borderLeftWidth: 4,
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  emptyContainer: {
    alignItems: 'center',
    marginTop: 40,
  },
});
