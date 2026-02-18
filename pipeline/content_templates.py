#!/usr/bin/env python3
"""Generic content templates for artifact generation, replacing hardcoded neuroscience content."""

from __future__ import annotations

from typing import Any, Dict, List


def get_summary_template(preset_id: str, lecture_id: str) -> Dict[str, Any]:
    """
    Get summary template based on preset.

    Args:
        preset_id: The preset mode (e.g., "beginner-mode", "research-mode")
        lecture_id: Lecture identifier for contextual examples

    Returns:
        Dictionary with overview and sections
    """
    preset = preset_id.lower()

    if preset in {"beginner-mode", "beginner"}:
        return {
            "overview": "Plain-language recap focused on core intuition and examples.",
            "sections": [
                {
                    "title": "Big idea",
                    "bullets": [
                        f"Core concept from {lecture_id}: fundamental principles explained simply.",
                        "Key mechanism: how the main process works in practice.",
                    ],
                },
                {
                    "title": "Why it matters",
                    "bullets": [
                        "Practical applications and real-world relevance.",
                        "Foundation for understanding advanced topics.",
                    ],
                },
            ],
        }
    elif preset in {"neurodivergent-friendly", "neurodivergent-friendly-mode"}:
        return {
            "overview": "Short, low-clutter recap with quick checkpoints.",
            "sections": [
                {
                    "title": "Key checkpoints",
                    "bullets": [
                        "Main concept = simple definition.",
                        "Key process: input → transformation → output.",
                        "Important factor affects result.",
                    ],
                },
                {
                    "title": "Remember",
                    "bullets": [
                        "Essential relationship between components.",
                        "Practice reinforces understanding.",
                    ],
                },
            ],
        }
    elif preset in {"research-mode", "research"}:
        return {
            "overview": "Claim-focused summary with evidence placeholders.",
            "sections": [
                {
                    "title": "Claims",
                    "bullets": [
                        "Primary mechanism depends on specific factors. [evidence]",
                        "Key process increases efficiency. [evidence]",
                    ],
                },
                {
                    "title": "Open questions",
                    "bullets": [
                        "What experimental data best quantifies the main effect?",
                        "How do secondary factors affect system stability?",
                    ],
                },
            ],
        }
    elif preset in {"concept-map-mode", "concept-map"}:
        return {
            "overview": "Relationship-first summary emphasizing connections.",
            "sections": [
                {
                    "title": "Core relationships",
                    "bullets": [
                        "Component A → process B → outcome C.",
                        "Factor X → enhanced process Y → improved result Z.",
                    ],
                },
                {
                    "title": "Cross-lecture hooks",
                    "bullets": [
                        "Current topic links to memory and learning.",
                        "Balance of competing factors ties to system behavior.",
                    ],
                },
            ],
        }
    else:
        return {
            "overview": f"Preset '{preset_id}' summary of lecture {lecture_id}.",
            "sections": [
                {
                    "title": "Core essentials",
                    "bullets": [
                        "Main concept and fundamental mechanisms.",
                        "Key process and driving factors.",
                    ],
                },
                {
                    "title": "Continuity hooks",
                    "bullets": [
                        "Factor X increases efficiency through specific mechanism.",
                        "Repeated application strengthens understanding for later lectures.",
                    ],
                },
            ],
        }


def get_outline_template(preset_id: str) -> Dict[str, Any]:
    """
    Get outline template based on preset.

    Args:
        preset_id: The preset mode

    Returns:
        Dictionary with outline structure
    """
    preset = preset_id.lower()

    if preset in {"concept-map-mode", "concept-map"}:
        return {
            "outline": [
                {
                    "title": "Core concept map",
                    "points": ["Main mechanism", "Key components", "Driving factors"],
                    "children": [
                        {
                            "title": "Efficiency factors",
                            "points": ["Optimization method", "Enhanced process"],
                        },
                        {
                            "title": "Adaptation",
                            "points": ["System strengthening", "Learning preparation"],
                        },
                    ],
                }
            ]
        }
    elif preset in {"exam-mode", "exam"}:
        return {
            "outline": [
                {
                    "title": "Exam essentials",
                    "points": [
                        "Define key terms and baseline state",
                        "Explain primary vs secondary component roles",
                        "Contrast different process types",
                    ],
                },
                {
                    "title": "Common exam angles",
                    "points": [
                        "Explain mechanism A vs mechanism B",
                        "Describe how factor X changes outcome Y",
                    ],
                },
            ]
        }
    else:
        return {
            "outline": [
                {
                    "title": "Main mechanisms",
                    "points": [
                        "Baseline state and threshold",
                        "Primary process via component A",
                        "Secondary process via component B",
                    ],
                },
                {
                    "title": "System transmission",
                    "points": [
                        "Type A vs Type B interactions",
                        "Optimization factor and speed",
                    ],
                    "children": [
                        {
                            "title": "Enhanced vs standard process",
                            "points": [
                                "Enhanced process uses optimization method",
                                "Standard process is slower without optimization",
                            ],
                        }
                    ],
                },
            ]
        }


def get_key_terms_template(preset_id: str, thread_refs: List[str]) -> Dict[str, Any]:
    """
    Get key terms template based on preset.

    Args:
        preset_id: The preset mode
        thread_refs: Thread reference IDs to link terms to

    Returns:
        Dictionary with terms list
    """
    preset = preset_id.lower()

    if preset in {"beginner-mode", "beginner"}:
        terms = [
            {
                "term": "Main concept",
                "definition": "A fundamental principle or mechanism in this topic.",
                "threadRef": thread_refs[0] if thread_refs else None,
            },
            {
                "term": "Key factor",
                "definition": "An important element that affects the process.",
            },
        ]
    elif preset in {"research-mode", "research"}:
        terms = [
            {
                "term": "Primary mechanism",
                "definition": "The main process driving the phenomenon. [evidence]",
                "threadRef": thread_refs[1] if len(thread_refs) > 1 else None,
            },
            {
                "term": "System adaptability",
                "definition": "The capacity for change and optimization. [evidence]",
            },
        ]
    else:
        terms = [
            {
                "term": "Core process",
                "definition": "The fundamental mechanism of the system.",
                "example": "Example: how component A transforms input to output.",
            },
            {
                "term": "Optimization factor",
                "definition": "Element that enhances efficiency or speed.",
                "threadRef": thread_refs[0] if thread_refs else None,
            },
        ]

    return {"terms": terms}


def get_flashcards_template(preset_id: str, thread_refs: List[str]) -> Dict[str, Any]:
    """
    Get flashcards template based on preset.

    Args:
        preset_id: The preset mode
        thread_refs: Thread reference IDs to link cards to

    Returns:
        Dictionary with cards list
    """
    preset = preset_id.lower()

    if preset in {"exam-mode", "exam"}:
        cards = [
            {
                "front": "Define the primary mechanism.",
                "back": "The main process that drives the system behavior.",
                "difficulty": "easy",
                "tags": ["definitions", "exam"],
                "threadRef": thread_refs[1] if len(thread_refs) > 1 else None,
            },
            {
                "front": "Compare enhanced vs standard process.",
                "back": "Enhanced uses optimization; standard is slower without it.",
                "difficulty": "medium",
                "tags": ["comparisons", "exam"],
            },
        ]
    elif preset in {"neurodivergent-friendly", "neurodivergent-friendly-mode"}:
        cards = [
            {
                "front": "Main concept = ?",
                "back": "A fundamental principle in the topic.",
                "difficulty": "easy",
                "tags": ["quick-check"],
            },
            {
                "front": "Key factor helps because?",
                "back": "It optimizes the process.",
                "difficulty": "easy",
                "tags": ["quick-check"],
            },
        ]
    else:
        cards = [
            {
                "front": "What triggers the primary mechanism?",
                "back": "Activation of component A and input processing.",
                "difficulty": "easy",
                "tags": ["core-concepts"],
                "threadRef": thread_refs[1] if len(thread_refs) > 1 else None,
            },
            {
                "front": "Why does optimization matter?",
                "back": "It enables enhanced process, increasing efficiency.",
                "difficulty": "medium",
                "tags": ["mechanisms"],
            },
        ]

    return {"cards": cards}


def get_exam_questions_template(preset_id: str, thread_refs: List[str]) -> Dict[str, Any]:
    """
    Get exam questions template based on preset.

    Args:
        preset_id: The preset mode
        thread_refs: Thread reference IDs to link questions to

    Returns:
        Dictionary with questions list
    """
    preset = preset_id.lower()

    if preset in {"research-mode", "research"}:
        questions = [
            {
                "prompt": "Summarize evidence for optimization affecting system efficiency.",
                "type": "short-answer",
                "answer": "Summarize cited data or experiments. [evidence]",
            },
            {
                "prompt": "What competing hypotheses explain mechanism strengthening?",
                "type": "essay",
                "answer": "List and contrast candidate mechanisms. [evidence]",
            },
        ]
    elif preset in {"exam-mode", "exam"}:
        questions = [
            {
                "prompt": "Which component is most associated with the primary process?",
                "type": "multiple-choice",
                "choices": [
                    "Component A (primary)",
                    "Component B (secondary)",
                    "Component C (regulatory)",
                    "Component D (auxiliary)",
                ],
                "correctChoiceIndex": 0,
                "answer": "Component A (primary).",
                "threadRef": thread_refs[1] if len(thread_refs) > 1 else None,
            },
            {
                "prompt": "Explain the enhanced process in one paragraph.",
                "type": "essay",
                "answer": (
                    "The enhanced process describes how optimization factors enable "
                    "more efficient system operation, which improves performance "
                    "and reduces resource requirements."
                ),
            },
        ]
    else:
        questions = [
            {
                "prompt": "Which component is most associated with the primary process?",
                "type": "multiple-choice",
                "choices": [
                    "Component A (primary)",
                    "Component B (secondary)",
                    "Component C (regulatory)",
                    "Component D (auxiliary)",
                ],
                "correctChoiceIndex": 0,
                "answer": "Component A (primary).",
                "threadRef": thread_refs[1] if len(thread_refs) > 1 else None,
            },
            {
                "prompt": "Explain the enhanced process in one paragraph.",
                "type": "essay",
                "answer": (
                    "The enhanced process describes how optimization factors enable "
                    "more efficient system operation, which improves performance "
                    "and reduces resource requirements."
                ),
            },
        ]

    return {"questions": questions}
