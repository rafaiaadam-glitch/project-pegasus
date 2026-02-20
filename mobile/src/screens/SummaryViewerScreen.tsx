import React from 'react';
import { ScrollView, View } from 'react-native';
import { Card, Text, Chip } from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  navigation: any;
  route: any;
}

export default function SummaryViewerScreen({ navigation, route }: Props) {
  const { theme } = useTheme();
  const { summary, lectureTitle } = route.params;

  React.useEffect(() => {
    if (lectureTitle) {
      navigation.setOptions({ title: lectureTitle });
    }
  }, [lectureTitle]);

  if (!summary) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          No summary data available
        </Text>
      </View>
    );
  }

  const sectionCount = summary.sections?.length || 0;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
    >
      {summary.overview && (
        <Card style={{ marginBottom: 16, backgroundColor: theme.colors.primaryContainer }} mode="elevated">
          <Card.Content>
            <Chip compact style={{ alignSelf: 'flex-start', marginBottom: 12 }}>OVERVIEW</Chip>
            <Text variant="bodyLarge" style={{ lineHeight: 24, color: theme.colors.onPrimaryContainer }}>
              {summary.overview}
            </Text>
          </Card.Content>
        </Card>
      )}

      {summary.sections?.map((section: any, index: number) => (
        <Card key={index} style={{ marginBottom: 12 }} mode="elevated">
          <Card.Content>
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
              <View
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 14,
                  backgroundColor: theme.colors.primary,
                  justifyContent: 'center',
                  alignItems: 'center',
                  marginRight: 10,
                }}
              >
                <Text variant="labelSmall" style={{ color: theme.colors.onPrimary, fontWeight: '700' }}>
                  {index + 1}
                </Text>
              </View>
              <Text variant="titleMedium" style={{ fontWeight: '600', flex: 1 }}>
                {section.title}
              </Text>
            </View>
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

      {sectionCount > 0 && (
        <Text
          variant="labelMedium"
          style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center', marginTop: 8 }}
        >
          {sectionCount} section{sectionCount !== 1 ? 's' : ''}
        </Text>
      )}
    </ScrollView>
  );
}
