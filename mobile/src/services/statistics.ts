import AsyncStorage from '@react-native-async-storage/async-storage';

const STATS_KEY = 'pegasus_statistics';

export interface StudySession {
  id: string;
  lectureId: string;
  type: 'flashcards' | 'exam' | 'review';
  startTime: string;
  endTime: string;
  durationSeconds: number;
  cardsReviewed?: number;
  correctAnswers?: number;
  incorrectAnswers?: number;
  score?: number;
}

export interface FlashcardStats {
  cardId: string;
  lectureId: string;
  timesReviewed: number;
  timesCorrect: number;
  timesIncorrect: number;
  lastReviewed: string;
  nextReview?: string;
  easeFactor: number; // For spaced repetition
  interval: number; // Days until next review
}

export interface Statistics {
  totalStudyTime: number; // seconds
  totalSessions: number;
  totalFlashcardsReviewed: number;
  totalExamsTaken: number;
  averageScore: number;
  sessions: StudySession[];
  flashcardStats: Record<string, FlashcardStats>;
  streakDays: number;
  lastStudyDate: string;
}

// Initialize or get statistics
export const getStatistics = async (): Promise<Statistics> => {
  try {
    const data = await AsyncStorage.getItem(STATS_KEY);
    if (data) {
      return JSON.parse(data);
    }

    const initialStats: Statistics = {
      totalStudyTime: 0,
      totalSessions: 0,
      totalFlashcardsReviewed: 0,
      totalExamsTaken: 0,
      averageScore: 0,
      sessions: [],
      flashcardStats: {},
      streakDays: 0,
      lastStudyDate: '',
    };

    await AsyncStorage.setItem(STATS_KEY, JSON.stringify(initialStats));
    return initialStats;
  } catch (error) {
    console.error('Error getting statistics:', error);
    throw error;
  }
};

// Record a study session
export const recordSession = async (session: Omit<StudySession, 'id'>): Promise<void> => {
  try {
    const stats = await getStatistics();

    const newSession: StudySession = {
      ...session,
      id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    };

    stats.sessions.push(newSession);
    stats.totalSessions++;
    stats.totalStudyTime += session.durationSeconds;

    if (session.type === 'flashcards' && session.cardsReviewed) {
      stats.totalFlashcardsReviewed += session.cardsReviewed;
    }

    if (session.type === 'exam') {
      stats.totalExamsTaken++;
      if (session.score !== undefined) {
        const totalScore = stats.averageScore * (stats.totalExamsTaken - 1) + session.score;
        stats.averageScore = totalScore / stats.totalExamsTaken;
      }
    }

    // Update streak
    const today = new Date().toDateString();
    const lastStudy = stats.lastStudyDate ? new Date(stats.lastStudyDate).toDateString() : '';

    if (lastStudy !== today) {
      const yesterday = new Date(Date.now() - 86400000).toDateString();
      if (lastStudy === yesterday) {
        stats.streakDays++;
      } else if (lastStudy !== today) {
        stats.streakDays = 1;
      }
      stats.lastStudyDate = new Date().toISOString();
    }

    await AsyncStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch (error) {
    console.error('Error recording session:', error);
    throw error;
  }
};

// Record flashcard review
export const recordFlashcardReview = async (
  cardId: string,
  lectureId: string,
  correct: boolean,
  quality: number = 3 // 0-5 scale for SM-2 algorithm
): Promise<void> => {
  try {
    const stats = await getStatistics();

    if (!stats.flashcardStats[cardId]) {
      stats.flashcardStats[cardId] = {
        cardId,
        lectureId,
        timesReviewed: 0,
        timesCorrect: 0,
        timesIncorrect: 0,
        lastReviewed: new Date().toISOString(),
        easeFactor: 2.5,
        interval: 1,
      };
    }

    const cardStats = stats.flashcardStats[cardId];
    cardStats.timesReviewed++;

    if (correct) {
      cardStats.timesCorrect++;
    } else {
      cardStats.timesIncorrect++;
    }

    cardStats.lastReviewed = new Date().toISOString();

    // SM-2 Algorithm for spaced repetition
    if (quality >= 3) {
      if (cardStats.interval === 1) {
        cardStats.interval = 6;
      } else {
        cardStats.interval = Math.round(cardStats.interval * cardStats.easeFactor);
      }

      cardStats.easeFactor = cardStats.easeFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    } else {
      cardStats.interval = 1;
    }

    cardStats.easeFactor = Math.max(1.3, cardStats.easeFactor);

    // Calculate next review date
    const nextReview = new Date();
    nextReview.setDate(nextReview.getDate() + cardStats.interval);
    cardStats.nextReview = nextReview.toISOString();

    await AsyncStorage.setItem(STATS_KEY, JSON.stringify(stats));
  } catch (error) {
    console.error('Error recording flashcard review:', error);
    throw error;
  }
};

// Get cards due for review
export const getDueCards = async (lectureId?: string): Promise<FlashcardStats[]> => {
  try {
    const stats = await getStatistics();
    const now = new Date();

    return Object.values(stats.flashcardStats).filter(card => {
      if (lectureId && card.lectureId !== lectureId) return false;
      if (!card.nextReview) return true; // Never reviewed
      return new Date(card.nextReview) <= now;
    });
  } catch (error) {
    console.error('Error getting due cards:', error);
    return [];
  }
};

// Get study streak
export const getStudyStreak = async (): Promise<number> => {
  try {
    const stats = await getStatistics();
    return stats.streakDays;
  } catch (error) {
    console.error('Error getting streak:', error);
    return 0;
  }
};

// Get sessions by date range
export const getSessionsByDateRange = async (
  startDate: Date,
  endDate: Date
): Promise<StudySession[]> => {
  try {
    const stats = await getStatistics();
    return stats.sessions.filter(session => {
      const sessionDate = new Date(session.startTime);
      return sessionDate >= startDate && sessionDate <= endDate;
    });
  } catch (error) {
    console.error('Error getting sessions:', error);
    return [];
  }
};

// Reset all statistics
export const resetStatistics = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem(STATS_KEY);
  } catch (error) {
    console.error('Error resetting statistics:', error);
    throw error;
  }
};
