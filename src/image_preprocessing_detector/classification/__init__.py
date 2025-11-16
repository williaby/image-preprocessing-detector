"""
PDF classification module for detecting document types.

This module provides utilities for classifying PDFs into different types
(born_digital, image_only, hybrid) based on text content and embedded images.
"""

from image_preprocessing_detector.classification.pdf_image_detector import (
    detect_embedded_images,
)
from image_preprocessing_detector.classification.pdf_text_extractor import (
    extract_text_from_pdf,
)
from image_preprocessing_detector.classification.pdf_type_classifier import (
    classify_pdf_type,
)

__all__ = [
    "classify_pdf_type",
    "detect_embedded_images",
    "extract_text_from_pdf",
]
