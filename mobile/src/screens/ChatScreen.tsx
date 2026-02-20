import React, { useState, useEffect, useRef } from 'react';
import { View, FlatList, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { Appbar, TextInput, Button, Text, ActivityIndicator, Divider } from 'react-native-paper';
import { useTheme } from '../theme';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import api from '../services/api';
import NetworkErrorView from '../components/NetworkErrorView';

type ChatRouteParamList = {
  Chat: { courseId: string };
};

type ChatScreenNavigationProp = StackNavigationProp<ChatRouteParamList, 'Chat'>;
type ChatScreenRouteProp = RouteProp<ChatRouteParamList, 'Chat'>;

interface Message {
  id: string;
  text: string;
  isUser: boolean;
}

const ChatScreen: React.FC = () => {
  const { theme } = useTheme();
  const navigation = useNavigation<ChatScreenNavigationProp>();
  const route = useRoute<ChatScreenRouteProp>();
  const { courseId } = route.params;

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<boolean>(false);
  const [courseTitle, setCourseTitle] = useState<string>('');
  const flatListRef = useRef<FlatList<Message>>(null);

  const DISCLAIMER_TEXT = "I am an AI assistant for studies, not a qualified mental health care provider. If you are experiencing high levels of distress, please reach out to your institutional support services.";

  useEffect(() => {
    loadCourseDetails();
  }, [courseId]);

  const loadCourseDetails = async () => {
    setLoadError(false);
    try {
      if (courseId !== 'default-course') {
        const course = await api.getCourse(courseId);
        setCourseTitle(course.title);
        setMessages([
          { id: '0', text: `Hello! I'm Pegasus. I'm ready to help you with ${course.title}. What's on your mind?`, isUser: false },
          { id: 'disclaimer', text: DISCLAIMER_TEXT, isUser: false },
        ]);
      } else {
         setMessages([
          { id: '0', text: `Hello! I'm Pegasus. How can I help you reflect on your studies today?`, isUser: false },
          { id: 'disclaimer', text: DISCLAIMER_TEXT, isUser: false },
        ]);
      }
    } catch (error) {
      console.error('Failed to load course details:', error);
      if (messages.length === 0) {
        setLoadError(true);
      } else {
        setMessages([
          { id: '0', text: `Hello! I'm Pegasus. How can I help you today?`, isUser: false },
          { id: 'disclaimer', text: DISCLAIMER_TEXT, isUser: false },
        ]);
      }
    }
  };

  useEffect(() => {
    // Scroll to bottom when messages change
    if (messages.length > 0) {
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages]);

  const sendMessage = async () => {
    if (inputText.trim() === '') return;

    const userMsgText = inputText;
    const newUserMessage: Message = { id: String(Date.now()), text: userMsgText, isUser: true };
    setMessages((prev) => [...prev, newUserMessage]);
    setInputText('');
    setLoading(true);

    try {
      // Prepare history for API (excluding the just added message which is current input)
      // Actually, standard practice is to send history including the new message?
      // Our API takes `message` separately. `history` is previous messages.
      const history = messages.filter(m => m.id !== 'disclaimer').map(m => ({
        text: m.text,
        isUser: m.isUser
      }));

      const response = await api.sendChatMessage(userMsgText, history, { courseId });
      
      const newAiMessage: Message = { 
        id: String(Date.now() + 1), 
        text: response.response || "I'm sorry, I couldn't generate a response.", 
        isUser: false 
      };
      setMessages((prev) => [...prev, newAiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      Alert.alert('Error', 'Failed to send message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderMessage = ({ item }: { item: Message }) => (
    <View
      style={{
        alignSelf: item.isUser ? 'flex-end' : 'flex-start',
        backgroundColor: item.isUser ? theme.colors.primaryContainer : theme.colors.surfaceVariant,
        borderRadius: 20,
        paddingHorizontal: 15,
        paddingVertical: 10,
        marginHorizontal: 10,
        marginVertical: 4,
        maxWidth: '80%',
      }}
    >
      <Text style={{ color: item.isUser ? theme.colors.onPrimaryContainer : theme.colors.onSurfaceVariant }}>
        {item.text}
      </Text>
    </View>
  );

  if (loadError && messages.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
        <Appbar.Header elevated>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title="Pegasus Chat" />
        </Appbar.Header>
        <NetworkErrorView onRetry={loadCourseDetails} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header elevated>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={`Pegasus Chat: ${courseId}`} />
        {/* Potentially add actions for settings or other chat modes */}
      </Appbar.Header>



      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ flexGrow: 1, justifyContent: 'flex-end' }}
      />

      {loading && (
        <ActivityIndicator animating={true} color={theme.colors.primary} style={{ marginVertical: 10 }} />
      )}

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 60 : 0}
      >
        <View style={{ flexDirection: 'row', padding: 8, backgroundColor: theme.colors.surface }}>
          <TextInput
            style={{ flex: 1, marginRight: 8, backgroundColor: theme.colors.surfaceVariant }}
            placeholder="Type your message..."
            value={inputText}
            onChangeText={setInputText}
            mode="outlined"
            dense
            multiline
            right={<TextInput.Icon icon="send" onPress={sendMessage} disabled={loading || inputText.trim() === ''} />}
          />
        </View>
      </KeyboardAvoidingView>
    </View>
  );
};

export default ChatScreen;
