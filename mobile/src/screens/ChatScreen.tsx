import React, { useState, useEffect, useRef } from 'react';
import { View, FlatList, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import { Appbar, TextInput, Button, Text, ActivityIndicator, Divider } from 'react-native-paper';
import { useTheme } from '../theme';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';

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
  const [courseContext, setCourseContext] = useState<{ summary: string; concepts: string[] } | null>(null);
  const flatListRef = useRef<FlatList<Message>>(null);

  const DISCLAIMER_TEXT = "I am an AI assistant for studies, not a qualified mental health care provider. If you are experiencing high levels of distress, please reach out to your institutional support services.";

  useEffect(() => {
    // Initial load for course context (this will be from backend API call later)
    setCourseContext({
      summary: "Loading course summary...",
      concepts: [],
    });
    // Simulate fetching context
    setTimeout(() => {
      setCourseContext({
        summary: "This course covers foundational neuroscience, focusing on neural pathways and cognitive functions.",
        concepts: ["Neural Pathways", "Cognitive Functions", "Synaptic Plasticity"],
      });
      setMessages([
        { id: '0', text: `Hello! I'm Pegasus, your study reflection copilot for ${courseId}. How can I help you reflect on your studies today?`, isUser: false },
        { id: 'disclaimer', text: DISCLAIMER_TEXT, isUser: false },
      ]);
    }, 1000);
  }, [courseId]);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages]);

  const sendMessage = async () => {
    if (inputText.trim() === '') return;

    const newUserMessage: Message = { id: String(messages.length), text: inputText, isUser: true };
    setMessages((prev) => [...prev, newUserMessage]);
    setInputText('');
    setLoading(true);

    try {
      // Simulate API call to Gemini
      // In a real implementation, this would connect to your backend /chat/reflect endpoint
      // and handle streaming responses.
      const simulatedResponse = `That's a great point! Let's explore how "${newUserMessage.text}" connects with "${courseContext?.concepts[0] || 'your core concepts'}". What are your initial thoughts on their relationship?`;
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate network delay

      const newAiMessage: Message = { id: String(messages.length + 1), text: simulatedResponse, isUser: false };
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

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.background }}>
      <Appbar.Header elevated>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={`Pegasus Chat: ${courseId}`} />
        {/* Potentially add actions for settings or other chat modes */}
      </Appbar.Header>

      <View style={{ padding: 10, backgroundColor: theme.colors.surface }}>
        <Text variant="labelSmall" style={{ color: theme.colors.onSurfaceVariant, marginBottom: 5 }}>
          Course Context:
        </Text>
        <Text variant="bodySmall" style={{ color: theme.colors.onSurface }}>
          {courseContext?.summary}
        </Text>
        {courseContext?.concepts.length > 0 && (
          <Text variant="bodySmall" style={{ color: theme.colors.onSurface, marginTop: 5 }}>
            Key Concepts: {courseContext.concepts.join(', ')}
          </Text>
        )}
        <Divider style={{ marginTop: 10 }} />
      </View>

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
