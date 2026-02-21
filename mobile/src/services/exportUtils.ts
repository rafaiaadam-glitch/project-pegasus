// Export utilities for study materials
import { Platform } from 'react-native';

// Conditionally import native modules (only available on iOS/Android)
let FileSystem: any = null;
let Sharing: any = null;

try {
  if (Platform.OS !== 'web') {
    const fs = require('expo-file-system/legacy');
    FileSystem = {
      ...fs,
      EncodingType: fs.EncodingType || { UTF8: 'utf8' },
      documentDirectory: fs.documentDirectory,
      writeAsStringAsync: fs.writeAsStringAsync,
    };
    Sharing = require('expo-sharing');
  }
} catch (error) {
  console.warn('Native modules not available - exports disabled');
}

export interface ExportOptions {
  format: 'markdown' | 'pdf' | 'anki-csv';
  lectureTitle: string;
  courseTitle?: string;
}

// Export Summary as Markdown
export const exportSummaryAsMarkdown = (summary: any, options: ExportOptions): string => {
  let markdown = `# ${options.lectureTitle}\n\n`;

  if (options.courseTitle) {
    markdown += `**Course:** ${options.courseTitle}\n\n`;
  }

  markdown += `## Summary\n\n${summary.overview}\n\n`;

  if (summary.sections) {
    summary.sections.forEach((section: any) => {
      markdown += `### ${section.title}\n\n`;
      if (section.bullets) {
        section.bullets.forEach((bullet: string) => {
          markdown += `- ${bullet}\n`;
        });
      }
      markdown += '\n';
    });
  }

  markdown += `\n---\n*Generated with Pegasus Lecture Copilot*\n`;

  return markdown;
};

// Export Outline as Markdown
export const exportOutlineAsMarkdown = (outline: any, options: ExportOptions): string => {
  let markdown = `# ${options.lectureTitle} - Outline\n\n`;

  const nodes = outline.outline || outline.sections || [];

  const renderNode = (node: any, depth: number) => {
    const indent = '  '.repeat(depth);
    const prefix = depth === 0 ? '##' : '-';
    markdown += depth === 0 ? `${prefix} ${node.title}\n` : `${indent}${prefix} ${node.title}\n`;
    if (node.points) {
      node.points.forEach((point: string) => {
        markdown += `${indent}  - ${point}\n`;
      });
    }
    if (node.children) {
      node.children.forEach((child: any) => renderNode(child, depth + 1));
    }
    if (depth === 0) markdown += '\n';
  };

  nodes.forEach((node: any) => renderNode(node, 0));

  markdown += `---\n*Generated with Pegasus Lecture Copilot*\n`;

  return markdown;
};

// Export Flashcards as Anki CSV
export const exportFlashcardsAsAnkiCSV = (flashcards: any): string => {
  let csv = '';

  if (flashcards.cards) {
    flashcards.cards.forEach((card: any) => {
      // Escape quotes and commas for CSV
      const front = card.front.replace(/"/g, '""');
      const back = card.back.replace(/"/g, '""');
      csv += `"${front}","${back}"\n`;
    });
  }

  return csv;
};

// Export Exam Questions as Markdown
export const exportExamQuestionsAsMarkdown = (
  questions: any,
  options: ExportOptions
): string => {
  let markdown = `# ${options.lectureTitle} - Practice Questions\n\n`;

  if (questions.questions) {
    questions.questions.forEach((q: any, idx: number) => {
      markdown += `## Question ${idx + 1}\n\n`;
      markdown += `**Type:** ${q.type || 'Question'}\n\n`;

      if (q.points) {
        markdown += `**Points:** ${q.points}\n\n`;
      }

      markdown += `${q.question}\n\n`;

      if (q.type === 'multiple-choice' && q.options) {
        q.options.forEach((option: string, optIdx: number) => {
          const letter = String.fromCharCode(65 + optIdx);
          markdown += `${letter}) ${option}\n`;
        });
        markdown += '\n';

        if (q.correctAnswer) {
          markdown += `**Answer:** ${q.correctAnswer}\n\n`;
        }
      }

      markdown += '---\n\n';
    });
  }

  markdown += `\n*Generated with Pegasus Lecture Copilot*\n`;

  return markdown;
};

// Export All Artifacts as Markdown
export const exportAllArtifactsAsMarkdown = (
  artifacts: any,
  options: ExportOptions
): string => {
  let markdown = `# ${options.lectureTitle}\n\n`;

  if (options.courseTitle) {
    markdown += `**Course:** ${options.courseTitle}\n\n`;
  }

  markdown += `**Generated:** ${new Date().toLocaleDateString()}\n\n`;
  markdown += `---\n\n`;

  // Summary
  if (artifacts.summary) {
    markdown += exportSummaryAsMarkdown(artifacts.summary, options);
    markdown += `\n---\n\n`;
  }

  // Outline
  if (artifacts.outline) {
    markdown += exportOutlineAsMarkdown(artifacts.outline, options);
    markdown += `\n---\n\n`;
  }

  // Key Terms
  if (artifacts['key-terms']?.terms) {
    markdown += `## Key Terms\n\n`;
    artifacts['key-terms'].terms.forEach((term: any) => {
      markdown += `### ${term.term}\n\n${term.definition}\n\n`;
    });
    markdown += `---\n\n`;
  }

  // Exam Questions
  if (artifacts['exam-questions']) {
    markdown += exportExamQuestionsAsMarkdown(artifacts['exam-questions'], options);
  }

  return markdown;
};

// Web fallback: download via Blob + anchor click
const downloadViaBlob = (content: string, filename: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

// Save and Share File
export const saveAndShareFile = async (
  content: string,
  filename: string,
  mimeType: string = 'text/plain'
): Promise<void> => {
  // Web platform: use blob download
  if (Platform.OS === 'web') {
    downloadViaBlob(content, filename, mimeType);
    return;
  }

  try {
    const fileUri = `${FileSystem.documentDirectory}${filename}`;

    // Write file
    await FileSystem.writeAsStringAsync(fileUri, content, {
      encoding: FileSystem.EncodingType.UTF8,
    });

    // Check if sharing is available
    const canShare = await Sharing.isAvailableAsync();

    if (canShare) {
      await Sharing.shareAsync(fileUri, {
        mimeType,
        dialogTitle: `Export ${filename}`,
        UTI: mimeType,
      });
    } else {
      throw new Error('Sharing is not available on this device');
    }
  } catch (error) {
    console.error('Error saving/sharing file:', error);
    throw error;
  }
};

// Export Handlers
export const exportSummary = async (
  summary: any,
  lectureTitle: string,
  courseTitle?: string
) => {
  const markdown = exportSummaryAsMarkdown(summary, {
    format: 'markdown',
    lectureTitle,
    courseTitle,
  });

  const filename = `${lectureTitle.replace(/[^a-z0-9]/gi, '_')}_summary.md`;
  await saveAndShareFile(markdown, filename, 'text/markdown');
};

export const exportFlashcards = async (flashcards: any, lectureTitle: string) => {
  const csv = exportFlashcardsAsAnkiCSV(flashcards);
  const filename = `${lectureTitle.replace(/[^a-z0-9]/gi, '_')}_flashcards.csv`;
  await saveAndShareFile(csv, filename, 'text/csv');
};

export const exportExamQuestions = async (
  questions: any,
  lectureTitle: string,
  courseTitle?: string
) => {
  const markdown = exportExamQuestionsAsMarkdown(questions, {
    format: 'markdown',
    lectureTitle,
    courseTitle,
  });

  const filename = `${lectureTitle.replace(/[^a-z0-9]/gi, '_')}_questions.md`;
  await saveAndShareFile(markdown, filename, 'text/markdown');
};

export const exportAllArtifacts = async (
  artifacts: any,
  lectureTitle: string,
  courseTitle?: string
) => {
  const markdown = exportAllArtifactsAsMarkdown(artifacts, {
    format: 'markdown',
    lectureTitle,
    courseTitle,
  });

  const filename = `${lectureTitle.replace(/[^a-z0-9]/gi, '_')}_complete.md`;
  await saveAndShareFile(markdown, filename, 'text/markdown');
};
