export type LectureMode =
  | 'MATHEMATICS'
  | 'NATURAL_SCIENCE'
  | 'SOCIAL_SCIENCE'
  | 'HUMANITIES'
  | 'INTERDISCIPLINARY'
  | 'OPEN';

export interface LectureModeOption {
  id: LectureMode;
  title: string;
  emoji: string;
  description: string;
}

export const LECTURE_MODE_OPTIONS: LectureModeOption[] = [
  {
    id: 'MATHEMATICS',
    title: 'Mathematics / Formal',
    emoji: '🧮',
    description: 'Focuses on what, how, and where with concise formal structure.',
  },
  {
    id: 'NATURAL_SCIENCE',
    title: 'Natural Science',
    emoji: '🔬',
    description: 'Balanced six-face reasoning with mechanism-first emphasis.',
  },
  {
    id: 'SOCIAL_SCIENCE',
    title: 'Social Science',
    emoji: '📊',
    description: 'Highlights agency (who) and mechanism (how) in context.',
  },
  {
    id: 'HUMANITIES',
    title: 'Humanities / Philosophy',
    emoji: '📚',
    description: 'Emphasizes interpretation, people, and meaning (why).',
  },

  {
    id: 'INTERDISCIPLINARY',
    title: 'Interdisciplinary / Mixed Methods',
    emoji: '🧩',
    description: 'Hybrid weighting: empirical and interpretive perspectives combined.',
  },
  {
    id: 'OPEN',
    title: 'Open / Mixed',
    emoji: '🧠',
    description: 'Equal weighting across all six reasoning dimensions.',
  },
];

export const LECTURE_MODE_META: Record<LectureMode, LectureModeOption> =
  LECTURE_MODE_OPTIONS.reduce(
    (acc, option) => {
      acc[option.id] = option;
      return acc;
    },
    {} as Record<LectureMode, LectureModeOption>
  );

export function getLectureModeTitle(mode: LectureMode): string {
  return LECTURE_MODE_META[mode]?.title ?? 'Open / Mixed';
}
