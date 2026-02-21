import React from 'react';
import { ScrollView, View } from 'react-native';
import { List, Text } from 'react-native-paper';
import { useTheme } from '../theme';

interface Props {
  route: any;
}

interface OutlineNode {
  title: string;
  points?: string[];
  children?: OutlineNode[];
}

function OutlineItem({ node, depth = 0 }: { node: OutlineNode; depth?: number }) {
  const { theme } = useTheme();
  const hasChildren = node.children && node.children.length > 0;
  const hasPoints = node.points && node.points.length > 0;

  if (hasChildren) {
    return (
      <List.Accordion
        title={node.title}
        titleStyle={{ fontWeight: '600' }}
        style={{ paddingLeft: depth * 16 }}
      >
        {hasPoints && node.points!.map((point, i) => (
          <List.Item
            key={`p-${i}`}
            title={point}
            titleNumberOfLines={5}
            style={{ paddingLeft: (depth + 1) * 16 }}
            left={(props) => (
              <List.Icon {...props} icon="circle-small" color={theme.colors.primary} />
            )}
          />
        ))}
        {node.children!.map((child, i) => (
          <OutlineItem key={`c-${i}`} node={child} depth={depth + 1} />
        ))}
      </List.Accordion>
    );
  }

  return (
    <View style={{ paddingLeft: depth * 16 }}>
      <List.Item
        title={node.title}
        titleStyle={{ fontWeight: depth === 0 ? '600' : 'normal' }}
        titleNumberOfLines={3}
        left={(props) => (
          <List.Icon
            {...props}
            icon={depth === 0 ? 'file-document-outline' : 'circle-small'}
            color={theme.colors.primary}
          />
        )}
      />
      {hasPoints && node.points!.map((point, i) => (
        <List.Item
          key={`p-${i}`}
          title={point}
          titleNumberOfLines={5}
          style={{ paddingLeft: (depth + 1) * 16 }}
          left={(props) => (
            <List.Icon {...props} icon="circle-small" color={theme.colors.onSurfaceVariant} />
          )}
        />
      ))}
    </View>
  );
}

export default function OutlineViewerScreen({ route }: Props) {
  const { theme } = useTheme();
  const { outline } = route.params;

  // Backend returns { outline: [...nodes] } — the array lives under the "outline" key
  const nodes: OutlineNode[] = outline?.outline || outline?.sections || [];

  if (nodes.length === 0) {
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
        {nodes.map((node: OutlineNode, index: number) => (
          <OutlineItem key={index} node={node} />
        ))}
      </List.Section>
    </ScrollView>
  );
}
