"""Tests for content_templates.py"""

import pytest

from pipeline.content_templates import (
    get_summary_template,
    get_outline_template,
    get_key_terms_template,
    get_flashcards_template,
    get_exam_questions_template,
)


class TestSummaryTemplate:
    """Tests for get_summary_template."""

    def test_beginner_mode(self):
        """Test beginner-mode template."""
        template = get_summary_template("beginner-mode", "lecture-001")

        assert "overview" in template
        assert "sections" in template
        assert "Plain-language" in template["overview"]
        assert len(template["sections"]) >= 2
        assert template["sections"][0]["title"] == "Big idea"

    def test_research_mode(self):
        """Test research-mode template."""
        template = get_summary_template("research-mode", "lecture-001")

        assert "Claim-focused" in template["overview"]
        assert any("[evidence]" in bullet
                   for section in template["sections"]
                   for bullet in section["bullets"])

    def test_exam_mode(self):
        """Test exam-mode template (default)."""
        template = get_summary_template("exam-mode", "lecture-001")

        assert "overview" in template
        assert "sections" in template
        assert len(template["sections"]) >= 2

    def test_concept_map_mode(self):
        """Test concept-map-mode template."""
        template = get_summary_template("concept-map-mode", "lecture-001")

        assert "Relationship-first" in template["overview"]
        assert any("relationships" in section["title"].lower()
                   for section in template["sections"])

    def test_neurodivergent_friendly_mode(self):
        """Test neurodivergent-friendly-mode template."""
        template = get_summary_template("neurodivergent-friendly-mode", "lecture-001")

        assert "Short, low-clutter" in template["overview"]
        assert any("checkpoint" in section["title"].lower()
                   for section in template["sections"])

    def test_unknown_preset_uses_default(self):
        """Test unknown preset falls back to default."""
        template = get_summary_template("unknown-preset", "lecture-001")

        assert "overview" in template
        assert "sections" in template
        assert "unknown-preset" in template["overview"]


class TestOutlineTemplate:
    """Tests for get_outline_template."""

    def test_concept_map_mode(self):
        """Test concept-map outline."""
        template = get_outline_template("concept-map-mode")

        assert "outline" in template
        assert len(template["outline"]) > 0
        assert "children" in template["outline"][0]

    def test_exam_mode(self):
        """Test exam-mode outline."""
        template = get_outline_template("exam-mode")

        assert "outline" in template
        assert any("exam" in item["title"].lower()
                   for item in template["outline"])

    def test_default_outline(self):
        """Test default outline structure."""
        template = get_outline_template("default")

        assert "outline" in template
        assert len(template["outline"]) >= 2
        assert "points" in template["outline"][0]


class TestKeyTermsTemplate:
    """Tests for get_key_terms_template."""

    def test_with_thread_refs(self):
        """Test key terms with thread references."""
        thread_refs = ["thread-001", "thread-002"]
        template = get_key_terms_template("exam-mode", thread_refs)

        assert "terms" in template
        assert len(template["terms"]) > 0
        assert "term" in template["terms"][0]
        assert "definition" in template["terms"][0]

        # At least one term should have a thread ref
        assert any("threadRef" in term for term in template["terms"])

    def test_without_thread_refs(self):
        """Test key terms without thread references."""
        template = get_key_terms_template("exam-mode", [])

        assert "terms" in template
        assert len(template["terms"]) > 0

    def test_beginner_mode_terms(self):
        """Test beginner-mode terms are simpler."""
        template = get_key_terms_template("beginner-mode", ["thread-001"])

        assert "terms" in template
        # Beginner mode should have simpler terms
        assert len(template["terms"]) >= 2

    def test_research_mode_terms(self):
        """Test research-mode terms have evidence placeholders."""
        template = get_key_terms_template("research-mode", [])

        assert "terms" in template
        # Research mode should have [evidence] tags
        assert any("[evidence]" in term["definition"]
                   for term in template["terms"])


class TestFlashcardsTemplate:
    """Tests for get_flashcards_template."""

    def test_flashcard_structure(self):
        """Test flashcard has required fields."""
        template = get_flashcards_template("exam-mode", ["thread-001"])

        assert "cards" in template
        assert len(template["cards"]) > 0

        card = template["cards"][0]
        assert "front" in card
        assert "back" in card
        assert "difficulty" in card
        assert card["difficulty"] in ["easy", "medium", "hard"]

    def test_exam_mode_flashcards(self):
        """Test exam-mode flashcards."""
        template = get_flashcards_template("exam-mode", ["thread-001", "thread-002"])

        assert "cards" in template
        assert any("exam" in tag for card in template["cards"]
                   for tag in card.get("tags", []))

    def test_neurodivergent_friendly_flashcards(self):
        """Test neurodivergent-friendly flashcards are simpler."""
        template = get_flashcards_template("neurodivergent-friendly-mode", [])

        assert "cards" in template
        # All cards should be easy difficulty
        assert all(card["difficulty"] == "easy" for card in template["cards"])

    def test_flashcards_with_thread_refs(self):
        """Test some flashcards have thread references."""
        thread_refs = ["thread-001", "thread-002"]
        template = get_flashcards_template("exam-mode", thread_refs)

        # At least one card should have a thread ref
        assert any("threadRef" in card for card in template["cards"])


class TestExamQuestionsTemplate:
    """Tests for get_exam_questions_template."""

    def test_question_structure(self):
        """Test question has required fields."""
        template = get_exam_questions_template("exam-mode", ["thread-001"])

        assert "questions" in template
        assert len(template["questions"]) > 0

        question = template["questions"][0]
        assert "prompt" in question
        assert "type" in question
        assert "answer" in question
        assert question["type"] in ["multiple-choice", "short-answer", "essay", "true-false"]

    def test_research_mode_questions(self):
        """Test research-mode has evidence placeholders."""
        template = get_exam_questions_template("research-mode", [])

        assert "questions" in template
        # Research mode should have [evidence] tags
        assert any("[evidence]" in q["answer"]
                   for q in template["questions"])

    def test_exam_mode_questions(self):
        """Test exam-mode has multiple-choice questions."""
        template = get_exam_questions_template("exam-mode", ["thread-001", "thread-002"])

        assert "questions" in template
        # Should have at least one multiple-choice question
        mc_questions = [q for q in template["questions"]
                       if q["type"] == "multiple-choice"]
        assert len(mc_questions) > 0

        # Multiple choice should have choices and correctChoiceIndex
        mc = mc_questions[0]
        assert "choices" in mc
        assert "correctChoiceIndex" in mc
        assert isinstance(mc["correctChoiceIndex"], int)
        assert 0 <= mc["correctChoiceIndex"] < len(mc["choices"])

    def test_questions_with_thread_refs(self):
        """Test some questions have thread references."""
        thread_refs = ["thread-001", "thread-002"]
        template = get_exam_questions_template("exam-mode", thread_refs)

        # At least one question should have a thread ref
        assert any("threadRef" in q for q in template["questions"])


class TestPresetConsistency:
    """Tests for consistency across all preset modes."""

    @pytest.mark.parametrize("preset", [
        "exam-mode",
        "beginner-mode",
        "research-mode",
        "concept-map-mode",
        "neurodivergent-friendly-mode",
    ])
    def test_all_presets_return_valid_summaries(self, preset):
        """Test all presets return valid summary structure."""
        template = get_summary_template(preset, "test-lecture")
        assert "overview" in template
        assert "sections" in template
        assert isinstance(template["sections"], list)
        assert len(template["sections"]) > 0

    @pytest.mark.parametrize("preset", [
        "exam-mode",
        "beginner-mode",
        "research-mode",
        "concept-map-mode",
        "neurodivergent-friendly-mode",
    ])
    def test_all_presets_return_valid_outlines(self, preset):
        """Test all presets return valid outline structure."""
        template = get_outline_template(preset)
        assert "outline" in template
        assert isinstance(template["outline"], list)
        assert len(template["outline"]) > 0
