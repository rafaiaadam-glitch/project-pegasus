import React from 'react';
import { ScrollView, View } from 'react-native';
import { Card, Text, Chip } from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  route: any;
}

export default function SummaryViewerScreen({ route }: Props) {
  const { theme } = useTheme();
  const { summary } = route.params;

  if (!summary) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          No summary data available
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
    >
      {summary.overview && (
        <Card style={{ marginBottom: 16 }} mode="elevated">
          <Card.Content>
            <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 12 }}>OVERVIEW</Chip>
            <Text variant="bodyLarge" style={{ lineHeight: 24, color: theme.colors.onSurface }}>
              {summary.overview}
            </Text>
          </Card.Content>
        </Card>
      )}

      {summary.sections?.map((section: any, index: number) => (
        <Card key={index} style={{ marginBottom: 12 }} mode="elevated">
          <Card.Content>
            <Text variant="titleMedium" style={{ marginBottom: 8, fontWeight: '600' }}>
              {section.title}
            </Text>
            {section.bullets?.map((bullet: string, bIndex: number) => (
              <View key={bIndex} style={{ flexDirection: 'row', marginBottom: 6, paddingRight: 8 }}>
                <Text style={{ color: theme.colors.primary, marginRight: 8, fontSize: 16 }}>
                  {'\u2022'}
                </Text>
                <Text variant="bodyMedium" style={{ flex: 1, lineHeight: 22, color: theme.colors.onSurface }}>
                  {bullet}
                </Text>
              </View>
            ))}
            {section.content && !section.bullets && (
              <Text variant="bodyMedium" style={{ lineHeight: 22, color: theme.colors.onSurface }}>
                {section.content}
              </Text>
            )}
          </Card.Content>
        </Card>
      ))}
    </ScrollView>
  );
}
