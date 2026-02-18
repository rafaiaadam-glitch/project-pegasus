import AsyncStorage from '@react-native-async-storage/async-storage';

const NOTES_KEY = 'pegasus_notes';

export interface Note {
  id: string;
  lectureId: string;
  content: string;
  timestamp?: number; // Audio timestamp in seconds
  createdAt: string;
  updatedAt: string;
}

export const getNotes = async (lectureId: string): Promise<Note[]> => {
  try {
    const data = await AsyncStorage.getItem(NOTES_KEY);
    const allNotes: Note[] = data ? JSON.parse(data) : [];
    return allNotes.filter(note => note.lectureId === lectureId);
  } catch (error) {
    console.error('Error getting notes:', error);
    return [];
  }
};

export const addNote = async (
  lectureId: string,
  content: string,
  timestamp?: number
): Promise<Note> => {
  try {
    const allNotes = await getAllNotes();
    const newNote: Note = {
      id: `note_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      lectureId,
      content,
      timestamp,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    allNotes.push(newNote);
    await AsyncStorage.setItem(NOTES_KEY, JSON.stringify(allNotes));
    return newNote;
  } catch (error) {
    console.error('Error adding note:', error);
    throw error;
  }
};

export const updateNote = async (noteId: string, content: string): Promise<void> => {
  try {
    const allNotes = await getAllNotes();
    const index = allNotes.findIndex(n => n.id === noteId);

    if (index > -1) {
      allNotes[index].content = content;
      allNotes[index].updatedAt = new Date().toISOString();
      await AsyncStorage.setItem(NOTES_KEY, JSON.stringify(allNotes));
    }
  } catch (error) {
    console.error('Error updating note:', error);
    throw error;
  }
};

export const deleteNote = async (noteId: string): Promise<void> => {
  try {
    const allNotes = await getAllNotes();
    const filtered = allNotes.filter(n => n.id !== noteId);
    await AsyncStorage.setItem(NOTES_KEY, JSON.stringify(filtered));
  } catch (error) {
    console.error('Error deleting note:', error);
    throw error;
  }
};

const getAllNotes = async (): Promise<Note[]> => {
  try {
    const data = await AsyncStorage.getItem(NOTES_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Error getting all notes:', error);
    return [];
  }
};
