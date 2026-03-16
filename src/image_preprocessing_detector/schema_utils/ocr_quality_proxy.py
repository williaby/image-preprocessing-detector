"""OCR quality proxy metrics for document images without ground truth text.

Computes proxy metrics from OCR output characteristics to estimate text
extraction quality. Designed for DIQA-OCR correlation analysis where no
ground truth transcription exists, but OCR output and layout detections
are available.

Nine metrics in three groups:

**Group A -- Text Extraction Volume**:
    text_yield, word_density, ocr_completeness

**Group B -- Intra-Document Coherence**:
    cjk_latin_consistency, line_regularity, valid_char_rate

**Group C -- Cross-Signal Agreement**:
    layout_text_agreement, ori_res_text_delta, siglip2_ocr_agreement

Example:
    >>> from image_preprocessing_detector.schema_utils.ocr_quality_proxy import (
    ...     compute_text_yield,
    ...     compute_line_regularity,
    ...     compute_all_proxies,
    ... )
    >>> yield_score = compute_text_yield("Hello world", 1000, 2000)
    >>> assert yield_score > 0.0
"""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class OcrProxyMetrics:
    """Per-image OCR quality proxy metrics.

    Attributes:
        text_yield: Characters extracted per megapixel of image area.
        word_density: Words per unit of text-region area (px^2), or 0.0.
        ocr_completeness: Fraction of layout text regions with extracted text.
        cjk_latin_consistency: Normalized Shannon entropy of Unicode block
            distribution (0=single block, 1=maximally dispersed/garbled).
        line_regularity: 1 - coefficient of variation of line lengths.
            Higher = more regular (well-extracted text).
        valid_char_rate: Fraction of non-whitespace chars in expected Unicode
            categories (Lo, Lu, Ll, Nd, Po, Ps, Pe). Garbled OCR produces
            control chars and private-use-area characters.
        layout_text_agreement: Normalized agreement between layout text-region
            count and OCR text volume. 1.0 = perfect agreement.
        ori_res_text_delta: Change in text_yield relative to the original
            image (for paired datasets). None if not applicable.
        siglip2_ocr_agreement: 1 - |normalized_iqa_mu - normalized_text_yield|.
            1.0 = perfect agreement. None if SigLIP2 data unavailable.
    """

    text_yield: float
    word_density: float
    ocr_completeness: float
    cjk_latin_consistency: float
    line_regularity: float
    valid_char_rate: float
    layout_text_agreement: float
    ori_res_text_delta: float | None = None
    siglip2_ocr_agreement: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        """Serialize to JSON-compatible dictionary."""
        result: dict[str, float | None] = {
            "text_yield": round(self.text_yield, 6),
            "word_density": round(self.word_density, 8),
            "ocr_completeness": round(self.ocr_completeness, 4),
            "cjk_latin_consistency": round(self.cjk_latin_consistency, 4),
            "line_regularity": round(self.line_regularity, 4),
            "valid_char_rate": round(self.valid_char_rate, 4),
            "layout_text_agreement": round(self.layout_text_agreement, 4),
        }
        if self.ori_res_text_delta is not None:
            result["ori_res_text_delta"] = round(self.ori_res_text_delta, 6)
        else:
            result["ori_res_text_delta"] = None
        if self.siglip2_ocr_agreement is not None:
            result["siglip2_ocr_agreement"] = round(self.siglip2_ocr_agreement, 4)
        else:
            result["siglip2_ocr_agreement"] = None
        return result


# -----------------------------------------------------------------------
# Valid Unicode categories for document text
# -----------------------------------------------------------------------
_VALID_CATEGORIES = frozenset(
    {
        "Lo",  # Other letter (CJK ideographs, etc.)
        "Lu",  # Uppercase letter
        "Ll",  # Lowercase letter
        "Lt",  # Titlecase letter
        "Lm",  # Modifier letter
        "Nd",  # Decimal digit
        "Nl",  # Letter number (Roman numerals, etc.)
        "Po",  # Other punctuation
        "Ps",  # Open punctuation
        "Pe",  # Close punctuation
        "Pi",  # Initial quote
        "Pf",  # Final quote
        "Pd",  # Dash punctuation
        "Sc",  # Currency symbol
        "Sm",  # Math symbol
        "No",  # Other number (superscripts, fractions)
    }
)


# -----------------------------------------------------------------------
# Group A: Text Extraction Volume
# -----------------------------------------------------------------------


def compute_text_yield(
    text: str,
    image_width: int,
    image_height: int,
) -> float:
    """Characters extracted per megapixel of image area.

    Args:
        text: Extracted OCR text.
        image_width: Image width in pixels.
        image_height: Image height in pixels.

    Returns:
        Characters per megapixel. 0.0 if image area is zero.
    """
    area_mpx = (image_width * image_height) / 1_000_000.0
    if area_mpx <= 0.0:
        return 0.0
    char_count = len(text.replace(" ", "").replace("\n", ""))
    return char_count / area_mpx


def compute_word_density(
    text: str,
    text_region_area_px: float,
) -> float:
    """Words per square pixel of text-region area.

    Args:
        text: Extracted OCR text.
        text_region_area_px: Total area in pixels of layout text regions.

    Returns:
        Word density. 0.0 if text_region_area is zero.
    """
    if text_region_area_px <= 0.0:
        return 0.0
    words = text.split()
    return len(words) / text_region_area_px


def compute_ocr_completeness(
    text_char_count: int,
    layout_text_region_count: int,
) -> float:
    """Ratio of text volume to text regions detected by layout.

    A simple proxy: if layout detects N text regions but OCR produces
    very few characters, OCR likely failed on some regions. Normalized
    to [0, 1] using a saturation threshold of 50 chars per region.

    Args:
        text_char_count: Total non-whitespace characters from OCR.
        layout_text_region_count: Number of text-class regions from layout.

    Returns:
        Completeness score in [0, 1]. 1.0 if all regions well-populated.
    """
    if layout_text_region_count <= 0:
        return 1.0 if text_char_count > 0 else 0.0
    chars_per_region = text_char_count / layout_text_region_count
    # Saturate at 50 chars/region (typical for a text line)
    return min(1.0, chars_per_region / 50.0)


# -----------------------------------------------------------------------
# Group B: Intra-Document Coherence
# -----------------------------------------------------------------------


def compute_cjk_latin_consistency(text: str) -> float:
    """Normalized Shannon entropy of Unicode block distribution.

    Well-formed documents use a small number of Unicode blocks (e.g.,
    CJK Unified + Basic Latin). Garbled OCR scatters characters across
    many blocks. Returns 0 for single-block text, 1 for maximally
    dispersed text.

    Args:
        text: Extracted OCR text (whitespace excluded from analysis).

    Returns:
        Normalized entropy in [0, 1]. Lower = more consistent.
    """
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 2:
        return 0.0

    # Map each char to its Unicode block (first 2 hex digits of codepoint)
    block_counts: Counter[int] = Counter()
    for c in chars:
        # Use codepoint >> 8 as a coarse block identifier
        block_counts[ord(c) >> 8] += 1

    total = sum(block_counts.values())
    if total == 0:
        return 0.0

    # Shannon entropy
    entropy = 0.0
    for count in block_counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    # Normalize by log2(num_blocks) for [0,1] range
    num_blocks = len(block_counts)
    if num_blocks <= 1:
        return 0.0
    max_entropy = math.log2(num_blocks)
    return entropy / max_entropy


def compute_line_regularity(text: str) -> float:
    """Regularity of line lengths in extracted text.

    Well-extracted text has consistent line lengths (wrapping at similar
    column widths). Garbled OCR produces erratic line lengths.

    Returns 1 - CV (coefficient of variation), clamped to [0, 1].
    Higher = more regular.

    Args:
        text: Extracted OCR text.

    Returns:
        Regularity score in [0, 1]. 1.0 = perfectly uniform lines.
    """
    lines = [line for line in text.split("\n") if len(line.strip()) > 0]
    if len(lines) < 3:
        return 0.5  # Insufficient data for meaningful CV

    lengths = [len(line) for line in lines]
    mean_len = sum(lengths) / len(lengths)
    if mean_len <= 0:
        return 0.0

    variance = sum((length - mean_len) ** 2 for length in lengths) / len(lengths)
    std_len = math.sqrt(variance)
    cv = std_len / mean_len

    return max(0.0, min(1.0, 1.0 - cv))


def compute_valid_char_rate(text: str) -> float:
    """Fraction of non-whitespace chars in expected Unicode categories.

    Document text should consist of letters, digits, and standard
    punctuation. Garbled OCR produces control characters, private-use
    area chars, and replacement characters.

    Args:
        text: Extracted OCR text.

    Returns:
        Valid character rate in [0, 1]. Higher = cleaner text.
    """
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0

    valid_count = sum(1 for c in chars if unicodedata.category(c) in _VALID_CATEGORIES)
    return valid_count / len(chars)


# -----------------------------------------------------------------------
# Group C: Cross-Signal Agreement
# -----------------------------------------------------------------------


def compute_layout_text_agreement(
    text_char_count: int,
    layout_text_region_count: int,
    layout_text_area_ratio: float,
) -> float:
    """Agreement between layout detection and OCR text extraction.

    Measures whether text regions detected by layout analysis actually
    produced OCR text. Disagreement (many regions, little text) suggests
    quality issues.

    Args:
        text_char_count: Total non-whitespace OCR characters.
        layout_text_region_count: Number of text-class layout regions.
        layout_text_area_ratio: Fraction of image area covered by text regions.

    Returns:
        Agreement score in [0, 1]. 1.0 = consistent signals.
    """
    if layout_text_region_count == 0 and text_char_count == 0:
        return 1.0  # Both agree: no text
    if layout_text_region_count == 0:
        return 0.5  # OCR found text but layout didn't (ambiguous)

    # Expected chars given text area and region count
    # Heuristic: ~100 chars per region is typical
    expected_chars = (
        layout_text_region_count * 100.0 * max(0.1, layout_text_area_ratio * 10)
    )
    if expected_chars <= 0:
        return 0.5

    ratio = text_char_count / expected_chars
    # Map ratio to [0, 1] agreement: ratio near 1.0 = good
    # Use exponential decay for distance from 1.0
    distance = abs(math.log(max(ratio, 0.01)))
    return math.exp(-distance)


def compute_ori_res_text_delta(
    res_text_yield: float,
    ori_text_yield: float,
) -> float:
    """Change in text yield from original to enhanced image.

    For paired datasets (DIQA-5000), enhanced images with higher MOS
    should yield more/better text extraction.

    Args:
        res_text_yield: text_yield of the enhanced (res/) image.
        ori_text_yield: text_yield of the original (ori/) image.

    Returns:
        Relative delta: (res - ori) / max(ori, epsilon).
        Positive = enhanced image yields more text.
    """
    epsilon = 1.0  # Avoid division by zero
    return (res_text_yield - ori_text_yield) / max(ori_text_yield, epsilon)


def compute_siglip2_ocr_agreement(
    iqa_overall_mu: float,
    text_yield: float,
    text_yield_max: float,
) -> float:
    """Agreement between SigLIP2 IQA prediction and OCR text yield.

    Both signals should correlate: higher quality images produce more
    readable text. Disagreement suggests calibration issues.

    Args:
        iqa_overall_mu: SigLIP2 overall IQA prediction (0-1 scale).
        text_yield: OCR text_yield for this image.
        text_yield_max: Maximum text_yield across the dataset (for normalization).

    Returns:
        Agreement score in [0, 1]. 1.0 = perfect agreement.
    """
    if text_yield_max <= 0:
        return 0.5

    normalized_yield = min(1.0, text_yield / text_yield_max)
    distance = abs(iqa_overall_mu - normalized_yield)
    return 1.0 - distance


# -----------------------------------------------------------------------
# Convenience: compute all metrics
# -----------------------------------------------------------------------


def compute_all_proxies(
    text: str,
    image_width: int,
    image_height: int,
    layout_text_region_count: int,
    text_region_area_px: float,
    layout_text_area_ratio: float,
    ori_text_yield: float | None = None,
    iqa_overall_mu: float | None = None,
    text_yield_max: float | None = None,
) -> OcrProxyMetrics:
    """Compute all 9 OCR quality proxy metrics for a single image.

    Args:
        text: Extracted OCR text.
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        layout_text_region_count: Number of text-class layout regions.
        text_region_area_px: Total area of text regions in pixels.
        layout_text_area_ratio: Fraction of image area covered by text regions.
        ori_text_yield: text_yield of the paired original image (optional).
        iqa_overall_mu: SigLIP2 IQA overall prediction (optional).
        text_yield_max: Max text_yield across dataset for normalization (optional).

    Returns:
        OcrProxyMetrics with all computed values.
    """
    non_ws_chars = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    text_yield_val = compute_text_yield(text, image_width, image_height)

    ori_res_delta = None
    if ori_text_yield is not None:
        ori_res_delta = compute_ori_res_text_delta(text_yield_val, ori_text_yield)

    siglip2_agreement = None
    if iqa_overall_mu is not None and text_yield_max is not None:
        siglip2_agreement = compute_siglip2_ocr_agreement(
            iqa_overall_mu, text_yield_val, text_yield_max
        )

    return OcrProxyMetrics(
        text_yield=text_yield_val,
        word_density=compute_word_density(text, text_region_area_px),
        ocr_completeness=compute_ocr_completeness(
            non_ws_chars, layout_text_region_count
        ),
        cjk_latin_consistency=compute_cjk_latin_consistency(text),
        line_regularity=compute_line_regularity(text),
        valid_char_rate=compute_valid_char_rate(text),
        layout_text_agreement=compute_layout_text_agreement(
            non_ws_chars, layout_text_region_count, layout_text_area_ratio
        ),
        ori_res_text_delta=ori_res_delta,
        siglip2_ocr_agreement=siglip2_agreement,
    )
