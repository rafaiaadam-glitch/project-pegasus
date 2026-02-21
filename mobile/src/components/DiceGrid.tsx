import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export type DiceFace = 'RED' | 'ORANGE' | 'YELLOW' | 'GREEN' | 'BLUE' | 'PURPLE';

interface DiceGridProps {
  schedule: DiceFace[][];
  activeIndex: number;
  scores: Record<DiceFace, number>;
  collapsed?: boolean;
  equilibrium?: boolean;
}

const FACE_COLORS: Record<DiceFace, string> = {
  RED: '#FF3B30',
  ORANGE: '#FF9500',
  YELLOW: '#FFCC00',
  GREEN: '#34C759',
  BLUE: '#007AFF',
  PURPLE: '#AF52DE',
};

const FACE_LABELS: Record<DiceFace, string> = {
  RED: 'How',
  ORANGE: 'What',
  YELLOW: 'When',
  GREEN: 'Where',
  BLUE: 'Who',
  PURPLE: 'Why',
};

export const DiceGrid: React.FC<DiceGridProps> = ({
  schedule,
  activeIndex,
  scores,
  collapsed = false,
  equilibrium = false,
}) => {
  return (
    <View
      style={[
        styles.container,
        collapsed && styles.containerCollapsed,
        equilibrium && styles.containerEquilibrium,
      ]}
    >
      <View style={styles.grid}>
        {schedule.map((row, rowIndex) => (
          <View
            key={rowIndex}
            style={[
              styles.row,
              rowIndex === activeIndex && styles.rowActive,
            ]}
          >
            {row.map((face, colIndex) => (
              <View
                key={colIndex}
                style={[
                  styles.dot,
                  {
                    backgroundColor: FACE_COLORS[face],
                    opacity: scores[face] || 0.3, // Opacity = confidence
                  },
                ]}
              />
            ))}
          </View>
        ))}
      </View>

      {/* Optional: Facet strength bars */}
      <View style={styles.legend}>
        {Object.entries(FACE_LABELS).map(([face, label]) => {
          const score = scores[face as DiceFace] || 0;
          const percentage = Math.round(score * 100);

          return (
            <View key={face} style={styles.legendRow}>
              <View
                style={[
                  styles.legendDot,
                  { backgroundColor: FACE_COLORS[face as DiceFace] },
                ]}
              />
              <Text style={styles.legendLabel}>{label}</Text>
              <View style={styles.legendBar}>
                <View
                  style={[
                    styles.legendBarFill,
                    {
                      width: `${percentage}%`,
                      backgroundColor: FACE_COLORS[face as DiceFace],
                    },
                  ]}
                />
              </View>
              <Text style={styles.legendValue}>{percentage}%</Text>
            </View>
          );
        })}
      </View>

      {/* Status indicator */}
      {collapsed && (
        <View style={styles.statusBadge}>
          <Text style={styles.statusText}>⚠️ Collapsed</Text>
        </View>
      )}
      {equilibrium && (
        <View style={[styles.statusBadge, styles.statusBadgeEquilibrium]}>
          <Text style={styles.statusText}>✅ Equilibrium</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  containerCollapsed: {
    borderColor: '#FF3B30',
    borderWidth: 2,
  },
  containerEquilibrium: {
    shadowColor: '#fff',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 4,
  },
  grid: {
    flexDirection: 'column',
    gap: 6,
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row' as const,
    gap: 6,
    opacity: 0.4,
  },
  rowActive: {
    opacity: 1,
    transform: [{ scale: 1.05 }],
  },
  dot: {
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  legend: {
    gap: 8,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendLabel: {
    fontSize: 12,
    fontWeight: '600',
    width: 50,
    color: '#333',
  },
  legendBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#f0f0f0',
    borderRadius: 3,
    overflow: 'hidden',
  },
  legendBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  legendValue: {
    fontSize: 11,
    color: '#666',
    width: 35,
    textAlign: 'right',
  },
  statusBadge: {
    marginTop: 12,
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: '#FF3B30',
    borderRadius: 8,
    alignItems: 'center',
  },
  statusBadgeEquilibrium: {
    backgroundColor: '#34C759',
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
});
