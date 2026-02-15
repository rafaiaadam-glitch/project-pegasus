from __future__ import annotations

PRESETS: list[dict] = [
    {
        "id": "exam-mode",
        "name": "Exam Mode",
        "kind": "exam",
        "description": "Optimized for revision and assessment prep with definitions and likely questions.",
        "outputProfile": {
            "summary_style": "concise_academic",
            "sections": ["overview", "examinable_points", "definitions", "likely_questions"],
            "chunking": "medium",
            "question_focus": True,
        },
    },
    {
        "id": "concept-map-mode",
        "name": "Concept Map Mode",
        "kind": "concept-map",
        "description": "Emphasizes hierarchies, dependencies, and conceptual relationships.",
        "outputProfile": {
            "summary_style": "conceptual",
            "sections": ["core_concepts", "relationships", "dependencies", "misconceptions"],
            "chunking": "hierarchical",
            "question_focus": False,
        },
    },
    {
        "id": "beginner-mode",
        "name": "Beginner Mode",
        "kind": "beginner",
        "description": "Uses plain language, examples, and analogies for first-pass comprehension.",
        "outputProfile": {
            "summary_style": "plain_language",
            "sections": ["overview", "key_ideas", "examples", "analogy_bank"],
            "chunking": "short",
            "question_focus": False,
        },
    },
    {
        "id": "neurodivergent-friendly-mode",
        "name": "Neurodivergent-Friendly Mode",
        "kind": "neurodivergent",
        "description": "Prioritizes short chunks, low clutter, and predictable structure.",
        "outputProfile": {
            "summary_style": "low_clutter",
            "sections": ["overview", "micro_chunks", "key_terms", "recall_prompts"],
            "chunking": "very_short",
            "question_focus": True,
        },
    },
    {
        "id": "research-mode",
        "name": "Research Mode",
        "kind": "research",
        "description": "Highlights claims, argument flow, and evidence placeholders.",
        "outputProfile": {
            "summary_style": "argumentative",
            "sections": ["claims", "arguments", "evidence", "open_questions"],
            "chunking": "medium",
            "question_focus": True,
        },
    },
    {
        "id": "seminar-mode",
        "name": "Seminar Mode",
        "kind": "seminar",
        "description": "Optimized for debate and discussion. Tracks arguments, counterarguments, and positions for seminar preparation.",
        "outputProfile": {
            "summary_style": "debate_focused",
            "sections": [
                "key_speakers",
                "core_claims",
                "evidence",
                "counterclaims",
                "critiques",
                "discussion_questions",
            ],
            "chunking": "argument_based",
            "question_focus": True,
            "emphasis": {
                "who": "high",  # Authors, speakers, schools of thought
                "why": "high",  # Normative claims, philosophical stakes
                "how": "high",  # Argument structure
                "what": "medium",  # Core concepts
            },
        },
    },
]


PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
