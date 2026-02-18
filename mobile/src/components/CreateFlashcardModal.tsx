import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Modal,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { useTheme } from '../theme';

interface Props {
  visible: boolean;
  onClose: () => void;
  onSave: (front: string, back: string) => void;
  initialFront?: string;
  initialBack?: string;
}

export default function CreateFlashcardModal({
  visible,
  onClose,
  onSave,
  initialFront = '',
  initialBack = '',
}: Props) {
  const { theme } = useTheme();
  const [front, setFront] = useState(initialFront);
  const [back, setBack] = useState(initialBack);

  const handleSave = () => {
    if (front.trim() && back.trim()) {
      onSave(front.trim(), back.trim());
      setFront('');
      setBack('');
      onClose();
    }
  };

  const handleCancel = () => {
    setFront('');
    setBack('');
    onClose();
  };

  const styles = createStyles(theme);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <View style={styles.overlay}>
          <View style={styles.modal}>
            <View style={styles.header}>
              <Text style={styles.title}>Create Flashcard</Text>
              <TouchableOpacity onPress={handleCancel}>
                <Text style={styles.closeButton}>✕</Text>
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              <View style={styles.section}>
                <Text style={styles.label}>Front (Question) *</Text>
                <TextInput
                  style={styles.input}
                  value={front}
                  onChangeText={setFront}
                  placeholder="Enter question or term..."
                  placeholderTextColor={theme.textTertiary}
                  multiline
                  numberOfLines={4}
                  textAlignVertical="top"
                  autoFocus
                />
              </View>

              <View style={styles.section}>
                <Text style={styles.label}>Back (Answer) *</Text>
                <TextInput
                  style={styles.input}
                  value={back}
                  onChangeText={setBack}
                  placeholder="Enter answer or definition..."
                  placeholderTextColor={theme.textTertiary}
                  multiline
                  numberOfLines={6}
                  textAlignVertical="top"
                />
              </View>

              <View style={styles.tips}>
                <Text style={styles.tipsTitle}>💡 Tips:</Text>
                <Text style={styles.tipText}>• Keep questions clear and specific</Text>
                <Text style={styles.tipText}>• Include examples in answers</Text>
                <Text style={styles.tipText}>• Use formatting for readability</Text>
              </View>
            </ScrollView>

            <View style={styles.footer}>
              <TouchableOpacity
                style={[styles.button, styles.cancelButton]}
                onPress={handleCancel}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.button,
                  styles.saveButton,
                  (!front.trim() || !back.trim()) && styles.saveButtonDisabled,
                ]}
                onPress={handleSave}
                disabled={!front.trim() || !back.trim()}
              >
                <Text style={styles.saveButtonText}>Create Card</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
    },
    overlay: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      justifyContent: 'flex-end',
    },
    modal: {
      backgroundColor: theme.background,
      borderTopLeftRadius: 20,
      borderTopRightRadius: 20,
      maxHeight: '90%',
      paddingBottom: Platform.OS === 'ios' ? 34 : 20,
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingVertical: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    title: {
      fontSize: 20,
      fontWeight: '700',
      color: theme.text,
    },
    closeButton: {
      fontSize: 24,
      color: theme.textSecondary,
      width: 32,
      height: 32,
      textAlign: 'center',
      lineHeight: 32,
    },
    content: {
      paddingHorizontal: 20,
      paddingTop: 20,
    },
    section: {
      marginBottom: 24,
    },
    label: {
      fontSize: 15,
      fontWeight: '600',
      color: theme.text,
      marginBottom: 8,
    },
    input: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      padding: 16,
      fontSize: 16,
      color: theme.text,
      borderWidth: 1,
      borderColor: theme.border,
      minHeight: 100,
    },
    tips: {
      backgroundColor: theme.primary + '10',
      borderRadius: 12,
      padding: 16,
      marginBottom: 20,
    },
    tipsTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: theme.primary,
      marginBottom: 8,
    },
    tipText: {
      fontSize: 13,
      color: theme.textSecondary,
      marginBottom: 4,
      lineHeight: 18,
    },
    footer: {
      flexDirection: 'row',
      paddingHorizontal: 20,
      paddingTop: 16,
      gap: 12,
    },
    button: {
      flex: 1,
      paddingVertical: 14,
      borderRadius: 12,
      alignItems: 'center',
    },
    cancelButton: {
      backgroundColor: theme.surface,
      borderWidth: 1,
      borderColor: theme.border,
    },
    cancelButtonText: {
      fontSize: 16,
      fontWeight: '600',
      color: theme.textSecondary,
    },
    saveButton: {
      backgroundColor: theme.primary,
    },
    saveButtonDisabled: {
      opacity: 0.5,
    },
    saveButtonText: {
      fontSize: 16,
      fontWeight: '600',
      color: '#FFF',
    },
  });
