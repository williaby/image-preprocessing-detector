# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for domain classification prompt templates."""

from __future__ import annotations

from image_preprocessing_detector.labeling.domain.prompts import (
    build_text_prompt,
    build_vision_prompt,
)


class TestBuildTextPrompt:
    """Tests for build_text_prompt."""

    def test_basic_prompt_structure(self) -> None:
        """Returns system and user messages."""
        messages = build_text_prompt("Sample document text")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_prompt_contains_domain_codes(self) -> None:
        """System prompt includes all 10 domain codes."""
        messages = build_text_prompt("text")
        system = messages[0]["content"]
        for code in (
            "TAX",
            "LEG",
            "FIN",
            "TEC",
            "SCI",
            "ADM",
            "MED",
            "EDU",
            "PER",
            "UNK",
        ):
            assert code in system

    def test_user_message_includes_text(self) -> None:
        """User message includes the provided text."""
        messages = build_text_prompt("Annual financial report for Q4 2025")
        user_content = messages[1]["content"]
        assert "Annual financial report for Q4 2025" in user_content

    def test_truncation_applied(self) -> None:
        """Long text is truncated with notice."""
        long_text = "x" * 5000
        messages = build_text_prompt(long_text, max_chars=100)
        user_content = messages[1]["content"]
        assert "[TEXT TRUNCATED]" in user_content
        # Should not contain the full text
        assert "x" * 5000 not in user_content

    def test_no_truncation_for_short_text(self) -> None:
        """Short text is not truncated."""
        messages = build_text_prompt("short text", max_chars=4000)
        user_content = messages[1]["content"]
        assert "[TEXT TRUNCATED]" not in user_content

    def test_system_prompt_requests_json(self) -> None:
        """System prompt requests JSON response format."""
        messages = build_text_prompt("text")
        system = messages[0]["content"]
        assert "JSON" in system
        assert "domain" in system
        assert "domain_confidence" in system

    def test_system_prompt_includes_language_instructions(self) -> None:
        """System prompt includes language and script detection."""
        messages = build_text_prompt("text")
        system = messages[0]["content"]
        assert "iso639_language" in system
        assert "iso15924_script" in system

    def test_custom_max_chars(self) -> None:
        """Custom max_chars parameter is respected."""
        text = "a" * 200
        messages = build_text_prompt(text, max_chars=50)
        user_content = messages[1]["content"]
        assert "[TEXT TRUNCATED]" in user_content


class TestBuildVisionPrompt:
    """Tests for build_vision_prompt."""

    def test_basic_structure(self) -> None:
        """Returns system and user messages."""
        messages = build_vision_prompt()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_content_is_list(self) -> None:
        """User message content is a list (for image appending)."""
        messages = build_vision_prompt()
        user_content = messages[1]["content"]
        assert isinstance(user_content, list)

    def test_user_content_has_text_block(self) -> None:
        """User message contains a text content block."""
        messages = build_vision_prompt()
        user_content = messages[1]["content"]
        assert len(user_content) >= 1
        assert user_content[0]["type"] == "text"

    def test_system_prompt_includes_capture_methods(self) -> None:
        """System prompt includes capture method options."""
        messages = build_vision_prompt()
        system = messages[0]["content"]
        for method in (
            "born_digital",
            "scanner_flatbed",
            "scanner_adf",
            "camera_smartphone",
        ):
            assert method in system

    def test_system_prompt_includes_content_flags(self) -> None:
        """System prompt includes content flag fields."""
        messages = build_vision_prompt()
        system = messages[0]["content"]
        for flag in (
            "has_table",
            "has_formula",
            "has_handwriting",
            "has_signature",
            "has_figure",
        ):
            assert flag in system

    def test_system_prompt_includes_orientation(self) -> None:
        """System prompt includes orientation detection."""
        messages = build_vision_prompt()
        system = messages[0]["content"]
        assert "portrait" in system
        assert "landscape" in system

    def test_system_prompt_includes_domain_codes(self) -> None:
        """Vision prompt also includes domain taxonomy."""
        messages = build_vision_prompt()
        system = messages[0]["content"]
        for code in ("TAX", "LEG", "FIN", "TEC", "SCI"):
            assert code in system
