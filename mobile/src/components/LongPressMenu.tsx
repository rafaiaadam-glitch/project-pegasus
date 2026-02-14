import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TouchableWithoutFeedback,
  Platform,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme';

export interface MenuItem {
  label: string;
  icon: string;
  onPress: () => void;
  destructive?: boolean;
}

interface Props {
  children: React.ReactNode;
  menuItems: MenuItem[];
  onLongPress?: () => void;
}

export default function LongPressMenu({ children, menuItems, onLongPress }: Props) {
  const { theme } = useTheme();
  const [menuVisible, setMenuVisible] = useState(false);

  const handleLongPress = async () => {
    if (Platform.OS !== 'web') {
      try {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      } catch (error) {
        console.warn('Haptics not available:', error);
      }
    }

    setMenuVisible(true);
    if (onLongPress) onLongPress();
  };

  const handleMenuItemPress = (item: MenuItem) => {
    setMenuVisible(false);
    setTimeout(() => {
      item.onPress();
    }, 100);
  };

  const styles = createStyles(theme);

  return (
    <>
      <TouchableOpacity
        onLongPress={handleLongPress}
        delayLongPress={500}
        activeOpacity={0.7}
      >
        {children}
      </TouchableOpacity>

      <Modal
        visible={menuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableWithoutFeedback onPress={() => setMenuVisible(false)}>
          <View style={styles.overlay}>
            <TouchableWithoutFeedback>
              <View style={styles.menu}>
                {menuItems.map((item, index) => (
                  <TouchableOpacity
                    key={index}
                    style={[
                      styles.menuItem,
                      index === menuItems.length - 1 && styles.lastMenuItem,
                    ]}
                    onPress={() => handleMenuItemPress(item)}
                  >
                    <Text style={styles.menuIcon}>{item.icon}</Text>
                    <Text
                      style={[
                        styles.menuLabel,
                        item.destructive && styles.destructiveLabel,
                      ]}
                    >
                      {item.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </TouchableWithoutFeedback>
          </View>
        </TouchableWithoutFeedback>
      </Modal>
    </>
  );
}

const createStyles = (theme: any) =>
  StyleSheet.create({
    overlay: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      justifyContent: 'center',
      alignItems: 'center',
      padding: 20,
    },
    menu: {
      backgroundColor: theme.surface,
      borderRadius: 12,
      minWidth: 200,
      maxWidth: 300,
      shadowColor: theme.shadowColor,
      shadowOpacity: 0.3,
      shadowRadius: 20,
      shadowOffset: { width: 0, height: 10 },
      elevation: 10,
    },
    menuItem: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
      borderBottomWidth: 0.5,
      borderBottomColor: theme.border,
    },
    lastMenuItem: {
      borderBottomWidth: 0,
    },
    menuIcon: {
      fontSize: 24,
      marginRight: 12,
    },
    menuLabel: {
      fontSize: 16,
      fontWeight: '500',
      color: theme.text,
      flex: 1,
    },
    destructiveLabel: {
      color: theme.error,
    },
  });
