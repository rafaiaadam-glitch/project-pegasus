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
  icon: string;
  description: string;
}

export const LECTURE_MODE_OPTIONS: LectureModeOption[] = [
  {
    id: 'MATHEMATICS',
    title: 'Mathematics / Formal',
    icon: 'sigma',
    description: 'Focuses on what, how, and where with concise formal structure.',
  },
  {
    id: 'NATURAL_SCIENCE',
    title: 'Natural Science',
    icon: 'microscope',
    description: 'Balanced six-face reasoning with mechanism-first emphasis.',
  },
  {
    id: 'SOCIAL_SCIENCE',
    title: 'Social Science',
    icon: 'chart-bar',
    description: 'Highlights agency (who) and mechanism (how) in context.',
  },
  {
    id: 'HUMANITIES',
    title: 'Humanities / Philosophy',
    icon: 'book-open-page-variant',
    description: 'Emphasizes interpretation, people, and meaning (why).',
  },

  {
    id: 'INTERDISCIPLINARY',
    title: 'Interdisciplinary / Mixed Methods',
    icon: 'puzzle-outline',
    description: 'Hybrid weighting: empirical and interpretive perspectives combined.',
  },
  {
    id: 'OPEN',
    title: 'Open / Mixed',
    icon: 'brain',
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
