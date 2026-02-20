from __future__ import annotations

PRESETS: list[dict] = [
    {
        "id": "exam-mode",
        "name": "Exam Mode",
        "kind": "exam",
        "description": "Optimized for structured answers, mark schemes, and clarity under assessment pressure. Prioritizes definitions and explanation marks.",
        "diceWeights": {
            "what": 0.25,   # ORANGE: Definitions are essential
            "how": 0.25,    # RED: Explanation marks
            "when": 0.15,   # YELLOW: Historical/conditional context
            "where": 0.15,  # GREEN: Scope/application
            "who": 0.05,    # BLUE: Lighter unless essay-based
            "why": 0.15,    # PURPLE: Evaluation/analysis marks
        },
        "optimizedFor": [
            "Clear definitions",
            "Mark scheme alignment",
            "Structured explanations",
            "Contextual awareness",
            "Evaluation and analysis",
        ],
        "generation_config": {
            "summary_max_words": 800,
            "flashcard_count": 25,
            "exam_question_count": 15,
            "tone": "formal_academic",
            "question_types": ["definition", "explanation", "application", "evaluation"],
            "special_instructions": [
                "Include clear definitions suitable for memorization",
                "Highlight examinable points and mark scheme criteria",
                "Structure explanations in exam-friendly bullet points",
                "Add 'Common mistakes to avoid' where relevant",
            ],
        },
        "outputProfile": {
            "summary_style": "concise_academic",
            "sections": ["overview", "examinable_points", "definitions", "likely_questions"],
            "chunking": "medium",
            "question_focus": True,
            "emphasis": {
                "what": "high",   # Definitions critical
                "how": "high",    # Process explanations
                "when": "medium", # Context matters
                "where": "medium", # Application scope
                "who": "low",     # Less critical
                "why": "medium",  # Analysis component
            },
        },
    },
    {
        "id": "concept-map-mode",
        "name": "Concept Map Mode",
        "kind": "concept-map",
        "description": "Shows relationships and system structure. Emphasizes connections, mechanisms, and system boundaries over deep meaning.",
        "diceWeights": {
            "what": 0.20,   # ORANGE: Nodes in the map
            "how": 0.25,    # RED: Connections between nodes
            "when": 0.10,   # YELLOW: Sequence relationships
            "where": 0.20,  # GREEN: System boundaries
            "who": 0.15,    # BLUE: Actors in system
            "why": 0.10,    # PURPLE: Lower, structure first
        },
        "optimizedFor": [
            "Relationship mapping",
            "Mechanism visualization",
            "System boundaries",
            "Hierarchical structure",
            "Dependency chains",
        ],
        "generation_config": {
            "summary_max_words": 600,
            "flashcard_count": 20,
            "exam_question_count": 10,
            "tone": "analytical_precise",
            "question_types": ["relationship", "system_analysis", "dependency"],
            "special_instructions": [
                "Emphasize how concepts connect and interact",
                "Identify hierarchical relationships and dependencies",
                "Describe system boundaries and scope clearly",
                "Use phrases like 'depends on', 'leads to', 'requires', 'influences'",
            ],
        },
        "outputProfile": {
            "summary_style": "conceptual",
            "sections": ["core_concepts", "relationships", "dependencies", "misconceptions"],
            "chunking": "hierarchical",
            "question_focus": False,
            "emphasis": {
                "what": "medium",  # Node definition
                "how": "high",     # Connection logic
                "when": "low",     # Temporal less critical
                "where": "high",   # Boundaries important
                "who": "medium",   # Actors moderate
                "why": "low",      # Meaning secondary
            },
        },
    },
    {
        "id": "beginner-mode",
        "name": "Beginner Mode",
        "kind": "beginner",
        "description": "Reduces overwhelm with clear definitions and simple explanations. Minimal debate, abstraction, or complex theoretical stakes.",
        "diceWeights": {
            "what": 0.35,   # ORANGE: Clear definitions (very strong)
            "how": 0.30,    # RED: Simple explanation (very strong)
            "when": 0.15,   # YELLOW: Basic context
            "where": 0.10,  # GREEN: Limited scope
            "who": 0.05,    # BLUE: Minimal
            "why": 0.05,    # PURPLE: Simplified
        },
        "optimizedFor": [
            "Foundational understanding",
            "Clear definitions",
            "Simple explanations",
            "Reduced cognitive load",
            "Plain language",
        ],
        "generation_config": {
            "summary_max_words": 500,
            "flashcard_count": 15,
            "exam_question_count": 8,
            "tone": "conversational",
            "question_types": ["recognition", "basic_understanding", "simple_application"],
            "special_instructions": [
                "Use plain, everyday language - avoid jargon",
                "Include concrete examples and analogies for every concept",
                "Break complex ideas into simple, digestible chunks",
                "Use phrases like 'Think of it like...', 'In simple terms...'",
                "Avoid abstract theoretical discussions",
            ],
        },
        "outputProfile": {
            "summary_style": "plain_language",
            "sections": ["overview", "key_ideas", "examples", "analogy_bank"],
            "chunking": "short",
            "question_focus": False,
            "emphasis": {
                "what": "very_high", # Core grounding
                "how": "high",       # Simple steps
                "when": "medium",    # Basic context
                "where": "low",      # Limited scope
                "who": "very_low",   # Minimal
                "why": "very_low",   # Avoid abstraction
            },
        },
    },
    {
        "id": "neurodivergent-friendly-mode",
        "name": "Neurodivergent-Friendly Mode",
        "kind": "neurodivergent",
        "description": "Reduces cognitive overload with clear structure, step-by-step logic, and temporal anchoring. Minimizes abstraction spirals.",
        "diceWeights": {
            "what": 0.25,   # ORANGE: Clarity anchor
            "how": 0.25,    # RED: Step-by-step logic
            "when": 0.20,   # YELLOW: Sequencing reduces chaos
            "where": 0.15,  # GREEN: Boundaries reduce ambiguity
            "who": 0.10,    # BLUE: Moderate
            "why": 0.05,    # PURPLE: Limited abstraction
        },
        "optimizedFor": [
            "Reduced cognitive overload",
            "Predictable structure",
            "Clear sequencing",
            "Explicit boundaries",
            "Minimal abstraction",
        ],
        "generation_config": {
            "summary_max_words": 400,
            "flashcard_count": 12,
            "exam_question_count": 6,
            "tone": "direct_predictable",
            "question_types": ["sequence", "recall", "pattern_recognition"],
            "special_instructions": [
                "Use numbered steps (1, 2, 3) instead of prose paragraphs",
                "Keep sentences short and direct (max 15 words per sentence)",
                "Use consistent structure and predictable formatting",
                "Provide clear temporal markers ('First', 'Then', 'Finally')",
                "Avoid metaphors, idioms, and ambiguous language",
                "Use high contrast formatting with clear visual breaks",
            ],
        },
        "outputProfile": {
            "summary_style": "low_clutter",
            "sections": ["overview", "micro_chunks", "key_terms", "recall_prompts"],
            "chunking": "very_short",
            "question_focus": True,
            "emphasis": {
                "what": "high",     # Clear anchor
                "how": "high",      # Logical steps
                "when": "high",     # Sequencing critical
                "where": "medium",  # Context bounds
                "who": "low",       # Moderate
                "why": "very_low",  # Avoid overload
            },
        },
    },
    {
        "id": "research-mode",
        "name": "Research Mode",
        "kind": "research",
        "description": "Emphasizes methodological depth, critical evaluation, and theoretical framing. Strong focus on mechanisms and context.",
        "diceWeights": {
            "what": 0.15,   # ORANGE: Operational definitions
            "how": 0.25,    # RED: Methods/mechanisms
            "when": 0.15,   # YELLOW: Longitudinal design
            "where": 0.20,  # GREEN: Population/context
            "who": 0.15,    # BLUE: Stakeholders/sample
            "why": 0.10,    # PURPLE: Hypothesis framing
        },
        "optimizedFor": [
            "Methodological rigor",
            "Critical evaluation",
            "Contextual analysis",
            "Multi-source integration",
            "Theoretical framing",
        ],
        "generation_config": {
            "summary_max_words": 1000,
            "flashcard_count": 20,
            "exam_question_count": 12,
            "tone": "analytical_precise",
            "question_types": ["critical_analysis", "methodology", "evaluation", "synthesis"],
            "special_instructions": [
                "Emphasize methodological rigor and research design",
                "Identify claims, evidence, and gaps in reasoning",
                "Highlight contextual factors and boundary conditions",
                "Use precise operational definitions",
                "Include phrases like 'The evidence suggests...', 'A limitation is...'",
                "Note stakeholders, populations, and sampling considerations",
            ],
        },
        "outputProfile": {
            "summary_style": "argumentative",
            "sections": ["claims", "arguments", "evidence", "open_questions"],
            "chunking": "medium",
            "question_focus": True,
            "emphasis": {
                "what": "medium",  # Operational clarity
                "how": "high",     # Methods critical
                "when": "medium",  # Temporal design
                "where": "high",   # Context essential
                "who": "medium",   # Sample/actors
                "why": "low",      # Hypothesis secondary
            },
        },
    },
    {
        "id": "seminar-mode",
        "name": "Seminar / Discussion Mode",
        "kind": "seminar",
        "description": "Optimized for debate and discussion tracking. Ideal for Political Science, Philosophy, Law, Sociology, Anthropology, and Literature. Emphasizes argument clarity, position mapping, and normative stakes.",
        "targetDisciplines": [
            "Political Science",
            "Philosophy",
            "Law",
            "Sociology",
            "Anthropology",
            "Literature",
        ],
        "diceWeights": {
            "what": 0.18,  # ORANGE: Core concepts and definitions
            "how": 0.22,   # RED: Argument structure and methodology
            "when": 0.08,  # YELLOW: Historical/temporal context
            "where": 0.12, # GREEN: Geographic/institutional context
            "who": 0.20,   # BLUE: Speaker attribution and schools of thought
            "why": 0.20,   # PURPLE: Normative claims and philosophical stakes
        },
        "optimizedFor": [
            "Argument clarity",
            "Debate tracking",
            "Position mapping",
            "Counterarguments",
            "Normative stakes",
            "Speaker attribution",
        ],
        "generation_config": {
            "summary_max_words": 900,
            "flashcard_count": 18,
            "exam_question_count": 10,
            "tone": "dialectical",
            "question_types": ["argument_analysis", "position_comparison", "critique", "normative_evaluation"],
            "special_instructions": [
                "Clearly attribute positions to specific speakers/authors",
                "Structure content around claims and counterarguments",
                "Identify normative stakes and philosophical implications",
                "Use phrases like 'X argues that...', 'In contrast, Y contends...'",
                "Highlight points of disagreement and debate",
                "Include open questions suitable for seminar discussion",
            ],
        },
        "outputProfile": {
            "summary_style": "debate_focused",
            "sections": [
                "main_claim",
                "supporting_argument",
                "counterargument",
                "critique",
                "open_question",
            ],
            "chunking": "argument_based",
            "question_focus": True,
            "emphasis": {
                "who": "high",  # Authors, speakers, schools of thought
                "why": "high",  # Normative claims, philosophical stakes
                "how": "high",  # Argument structure
                "what": "medium",  # Core concepts
                "where": "low",  # Geographic context
                "when": "low",   # Temporal context
            },
        },
    },
]


PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
