import React, { useState, useEffect } from 'react';
import { View, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import { Text, ActivityIndicator, Checkbox, Chip } from 'react-native-paper';
import { useTheme } from '../theme';
import api from '../services/api';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function ActionItemsView() {
  const { theme } = useTheme();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadItems();
  }, []);

  const loadItems = async () => {
    try {
      setLoading(true);
      const response = await api.getActionItems();
      setItems(response.actionItems);
    } catch (error) {
      console.error('Failed to load action items:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (index: number) => {
    // Local toggle only for MVP
    const newItems = [...items];
    newItems[index].completed = !newItems[index].completed;
    setItems(newItems);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return theme.colors.error;
      case 'medium': return theme.colors.warning;
      case 'low': return theme.colors.primary;
      default: return theme.colors.primary;
    }
  };

  const renderItem = ({ item, index }: { item: any, index: number }) => (
    <TouchableOpacity 
      style={[styles.itemContainer, { backgroundColor: theme.colors.surface }]}
      onPress={() => toggleItem(index)}
    >
      <View style={styles.checkContainer}>
        <Checkbox
          status={item.completed ? 'checked' : 'unchecked'}
          onPress={() => toggleItem(index)}
          color={theme.colors.primary}
        />
      </View>
      <View style={styles.contentContainer}>
        <Text 
          variant="titleMedium" 
          style={{ 
            color: item.completed ? theme.colors.onSurfaceVariant : theme.colors.onSurface,
            textDecorationLine: item.completed ? 'line-through' : 'none'
          }}
        >
          {item.task}
        </Text>
        {item.context && (
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
            {item.context}
          </Text>
        )}
        <View style={styles.metaRow}>
          <Text variant="labelSmall" style={{ color: theme.colors.primary, marginRight: 8 }}>
            {item.lectureTitle}
          </Text>
          {item.priority && (
            <Chip 
              textStyle={{ fontSize: 10, marginVertical: 0, marginHorizontal: 4 }} 
              style={{ backgroundColor: getPriorityColor(item.priority) + '20', height: 24 }}
            >
              {item.priority.toUpperCase()}
            </Chip>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return <ActivityIndicator style={{ marginTop: 20 }} />;
  }

  if (items.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <MaterialCommunityIcons name="checkbox-marked-circle-outline" size={48} color={theme.colors.surfaceVariant} />
        <Text variant="bodyLarge" style={{ color: theme.colors.onSurfaceVariant, marginTop: 16 }}>
          No action items found.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={items}
      renderItem={renderItem}
      keyExtractor={(item, index) => index.toString()}
      contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
    />
  );
}

const styles = StyleSheet.create({
  itemContainer: {
    flexDirection: 'row',
    padding: 12,
    marginBottom: 12,
    borderRadius: 12,
    elevation: 1,
  },
  checkContainer: {
    justifyContent: 'center',
    marginRight: 8,
  },
  contentContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  emptyContainer: {
    alignItems: 'center',
    marginTop: 60,
  },
});
