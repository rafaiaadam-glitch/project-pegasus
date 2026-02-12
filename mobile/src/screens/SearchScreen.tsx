import React, { useState, useEffect, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  ActivityIndicator,
} from 'react-native';
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
      // Search in lecture title
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

      // Search in summary if available
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
      <Text style={styles.resultText}>
        {parts.map((part, index) =>
          index % 2 === 1 ? (
            <Text key={index} style={styles.highlight}>
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
        return '🎙️';
      case 'summary':
        return '📝';
      case 'flashcard':
        return '🎴';
      default:
        return '📄';
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
    <TouchableOpacity
      style={styles.resultCard}
      onPress={() => handleResultPress(item)}
    >
      <View style={styles.resultIcon}>
        <Text style={styles.resultIconText}>{getResultIcon(item.type)}</Text>
      </View>
      <View style={styles.resultContent}>
        <View style={styles.resultHeader}>
          <Text style={styles.resultType}>{getResultTypeLabel(item.type)}</Text>
          <Text style={styles.resultLecture}>{item.lectureTitle}</Text>
        </View>
        {renderHighlightedText(item.highlightedText)}
      </View>
      <Text style={styles.chevron}>›</Text>
    </TouchableOpacity>
  );

  const renderEmpty = () => {
    if (loading) {
      return (
        <View style={styles.emptyContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      );
    }

    if (!searchQuery.trim()) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🔍</Text>
          <Text style={styles.emptyTitle}>Search Lectures</Text>
          <Text style={styles.emptyText}>
            Search across all your lectures, summaries, and study materials
          </Text>
        </View>
      );
    }

    if (results.length === 0) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🤷</Text>
          <Text style={styles.emptyTitle}>No Results Found</Text>
          <Text style={styles.emptyText}>
            Try adjusting your search query
          </Text>
        </View>
      );
    }

    return null;
  };

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            placeholder="Search lectures, summaries..."
            placeholderTextColor={theme.textTertiary}
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
            autoCorrect={false}
            autoFocus
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Text style={styles.clearButton}>✕</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Results */}
      {results.length > 0 && (
        <View style={styles.resultsHeader}>
          <Text style={styles.resultsCount}>
            {results.length} {results.length === 1 ? 'result' : 'results'}
          </Text>
        </View>
      )}

      <FlatList
        data={results}
        renderItem={renderResult}
        keyExtractor={(item, index) => `${item.lectureId}-${item.type}-${index}`}
        contentContainerStyle={styles.listContent}
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
    searchContainer: {
      backgroundColor: theme.surface,
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    searchBar: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: theme.inputBackground,
      borderRadius: 10,
      paddingHorizontal: 12,
      height: 40,
    },
    searchIcon: {
      fontSize: 16,
      marginRight: 8,
    },
    searchInput: {
      flex: 1,
      fontSize: 16,
      color: theme.text,
    },
    clearButton: {
      fontSize: 18,
      color: theme.textTertiary,
      paddingHorizontal: 8,
    },
    resultsHeader: {
      paddingHorizontal: 20,
      paddingVertical: 12,
      backgroundColor: theme.background,
    },
    resultsCount: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.textSecondary,
    },
    listContent: {
      paddingHorizontal: 16,
      paddingTop: 8,
      flexGrow: 1,
    },
    resultCard: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 12,
      marginBottom: 8,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    resultIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: theme.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
    },
    resultIconText: {
      fontSize: 20,
    },
    resultContent: {
      flex: 1,
    },
    resultHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 4,
    },
    resultType: {
      fontSize: 11,
      fontWeight: '600',
      color: theme.primary,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
      marginRight: 8,
    },
    resultLecture: {
      fontSize: 13,
      color: theme.textSecondary,
      flex: 1,
    },
    resultText: {
      fontSize: 14,
      color: theme.text,
      lineHeight: 20,
    },
    highlight: {
      fontWeight: '700',
      color: theme.primary,
      backgroundColor: theme.primary + '20',
      paddingHorizontal: 2,
    },
    chevron: {
      fontSize: 24,
      color: theme.textTertiary,
      fontWeight: '300',
      marginLeft: 8,
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
