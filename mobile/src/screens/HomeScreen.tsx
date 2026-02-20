import React, { useState, useEffect, useRef } from 'react';
import { View, StyleSheet, TouchableOpacity, Platform, FlatList, RefreshControl, Animated, Alert } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { useTheme } from '../theme';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, Defs, LinearGradient as SvgGradient, Stop } from 'react-native-svg';
import { Swipeable } from 'react-native-gesture-handler';
import CalendarView from '../components/CalendarView';
import ActionItemsView from '../components/ActionItemsView';
import api from '../services/api';
import { Lecture } from '../types';
import NetworkErrorView from '../components/NetworkErrorView';

interface Props {
  navigation: any;
}

type Tab = 'conversations' | 'calendar' | 'actionItems';

export default function HomeScreen({ navigation }: Props) {
  const { theme, isDark, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<Tab>('conversations');
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchLectures();
  }, []);

  const fetchLectures = async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await api.getLectures(undefined, 20);
      setLectures(response.lectures || []);
    } catch (err) {
      console.error('Failed to fetch lectures:', err);
      setError(true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchLectures();
  };

  // Navigation handlers
  const handleRecord = () => {
    navigation.navigate('CourseList', { selectForRecording: true });
  };

  const handleLecturePress = (lecture: Lecture) => {
    navigation.navigate('LectureDetail', { lectureId: lecture.id });
  };

  const handleDeleteLecture = (lecture: Lecture) => {
    Alert.alert(
      'Delete Lecture',
      `Are you sure you want to delete "${lecture.title || 'Untitled'}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.deleteLecture(lecture.id);
              setLectures((prev) => prev.filter((l) => l.id !== lecture.id));
            } catch (err) {
              console.error('Failed to delete lecture:', err);
              Alert.alert('Error', 'Failed to delete lecture.');
            }
          },
        },
      ]
    );
  };

  const handleChat = () => {
    navigation.navigate('Chat', { courseId: 'default-course' });
  };
  
  const handleCourses = () => {
    navigation.navigate('CourseList');
  }

  const handleAccount = () => {
    navigation.navigate('Settings');
  };

  const renderRightActions = (item: Lecture) => (
    _progress: Animated.AnimatedInterpolation<number>,
    _dragX: Animated.AnimatedInterpolation<number>,
  ) => (
    <TouchableOpacity
      style={[styles.deleteAction, { backgroundColor: theme.colors.error }]}
      onPress={() => handleDeleteLecture(item)}
    >
      <MaterialCommunityIcons name="delete-outline" size={24} color="#fff" />
      <Text style={{ color: '#fff', fontSize: 12, marginTop: 4 }}>Delete</Text>
    </TouchableOpacity>
  );

  const renderLectureItem = ({ item }: { item: Lecture }) => (
    <Swipeable renderRightActions={renderRightActions(item)} overshootRight={false}>
      <TouchableOpacity
        style={[styles.lectureCard, { backgroundColor: theme.colors.surfaceVariant }]}
        onPress={() => handleLecturePress(item)}
      >
        <View style={styles.lectureIcon}>
          <MaterialCommunityIcons
            name={item.source_type === 'pdf' ? 'file-document-outline' : 'microphone-outline'}
            size={24}
            color={theme.colors.primary}
          />
        </View>
        <View style={styles.lectureInfo}>
          <Text variant="titleMedium" numberOfLines={1} style={{ color: theme.colors.onSurface }}>
            {item.title || 'Untitled Lecture'}
          </Text>
          <Text variant="bodySmall" style={{ color: theme.colors.onSurfaceVariant }}>
            {new Date(item.created_at).toLocaleDateString()} • {item.status}
          </Text>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={24} color={theme.colors.onSurfaceVariant} />
      </TouchableOpacity>
    </Swipeable>
  );

  const renderContent = () => {
    if (activeTab === 'calendar') {
      return <CalendarView navigation={navigation} />;
    }

    if (activeTab === 'actionItems') {
      return <ActionItemsView />;
    }

    // Default: Conversations (Home)
    if (error && lectures.length === 0) {
      return <NetworkErrorView onRetry={fetchLectures} />;
    }

    if (loading && !refreshing && lectures.length === 0) {
      return (
        <View style={styles.centerContent}>
          <ActivityIndicator animating={true} color={theme.colors.primary} />
        </View>
      );
    }

    if (lectures.length === 0) {
      return (
        <View style={styles.centerContent}>
          <View style={[styles.emptyIconContainer, { backgroundColor: theme.colors.secondaryContainer }]}>
            <MaterialCommunityIcons name="home-variant-outline" size={32} color={theme.colors.primary} />
          </View>
          <Text variant="headlineSmall" style={{ fontWeight: '700', marginBottom: 12, color: theme.colors.onSurface }}>
            Home
          </Text>
          <Text variant="bodyLarge" style={{ textAlign: 'center', color: theme.colors.onSurfaceVariant, paddingHorizontal: 48, lineHeight: 24 }}>
            Start capturing ideas by recording or importing notes—they'll appear here.
          </Text>
          <TouchableOpacity onPress={fetchLectures} style={{ marginTop: 20 }}>
             <Text style={{ color: theme.colors.primary }}>Refresh</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return (
      <FlatList
        data={lectures}
        renderItem={renderLectureItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.colors.primary]} />
        }
      />
    );
  };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.colors.background }]} edges={['top', 'left', 'right']}>
      
      {/* --- HEADER --- */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text variant="headlineSmall" style={[styles.logoText, { color: theme.colors.primary }]}>
            Pegasus
          </Text>
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity onPress={() => navigation.navigate('Search')} style={styles.headerIconBtn}>
            <MaterialCommunityIcons name="magnify" size={26} color={theme.colors.onSurface} />
          </TouchableOpacity>
          <TouchableOpacity onPress={handleRecord} style={styles.headerIconBtn}>
            <MaterialCommunityIcons name="plus" size={26} color={theme.colors.onSurface} />
          </TouchableOpacity>
          <TouchableOpacity onPress={toggleTheme} style={styles.headerIconBtn}>
            <MaterialCommunityIcons 
              name={isDark ? "weather-sunny" : "bell-outline"} 
              size={24} 
              color={theme.colors.onSurface} 
            />
          </TouchableOpacity>
        </View>
      </View>

      {/* --- TABS --- */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          onPress={() => setActiveTab('conversations')} 
          style={[styles.tabItem, activeTab === 'conversations' && styles.tabItemActive, { borderBottomColor: theme.colors.primary }]}
        >
          <Text style={[styles.tabText, { color: activeTab === 'conversations' ? theme.colors.primary : theme.colors.onSurfaceVariant, fontWeight: activeTab === 'conversations' ? '700' : '500' }]}>Conversations</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          onPress={() => setActiveTab('calendar')} 
          style={[styles.tabItem, activeTab === 'calendar' && styles.tabItemActive, { borderBottomColor: theme.colors.primary }]}
        >
          <Text style={[styles.tabText, { color: activeTab === 'calendar' ? theme.colors.primary : theme.colors.onSurfaceVariant, fontWeight: activeTab === 'calendar' ? '700' : '500' }]}>Calendar</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          onPress={() => setActiveTab('actionItems')} 
          style={[styles.tabItem, activeTab === 'actionItems' && styles.tabItemActive, { borderBottomColor: theme.colors.primary }]}
        >
          <Text style={[styles.tabText, { color: activeTab === 'actionItems' ? theme.colors.primary : theme.colors.onSurfaceVariant, fontWeight: activeTab === 'actionItems' ? '700' : '500' }]}>Action Items</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.divider, { backgroundColor: theme.colors.outlineVariant }]} />

      {/* --- SUB-HEADER --- */}
      <View style={styles.subHeader}>
        <Text variant="titleMedium" style={{ fontWeight: '700', color: theme.colors.onSurface }}>
          {activeTab === 'calendar' ? 'Schedule' : activeTab === 'conversations' ? 'Recent' : 'Tasks'}
        </Text>
        <View style={styles.sortContainer}>
          <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginRight: 4 }}>
            {activeTab === 'calendar' ? 'All Events' : activeTab === 'conversations' ? 'Newest First' : 'Priority'}
          </Text>
          <MaterialCommunityIcons name="unfold-more-horizontal" size={18} color={theme.colors.onSurfaceVariant} />
        </View>
      </View>

      {/* --- MAIN CONTENT --- */}
      <View style={{ flex: 1 }}>
        {renderContent()}
      </View>

      {/* --- BOTTOM NAVIGATION BAR --- */}
      <View style={[styles.bottomBar, { 
        backgroundColor: theme.colors.surface, 
        borderTopColor: theme.colors.outlineVariant,
        paddingBottom: Platform.OS === 'ios' ? 24 : 0 
      }]}>
        
        {/* Home (Active) */}
        <TouchableOpacity style={styles.navItem} onPress={() => setActiveTab('conversations')}>
          <MaterialCommunityIcons name="home" size={28} color={theme.colors.primary} />
          <Text style={[styles.navLabel, { color: theme.colors.primary }]}>Home</Text>
        </TouchableOpacity>

        {/* Channels/Courses */}
        <TouchableOpacity style={styles.navItem} onPress={handleCourses}>
          <MaterialCommunityIcons name="folder-outline" size={28} color={theme.colors.onSurfaceVariant} />
          <Text style={[styles.navLabel, { color: theme.colors.onSurfaceVariant }]}>Courses</Text>
        </TouchableOpacity>

        {/* Placeholder for center Mic Button */}
        <View style={styles.navItem} pointerEvents="box-none"> 
           <View style={{ width: 40 }} /> 
        </View>

        {/* AI Chat */}
        <TouchableOpacity style={styles.navItem} onPress={handleChat}>
          <MaterialCommunityIcons name="chat-outline" size={28} color={theme.colors.onSurfaceVariant} />
          <Text style={[styles.navLabel, { color: theme.colors.onSurfaceVariant }]}>AI Chat</Text>
        </TouchableOpacity>

        {/* Account */}
        <TouchableOpacity style={styles.navItem} onPress={handleAccount}>
          <MaterialCommunityIcons name="account-circle-outline" size={28} color={theme.colors.onSurfaceVariant} />
          <Text style={[styles.navLabel, { color: theme.colors.onSurfaceVariant }]}>Account</Text>
        </TouchableOpacity>

        {/* Absolute Floating Button with Dotted Holographic Outline */}
        <TouchableOpacity 
          style={styles.micButtonContainer}
          onPress={handleRecord}
          activeOpacity={0.9}
        >
          <View style={styles.micWrapper}>
            {/* SVG Dotted Border */}
            <View style={styles.svgOverlay}>
              <Svg height="76" width="76" viewBox="0 0 76 76">
                <Defs>
                  <SvgGradient id="holoGrad" x1="0" y1="0" x2="1" y2="1">
                    <Stop offset="0" stopColor="#00FFFF" stopOpacity="1" />
                    <Stop offset="0.33" stopColor="#FF00FF" stopOpacity="1" />
                    <Stop offset="0.66" stopColor="#C0C0C0" stopOpacity="1" />
                    <Stop offset="1" stopColor="#ADD8E6" stopOpacity="1" />
                  </SvgGradient>
                </Defs>
                <Circle
                  cx="38"
                  cy="38"
                  r="35"
                  stroke="url(#holoGrad)"
                  strokeWidth="3"
                  strokeDasharray="5, 5"
                  strokeLinecap="round"
                  fill="transparent"
                />
              </Svg>
            </View>

            {/* Inner Button */}
            <View style={[styles.micInner, { backgroundColor: theme.colors.primary }]}>
              <MaterialCommunityIcons name="microphone" size={32} color={theme.colors.onPrimary} />
            </View>
          </View>
        </TouchableOpacity>

      </View>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoText: {
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
  },
  headerIconBtn: {
    padding: 4,
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginTop: 8,
  },
  tabItem: {
    marginRight: 24,
    paddingBottom: 12,
  },
  tabItemActive: {
    borderBottomWidth: 3,
  },
  tabText: {
    fontSize: 16,
    fontWeight: '500',
  },
  divider: {
    height: 1,
    width: '100%',
    opacity: 0.2,
  },
  subHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  sortContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingBottom: 120, // Make room for bottom bar
  },
  emptyIconContainer: {
    width: 72,
    height: 72,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  lectureCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    elevation: 1,
  },
  lectureIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(0,0,0,0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  lectureInfo: {
    flex: 1,
  },
  deleteAction: {
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
    borderRadius: 12,
    marginBottom: 12,
    marginLeft: 8,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: Platform.OS === 'ios' ? 90 : 70,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingHorizontal: 8,
    borderTopWidth: 1,
    elevation: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    zIndex: 1,
  },
  navItem: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 50,
    minWidth: 60,
  },
  navLabel: {
    fontSize: 10,
    marginTop: 4,
    fontWeight: '600',
  },
  micButtonContainer: {
    position: 'absolute',
    bottom: Platform.OS === 'ios' ? 40 : 25,
    alignSelf: 'center',
    left: '50%',
    marginLeft: -38, // Half of width (76)
    zIndex: 10,
    // Illuminated Glow
    shadowColor: '#00FFFF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 12,
  },
  micWrapper: {
    width: 76,
    height: 76,
    justifyContent: 'center',
    alignItems: 'center',
  },
  svgOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  micInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
