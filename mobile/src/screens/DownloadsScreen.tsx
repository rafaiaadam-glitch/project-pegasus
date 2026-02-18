import React, { useState, useEffect } from 'react';
import { View, FlatList, Alert, RefreshControl } from 'react-native';
import {
  Card,
  Text,
  Button,
  List,
  IconButton,
  ProgressBar,
} from 'react-native-paper';
import { useTheme } from '../theme';
import {
  getDownloadedLectures,
  deleteDownloadedLecture,
  getOfflineStorageSize,
  formatBytes,
  clearAllOfflineData,
  DownloadedLecture,
} from '../services/offlineManager';

interface Props {
  navigation: any;
}

export default function DownloadsScreen({ navigation }: Props) {
  const { theme } = useTheme();
  const [downloads, setDownloads] = useState<DownloadedLecture[]>([]);
  const [storageSize, setStorageSize] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDownloads();
  }, []);

  const loadDownloads = async () => {
    try {
      setLoading(true);
      const [downloadedLectures, totalSize] = await Promise.all([
        getDownloadedLectures(),
        getOfflineStorageSize(),
      ]);

      setDownloads(downloadedLectures);
      setStorageSize(totalSize);
    } catch (error) {
      console.error('Error loading downloads:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDownloads();
  };

  const handleDelete = (lectureId: string, title: string) => {
    Alert.alert(
      'Delete Download',
      `Remove "${title}" from offline storage?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteDownloadedLecture(lectureId);
              await loadDownloads();
            } catch (error) {
              Alert.alert('Error', 'Failed to delete download');
            }
          },
        },
      ]
    );
  };

  const handleClearAll = () => {
    Alert.alert(
      'Clear All Downloads',
      'This will remove all offline lectures. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            try {
              await clearAllOfflineData();
              await loadDownloads();
              Alert.alert('Success', 'All offline data cleared');
            } catch (error) {
              Alert.alert('Error', 'Failed to clear offline data');
            }
          },
        },
      ]
    );
  };

  const handleLecturePress = (download: DownloadedLecture) => {
    navigation.navigate('LectureDetail', {
      lectureId: download.lectureId,
      lectureTitle: download.lectureData.title,
      courseId: download.lectureData.course_id,
      offline: true,
    });
  };

  const renderDownload = ({ item }: { item: DownloadedLecture }) => (
    <List.Item
      title={item.lectureData.title}
      description={`${formatBytes(item.size)} • ${new Date(item.downloadedAt).toLocaleDateString()}`}
      left={(props) => <List.Icon {...props} icon="download" />}
      right={(props) => (
        <IconButton
          {...props}
          icon="delete-outline"
          iconColor={theme.colors.error}
          onPress={() => handleDelete(item.lectureId, item.lectureData.title)}
        />
      )}
      onPress={() => handleLecturePress(item)}
      style={{ backgroundColor: theme.colors.surface, borderRadius: 12, marginBottom: 8 }}
    />
  );

  const renderEmpty = () => (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 40, paddingTop: 60 }}>
      <Text style={{ fontSize: 64, marginBottom: 16 }}>📥</Text>
      <Text variant="titleLarge" style={{ marginBottom: 8 }}>No Offline Lectures</Text>
      <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, textAlign: 'center' }}>
        Download lectures to access them without an internet connection
      </Text>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      {/* Storage Info */}
      {downloads.length > 0 && (
        <Card style={{ marginHorizontal: 16, marginTop: 16, marginBottom: 8 }} mode="elevated">
          <Card.Content>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <View>
                <Text variant="labelMedium" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 4 }}>
                  Offline Storage
                </Text>
                <Text variant="headlineSmall" style={{ fontWeight: '700' }}>
                  {formatBytes(storageSize)}
                </Text>
              </View>
              <Button
                mode="text"
                textColor={theme.colors.error}
                onPress={handleClearAll}
              >
                Clear All
              </Button>
            </View>

            <ProgressBar
              progress={Math.min(1, storageSize / (500 * 1024 * 1024))}
              style={{ borderRadius: 4, marginBottom: 4 }}
            />
            <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant }}>
              Limit: 500 MB
            </Text>
          </Card.Content>
        </Card>
      )}

      {/* Downloads List */}
      <FlatList
        data={downloads}
        renderItem={renderDownload}
        keyExtractor={(item) => item.lectureId}
        contentContainerStyle={{ padding: 16, flexGrow: 1 }}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.colors.primary}
          />
        }
        ListEmptyComponent={renderEmpty}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
