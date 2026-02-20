import React, { useState, useMemo } from 'react';
import { View, FlatList } from 'react-native';
import { TextInput, Card, Text } from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  route: any;
}

interface KeyTerm {
  term: string;
  definition: string;
}

export default function KeyTermsViewerScreen({ route }: Props) {
  const { theme } = useTheme();
  const { keyTerms } = route.params;
  const [searchQuery, setSearchQuery] = useState('');

  const terms: KeyTerm[] = keyTerms?.terms || [];

  const filteredTerms = useMemo(() => {
    if (!searchQuery.trim()) return terms;
    const query = searchQuery.toLowerCase();
    return terms.filter(
      (t) =>
        t.term.toLowerCase().includes(query) ||
        t.definition.toLowerCase().includes(query)
    );
  }, [terms, searchQuery]);

  if (terms.length === 0) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          No key terms available
        </Text>
      </View>
    );
  }

  const renderTerm = ({ item }: { item: KeyTerm }) => (
    <Card style={{ marginBottom: 12, marginHorizontal: 16 }} mode="elevated">
      <Card.Content>
        <Text variant="titleMedium" style={{ fontWeight: '700', marginBottom: 6, color: theme.colors.primary }}>
          {item.term}
        </Text>
        <Text variant="bodyMedium" style={{ lineHeight: 22, color: theme.colors.onSurface }}>
          {item.definition}
        </Text>
      </Card.Content>
    </Card>
  );

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <TextInput
        mode="outlined"
        placeholder="Search terms..."
        value={searchQuery}
        onChangeText={setSearchQuery}
        left={<TextInput.Icon icon="magnify" />}
        style={{ marginHorizontal: 16, marginVertical: 12 }}
      />
      <FlatList
        data={filteredTerms}
        renderItem={renderTerm}
        keyExtractor={(item, index) => `${item.term}-${index}`}
        contentContainerStyle={{ paddingBottom: 40 }}
        ListEmptyComponent={
          <View style={{ alignItems: 'center', paddingVertical: 40 }}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              No terms match your search
            </Text>
          </View>
        }
      />
    </View>
  );
}
