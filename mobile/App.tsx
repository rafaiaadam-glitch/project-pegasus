import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  BlurView, // Requires expo-blur
} from 'react-native';

export default function App() {
  const [activeTab, setActiveTab] = useState<'Transcript' | 'Artifacts'>('Artifacts');
  const [preset, setPreset] = useState('Exam');

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />

      {/* 1. APPLE-STYLE NAV BAR */}
      <View style={styles.navBar}>
        <Text style={styles.navTitle}>Neural Signaling</Text>
        <Text style={styles.navSubtitle}>Bio 101 • Lec 04</Text>
      </View>

      {/* 2. CRISP TAB SWITCHER */}
      <View style={styles.tabContainer}>
        <View style={styles.segmentBackground}>
          <TouchableOpacity 
            style={[styles.segment, activeTab === 'Artifacts' && styles.segmentActive]}
            onPress={() => setActiveTab('Artifacts')}
          >
            <Text style={[styles.segmentText, activeTab === 'Artifacts' && styles.segmentTextActive]}>Study Guide</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.segment, activeTab === 'Transcript' && styles.segmentActive]}
            onPress={() => setActiveTab('Transcript')}
          >
            <Text style={[styles.segmentText, activeTab === 'Transcript' && styles.segmentTextActive]}>Transcript</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.scrollArea} showsVerticalScrollIndicator={false}>
        
        {/* 3. PRESET SWITCHER (Material Structure Change) */}
        <View style={styles.presetContainer}>
          <Text style={styles.label}>Style Preset</Text>
          <View style={styles.presetRow}>
            {['Exam', 'ADHD', 'Research'].map((p) => (
              <TouchableOpacity 
                key={p} 
                style={[styles.pBadge, preset === p && styles.pBadgeActive]}
                onPress={() => setPreset(p)}
              >
                <Text style={[styles.pBadgeText, preset === p && styles.pBadgeTextActive]}>{p}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* 4. CONTENT CARDS (High Whitespace) */}
        <View style={styles.card}>
          <Text style={styles.cardTag}>SUMMARY</Text>
          <Text style={styles.cardTitle}>The Sodium-Potassium Pump</Text>
          <Text style={styles.cardBody}>
            Crucial for maintaining resting potential. It moves 3 sodium ions out for every 2 potassium ions in, creating an electrical gradient.
          </Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTag}>🧵 THREAD EVOLUTION</Text>
          <Text style={styles.cardTitle}>Action Potential</Text>
          <Text style={styles.cardBody}>
            Concept introduced in Lec 01. Today: Refined with Saltatory Conduction details.
          </Text>
          <TouchableOpacity>
            <Text style={styles.linkText}>See Growth History →</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>

      {/* 5. MINIMALIST RECORD BUTTON (Floating Action) */}
      <View style={styles.footer}>
        <TouchableOpacity style={styles.recordButton}>
          <View style={styles.recordInner} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' }, // Apple White
  navBar: { padding: 20, alignItems: 'center', borderBottomWidth: 0.5, borderColor: '#E5E5E5' },
  navTitle: { fontSize: 17, fontWeight: '600', color: '#000' },
  navSubtitle: { fontSize: 13, color: '#8E8E93', marginTop: 2 },
  tabContainer: { padding: 16, backgroundColor: '#F2F2F7' },
  segmentBackground: { flexDirection: 'row', backgroundColor: '#E3E3E8', borderRadius: 8, padding: 2 },
  segment: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  segmentActive: { backgroundColor: '#FFF', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  segmentText: { fontSize: 13, color: '#8E8E93', fontWeight: '500' },
  segmentTextActive: { color: '#000', fontWeight: '600' },
  scrollArea: { flex: 1, padding: 20 },
  presetContainer: { marginBottom: 30 },
  label: { fontSize: 12, fontWeight: '600', color: '#8E8E93', textTransform: 'uppercase', marginBottom: 12 },
  presetRow: { flexDirection: 'row', gap: 10 },
  pBadge: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, backgroundColor: '#F2F2F7' },
  pBadgeActive: { backgroundColor: '#007AFF' },
  pBadgeText: { fontSize: 14, color: '#007AFF', fontWeight: '500' },
  pBadgeTextActive: { color: '#FFF' },
  card: { backgroundColor: '#FFF', padding: 20, borderRadius: 16, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2, borderOrigin: '1px solid #F2F2F7' },
  cardTag: { fontSize: 10, fontWeight: '700', color: '#007AFF', letterSpacing: 1, marginBottom: 8 },
  cardTitle: { fontSize: 20, fontWeight: '700', color: '#000', marginBottom: 10 },
  cardBody: { fontSize: 16, lineHeight: 24, color: '#3A3A3C' },
  linkText: { color: '#007AFF', fontWeight: '600', marginTop: 15 },
  footer: { position: 'absolute', bottom: 40, width: '100%', alignItems: 'center' },
  recordButton: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#FFF', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 15, elevation: 5 },
  recordInner: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#FF3B30' }, // Apple Red
});
