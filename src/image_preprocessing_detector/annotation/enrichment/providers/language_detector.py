# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""OpenLID-v2 Language Detection Provider.

This module provides language and script detection for document images using
the OpenLID-v2 model. It extracts text from parser outputs and uses fasttext-based
language identification to populate EnrichmentData with ISO-compliant codes.

Classes:
    LanguageDetectionProvider: Enrichment provider for language/script detection

Text Sources (priority order):
    1. OriginalLabels.transcription - Direct ground truth text
    2. OriginalLabels.text_instances - Scene text word/line annotations
    3. OriginalLabels.raw_labels["text_lines"] - Line-level text (e.g., muharaf)
    4. OriginalLabels.raw_labels["answer"] - OCR answer text (e.g., cc-ocr)
    5. Docling OCR (if no ground truth available) - NOT YET IMPLEMENTED

Example:
    >>> from image_preprocessing_detector.annotation.enrichment.providers.language_detector import (
    ...     LanguageDetectionProvider,
    ... )
    >>> from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels
    >>>
    >>> provider = LanguageDetectionProvider()
    >>> labels = OriginalLabels(transcription="Hello, world!")
    >>> enrichment = provider.enrich_from_labels(labels)
    >>> print(enrichment.iso639_language)  # 'en'
    >>> print(enrichment.iso15924_script)  # 'Latn'
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import EnrichmentError
from ...schemas.enrichment import EnrichmentData
from ...schemas.immutable import OriginalLabels

logger = logging.getLogger(__name__)

# =============================================================================
# Script Family Classification
# =============================================================================

# ISO 15924 to script family mapping
SCRIPT_FAMILIES: dict[str, str] = {
    # Latin family
    "Latn": "latin",
    # Arabic family
    "Arab": "arabic",
    "Aran": "arabic",  # Nastaliq variant
    # CJK family
    "Hans": "cjk",  # Simplified Chinese
    "Hant": "cjk",  # Traditional Chinese
    "Jpan": "cjk",  # Japanese
    "Kore": "cjk",  # Korean
    "Hang": "cjk",  # Hangul
    "Hani": "cjk",  # Han (general)
    "Bopo": "cjk",  # Bopomofo
    # Cyrillic family
    "Cyrl": "cyrillic",
    # Devanagari family (Indic)
    "Deva": "indic",
    "Beng": "indic",
    "Gujr": "indic",
    "Guru": "indic",
    "Orya": "indic",
    "Taml": "indic",
    "Telu": "indic",
    "Knda": "indic",
    "Mlym": "indic",
    "Sinh": "indic",
    "Thai": "indic",
    "Laoo": "indic",
    "Mymr": "indic",
    "Khmr": "indic",
    "Tibt": "indic",
    # Greek family
    "Grek": "greek",
    # Hebrew family
    "Hebr": "hebrew",
    # Ethiopian family
    "Ethi": "ethiopic",
    # Georgian family
    "Geor": "georgian",
    # Armenian family
    "Armn": "armenian",
    # Unknown/undetermined
    "Zyyy": "common",  # Common (numbers, punctuation)
    "Zinh": "inherited",
    "Zzzz": "unknown",
}


def get_script_family(script_code: str) -> str:
    """Get script family from ISO 15924 code.

    Args:
        script_code: ISO 15924 4-letter script code

    Returns:
        Script family name (latin, arabic, cjk, cyrillic, indic, etc.)
    """
    return SCRIPT_FAMILIES.get(script_code, "other")


# =============================================================================
# Text Extraction
# =============================================================================


@dataclass
class ExtractedText:
    """Result of text extraction from parser output.

    Attributes:
        text: Combined extracted text
        source: Where text came from (transcription, text_instances, raw_labels, etc.)
        char_count: Number of characters extracted
        word_count: Estimated word count
    """

    text: str
    source: str
    char_count: int
    word_count: int

    @classmethod
    def empty(cls) -> ExtractedText:
        """Create empty extraction result."""
        return cls(text="", source="none", char_count=0, word_count=0)


def extract_text_from_labels(labels: OriginalLabels) -> ExtractedText:
    """Extract text content from OriginalLabels.

    Searches multiple fields in priority order to find available text:
    1. transcription - Direct ground truth
    2. text_instances - Scene text annotations
    3. raw_labels.text_lines - Line-level text (muharaf, etc.)
    4. raw_labels.answer - OCR answer (cc-ocr, etc.)
    5. raw_labels.transcription - Fallback transcription

    Args:
        labels: OriginalLabels from parser

    Returns:
        ExtractedText with combined text and source info
    """
    # Priority 1: Direct transcription
    if labels.transcription:
        text = labels.transcription.strip()
        if text:
            words = len(text.split())
            return ExtractedText(
                text=text,
                source="transcription",
                char_count=len(text),
                word_count=words,
            )

    # Priority 2: text_instances (scene text)
    if labels.text_instances:
        texts = []
        for instance in labels.text_instances:
            if isinstance(instance, dict) and instance.get("text"):
                texts.append(str(instance["text"]))
        if texts:
            combined = " ".join(texts)
            return ExtractedText(
                text=combined,
                source="text_instances",
                char_count=len(combined),
                word_count=len(texts),  # Approximate - each instance is ~1 word
            )

    # Priority 3+: raw_labels fields
    if labels.raw_labels:
        # Check text_lines (muharaf PAGE XML)
        if "text_lines" in labels.raw_labels:
            text_lines = labels.raw_labels["text_lines"]
            if isinstance(text_lines, list):
                texts = []
                for line in text_lines:
                    if isinstance(line, dict) and line.get("text"):
                        texts.append(str(line["text"]))
                if texts:
                    combined = " ".join(texts)
                    return ExtractedText(
                        text=combined,
                        source="raw_labels.text_lines",
                        char_count=len(combined),
                        word_count=len(texts),
                    )

        # Check text_regions (muharaf regions with nested lines)
        if "text_regions" in labels.raw_labels:
            regions = labels.raw_labels["text_regions"]
            if isinstance(regions, list):
                texts = []
                for region in regions:
                    if isinstance(region, dict) and "lines" in region:
                        for line in region.get("lines", []):
                            if isinstance(line, dict) and line.get("text"):
                                texts.append(str(line["text"]))
                if texts:
                    combined = " ".join(texts)
                    return ExtractedText(
                        text=combined,
                        source="raw_labels.text_regions",
                        char_count=len(combined),
                        word_count=len(texts),
                    )

        # Check answer field (cc-ocr)
        if "answer" in labels.raw_labels:
            answer = labels.raw_labels["answer"]
            if answer and isinstance(answer, str):
                text = answer.strip()
                if text:
                    return ExtractedText(
                        text=text,
                        source="raw_labels.answer",
                        char_count=len(text),
                        word_count=len(text.split()),
                    )

        # Check generic transcription in raw_labels
        if "transcription" in labels.raw_labels:
            trans = labels.raw_labels["transcription"]
            if trans and isinstance(trans, str):
                text = trans.strip()
                if text:
                    return ExtractedText(
                        text=text,
                        source="raw_labels.transcription",
                        char_count=len(text),
                        word_count=len(text.split()),
                    )

        # Check table_html (for table-heavy datasets)
        if "table_html" in labels.raw_labels or labels.table_html:
            html = labels.table_html or labels.raw_labels.get("table_html", "")
            if html:
                # Simple extraction: strip HTML tags
                import re

                text = re.sub(r"<[^>]+>", " ", html)
                text = " ".join(text.split())
                if text:
                    return ExtractedText(
                        text=text,
                        source="table_html",
                        char_count=len(text),
                        word_count=len(text.split()),
                    )

    return ExtractedText.empty()


# =============================================================================
# Language Detection Provider
# =============================================================================


class LanguageDetectionProvider:
    """OpenLID-v2 based language detection provider.

    Extracts text from parser outputs and uses fasttext-based language
    identification to populate EnrichmentData with ISO-compliant codes.

    Features:
        - ISO 639-1/3 language codes
        - ISO 15924 script codes
        - Script family classification
        - BCP 47 language tags
        - Confidence scores

    Attributes:
        name: Provider identifier ("openlid_v2")
        tier: Enrichment tier ("tier_2_model")
        min_confidence: Minimum confidence threshold
        min_text_length: Minimum text length for reliable detection
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        min_text_length: int = 10,
        model_path: Path | str | None = None,
    ):
        """Initialize language detection provider.

        Args:
            min_confidence: Minimum confidence for valid detection (0.0-1.0)
            min_text_length: Minimum characters needed for reliable detection
            model_path: Optional custom path to OpenLID model
        """
        self.min_confidence = min_confidence
        self.min_text_length = min_text_length
        self._model_path = model_path
        self._detector: Any | None = None

    @property
    def name(self) -> str:
        """Provider name for logging and provenance."""
        return "openlid_v2"

    @property
    def tier(self) -> str:
        """Enrichment tier for this provider."""
        return "tier_2_model"

    def is_available(self) -> bool:
        """Check if OpenLID-v2 model is available."""
        try:
            self._ensure_detector()
            return True
        except Exception as e:
            logger.warning(f"OpenLID-v2 not available: {e}")
            return False

    def _ensure_detector(self) -> None:
        """Ensure OpenLID detector is loaded."""
        if self._detector is not None:
            return

        try:
            from ....schema_utils.openlid_integration import OpenLIDDetector

            self._detector = OpenLIDDetector(
                model_path=self._model_path,
                auto_download=True,
            )
        except ImportError as e:
            raise EnrichmentError(
                "OpenLID dependencies not installed. "
                "Install with: uv add fasttext huggingface_hub"
            ) from e

    def supports(self, image_path: Path) -> bool:
        """Check if this provider should process the given image.

        Always returns True - language detection is applicable to all documents.
        """
        return True

    def detect_language(self, text: str) -> dict[str, Any]:
        """Detect language and script from text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with language detection results
        """
        self._ensure_detector()

        if not text or len(text) < self.min_text_length:
            return {
                "iso639_language": None,
                "iso15924_script": None,
                "script_family": None,
                "bcp47_tag": None,
                "primary_language": None,
                "language_confidence": 0.0,
                "detection_status": "insufficient_text",
            }

        result = self._detector.detect(text, threshold=self.min_confidence)

        if result.language_639_1 == "und":
            return {
                "iso639_language": None,
                "iso15924_script": None,
                "script_family": None,
                "bcp47_tag": None,
                "primary_language": None,
                "language_confidence": result.confidence,
                "detection_status": "undetermined",
            }

        script_family = get_script_family(result.script_code)

        return {
            "iso639_language": result.language_639_1,
            "iso15924_script": result.script_code,
            "script_family": script_family,
            "bcp47_tag": result.bcp47_tag,
            "primary_language": result.language_639_3,  # Store 639-3 as primary
            "language_confidence": result.confidence,
            "detection_status": "detected",
            "language_639_3": result.language_639_3,  # Additional detail
        }

    def enrich_from_labels(
        self,
        labels: OriginalLabels,
        existing: EnrichmentData | None = None,
        preserve_high_confidence: bool = True,
    ) -> EnrichmentData:
        """Enrich from parser labels by extracting text and detecting language.

        This is the primary method for language detection during annotation
        processing. It extracts text from OriginalLabels and runs OpenLID.

        Args:
            labels: OriginalLabels from parser
            existing: Optional existing EnrichmentData to augment
            preserve_high_confidence: If True, don't overwrite existing language
                data if it has higher confidence than new detection

        Returns:
            EnrichmentData with language/script fields populated
        """
        if existing is None:
            existing = EnrichmentData()

        # Extract text from labels
        extracted = extract_text_from_labels(labels)

        if not extracted.text:
            logger.debug("No text found in labels for language detection")
            return existing

        # Detect language
        detection = self.detect_language(extracted.text)

        new_confidence = detection.get("language_confidence", 0.0) or 0.0
        existing_confidence = existing.language_confidence or 0.0

        # Check if we should preserve existing data
        if preserve_high_confidence and existing.iso639_language is not None:
            if existing_confidence >= new_confidence:
                logger.debug(
                    f"Preserving existing language data (conf={existing_confidence:.2%}) "
                    f"over new detection (conf={new_confidence:.2%})"
                )
                # Still update text scope info
                existing.text_scope_estimated_chars = extracted.char_count
                existing.text_scope_estimated_words = extracted.word_count
                return existing

        # Update enrichment data with new detection
        existing.iso639_language = detection.get("iso639_language")
        existing.iso15924_script = detection.get("iso15924_script")
        existing.script_family = detection.get("script_family")
        existing.bcp47_tag = detection.get("bcp47_tag")
        existing.primary_language = detection.get("primary_language")
        existing.language_confidence = detection.get("language_confidence")

        # Also update text scope info
        existing.text_scope_estimated_chars = extracted.char_count
        existing.text_scope_estimated_words = extracted.word_count
        existing.text_scope_detection_method = f"openlid_v2:{extracted.source}"

        return existing

    def enrich(self, image_path: Path) -> EnrichmentData:
        """Enrich a single image.

        Note: This method is for the EnrichmentProvider protocol but language
        detection requires text, not images. For image-based detection, use
        Docling OCR first, then call detect_language() on extracted text.

        Args:
            image_path: Path to image file

        Returns:
            Empty EnrichmentData (images require OCR first)

        Raises:
            NotImplementedError: Direct image detection not supported
        """
        # For now, return empty - images need OCR first
        logger.warning(
            f"Language detection from image not implemented for {image_path}. "
            "Use enrich_from_labels() with parser output, or extract text with Docling."
        )
        return EnrichmentData()

    def enrich_batch(self, image_paths: list[Path]) -> list[EnrichmentData]:
        """Enrich multiple images.

        See enrich() - returns empty EnrichmentData for each image.
        """
        return [self.enrich(p) for p in image_paths]

    def enrich_from_labels_batch(
        self,
        labels_list: list[OriginalLabels],
        existing_list: list[EnrichmentData | None] | None = None,
    ) -> list[EnrichmentData]:
        """Batch process labels for language detection.

        Args:
            labels_list: List of OriginalLabels from parsers
            existing_list: Optional existing EnrichmentData to augment

        Returns:
            List of EnrichmentData with language/script fields populated
        """
        if existing_list is None:
            existing_list = [None] * len(labels_list)

        results = []
        for labels, existing in zip(labels_list, existing_list):
            results.append(self.enrich_from_labels(labels, existing))

        return results


__all__ = [
    "ExtractedText",
    "LanguageDetectionProvider",
    "SCRIPT_FAMILIES",
    "extract_text_from_labels",
    "get_script_family",
]
