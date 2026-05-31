"""PyMuPDF-based analysis of PDF text layers.

Evaluates four signals to determine text layer quality and whether OCR can be
skipped for born-digital or hybrid PDFs:

1. Character extractability rate - ratio of pages with extractable text.
2. Unicode replacement character ratio - high ratio indicates corrupted/missing fonts.
3. Font embedding completeness - whether referenced fonts are embedded.
4. Coordinate precision - suspiciously round coordinates suggest auto-generated layers.

Populates ``DocumentMetadata.text_layer_quality`` and
``DocumentMetadata.text_layer_skip_ocr``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from image_preprocessing_detector.utils import get_logger
from image_preprocessing_detector.utils.path_security import validate_safe_path

try:
    import fitz  # PyMuPDF

    _has_fitz = True
except ImportError:
    fitz = None
    _has_fitz = False

logger = get_logger(__name__)

# Replacement characters that indicate corrupted or missing font mappings.
_REPLACEMENT_CHARS = frozenset(
    {
        "\ufffd",  # U+FFFD REPLACEMENT CHARACTER
        "\ufffe",  # U+FFFE noncharacter (sometimes emitted)
        "\x00",  # NULL byte (rare but possible in broken extractors)
    }
)

# Default weight vector for combining the four signal scores into
# ``text_layer_quality``.  Extractability and font embedding are the
# strongest predictors; replacement chars and coordinate precision are
# secondary.
_DEFAULT_WEIGHTS = {
    "extractability": 0.35,
    "replacement_char": 0.25,
    "font_embedding": 0.25,
    "coordinate_precision": 0.15,
}

# A coordinate decimal component is considered "round" when its fractional
# part is exactly zero (i.e. the value is an integer).
_ROUND_TOLERANCE = 1e-9


@dataclass(frozen=True)
class TextLayerAnalysisResult:
    """Result of PDF text-layer quality analysis.

    All score fields are clamped to the ``[0, 1]`` range.

    Attributes:
        text_layer_quality (float): Weighted aggregate quality score (1 = perfect).
        text_layer_skip_ocr (bool): Whether the quality is high enough to skip OCR.
        extractability_rate (float): Fraction of pages that contain extractable text.
        replacement_char_ratio (float): Fraction of extracted characters that are
            Unicode replacement characters (lower is better; the *score*
            stored here is ``1 - ratio`` so that 1 means no replacements).
        font_embedding_score (float): Fraction of referenced fonts that are embedded.
        coordinate_precision_score (float): Fraction of word coordinates that are
            *not* suspiciously round (1 = all precise).
        page_count (int): Total number of pages analysed.
        total_characters (int): Total characters extracted across all pages.
        confidence (float): Confidence in the result (higher when more data available).
    """

    text_layer_quality: float
    text_layer_skip_ocr: bool
    extractability_rate: float
    replacement_char_ratio: float
    font_embedding_score: float
    coordinate_precision_score: float
    page_count: int
    total_characters: int
    confidence: float


class TextLayerAnalyzer:
    """Analyse the text layer of a PDF document.

    Args:
        skip_ocr_threshold (float): Minimum ``text_layer_quality`` needed to
            recommend skipping OCR.  Defaults to ``0.85``.
        weights (dict[str, float] | None): Optional dict mapping signal names to their weights in the
            aggregate quality calculation.  Keys must be a subset of
            ``{extractability, replacement_char, font_embedding,
            coordinate_precision}``.  Weights are normalised internally.

    Raises:
        ImportError: If PyMuPDF (fitz) is not installed.
        ValueError: If a weight key is invalid or weight value is negative.
    """

    def __init__(
        self,
        skip_ocr_threshold: float = 0.85,
        weights: dict[str, float] | None = None,
    ) -> None:
        if not _has_fitz:
            msg = (
                "PyMuPDF (fitz) is required for TextLayerAnalyzer. "
                "Install it with: pip install PyMuPDF"
            )
            raise ImportError(msg)

        self._skip_ocr_threshold = skip_ocr_threshold

        if weights is not None:
            valid_keys = set(_DEFAULT_WEIGHTS.keys())
            for key, value in weights.items():
                if key not in valid_keys:
                    msg = (
                        f"Invalid weight key {key!r}. "
                        f"Valid keys are: {sorted(valid_keys)}"
                    )
                    raise ValueError(msg)
                if not isinstance(value, (int, float)) or value < 0:
                    msg = (
                        f"Weight for {key!r} must be a non-negative numeric value, "
                        f"got {value!r}"
                    )
                    raise ValueError(msg)
            self._weights = dict(weights)
        else:
            self._weights = dict(_DEFAULT_WEIGHTS)

        # Normalise weights so they sum to 1.
        weight_sum = sum(self._weights.values())
        if weight_sum > 0:
            self._weights = {k: v / weight_sum for k, v in self._weights.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, pdf_path: str | Path) -> TextLayerAnalysisResult:
        """Analyse the text layer of *pdf_path*.

        Args:
            pdf_path (str | Path): Filesystem path to a PDF file (str or Path).

        Returns:
            TextLayerAnalysisResult: A :class:`TextLayerAnalysisResult` with per-signal scores and
            an aggregate quality metric.

        """
        path = validate_safe_path(pdf_path, must_exist=True)

        logger.info("Analysing PDF text layer", path=str(path))

        doc = fitz.open(str(path))
        try:
            page_count: int = doc.page_count
            if page_count == 0:
                return self._empty_result()

            # Accumulate per-page statistics.
            pages_with_text = 0
            total_chars = 0
            replacement_chars = 0
            all_fonts: list[tuple[int, str, str, str, str, int]] = []
            total_coords = 0
            round_coords = 0

            for page in doc:
                text: str = page.get_text()
                if text.strip():
                    pages_with_text += 1

                total_chars += len(text)
                replacement_chars += sum(1 for ch in text if ch in _REPLACEMENT_CHARS)

                # Font information: list of (xref, ext, type, basefont, name, encoding)
                fonts = page.get_fonts()
                all_fonts.extend(fonts)

                # Word-level coordinates for precision analysis.
                words = page.get_text_words()
                for word_info in words:
                    # Tuple layout: (x0, y0, x1, y1, word, block_no, line_no, word_no).
                    coords = word_info[:4]
                    total_coords += len(coords)
                    round_coords += sum(
                        1 for c in coords if abs(c - round(c)) < _ROUND_TOLERANCE
                    )
        finally:
            doc.close()

        # 1. Extractability rate.
        extractability = pages_with_text / page_count if page_count > 0 else 0.0

        # 2. Replacement character ratio (inverted: 1 = no replacements).
        raw_replacement_ratio = (
            replacement_chars / total_chars if total_chars > 0 else 0.0
        )
        replacement_score = 1.0 - raw_replacement_ratio

        # 3. Font embedding completeness.
        font_embedding = self._compute_font_embedding_score(all_fonts)

        # 4. Coordinate precision (inverted: 1 = all precise / non-round).
        if total_coords > 0:
            round_ratio = round_coords / total_coords
            coord_precision = 1.0 - round_ratio
        else:
            # No words at all -- cannot assess; default to neutral 0.5.
            coord_precision = 0.5

        # Aggregate quality using weighted sum.
        quality = self._weighted_quality(
            extractability, replacement_score, font_embedding, coord_precision
        )

        # Confidence is based on data volume: more chars / pages -> higher.
        confidence = self._compute_confidence(page_count, total_chars)

        skip_ocr = quality >= self._skip_ocr_threshold

        result = TextLayerAnalysisResult(
            text_layer_quality=_clamp01(quality),
            text_layer_skip_ocr=skip_ocr,
            extractability_rate=_clamp01(extractability),
            replacement_char_ratio=_clamp01(raw_replacement_ratio),
            font_embedding_score=_clamp01(font_embedding),
            coordinate_precision_score=_clamp01(coord_precision),
            page_count=page_count,
            total_characters=total_chars,
            confidence=_clamp01(confidence),
        )

        logger.info(
            "Text layer analysis complete",
            path=str(path),
            quality=result.text_layer_quality,
            skip_ocr=result.text_layer_skip_ocr,
            pages=page_count,
            characters=total_chars,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _weighted_quality(
        self,
        extractability: float,
        replacement_score: float,
        font_embedding: float,
        coord_precision: float,
    ) -> float:
        """Compute weighted aggregate quality from individual signals."""
        scores = {
            "extractability": extractability,
            "replacement_char": replacement_score,
            "font_embedding": font_embedding,
            "coordinate_precision": coord_precision,
        }
        total = 0.0
        for key, weight in self._weights.items():
            total += weight * scores.get(key, 0.0)
        return total

    @staticmethod
    def _compute_font_embedding_score(
        fonts: list[tuple[int, str, str, str, str, int]],
    ) -> float:
        """Return the fraction of fonts that are embedded.

        PyMuPDF ``page.get_fonts()`` returns tuples of the form
        ``(xref, ext, type, basefont, name, encoding)``.  A font is
        considered embedded when its *ext* field (index 1) is non-empty
        **and** its *name* field (index 4) is non-empty.  The *encoding*
        field (index 5) being non-zero also signals embedding for some
        font types, but the ext+name heuristic is more reliable across
        PDF producers.
        """
        if not fonts:
            # No fonts referenced at all -- treat as perfect (no risk).
            return 1.0

        # Deduplicate by (basefont, name) to avoid over-counting repeated
        # references to the same font across pages.
        seen: set[tuple[str, str]] = set()
        embedded_count = 0
        unique_count = 0

        for font_info in fonts:
            # Tuple layout: (xref, ext, type, basefont, name, encoding).
            basefont = font_info[3]
            name = font_info[4]
            key = (basefont, name)
            if key in seen:
                continue
            seen.add(key)
            unique_count += 1

            ext = font_info[1]
            # A font is embedded when it has both a file extension and a name.
            if ext and name:
                embedded_count += 1

        return embedded_count / unique_count if unique_count > 0 else 1.0

    @staticmethod
    def _compute_confidence(page_count: int, total_chars: int) -> float:
        """Heuristic confidence based on available evidence.

        More pages and more characters give higher confidence.
        Confidence saturates toward 1.0 as character count grows.
        """
        if total_chars == 0:
            return 0.1  # very low -- essentially no data
        if total_chars < 50:
            return 0.3
        if total_chars < 500:
            return 0.6
        if total_chars < 5000:
            return 0.8
        # > 5000 chars: high confidence, small bonus for multi-page.
        bonus = min(page_count * 0.02, 0.1)
        return min(0.9 + bonus, 1.0)

    def _empty_result(self) -> TextLayerAnalysisResult:
        """Return a zero-quality result for PDFs with no pages."""
        return TextLayerAnalysisResult(
            text_layer_quality=0.0,
            text_layer_skip_ocr=False,
            extractability_rate=0.0,
            replacement_char_ratio=0.0,
            font_embedding_score=1.0,
            coordinate_precision_score=0.5,
            page_count=0,
            total_characters=0,
            confidence=0.1,
        )


# ------------------------------------------------------------------
# Module-level convenience function
# ------------------------------------------------------------------


def analyze_text_layer(pdf_path: str | Path) -> TextLayerAnalysisResult:
    """Analyse the PDF text layer at *pdf_path* with default settings.

    This is a thin wrapper around :class:`TextLayerAnalyzer` for quick,
    one-shot usage.

    Args:
        pdf_path (str | Path): Filesystem path to a PDF file (str or Path).

    Returns:
        TextLayerAnalysisResult: A :class:`TextLayerAnalysisResult`.

    """
    analyzer = TextLayerAnalyzer()
    return analyzer.analyze(pdf_path)


# ------------------------------------------------------------------
# Private utilities
# ------------------------------------------------------------------


def _clamp01(value: float) -> float:
    """Clamp *value* to the ``[0, 1]`` range."""
    return max(0.0, min(1.0, value))
