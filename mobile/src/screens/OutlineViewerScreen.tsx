import React, { useState } from 'react';
import { ScrollView, View } from 'react-native';
import { List, Text } from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  route: any;
}

interface OutlineSection {
  title: string;
  level?: number;
  children?: OutlineSection[];
  content?: string;
}

function OutlineItem({ section }: { section: OutlineSection }) {
  const { theme } = useTheme();

  if (section.children && section.children.length > 0) {
    return (
      <List.Accordion
        title={section.title}
        titleStyle={{ fontWeight: '600' }}
        style={{ paddingLeft: ((section.level || 1) - 1) * 16 }}
      >
        {section.children.map((child, index) => (
          <OutlineItem key={index} section={child} />
        ))}
      </List.Accordion>
    );
  }

  return (
    <List.Item
      title={section.title}
      description={section.content}
      style={{ paddingLeft: ((section.level || 1) - 1) * 16 }}
      left={(props) => (
        <List.Icon
          {...props}
          icon="circle-small"
          color={theme.colors.primary}
        />
      )}
    />
  );
}

export default function OutlineViewerScreen({ route }: Props) {
  const { theme } = useTheme();
  const { outline } = route.params;

  if (!outline || !outline.sections || outline.sections.length === 0) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background }}>
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant }}>
          No outline data available
        </Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      contentContainerStyle={{ paddingBottom: 40 }}
    >
      <List.Section>
        {outline.sections.map((section: OutlineSection, index: number) => (
          <OutlineItem key={index} section={section} />
        ))}
      </List.Section>
    </ScrollView>
  );
}
