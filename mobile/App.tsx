import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Dimensions,
} from 'react-native';

const { width } = Dimensions.get('window');

// --- Types for our State Management ---
type TabType = 'Transcript' | 'Takeaways';
type PresetType = 'Exam' | 'Neurodivergent';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('Takeaways');
  const [preset, setPreset] = useState<PresetType>('Exam');

  // --- Mock Data: This would eventually come from your FastAPI Backend ---
  const lectureData = {
    title: "Lec 04: Neural Signaling",
    course: "Introduction to Neuroscience",
    transcript: [
      { time: "0:00", text: "Today we're diving into the action potential." },
      { time: "0:12", text: "It's essentially the electrical impulse that travels down an axon, allowing neurons to communicate." },
      { time: "0:45", text: "The key is the sodium-potassium pump, which maintains the resting potential at -70mV." },
    ],
    artifacts: {
      exam: {
        summary: "High-density recall focus. Focus on ionic gradients and threshold potentials.",
        bullets: [
          "Sodium/Potassium Pump: 3 Na+ out, 2 K+ in (Likely Exam Question).",
          "Threshold of Excitation: -55mV required to trigger firing.",
          "Saltatory Conduction: Occurs in Myelinated axons via Nodes of Ranvier."
        ]
      },
      neuro: {
        summary: "Simple analogies and low-clutter summary to reduce cognitive load.",
        bullets: [
          "The 'Flush' Rule: A neuron fires all-the-way or not at all.",
          "Insulation: Myelin is like the plastic on a wire—it keeps the signal fast.",
          "The Spark: Sodium rushing in is what starts the message."
        ]
      }
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* 1. HEADER SECTION (Course Info) */}
      <View style={styles.header}>
        <View>
          <Text style={styles.courseSubtitle}>{lectureData.course}</Text>
          <Text style={styles.lectureTitle}>{lectureData.title}</Text>
        </View>
        <TouchableOpacity style={styles.moreButton}>
          <Text style={styles.moreIcon}>•••</Text>
        </TouchableOpacity>
      </View>

      {/* 2. TAB SWITCHER (Otter Pattern) */}
      <View style={styles.tabContainer}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'Transcript' && styles.activeTab]} 
          onPress={() => setActiveTab('Transcript')}
        >
          <Text style={activeTab === 'Transcript' ? styles.activeTabText : styles.tabText}>Transcript</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'Takeaways' && styles.activeTab]} 
          onPress={() => setActiveTab('Takeaways')}
        >
          <Text style={activeTab === 'Takeaways' ? styles.activeTabText : styles.tabText}>Takeaways</Text>
        </TouchableOpacity>
      </View>

      {/* 3. MAIN CONTENT AREA */}
      <ScrollView style={styles.scrollArea} contentContainerStyle={styles.scrollContent}>
        
        {activeTab === 'Transcript' ? (
          /* TRANSCRIPT VIEW */
          <View style={styles.transcriptList}>
            {lectureData.transcript.map((item, index) => (
              <View key={index} style={styles.transcriptRow}>
                <Text style={styles.timestamp}>{item.time}</Text>
                <View style={styles.textBubble}>
                  <Text style={styles.transcriptText}>{item.text}</Text>
                </View>
              </View>
            ))}
          </View>
        ) : (
          /* TAKEAWAYS VIEW (Materially changes based on Preset) */
          <View>
            {/* PRESET TOGGLE: The Core Differentiator */}
            <View style={styles.presetPicker}>
              <Text style={styles.pickerLabel}>Learning Style Preset:</Text>
              <View style={styles.toggleRow}>
                <TouchableOpacity 
                  style={[styles.toggleBtn, preset === 'Exam' && styles.toggleBtnActive]}
                  onPress={() => setPreset('Exam')}
                >
                  <Text style={[styles.toggleBtnText, preset === 'Exam' && styles.toggleBtnTextActive]}>Exam Mode</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={[styles.toggleBtn, preset === 'Neurodivergent' && styles.toggleBtnActive]}
                  onPress={() => setPreset('Neurodivergent')}
                >
                  <Text style={[styles.toggleBtnText, preset === 'Neurodivergent' && styles.toggleBtnTextActive]}>Simple (ADHD)</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* ARTIFACT CARDS */}
            <View style={styles.card}>
              <Text style={styles.cardHeader}>Overview</Text>
              <Text style={styles.cardBody}>
                {preset === 'Exam' ? lectureData.artifacts.exam.summary : lectureData.artifacts.neuro.summary}
              </Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardHeader}>
                {preset === 'Exam' ? "Examinable Points" : "Key Takeaways"}
              </Text>
              {(preset === 'Exam' ? lectureData.artifacts.exam.bullets : lectureData.artifacts.neuro.bullets).map((bullet, i) => (
                <Text key={i} style={styles.bulletPoint}>• {bullet}</Text>
              ))}
            </View>

            {/* THREAD ENGINE PREVIEW */}
            <View style={[styles.card, styles.threadCard]}>
              <Text style={styles.threadHeader}>🧵 Thread Evolution</Text>
              <Text style={styles.threadText}>
                "Action Potential" was refined in this lecture. 
                <Text style={styles.linkText}> View History →</Text>
              </Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* 4. PERSISTENT FLOATING RECORD BUTTON (Otter Identity) */}
      <TouchableOpacity style={styles.fab} activeOpacity={0.8}>
        <Text style={styles.fabIcon}>🎙️</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F4F7', // Otter grey-blue background
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: '#FFF',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderColor: '#E4E7EB',
  },
  courseSubtitle: {
    fontSize: 12,
    color: '#667085',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  lectureTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#101828',
    marginTop: 2,
  },
  moreButton: {
    padding: 8,
  },
  moreIcon: {
    fontSize: 18,
    color: '#98A2B3',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderColor: '#E4E7EB',
  },
  tab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: 'center',
    borderBottomWidth: 3,
    borderColor: 'transparent',
  },
  activeTab: {
    borderColor: '#007AFF', // Pegasus Primary Blue
  },
  tabText: {
    fontSize: 15,
    color: '#667085',
    fontWeight: '500',
  },
  activeTabText: {
    fontSize: 15,
    color: '#007AFF',
    fontWeight: '700',
  },
  scrollArea: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100, // Space for FAB
  },
  /* Transcript Styles */
  transcriptList: {
    marginTop: 10,
  },
  transcriptRow: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  timestamp: {
    width: 40,
    fontSize: 12,
    color: '#98A2B3',
    paddingTop: 4,
  },
  textBubble: {
    flex: 1,
    paddingLeft: 10,
  },
  transcriptText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#344054',
  },
  /* Takeaway Styles */
  presetPicker: {
    backgroundColor: '#FFF',
    padding: 12,
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#D0D5DD',
  },
  pickerLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#475467',
    marginBottom: 10,
  },
  toggleRow: {
    flexDirection: 'row',
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 4,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 6,
  },
  toggleBtnActive: {
    backgroundColor: '#FFF',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  toggleBtnText: {
    fontSize: 14,
    color: '#667085',
    fontWeight: '500',
  },
  toggleBtnTextActive: {
    color: '#101828',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E4E7EB',
  },
  cardHeader: {
    fontSize: 16,
    fontWeight: '700',
    color: '#101828',
    marginBottom: 8,
  },
  cardBody: {
    fontSize: 15,
    lineHeight: 22,
    color: '#475467',
  },
  bulletPoint: {
    fontSize: 15,
    lineHeight: 24,
    color: '#344054',
    marginBottom: 6,
  },
  threadCard: {
    backgroundColor: '#F5F9FF',
    borderColor: '#B2CCFF',
  },
  threadHeader: {
    fontSize: 15,
    fontWeight: '700',
    color: '#2E90FA',
  },
  threadText: {
    marginTop: 4,
    fontSize: 14,
    color: '#475467',
  },
  linkText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  /* FAB */
  fab: {
    position: 'absolute',
    bottom: 30,
    left: width / 2 - 32, // Centered like Otter
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#007AFF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
  },
  fabIcon: {
    fontSize: 28,
  },
});
