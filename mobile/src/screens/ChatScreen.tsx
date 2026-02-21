import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  TouchableOpacity,
  TextInput as RNTextInput,
  Image,
} from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../theme';
import api from '../services/api';
import NetworkErrorView from '../components/NetworkErrorView';

const pegasusLogo = require('../../assets/icon.png');

interface Props {
  navigation: any;
  route: any;
}

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp?: string;
}

export default function ChatScreen({ navigation, route }: Props) {
  const { theme, isDark } = useTheme();
  const { courseId } = route.params;

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [courseTitle, setCourseTitle] = useState('');
  const flatListRef = useRef<FlatList<Message>>(null);
  const inputRef = useRef<RNTextInput>(null);

  useEffect(() => {
    loadCourseDetails();
  }, [courseId]);

  const loadCourseDetails = async () => {
    setLoadError(false);
    try {
      if (courseId !== 'default-course') {
        const course = await api.getCourse(courseId);
        setCourseTitle(course.title);
        navigation.setOptions({ title: `Chat: ${course.title}` });
      } else {
        setCourseTitle('your studies');
        navigation.setOptions({ title: 'Pegasus Chat' });
      }
    } catch {
      if (messages.length === 0) setLoadError(true);
      setCourseTitle('your studies');
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages]);

  const sendMessage = async () => {
    const text = inputText.trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: String(Date.now()),
      text,
      isUser: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setLoading(true);

    try {
      const history = messages.filter((m) => m.id !== 'welcome').map((m) => ({
        text: m.text,
        isUser: m.isUser,
      }));
      const response = await api.sendChatMessage(text, history, { courseId });
      const aiMsg: Message = {
        id: String(Date.now() + 1),
        text: response.response || "I couldn't generate a response.",
        isUser: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const errMsg: Message = {
        id: String(Date.now() + 1),
        text: 'Failed to send. Please try again.',
        isUser: false,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const renderWelcome = () => {
    const topic = courseTitle || 'your studies';
    return (
      <View style={styles.welcomeContainer}>
        {/* Avatar */}
        <View style={[styles.avatar, { backgroundColor: isDark ? '#1C1C1E' : '#E5E5EA' }]}>
          <Image source={pegasusLogo} style={styles.avatarImage} />
        </View>

        <Text variant="bodyLarge" style={[styles.welcomeHeading, { color: theme.colors.onSurface }]}>
          This is just between <Text style={{ color: theme.colors.primary, fontWeight: '600' }}>@pegasus</Text> and you.
          {'\n'}Ask anything about {topic}.
        </Text>

        <View style={[styles.divider, { backgroundColor: theme.colors.outlineVariant }]} />

        {/* Intro card */}
        <View style={styles.introSection}>
          <View style={styles.introHeader}>
            <View style={[styles.avatarSmall, { backgroundColor: isDark ? '#1C1C1E' : '#E5E5EA' }]}>
              <Image source={pegasusLogo} style={styles.avatarSmallImage} />
            </View>
            <Text variant="titleSmall" style={{ fontWeight: '700', marginLeft: 10 }}>Pegasus</Text>
          </View>

          <Text variant="bodyMedium" style={[styles.introText, { color: theme.colors.onSurface }]}>
            Need help revising? Pegasus Chat has you covered.
          </Text>
          <Text variant="bodyMedium" style={[styles.introBody, { color: theme.colors.onSurfaceVariant }]}>
            Ask questions about your lectures and I'll pull from your transcripts, summaries, and notes. Try things like:
          </Text>

          <View style={styles.bulletList}>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant }}>
              {'\u2022'}  "Explain the key concepts from last lecture"
            </Text>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
              {'\u2022'}  "What are the differences between X and Y?"
            </Text>
            <Text variant="bodyMedium" style={{ color: theme.colors.onSurfaceVariant, marginTop: 4 }}>
              {'\u2022'}  "Quiz me on the flashcard topics"
            </Text>
          </View>
        </View>

        <Text
          variant="labelSmall"
          style={[styles.disclaimer, { color: theme.colors.onSurfaceVariant }]}
        >
          Pegasus is an AI study assistant. If you are experiencing distress, please reach out to your institutional support services.
        </Text>
      </View>
    );
  };

  const renderMessage = ({ item }: { item: Message }) => {
    if (item.isUser) {
      return (
        <View style={styles.userRow}>
          <View style={[styles.userBubble, { backgroundColor: theme.colors.primary }]}>
            <Text style={{ color: '#FFFFFF', fontSize: 15, lineHeight: 21 }}>{item.text}</Text>
          </View>
          {item.timestamp && (
            <Text variant="labelSmall" style={[styles.timestamp, { alignSelf: 'flex-end', color: theme.colors.onSurfaceVariant }]}>
              {item.timestamp}
            </Text>
          )}
        </View>
      );
    }

    return (
      <View style={styles.aiRow}>
        <View style={[styles.avatarTiny, { backgroundColor: isDark ? '#1C1C1E' : '#E5E5EA' }]}>
          <Image source={pegasusLogo} style={styles.avatarTinyImage} />
        </View>
        <View style={{ flex: 1, marginLeft: 8 }}>
          <View style={[styles.aiBubble, { backgroundColor: theme.colors.surfaceVariant }]}>
            <Text style={{ color: theme.colors.onSurface, fontSize: 15, lineHeight: 21 }}>{item.text}</Text>
          </View>
          {item.timestamp && (
            <Text variant="labelSmall" style={[styles.timestamp, { color: theme.colors.onSurfaceVariant }]}>
              {item.timestamp}
            </Text>
          )}
        </View>
      </View>
    );
  };

  if (loadError && messages.length === 0) {
    return (
      <View style={[styles.center, { backgroundColor: theme.colors.background }]}>
        <NetworkErrorView onRetry={loadCourseDetails} message="Could not connect to Pegasus Chat." />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: theme.colors.background }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={renderWelcome}
        contentContainerStyle={styles.listContent}
        keyboardShouldPersistTaps="handled"
      />

      {loading && (
        <View style={styles.typingRow}>
          <View style={[styles.avatarTiny, { backgroundColor: isDark ? '#1C1C1E' : '#E5E5EA' }]}>
            <Image source={pegasusLogo} style={styles.avatarTinyImage} />
          </View>
          <ActivityIndicator size="small" style={{ marginLeft: 10 }} color={theme.colors.primary} />
          <Text variant="labelSmall" style={{ marginLeft: 8, color: theme.colors.onSurfaceVariant }}>
            Thinking...
          </Text>
        </View>
      )}

      {/* Input bar */}
      <View style={[styles.inputBar, { backgroundColor: theme.colors.surface, borderTopColor: theme.colors.outlineVariant }]}>
        <View style={[styles.inputWrapper, { backgroundColor: isDark ? '#2C2C2E' : '#F2F2F7', borderColor: theme.colors.outlineVariant }]}>
          <RNTextInput
            ref={inputRef}
            style={[styles.textInput, { color: theme.colors.onSurface }]}
            placeholder="Message Pegasus"
            placeholderTextColor={theme.colors.onSurfaceVariant}
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={2000}
            onSubmitEditing={sendMessage}
            blurOnSubmit={false}
          />
          <TouchableOpacity
            onPress={sendMessage}
            disabled={loading || inputText.trim() === ''}
            style={[
              styles.sendButton,
              {
                backgroundColor: inputText.trim() && !loading ? theme.colors.primary : isDark ? '#3A3A3C' : '#E5E5EA',
              },
            ]}
          >
            <MaterialCommunityIcons
              name="creation"
              size={18}
              color={inputText.trim() && !loading ? '#FFFFFF' : theme.colors.onSurfaceVariant}
            />
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  listContent: {
    paddingBottom: 8,
  },

  // Welcome
  welcomeContainer: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 8,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarImage: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  welcomeHeading: {
    fontSize: 17,
    lineHeight: 24,
    marginBottom: 16,
  },
  divider: {
    height: 1,
    marginBottom: 20,
  },
  introSection: {
    marginBottom: 16,
  },
  introHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarSmall: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarSmallImage: {
    width: 28,
    height: 28,
    borderRadius: 14,
  },
  introText: {
    fontWeight: '600',
    marginBottom: 8,
  },
  introBody: {
    lineHeight: 22,
    marginBottom: 12,
  },
  bulletList: {
    paddingLeft: 4,
    marginBottom: 4,
  },
  disclaimer: {
    textAlign: 'center',
    lineHeight: 16,
    paddingHorizontal: 12,
    paddingTop: 8,
    opacity: 0.6,
  },

  // Messages
  userRow: {
    paddingHorizontal: 16,
    marginTop: 12,
    alignItems: 'flex-end',
  },
  userBubble: {
    borderRadius: 20,
    borderBottomRightRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxWidth: '80%',
  },
  aiRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    marginTop: 12,
  },
  avatarTiny: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2,
  },
  avatarTinyImage: {
    width: 22,
    height: 22,
    borderRadius: 11,
  },
  aiBubble: {
    borderRadius: 20,
    borderTopLeftRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxWidth: '92%',
  },
  timestamp: {
    marginTop: 4,
    paddingHorizontal: 4,
  },

  // Typing indicator
  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },

  // Input
  inputBar: {
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: Platform.OS === 'ios' ? 28 : 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
    paddingLeft: 16,
    paddingRight: 6,
    paddingVertical: 6,
    minHeight: 44,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    lineHeight: 21,
    maxHeight: 100,
    paddingTop: Platform.OS === 'ios' ? 6 : 4,
    paddingBottom: Platform.OS === 'ios' ? 6 : 4,
  },
  sendButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
});
