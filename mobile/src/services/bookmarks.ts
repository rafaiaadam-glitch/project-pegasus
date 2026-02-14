import AsyncStorage from '@react-native-async-storage/async-storage';

const BOOKMARKS_KEY = 'pegasus_bookmarks';
const FAVORITES_KEY = 'pegasus_favorites';

export interface Bookmark {
  id: string;
  lectureId: string;
  lectureTitle: string;
  timestamp: number; // seconds into the audio
  note: string;
  createdAt: string;
}

// Favorites
export const toggleFavorite = async (lectureId: string): Promise<boolean> => {
  try {
    const favorites = await getFavorites();
    const index = favorites.indexOf(lectureId);

    if (index > -1) {
      favorites.splice(index, 1);
      await AsyncStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
      return false; // unfavorited
    } else {
      favorites.push(lectureId);
      await AsyncStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
      return true; // favorited
    }
  } catch (error) {
    console.error('Error toggling favorite:', error);
    return false;
  }
};

export const getFavorites = async (): Promise<string[]> => {
  try {
    const data = await AsyncStorage.getItem(FAVORITES_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Error getting favorites:', error);
    return [];
  }
};

export const isFavorite = async (lectureId: string): Promise<boolean> => {
  const favorites = await getFavorites();
  return favorites.includes(lectureId);
};

// Bookmarks
export const addBookmark = async (bookmark: Omit<Bookmark, 'id' | 'createdAt'>): Promise<Bookmark> => {
  try {
    const bookmarks = await getBookmarks();
    const newBookmark: Bookmark = {
      ...bookmark,
      id: `bookmark_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date().toISOString(),
    };

    bookmarks.push(newBookmark);
    await AsyncStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
    return newBookmark;
  } catch (error) {
    console.error('Error adding bookmark:', error);
    throw error;
  }
};

export const getBookmarks = async (lectureId?: string): Promise<Bookmark[]> => {
  try {
    const data = await AsyncStorage.getItem(BOOKMARKS_KEY);
    const allBookmarks: Bookmark[] = data ? JSON.parse(data) : [];

    if (lectureId) {
      return allBookmarks.filter(b => b.lectureId === lectureId);
    }

    return allBookmarks;
  } catch (error) {
    console.error('Error getting bookmarks:', error);
    return [];
  }
};

export const deleteBookmark = async (bookmarkId: string): Promise<void> => {
  try {
    const bookmarks = await getBookmarks();
    const filtered = bookmarks.filter(b => b.id !== bookmarkId);
    await AsyncStorage.setItem(BOOKMARKS_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Error deleting bookmark:', error);
    throw error;
  }
};

export const updateBookmark = async (bookmarkId: string, updates: Partial<Bookmark>): Promise<void> => {
  try {
    const bookmarks = await getBookmarks();
    const index = bookmarks.findIndex(b => b.id === bookmarkId);

    if (index > -1) {
      bookmarks[index] = { ...bookmarks[index], ...updates };
      await AsyncStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
    }
  } catch (error) {
    console.error('Error updating bookmark:', error);
    throw error;
  }
};
