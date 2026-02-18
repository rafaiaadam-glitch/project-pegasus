import React, { useState, useEffect, useMemo } from 'react';
import { View, FlatList } from 'react-native';
import {
  Searchbar,
  List,
  Text,
  ActivityIndicator,
  Chip,
} from 'react-native-paper';
import { useTheme } from '../theme';
import api from '../services/api';
import { Lecture } from '../types';

interface SearchResult {
  type: 'lecture' | 'flashcard' | 'summary';
  lectureId: string;
  lectureTitle: string;
  courseId: string;
  matchText: string;
  highlightedText: string;
}

interface Props {
  navigation: any;
}

export default function SearchScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [allLectures, setAllLectures] = useState<Lecture[]>([]);

  useEffect(() => {
    loadAllLectures();
  }, []);

  const loadAllLectures = async () => {
    try {
      const response = await api.getLectures(undefined, 100, 0);
      setAllLectures(response.lectures);
    } catch (error) {
      console.error('Error loading lectures:', error);
    }
  };

  const performSearch = useMemo(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      return [];
    }

    const query = searchQuery.toLowerCase();
    const searchResults: SearchResult[] = [];

    allLectures.forEach((lecture) => {
      if (lecture.title.toLowerCase().includes(query)) {
        searchResults.push({
          type: 'lecture',
          lectureId: lecture.id,
          lectureTitle: lecture.title,
          courseId: lecture.course_id,
          matchText: lecture.title,
          highlightedText: highlightText(lecture.title, query),
        });
      }

      if (lecture.summary && lecture.summary.toLowerCase().includes(query)) {
        const excerpt = getExcerpt(lecture.summary, query);
        searchResults.push({
          type: 'summary',
          lectureId: lecture.id,
          lectureTitle: lecture.title,
          courseId: lecture.course_id,
          matchText: excerpt,
          highlightedText: highlightText(excerpt, query),
        });
      }
    });

    return searchResults;
  }, [searchQuery, allLectures]);

  useEffect(() => {
    const results = performSearch;
    setResults(results);
  }, [performSearch]);

  const highlightText = (text: string, query: string): string => {
    const index = text.toLowerCase().indexOf(query.toLowerCase());
    if (index === -1) return text;

    return (
      text.substring(0, index) +
      '**' +
      text.substring(index, index + query.length) +
      '**' +
      text.substring(index + query.length)
    );
  };

  const getExcerpt = (text: string, query: string, contextLength: number = 100): string => {
    const index = text.toLowerCase().indexOf(query.toLowerCase());
    if (index === -1) return text.substring(0, contextLength) + '...';

    const start = Math.max(0, index - contextLength / 2);
    const end = Math.min(text.length, index + query.length + contextLength / 2);

    let excerpt = text.substring(start, end);
    if (start > 0) excerpt = '...' + excerpt;
    if (end < text.length) excerpt = excerpt + '...';

    return excerpt;
  };

  const handleResultPress = (result: SearchResult) => {
    navigation.navigate('LectureDetail', {
      lectureId: result.lectureId,
      lectureTitle: result.lectureTitle,
      courseId: result.courseId,
    });
  };

  const renderHighlightedText = (text: string) => {
    const parts = text.split('**');
    return (
      <Text variant="bodyMedium">
        {parts.map((part, index) =>
          index % 2 === 1 ? (
            <Text
              key={index}
              style={{ fontWeight: '700', color: theme.colors.primary, backgroundColor: theme.colors.primaryContainer }}
            >
              {part}
            </Text>
          ) : (
            <Text key={index}>{part}</Text>
          )
        )}
      </Text>
    );
  };

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'lecture':
        return 'microphone';
      case 'summary':
        return 'text-box-outline';
      case 'flashcard':
        return 'cards-outline';
      default:
        return 'file-document-outline';
    }
  };

  const getResultTypeLabel = (type: string) => {
    switch (type) {
      case 'lecture':
        return 'Lecture';
      case 'summary':
        return 'Summary';
      case 'flashcard':
        return 'Flashcard';
      default:
        return 'Result';
    }
  };

  const renderResult = ({ item }: { item: SearchResult }) => (
    <List.Item
      title={item.lectureTitle}
      description={() => (
        <View style={{ marginTop: 4 }}>
          <Chip compact textStyle={{ fontSize: 10 }} style={{ alignSelf: 'flex-start', marginBottom: 4 }}>
            {getResultTypeLabel(item.type)}
          </Chip>
          {renderHighlightedText(item.highlightedText)}
        </View>
      )}
      left={(props) => <List.Icon {...props} icon={getResultIcon(item.type)} />}
      onPress={() => handleResultPress(item)}
      style={{ backgroundColor: theme.colors.surface, borderRadius: 12, marginBottom: 8 }}
    />
  );

  const renderEmpty = () => {
    if (loading) {
      return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 60 }}>
          <ActivityIndicator size="large" />
        </View>
      );
    }

    if (!searchQuery.trim()) {
      return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40, paddingTop: 60 }}>
          <Text style={{ fontSize: 64, marginBottom: 16 }}>🔍</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>Search Lectures</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            Search across all your lectures, summaries, and study materials
          </Text>
        </View>
      );
    }

    if (results.length === 0) {
      return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40, paddingTop: 60 }}>
          <Text style={{ fontSize: 64, marginBottom: 16 }}>🤷</Text>
          <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Results Found</Text>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
            Try adjusting your search query
          </Text>
        </View>
      );
    }

    return null;
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Searchbar
        placeholder="Search lectures, summaries..."
        onChangeText={setSearchQuery}
        value={searchQuery}
        autoFocus
        style={{ marginHorizontal: 16, marginVertical: 12 }}
      />

      {results.length > 0 && (
        <View style={{ paddingHorizontal: 20, paddingBottom: 8 }}>
          <Text variant="labelLarge" style={{ color: theme.colors.onSurfaceVariant }}>
            {results.length} {results.length === 1 ? 'result' : 'results'}
          </Text>
        </View>
      )}

      <FlatList
        data={results}
        renderItem={renderResult}
        keyExtractor={(item, index) => `${item.lectureId}-${item.type}-${index}`}
        contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 8, flexGrow: 1 }}
        ListEmptyComponent={renderEmpty}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
