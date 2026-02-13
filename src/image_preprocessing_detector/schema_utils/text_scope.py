"""Text Scope Classification for Document Images.

Provides standardized vocabulary for describing the text content scope
of document image samples. The granularity of text content significantly
impacts:
- OCR model selection (character-level vs word-level vs document-level)
- Training data suitability (some models need word-level, others document-level)
- Quality assessment metrics (different metrics apply at different scales)

Scope Hierarchy:
    CHARACTER < WORD < PHRASE < SENTENCE < PARAGRAPH < PAGE < DOCUMENT

References:
- IAM Handwriting Database: Word and line-level annotations
- COCO-Text: Word-level text detection
- DocLayNet: Document-level layout annotations
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict


class TextScope(StrEnum):
    """Text content scope/granularity classification.

    Ordered from smallest to largest unit of text.
    """

    CHARACTER = "character"  # Single character (e.g., MNIST, Kuzushiji)
    WORD = "word"  # Single word (e.g., IAM words, COCO-Text)
    PHRASE = "phrase"  # 2-5 words, short expression
    SENTENCE = "sentence"  # Complete sentence (e.g., IAM sentences)
    LINE = "line"  # Single text line (may span multiple sentences)
    PARAGRAPH = "paragraph"  # Multiple sentences, single block
    PAGE = "page"  # Full page with multiple paragraphs
    DOCUMENT = "document"  # Multi-page document
    MIXED = "mixed"  # Variable scope within dataset
    UNKNOWN = "unknown"  # Scope not determined


class TextDensity(StrEnum):
    """Text density classification based on text-to-image ratio."""

    SPARSE = "sparse"  # < 10% text coverage
    LIGHT = "light"  # 10-25% text coverage
    MODERATE = "moderate"  # 25-50% text coverage
    DENSE = "dense"  # 50-75% text coverage
    VERY_DENSE = "very_dense"  # > 75% text coverage


class ContentType(StrEnum):
    """Primary content type classification."""

    PRINTED = "printed"  # Machine-printed text
    HANDWRITTEN = "handwritten"  # Handwritten text
    MIXED_PRINT_HW = "mixed"  # Both printed and handwritten
    SCENE_TEXT = "scene_text"  # Text in natural scenes
    SYNTHETIC = "synthetic"  # Synthetically generated text
    UNKNOWN = "unknown"


# Scope ordering for comparison
SCOPE_ORDER: dict[TextScope, int] = {
    TextScope.CHARACTER: 0,
    TextScope.WORD: 1,
    TextScope.PHRASE: 2,
    TextScope.SENTENCE: 3,
    TextScope.LINE: 4,
    TextScope.PARAGRAPH: 5,
    TextScope.PAGE: 6,
    TextScope.DOCUMENT: 7,
    TextScope.MIXED: -1,  # Cannot be ordered
    TextScope.UNKNOWN: -1,  # Cannot be ordered
}


# Typical character counts per scope (approximate ranges)
SCOPE_CHAR_RANGES: dict[TextScope, tuple[int, int]] = {
    TextScope.CHARACTER: (1, 1),
    TextScope.WORD: (2, 20),
    TextScope.PHRASE: (10, 50),
    TextScope.SENTENCE: (30, 200),
    TextScope.LINE: (20, 150),
    TextScope.PARAGRAPH: (100, 1000),
    TextScope.PAGE: (500, 5000),
    TextScope.DOCUMENT: (1000, 100000),
}


# Typical word counts per scope (approximate ranges)
SCOPE_WORD_RANGES: dict[TextScope, tuple[int, int]] = {
    TextScope.CHARACTER: (0, 0),
    TextScope.WORD: (1, 1),
    TextScope.PHRASE: (2, 5),
    TextScope.SENTENCE: (5, 30),
    TextScope.LINE: (3, 20),
    TextScope.PARAGRAPH: (20, 200),
    TextScope.PAGE: (100, 1000),
    TextScope.DOCUMENT: (200, 20000),
}


@dataclass(frozen=True)
class TextScopeSpec:
    """Text scope specification with metadata."""

    scope: TextScope
    min_chars: int
    max_chars: int
    min_words: int
    max_words: int
    typical_uses: tuple[str, ...]


# Detailed scope specifications
TEXT_SCOPE_SPECS: dict[TextScope, TextScopeSpec] = {
    TextScope.CHARACTER: TextScopeSpec(
        scope=TextScope.CHARACTER,
        min_chars=1,
        max_chars=1,
        min_words=0,
        max_words=0,
        typical_uses=(
            "character recognition",
            "digit recognition",
            "symbol classification",
        ),
    ),
    TextScope.WORD: TextScopeSpec(
        scope=TextScope.WORD,
        min_chars=2,
        max_chars=20,
        min_words=1,
        max_words=1,
        typical_uses=(
            "word recognition",
            "lexicon-based OCR",
            "handwriting recognition",
        ),
    ),
    TextScope.PHRASE: TextScopeSpec(
        scope=TextScope.PHRASE,
        min_chars=10,
        max_chars=50,
        min_words=2,
        max_words=5,
        typical_uses=("short text recognition", "caption extraction", "label reading"),
    ),
    TextScope.SENTENCE: TextScopeSpec(
        scope=TextScope.SENTENCE,
        min_chars=30,
        max_chars=200,
        min_words=5,
        max_words=30,
        typical_uses=(
            "sentence-level OCR",
            "grammar-aware recognition",
            "NLP integration",
        ),
    ),
    TextScope.LINE: TextScopeSpec(
        scope=TextScope.LINE,
        min_chars=20,
        max_chars=150,
        min_words=3,
        max_words=20,
        typical_uses=("line-level recognition", "receipt OCR", "form field extraction"),
    ),
    TextScope.PARAGRAPH: TextScopeSpec(
        scope=TextScope.PARAGRAPH,
        min_chars=100,
        max_chars=1000,
        min_words=20,
        max_words=200,
        typical_uses=(
            "paragraph extraction",
            "block segmentation",
            "text flow analysis",
        ),
    ),
    TextScope.PAGE: TextScopeSpec(
        scope=TextScope.PAGE,
        min_chars=500,
        max_chars=5000,
        min_words=100,
        max_words=1000,
        typical_uses=("full page OCR", "layout analysis", "document digitization"),
    ),
    TextScope.DOCUMENT: TextScopeSpec(
        scope=TextScope.DOCUMENT,
        min_chars=1000,
        max_chars=100000,
        min_words=200,
        max_words=20000,
        typical_uses=(
            "document understanding",
            "multi-page processing",
            "book digitization",
        ),
    ),
}


class TextScopeInfo(TypedDict):
    """Text scope detection result for schema integration."""

    scope: str  # TextScope enum value
    content_type: str  # ContentType enum value
    density: str  # TextDensity enum value
    estimated_chars: int | None
    estimated_words: int | None
    confidence: float  # Detection confidence (0-1)
    detection_method: str  # How scope was determined


def estimate_scope_from_chars(char_count: int) -> TextScope:
    """Estimate text scope from character count.

    Args:
        char_count: Number of characters in the text

    Returns:
        Best-matching TextScope
    """
    if char_count <= 1:
        return TextScope.CHARACTER
    if char_count <= 20:
        return TextScope.WORD
    if char_count <= 50:
        return TextScope.PHRASE
    if char_count <= 200:
        return TextScope.SENTENCE
    if char_count <= 1000:
        return TextScope.PARAGRAPH
    if char_count <= 5000:
        return TextScope.PAGE
    return TextScope.DOCUMENT


def estimate_scope_from_words(word_count: int) -> TextScope:
    """Estimate text scope from word count.

    Args:
        word_count: Number of words in the text

    Returns:
        Best-matching TextScope
    """
    if word_count == 0:
        return TextScope.CHARACTER
    if word_count == 1:
        return TextScope.WORD
    if word_count <= 5:
        return TextScope.PHRASE
    if word_count <= 30:
        return TextScope.SENTENCE
    if word_count <= 200:
        return TextScope.PARAGRAPH
    if word_count <= 1000:
        return TextScope.PAGE
    return TextScope.DOCUMENT


def estimate_scope_from_dimensions(
    width_px: int,
    height_px: int,
    dpi: int = 300,
) -> TextScope:
    """Estimate text scope from image dimensions.

    Uses typical document dimensions to infer scope.
    Assumes standard document proportions.

    Args:
        width_px: Image width in pixels
        height_px: Image height in pixels
        dpi: Dots per inch (default 300)

    Returns:
        Best-matching TextScope
    """
    # Convert to inches
    width_in = width_px / dpi
    height_in = height_px / dpi

    # Calculate area in square inches
    area_sq_in = width_in * height_in

    # Heuristic based on typical text regions
    if area_sq_in < 0.1:  # < 0.1 sq in
        return TextScope.CHARACTER
    if area_sq_in < 0.5:  # < 0.5 sq in
        return TextScope.WORD
    if area_sq_in < 2:  # < 2 sq in
        return TextScope.PHRASE
    if area_sq_in < 5:  # < 5 sq in
        return TextScope.SENTENCE
    if area_sq_in < 20:  # < 20 sq in
        return TextScope.PARAGRAPH
    if area_sq_in < 100:  # < 100 sq in (typical page)
        return TextScope.PAGE
    return TextScope.DOCUMENT


def create_text_scope_info(
    scope: TextScope | str,
    content_type: ContentType | str = ContentType.UNKNOWN,
    density: TextDensity | str = TextDensity.MODERATE,
    estimated_chars: int | None = None,
    estimated_words: int | None = None,
    confidence: float = 1.0,
    detection_method: str = "manual",
) -> TextScopeInfo:
    """Create a TextScopeInfo dict for schema integration.

    Args:
        scope: Text scope classification
        content_type: Primary content type (printed/handwritten/etc.)
        density: Text density classification
        estimated_chars: Estimated character count (optional)
        estimated_words: Estimated word count (optional)
        confidence: Detection confidence (0-1)
        detection_method: How scope was determined

    Returns:
        TextScopeInfo TypedDict
    """
    # Convert enums to strings if needed
    scope_str = scope.value if isinstance(scope, TextScope) else scope
    content_str = (
        content_type.value if isinstance(content_type, ContentType) else content_type
    )
    density_str = density.value if isinstance(density, TextDensity) else density

    return TextScopeInfo(
        scope=scope_str,
        content_type=content_str,
        density=density_str,
        estimated_chars=estimated_chars,
        estimated_words=estimated_words,
        confidence=round(confidence, 3),
        detection_method=detection_method,
    )


def compare_scopes(scope1: TextScope, scope2: TextScope) -> int:
    """Compare two text scopes.

    Args:
        scope1: First scope
        scope2: Second scope

    Returns:
        -1 if scope1 < scope2
         0 if scope1 == scope2
         1 if scope1 > scope2
        None if comparison not possible (MIXED or UNKNOWN)
    """
    order1 = SCOPE_ORDER.get(scope1, -1)
    order2 = SCOPE_ORDER.get(scope2, -1)

    if order1 < 0 or order2 < 0:
        return 0  # Cannot compare

    if order1 < order2:
        return -1
    if order1 > order2:
        return 1
    return 0


def is_scope_compatible(
    sample_scope: TextScope,
    required_scope: TextScope,
    allow_larger: bool = True,
) -> bool:
    """Check if a sample's scope is compatible with a required scope.

    Args:
        sample_scope: The scope of the sample
        required_scope: The required scope for the task
        allow_larger: If True, larger scopes are also compatible

    Returns:
        True if compatible, False otherwise

    Example:
        >>> is_scope_compatible(TextScope.PAGE, TextScope.SENTENCE, allow_larger=True)
        True  # Page contains sentences
        >>> is_scope_compatible(TextScope.WORD, TextScope.SENTENCE, allow_larger=True)
        False  # Word is smaller than sentence
    """
    if sample_scope == required_scope:
        return True

    if sample_scope in (TextScope.MIXED, TextScope.UNKNOWN):
        return False
    if required_scope in (TextScope.MIXED, TextScope.UNKNOWN):
        return True

    sample_order = SCOPE_ORDER[sample_scope]
    required_order = SCOPE_ORDER[required_scope]

    if allow_larger:
        return sample_order >= required_order
    return sample_order == required_order


# Dataset scope mappings (common datasets)
DATASET_SCOPE_DEFAULTS: dict[str, TextScope] = {
    # Character-level
    "mnist": TextScope.CHARACTER,
    "emnist": TextScope.CHARACTER,
    "kuzushiji": TextScope.CHARACTER,
    "omniglot": TextScope.CHARACTER,
    # Word-level
    "iam_words": TextScope.WORD,
    "coco_text": TextScope.WORD,
    "svt": TextScope.WORD,
    "iiit5k": TextScope.WORD,
    "icdar2013": TextScope.WORD,
    # Line-level
    "iam_lines": TextScope.LINE,
    "rimes": TextScope.LINE,
    # Sentence-level
    "iam_sentences": TextScope.SENTENCE,
    # Page/Document-level
    "doclaynet": TextScope.PAGE,
    "publaynet": TextScope.PAGE,
    "funsd": TextScope.PAGE,
    "cord": TextScope.PAGE,
    "sroie": TextScope.PAGE,
    "rvl_cdip": TextScope.PAGE,
    "docvqa": TextScope.PAGE,
    "infographics_vqa": TextScope.PAGE,
}
