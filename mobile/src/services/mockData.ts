// Mock Data for Demo/Testing
import { Course, Lecture, Preset, LectureProgress } from '../types';

export const mockCourses: Course[] = [
  {
    id: 'course-bio-101',
    title: 'Biology 101: Cellular Biology',
    description: 'Introduction to cell structure, function, and molecular processes',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-02-10T14:30:00Z',
  },
  {
    id: 'course-cs-201',
    title: 'Computer Science 201: Data Structures',
    description: 'Advanced algorithms and data structure implementations',
    created_at: '2024-01-20T09:00:00Z',
    updated_at: '2024-02-11T11:00:00Z',
  },
  {
    id: 'course-phys-150',
    title: 'Physics 150: Mechanics',
    description: 'Classical mechanics, motion, forces, and energy',
    created_at: '2024-02-01T08:30:00Z',
    updated_at: '2024-02-11T16:00:00Z',
  },
];

export const mockLectures: Record<string, Lecture[]> = {
  'course-bio-101': [
    {
      id: 'lecture-001',
      course_id: 'course-bio-101',
      title: 'Neural Signaling & Action Potentials',
      preset_id: 'exam-mode',
      status: 'generated',
      duration_sec: 3420,
      created_at: '2024-02-10T10:00:00Z',
    },
    {
      id: 'lecture-002',
      course_id: 'course-bio-101',
      title: 'Cell Membrane Structure',
      preset_id: 'beginner-mode',
      status: 'generated',
      duration_sec: 2880,
      created_at: '2024-02-08T14:00:00Z',
    },
    {
      id: 'lecture-003',
      course_id: 'course-bio-101',
      title: 'Mitochondria & Energy Production',
      preset_id: 'exam-mode',
      status: 'processing',
      duration_sec: 3120,
      created_at: '2024-02-11T09:00:00Z',
    },
  ],
  'course-cs-201': [
    {
      id: 'lecture-101',
      course_id: 'course-cs-201',
      title: 'Binary Search Trees',
      preset_id: 'exam-mode',
      status: 'generated',
      duration_sec: 3600,
      created_at: '2024-02-09T13:00:00Z',
    },
    {
      id: 'lecture-102',
      course_id: 'course-cs-201',
      title: 'Hash Tables & Collision Resolution',
      preset_id: 'research-mode',
      status: 'uploaded',
      duration_sec: 3300,
      created_at: '2024-02-11T10:30:00Z',
    },
  ],
  'course-phys-150': [
    {
      id: 'lecture-201',
      course_id: 'course-phys-150',
      title: "Newton's Laws of Motion",
      preset_id: 'beginner-mode',
      status: 'generated',
      duration_sec: 2700,
      created_at: '2024-02-10T11:00:00Z',
    },
  ],
};

export const mockPresets: Preset[] = [
  {
    id: 'exam-mode',
    name: 'Exam Mode',
    kind: 'exam',
    description: 'Definitions, examinable points, and practice questions',
    outputProfile: {},
  },
  {
    id: 'beginner-mode',
    name: 'Beginner',
    kind: 'beginner',
    description: 'Plain language explanations with analogies',
    outputProfile: {},
  },
  {
    id: 'research-mode',
    name: 'Research',
    kind: 'research',
    description: 'Claims, arguments, and evidence placeholders',
    outputProfile: {},
  },
  {
    id: 'concept-map-mode',
    name: 'Concept Map',
    kind: 'concept-map',
    description: 'Hierarchies and conceptual relationships',
    outputProfile: {},
  },
  {
    id: 'neurodivergent-friendly-mode',
    name: 'ADHD-Friendly',
    kind: 'neurodivergent-friendly',
    description: 'Short chunks, minimal clutter, clear structure',
    outputProfile: {},
  },
];

export const mockArtifacts: Record<string, any> = {
  'lecture-001': {
    lectureId: 'lecture-001',
    artifacts: {
      summary: {
        id: 'summary-001',
        overview: 'Comprehensive exploration of neural signaling mechanisms, focusing on the sodium-potassium pump, action potential generation, and saltatory conduction in myelinated neurons.',
        sections: [
          {
            title: 'The Sodium-Potassium Pump',
            bullets: [
              'Maintains resting membrane potential by moving 3 Na+ out for every 2 K+ in',
              'Requires ATP energy to function against concentration gradients',
              'Creates electrical gradient essential for neural signaling',
            ],
          },
          {
            title: 'Action Potential Mechanism',
            bullets: [
              'All-or-nothing electrical signal propagated along axon',
              'Voltage-gated sodium channels open at threshold (-55mV)',
              'Rapid depolarization followed by repolarization and hyperpolarization',
            ],
          },
          {
            title: 'Saltatory Conduction',
            bullets: [
              'Action potential "jumps" between Nodes of Ranvier in myelinated axons',
              'Myelin sheath insulates axon, dramatically increasing conduction speed',
              'Energy-efficient compared to continuous propagation',
            ],
          },
        ],
      },
      outline: {
        id: 'outline-001',
        sections: [
          { title: 'I. Neural Signaling Fundamentals', level: 1 },
          { title: 'A. Resting Membrane Potential', level: 2 },
          { title: 'B. Ion Distribution', level: 2 },
          { title: 'II. Action Potential Generation', level: 1 },
          { title: 'A. Threshold Stimulation', level: 2 },
          { title: 'B. Depolarization Phase', level: 2 },
          { title: 'C. Repolarization', level: 2 },
          { title: 'III. Signal Propagation', level: 1 },
          { title: 'A. Saltatory Conduction', level: 2 },
          { title: 'B. Myelin Sheath Function', level: 2 },
        ],
      },
      flashcards: {
        id: 'flashcards-001',
        cards: [
          {
            front: 'What is the ratio of ions moved by the sodium-potassium pump?',
            back: '3 sodium ions OUT for every 2 potassium ions IN',
          },
          {
            front: 'What is the threshold voltage for action potential initiation?',
            back: 'Approximately -55mV',
          },
          {
            front: 'Define saltatory conduction',
            back: 'The "jumping" of action potentials between Nodes of Ranvier in myelinated neurons, allowing faster signal propagation',
          },
          {
            front: 'What is the resting membrane potential of a typical neuron?',
            back: 'Approximately -70mV',
          },
        ],
      },
      'exam-questions': {
        id: 'exam-001',
        questions: [
          {
            question: 'Explain how the sodium-potassium pump maintains resting membrane potential.',
            type: 'short-answer',
            points: 5,
          },
          {
            question: 'Compare and contrast continuous conduction vs. saltatory conduction. Which is more energy-efficient and why?',
            type: 'essay',
            points: 10,
          },
          {
            question: 'During the action potential, voltage-gated sodium channels open at: A) -70mV, B) -55mV, C) 0mV, D) +30mV',
            type: 'multiple-choice',
            correctAnswer: 'B',
          },
        ],
      },
      threads: [
        {
          id: 'thread-001',
          courseId: 'course-bio-101',
          title: 'Action Potential',
          summary: 'Electrical signal propagation in neurons',
          status: 'foundational',
          complexityLevel: 2,
          lectureRefs: ['lecture-001', 'lecture-002'],
        },
        {
          id: 'thread-002',
          courseId: 'course-bio-101',
          title: 'Myelin Sheath',
          summary: 'Insulating layer enabling saltatory conduction',
          status: 'advanced',
          complexityLevel: 3,
          lectureRefs: ['lecture-001'],
        },
      ],
    },
  },
};

export const mockProgress: Record<string, LectureProgress> = {
  'lecture-001': {
    lectureId: 'lecture-001',
    lectureStatus: 'generated',
    overallStatus: 'completed',
    stageCount: 3,
    completedStageCount: 3,
    progressPercent: 100,
    currentStage: undefined,
    hasFailedStage: false,
    stages: {
      transcription: {
        status: 'completed',
      },
      generation: {
        status: 'completed',
      },
      export: {
        status: 'completed',
      },
    },
    links: {
      summary: '/lectures/lecture-001/summary',
      progress: '/lectures/lecture-001/progress',
      artifacts: '/lectures/lecture-001/artifacts',
      jobs: '/lectures/lecture-001/jobs',
    },
  },
  'lecture-003': {
    lectureId: 'lecture-003',
    lectureStatus: 'processing',
    overallStatus: 'in_progress',
    stageCount: 3,
    completedStageCount: 2,
    progressPercent: 66,
    currentStage: 'export',
    hasFailedStage: false,
    stages: {
      transcription: {
        status: 'completed',
      },
      generation: {
        status: 'completed',
      },
      export: {
        status: 'processing',
      },
    },
    links: {
      summary: '/lectures/lecture-003/summary',
      progress: '/lectures/lecture-003/progress',
      artifacts: '/lectures/lecture-003/artifacts',
      jobs: '/lectures/lecture-003/jobs',
    },
  },
};

// Helper to get mock data
export const getMockCourses = () => ({ courses: mockCourses });
export const getMockLectures = (courseId: string) => ({
  lectures: mockLectures[courseId] || [],
});
export const getMockPresets = () => ({ presets: mockPresets });
export const getMockArtifacts = (lectureId: string) =>
  mockArtifacts[lectureId] || { lectureId, artifacts: {} };
export const getMockProgress = (lectureId: string) =>
  mockProgress[lectureId] || null;
export const getMockSummary = (lectureId: string) => {
  const artifacts = mockArtifacts[lectureId];
  const progress = mockProgress[lectureId];
  return {
    lecture: mockLectures['course-bio-101']?.find((l) => l.id === lectureId),
    artifactCount: artifacts ? Object.keys(artifacts.artifacts).length : 0,
    ...progress,
  };
};
