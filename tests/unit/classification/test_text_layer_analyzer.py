# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Unit tests for TextLayerAnalyzer.

All tests mock ``fitz.open()`` so that no real PDF files are required.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

# Module path used to patch the ``fitz`` reference inside the analyzer module.
_FITZ_MODULE = "image_preprocessing_detector.classification.text_layer_analyzer.fitz"

# Module path for Path existence checks added in text_layer_analyzer.analyze().
# Tests use fake paths like "/fake/clean.pdf"; we patch Path methods so the
# file-not-found guard added by the wave agents does not raise in unit tests.
_PATH_EXISTS = (
    "image_preprocessing_detector.classification.text_layer_analyzer.Path.exists"
)
_PATH_IS_FILE = (
    "image_preprocessing_detector.classification.text_layer_analyzer.Path.is_file"
)


@pytest.fixture(autouse=True)
def _patch_path_checks() -> Generator[None, None, None]:
    """Patch Path.exists and Path.is_file to return True for all tests.

    The analyze() method added file-existence guards after accepting Path inputs.
    Unit tests intentionally use fake paths (e.g. '/fake/clean.pdf') and mock
    the fitz layer, so we stub Path checks to avoid FileNotFoundError.
    """
    with (
        patch(_PATH_EXISTS, return_value=True),
        patch(_PATH_IS_FILE, return_value=True),
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers to build mock fitz objects
# ---------------------------------------------------------------------------


def _make_mock_page(
    text: str = "",
    words: list[tuple[float, ...]] | None = None,
    fonts: list[tuple[int, str, str, str, str, int]] | None = None,
) -> MagicMock:
    """Return a ``MagicMock`` mimicking a ``fitz.Page``.

    Args:
        text: Raw text returned by ``page.get_text()``.
        words: List of word tuples ``(x0, y0, x1, y1, word, blk, ln, wn)``.
            Defaults to one word at precise coordinates when *text* is non-empty.
        fonts: List of font tuples ``(xref, ext, type, basefont, name, enc)``.
            Defaults to a single embedded font when *text* is non-empty.
    """
    page = MagicMock()
    page.get_text.return_value = text

    if words is None:
        words = [(100.5, 200.3, 150.7, 220.1, "word", 0, 0, 0)] if text.strip() else []
    page.get_text_words.return_value = words

    if fonts is None:
        fonts = [(0, "ttf", "TrueType", "Helvetica", "Helv", 1)] if text.strip() else []
    page.get_fonts.return_value = fonts

    return page


def _make_mock_doc(
    pages: list[MagicMock] | None = None,
) -> MagicMock:
    """Return a ``MagicMock`` mimicking a ``fitz.Document``.

    The mock supports ``len(doc)``, ``doc.page_count``, iteration, and
    context-manager ``close()``.
    """
    if pages is None:
        pages = []

    doc = MagicMock()
    doc.page_count = len(pages)
    doc.__len__ = MagicMock(return_value=len(pages))
    doc.__iter__ = MagicMock(return_value=iter(pages))
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_clean_page() -> MagicMock:
    """A page with clean, extractable text and an embedded font."""
    return _make_mock_page(
        text="Hello world, this is a clean document page with enough text.",
        words=[
            (100.5, 200.3, 150.7, 220.1, "Hello", 0, 0, 0),
            (155.2, 200.3, 200.8, 220.1, "world", 0, 0, 1),
        ],
        fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
    )


@pytest.fixture
def mock_empty_page() -> MagicMock:
    """A page with no extractable text at all."""
    return _make_mock_page(text="", words=[], fonts=[])


@pytest.fixture
def mock_replacement_page() -> MagicMock:
    """A page where 50% of characters are replacement chars."""
    # 10 chars total, 5 are U+FFFD
    text = "He\ufffdl\ufffdo\ufffd w\ufffdr\ufffdd"
    return _make_mock_page(
        text=text,
        words=[(100.5, 200.3, 150.7, 220.1, "word", 0, 0, 0)],
        fonts=[(0, "ttf", "TrueType", "Arial", "Arial", 1)],
    )


@pytest.fixture
def mock_unembedded_font_page() -> MagicMock:
    """A page referencing a font that is NOT embedded."""
    return _make_mock_page(
        text="Some text with unembedded fonts here.",
        words=[(100.5, 200.3, 150.7, 220.1, "Some", 0, 0, 0)],
        fonts=[
            # ext="" and name="" signals an unembedded font
            (0, "", "Type1", "TimesNewRoman", "", 0),
        ],
    )


@pytest.fixture
def mock_round_coords_page() -> MagicMock:
    """A page where all word coordinates are suspiciously round."""
    return _make_mock_page(
        text="Auto-generated text with round coordinates.",
        words=[
            (100.0, 200.0, 300.0, 400.0, "Auto-generated", 0, 0, 0),
            (100.0, 210.0, 300.0, 410.0, "text", 0, 0, 1),
        ],
        fonts=[(0, "ttf", "TrueType", "Courier", "Cour", 1)],
    )


# ---------------------------------------------------------------------------
# Test class: TextLayerAnalyzer
# ---------------------------------------------------------------------------


class TestTextLayerAnalyzer:
    """Tests for the ``TextLayerAnalyzer`` class."""

    @patch(_FITZ_MODULE)
    def test_clean_pdf_high_quality_skip_ocr(
        self, mock_fitz: MagicMock, mock_clean_page: MagicMock
    ) -> None:
        """A PDF with clean text, embedded fonts, and precise coords should
        score high and recommend skipping OCR."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_clean_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer(skip_ocr_threshold=0.85)
        result = analyzer.analyze("/fake/clean.pdf")

        assert result.text_layer_quality > 0.85
        assert result.text_layer_skip_ocr is True
        assert result.extractability_rate == pytest.approx(1.0)
        assert result.replacement_char_ratio == pytest.approx(0.0)
        assert result.font_embedding_score == pytest.approx(1.0)
        assert result.coordinate_precision_score > 0.5
        assert result.page_count == 1
        assert result.total_characters > 0
        assert result.confidence > 0.0

    @patch(_FITZ_MODULE)
    def test_no_text_pdf_zero_quality(
        self, mock_fitz: MagicMock, mock_empty_page: MagicMock
    ) -> None:
        """A PDF with no extractable text should score low and not skip OCR."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_empty_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/empty.pdf")

        # Extractability is 0, but font_embedding defaults to 1.0 when no
        # fonts, and coord precision to 0.5 when no words.  The aggregate
        # quality should still be well below the skip-OCR threshold.
        assert result.text_layer_quality < 0.85
        assert result.text_layer_skip_ocr is False
        assert result.extractability_rate == pytest.approx(0.0)
        assert result.total_characters == 0
        assert result.page_count == 1

    @patch(_FITZ_MODULE)
    def test_replacement_chars_lower_quality(
        self, mock_fitz: MagicMock, mock_replacement_page: MagicMock
    ) -> None:
        """A PDF with many replacement characters should have reduced quality."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_replacement_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/replacement.pdf")

        assert result.replacement_char_ratio > 0.0
        # The replacement_char component reduces quality vs. a clean document.
        assert result.text_layer_quality < 1.0

    @patch(_FITZ_MODULE)
    def test_heavy_replacement_chars_skip_ocr_false(self, mock_fitz: MagicMock) -> None:
        """A PDF where all text is replacement chars should not skip OCR."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        # All characters are replacement characters.
        page = _make_mock_page(
            text="\ufffd" * 20,
            words=[(100.5, 200.3, 150.7, 220.1, "\ufffd", 0, 0, 0)],
            # Unembedded font to compound the penalty.
            fonts=[(0, "", "Type1", "BadFont", "", 0)],
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/all_bad.pdf")

        assert result.replacement_char_ratio == pytest.approx(1.0)
        assert result.font_embedding_score == pytest.approx(0.0)
        assert result.text_layer_skip_ocr is False

    @patch(_FITZ_MODULE)
    def test_unembedded_fonts_lower_score(
        self, mock_fitz: MagicMock, mock_unembedded_font_page: MagicMock
    ) -> None:
        """A PDF with unembedded fonts should have font_embedding_score < 1."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_unembedded_font_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/unembedded.pdf")

        assert result.font_embedding_score == pytest.approx(0.0)
        # Quality should be reduced by the font embedding penalty.
        assert result.text_layer_quality < 0.85

    @patch(_FITZ_MODULE)
    def test_round_coordinates_lower_precision(
        self, mock_fitz: MagicMock, mock_round_coords_page: MagicMock
    ) -> None:
        """Pages with all-round coordinates should have low precision score."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_round_coords_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/round.pdf")

        assert result.coordinate_precision_score == pytest.approx(0.0)

    @patch(_FITZ_MODULE)
    def test_multipage_pdf(self, mock_fitz: MagicMock) -> None:
        """Multi-page PDFs should aggregate statistics across all pages."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page1 = _make_mock_page(text="First page content with text.")
        page2 = _make_mock_page(text="Second page also has text.")
        page3 = _make_mock_page(text="")  # empty page

        doc = _make_mock_doc([page1, page2, page3])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/multipage.pdf")

        assert result.page_count == 3
        # 2 of 3 pages have text
        assert abs(result.extractability_rate - 2.0 / 3.0) < 1e-6
        assert result.total_characters > 0

    @patch(_FITZ_MODULE)
    def test_single_page_pdf(self, mock_fitz: MagicMock) -> None:
        """Single-page PDF should work correctly."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(
            text="A single page with enough text to be confident about the quality."
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/single.pdf")

        assert result.page_count == 1
        assert result.extractability_rate == pytest.approx(1.0)

    @patch(_FITZ_MODULE)
    def test_zero_page_pdf(self, mock_fitz: MagicMock) -> None:
        """A PDF with zero pages should return the empty result."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/zeropages.pdf")

        assert result.page_count == 0
        assert result.text_layer_quality == pytest.approx(0.0)
        assert result.text_layer_skip_ocr is False
        assert result.total_characters == 0

    @patch(_FITZ_MODULE)
    def test_custom_skip_ocr_threshold(self, mock_fitz: MagicMock) -> None:
        """A lower threshold should make it easier to recommend skip-OCR."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(text="Some text for testing threshold values.")
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        # With a very low threshold, even moderate quality should pass.
        analyzer = TextLayerAnalyzer(skip_ocr_threshold=0.3)
        result = analyzer.analyze("/fake/threshold.pdf")

        assert result.text_layer_skip_ocr is True

    @patch(_FITZ_MODULE)
    def test_custom_weights(self, mock_fitz: MagicMock) -> None:
        """Custom weights should change the aggregate score."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        # Page with all-round coords (low precision score).
        page = _make_mock_page(
            text="Testing custom weight configuration here.",
            words=[(100.0, 200.0, 300.0, 400.0, "Testing", 0, 0, 0)],
            fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
        )

        # We need two separate doc mocks since each call iterates the pages.
        doc_a = _make_mock_doc([page])
        page_b = _make_mock_page(
            text="Testing custom weight configuration here.",
            words=[(100.0, 200.0, 300.0, 400.0, "Testing", 0, 0, 0)],
            fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
        )
        doc_b = _make_mock_doc([page_b])
        mock_fitz.open.side_effect = [doc_a, doc_b]

        # Default weights: coord_precision has 0.15 weight.
        analyzer_default = TextLayerAnalyzer()
        result_default = analyzer_default.analyze("/fake/a.pdf")

        # Give coord_precision 100% of the weight.
        analyzer_coord_heavy = TextLayerAnalyzer(
            weights={
                "extractability": 0.0,
                "replacement_char": 0.0,
                "font_embedding": 0.0,
                "coordinate_precision": 1.0,
            }
        )
        result_coord = analyzer_coord_heavy.analyze("/fake/b.pdf")

        # The coord-heavy result should be noticeably lower since all coords
        # are round (precision = 0).
        assert result_coord.text_layer_quality < result_default.text_layer_quality

    @patch(_FITZ_MODULE)
    def test_mixed_embedded_and_unembedded_fonts(self, mock_fitz: MagicMock) -> None:
        """Pages with a mix of embedded and unembedded fonts."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(
            text="Mixed font embedding document.",
            fonts=[
                (0, "ttf", "TrueType", "Helvetica", "Helv", 1),  # embedded
                (1, "", "Type1", "TimesNewRoman", "", 0),  # unembedded
            ],
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/mixed_fonts.pdf")

        # 1 of 2 fonts embedded -> 0.5
        assert abs(result.font_embedding_score - 0.5) < 1e-6

    @patch(_FITZ_MODULE)
    def test_duplicate_fonts_deduplicated(self, mock_fitz: MagicMock) -> None:
        """The same font referenced on multiple pages should be counted once."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        shared_fonts: list[tuple[int, str, str, str, str, int]] = [
            (0, "ttf", "TrueType", "Helvetica", "Helv", 1),  # embedded
            (1, "", "Type1", "TimesNewRoman", "", 0),  # unembedded
        ]
        page1 = _make_mock_page(text="Page one.", fonts=shared_fonts)
        page2 = _make_mock_page(text="Page two.", fonts=shared_fonts)
        doc = _make_mock_doc([page1, page2])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/dup_fonts.pdf")

        # Still 1 of 2 unique fonts embedded.
        assert abs(result.font_embedding_score - 0.5) < 1e-6

    @patch(_FITZ_MODULE)
    def test_all_scores_in_zero_one_range(
        self, mock_fitz: MagicMock, mock_clean_page: MagicMock
    ) -> None:
        """Every numeric score in the result must be in [0, 1]."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([mock_clean_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/range.pdf")

        assert 0.0 <= result.text_layer_quality <= 1.0
        assert 0.0 <= result.extractability_rate <= 1.0
        assert 0.0 <= result.replacement_char_ratio <= 1.0
        assert 0.0 <= result.font_embedding_score <= 1.0
        assert 0.0 <= result.coordinate_precision_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @patch(_FITZ_MODULE)
    def test_all_scores_in_range_empty_pdf(self, mock_fitz: MagicMock) -> None:
        """Score range check for edge case: zero-page PDF."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        doc = _make_mock_doc([])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/empty_range.pdf")

        assert 0.0 <= result.text_layer_quality <= 1.0
        assert 0.0 <= result.extractability_rate <= 1.0
        assert 0.0 <= result.replacement_char_ratio <= 1.0
        assert 0.0 <= result.font_embedding_score <= 1.0
        assert 0.0 <= result.coordinate_precision_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @patch(_FITZ_MODULE)
    def test_all_scores_in_range_replacement_heavy(self, mock_fitz: MagicMock) -> None:
        """Score range check when nearly all chars are replacement chars."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        # All 5 chars are replacement characters.
        page = _make_mock_page(
            text="\ufffd\ufffd\ufffd\ufffd\ufffd",
            words=[(100.5, 200.3, 150.7, 220.1, "\ufffd", 0, 0, 0)],
            fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/all_replacement.pdf")

        assert 0.0 <= result.text_layer_quality <= 1.0
        assert 0.0 <= result.replacement_char_ratio <= 1.0
        assert result.replacement_char_ratio == pytest.approx(1.0)

    @patch(_FITZ_MODULE)
    def test_confidence_increases_with_more_text(self, mock_fitz: MagicMock) -> None:
        """Confidence should be higher for PDFs with more text."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        # Short text.
        short_page = _make_mock_page(text="Hi")
        doc_short = _make_mock_doc([short_page])

        # Long text.
        long_text = "A" * 6000
        long_page = _make_mock_page(text=long_text)
        doc_long = _make_mock_doc([long_page])

        mock_fitz.open.side_effect = [doc_short, doc_long]

        analyzer = TextLayerAnalyzer()
        result_short = analyzer.analyze("/fake/short.pdf")
        result_long = analyzer.analyze("/fake/long.pdf")

        assert result_long.confidence > result_short.confidence


# ---------------------------------------------------------------------------
# Test class: fitz unavailable
# ---------------------------------------------------------------------------


class TestFitzUnavailable:
    """Tests for graceful degradation when PyMuPDF is not installed."""

    def test_import_error_when_fitz_missing(self) -> None:
        """Instantiating TextLayerAnalyzer without fitz should raise ImportError."""
        with patch(
            "image_preprocessing_detector.classification.text_layer_analyzer._has_fitz",
            False,
        ):
            from image_preprocessing_detector.classification.text_layer_analyzer import (
                TextLayerAnalyzer,
            )

            with pytest.raises(ImportError, match="PyMuPDF"):
                TextLayerAnalyzer()

    def test_import_error_message_is_helpful(self) -> None:
        """The error message should tell the user how to install fitz."""
        with patch(
            "image_preprocessing_detector.classification.text_layer_analyzer._has_fitz",
            False,
        ):
            from image_preprocessing_detector.classification.text_layer_analyzer import (
                TextLayerAnalyzer,
            )

            with pytest.raises(ImportError, match="pip install PyMuPDF"):
                TextLayerAnalyzer()


# ---------------------------------------------------------------------------
# Test class: module-level convenience function
# ---------------------------------------------------------------------------


class TestAnalyzeTextLayerFunction:
    """Tests for the ``analyze_text_layer`` module-level function."""

    @patch(_FITZ_MODULE)
    def test_convenience_function_returns_result(
        self, mock_fitz: MagicMock, mock_clean_page: MagicMock
    ) -> None:
        """``analyze_text_layer`` should return a valid result."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            analyze_text_layer,
        )

        doc = _make_mock_doc([mock_clean_page])
        mock_fitz.open.return_value = doc

        result = analyze_text_layer("/fake/convenience.pdf")

        assert result.page_count == 1
        assert result.text_layer_quality > 0.0

    @patch(_FITZ_MODULE)
    def test_convenience_function_uses_default_threshold(
        self, mock_fitz: MagicMock, mock_clean_page: MagicMock
    ) -> None:
        """The convenience function should use the default 0.85 threshold."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            analyze_text_layer,
        )

        doc = _make_mock_doc([mock_clean_page])
        mock_fitz.open.return_value = doc

        result = analyze_text_layer("/fake/default_threshold.pdf")

        # Clean page with embedded font and precise coords -> should exceed 0.85.
        assert result.text_layer_skip_ocr is True


# ---------------------------------------------------------------------------
# Test class: TextLayerAnalysisResult dataclass
# ---------------------------------------------------------------------------


class TestTextLayerAnalysisResult:
    """Tests for the ``TextLayerAnalysisResult`` frozen dataclass."""

    def test_result_is_frozen(self) -> None:
        """Fields should not be reassignable (frozen dataclass)."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalysisResult,
        )

        result = TextLayerAnalysisResult(
            text_layer_quality=0.9,
            text_layer_skip_ocr=True,
            extractability_rate=1.0,
            replacement_char_ratio=0.0,
            font_embedding_score=1.0,
            coordinate_precision_score=0.8,
            page_count=1,
            total_characters=100,
            confidence=0.8,
        )
        with pytest.raises(AttributeError):
            result.text_layer_quality = 0.5  # type: ignore[misc]

    def test_result_equality(self) -> None:
        """Two results with identical values should be equal."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalysisResult,
        )

        kwargs = {
            "text_layer_quality": 0.9,
            "text_layer_skip_ocr": True,
            "extractability_rate": 1.0,
            "replacement_char_ratio": 0.0,
            "font_embedding_score": 1.0,
            "coordinate_precision_score": 0.8,
            "page_count": 1,
            "total_characters": 100,
            "confidence": 0.8,
        }
        assert TextLayerAnalysisResult(**kwargs) == TextLayerAnalysisResult(**kwargs)


# ---------------------------------------------------------------------------
# Test class: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case and boundary-value tests."""

    @patch(_FITZ_MODULE)
    def test_page_with_only_whitespace(self, mock_fitz: MagicMock) -> None:
        """A page containing only whitespace should count as having no text."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(text="   \n\t  ", words=[], fonts=[])
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/whitespace.pdf")

        assert result.extractability_rate == pytest.approx(0.0)

    @patch(_FITZ_MODULE)
    def test_page_with_no_fonts_referenced(self, mock_fitz: MagicMock) -> None:
        """A page with text but no font references should get perfect font score."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(
            text="Text without font references.",
            words=[(100.5, 200.3, 150.7, 220.1, "Text", 0, 0, 0)],
            fonts=[],  # no fonts
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/no_fonts.pdf")

        # No fonts = nothing to fail on, score defaults to 1.0.
        assert result.font_embedding_score == pytest.approx(1.0)

    @patch(_FITZ_MODULE)
    def test_page_with_no_words(self, mock_fitz: MagicMock) -> None:
        """A page with text but no word boxes should get neutral coord score."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(
            text="Has text.",
            words=[],  # no words (unusual but possible)
            fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/no_words.pdf")

        # Neutral default when no coordinate data.
        assert result.coordinate_precision_score == pytest.approx(0.5)

    @patch(_FITZ_MODULE)
    def test_mixed_round_and_precise_coords(self, mock_fitz: MagicMock) -> None:
        """Pages with a mix of round and precise coordinates."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(
            text="Mixed precision coordinates.",
            words=[
                # word 1: 2 round (x0=100.0, y0=200.0), 2 precise -> 4 total coords
                (100.0, 200.0, 150.7, 220.1, "Mixed", 0, 0, 0),
            ],
            fonts=[(0, "ttf", "TrueType", "Helvetica", "Helv", 1)],
        )
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/mixed_coords.pdf")

        # 2 of 4 coords are round -> 50% round -> precision = 0.5
        assert abs(result.coordinate_precision_score - 0.5) < 1e-6

    @patch(_FITZ_MODULE)
    def test_doc_close_called_even_on_error(self, mock_fitz: MagicMock) -> None:
        """The document should be closed even if analysis raises."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        bad_page = MagicMock()
        bad_page.get_text.side_effect = RuntimeError("corrupt page")

        doc = _make_mock_doc([bad_page])
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        with pytest.raises(RuntimeError, match="corrupt page"):
            analyzer.analyze("/fake/error.pdf")

        doc.close.assert_called_once()

    @patch(_FITZ_MODULE)
    def test_large_page_count_high_confidence(self, mock_fitz: MagicMock) -> None:
        """A PDF with many pages and lots of text should yield high confidence."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        pages = [_make_mock_page(text=f"Page {i} " * 100) for i in range(10)]
        doc = _make_mock_doc(pages)
        mock_fitz.open.return_value = doc

        analyzer = TextLayerAnalyzer()
        result = analyzer.analyze("/fake/bigdoc.pdf")

        assert result.page_count == 10
        assert result.confidence >= 0.9

    @patch(_FITZ_MODULE)
    def test_skip_ocr_false_at_boundary(self, mock_fitz: MagicMock) -> None:
        """Quality exactly at the threshold boundary should still skip OCR."""
        from image_preprocessing_detector.classification.text_layer_analyzer import (
            TextLayerAnalyzer,
        )

        page = _make_mock_page(text="Threshold test.")
        doc = _make_mock_doc([page])
        mock_fitz.open.return_value = doc

        # Use a threshold of 0.0 so any quality should pass.
        analyzer = TextLayerAnalyzer(skip_ocr_threshold=0.0)
        result = analyzer.analyze("/fake/boundary.pdf")

        assert result.text_layer_skip_ocr is True
