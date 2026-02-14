import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Alert,
  RefreshControl,
} from 'react-native';
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
    <View style={styles.downloadCard}>
      <TouchableOpacity
        style={styles.downloadContent}
        onPress={() => handleLecturePress(item)}
      >
        <View style={styles.downloadIcon}>
          <Text style={styles.downloadIconText}>📥</Text>
        </View>
        <View style={styles.downloadInfo}>
          <Text style={styles.downloadTitle}>{item.lectureData.title}</Text>
          <View style={styles.downloadMeta}>
            <Text style={styles.downloadSize}>{formatBytes(item.size)}</Text>
            <Text style={styles.downloadDot}>•</Text>
            <Text style={styles.downloadDate}>
              {new Date(item.downloadedAt).toLocaleDateString()}
            </Text>
          </View>
        </View>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => handleDelete(item.lectureId, item.lectureData.title)}
      >
        <Text style={styles.deleteIcon}>🗑️</Text>
      </TouchableOpacity>
    </View>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyIcon}>📥</Text>
      <Text style={styles.emptyTitle}>No Offline Lectures</Text>
      <Text style={styles.emptyText}>
        Download lectures to access them without an internet connection
      </Text>
    </View>
  );

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      {/* Storage Info */}
      {downloads.length > 0 && (
        <View style={styles.storageCard}>
          <View style={styles.storageHeader}>
            <View>
              <Text style={styles.storageTitle}>Offline Storage</Text>
              <Text style={styles.storageSize}>{formatBytes(storageSize)}</Text>
            </View>
            <TouchableOpacity style={styles.clearButton} onPress={handleClearAll}>
              <Text style={styles.clearButtonText}>Clear All</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.storageBar}>
            <View style={styles.storageBarTrack}>
              <View
                style={[
                  styles.storageBarFill,
                  { width: `${Math.min(100, (storageSize / (500 * 1024 * 1024)) * 100)}%` },
                ]}
              />
            </View>
            <Text style={styles.storageLimit}>Limit: 500 MB</Text>
          </View>
        </View>
      )}

      {/* Downloads List */}
      <FlatList
        data={downloads}
        renderItem={renderDownload}
        keyExtractor={(item) => item.lectureId}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={theme.primary}
          />
        }
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
    storageCard: {
      backgroundColor: theme.surface,
      marginHorizontal: 16,
      marginTop: 16,
      marginBottom: 8,
      borderRadius: 12,
      padding: 16,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    storageHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 12,
    },
    storageTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.textSecondary,
      marginBottom: 4,
    },
    storageSize: {
      fontSize: 24,
      fontWeight: '700',
      color: theme.text,
    },
    clearButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
      backgroundColor: theme.error + '20',
    },
    clearButtonText: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.error,
    },
    storageBar: {
      marginTop: 8,
    },
    storageBarTrack: {
      height: 8,
      backgroundColor: theme.border,
      borderRadius: 4,
      overflow: 'hidden',
    },
    storageBarFill: {
      height: '100%',
      backgroundColor: theme.primary,
      borderRadius: 4,
    },
    storageLimit: {
      fontSize: 12,
      color: theme.textTertiary,
      marginTop: 4,
    },
    listContent: {
      padding: 16,
      flexGrow: 1,
    },
    downloadCard: {
      flexDirection: 'row',
      backgroundColor: theme.surface,
      borderRadius: 12,
      marginBottom: 12,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.05,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
      overflow: 'hidden',
    },
    downloadContent: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
    },
    downloadIcon: {
      width: 48,
      height: 48,
      borderRadius: 24,
      backgroundColor: theme.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
    },
    downloadIconText: {
      fontSize: 24,
    },
    downloadInfo: {
      flex: 1,
    },
    downloadTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 4,
    },
    downloadMeta: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    downloadSize: {
      fontSize: 13,
      color: theme.textSecondary,
    },
    downloadDot: {
      fontSize: 13,
      color: theme.textTertiary,
      marginHorizontal: 6,
    },
    downloadDate: {
      fontSize: 13,
      color: theme.textSecondary,
    },
    deleteButton: {
      width: 60,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: theme.error + '10',
    },
    deleteIcon: {
      fontSize: 24,
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
