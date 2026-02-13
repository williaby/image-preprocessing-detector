"""Classification module for document type, degradation severity, and source.

This module provides utilities for classifying PDFs into different types
(born_digital, image_only, hybrid) based on text content and embedded images,
for classifying degradation severity (simple/complex) for routing decisions,
and for classifying document capture method (scanner vs. camera).
"""

from image_preprocessing_detector.classification.degradation_classifier import (
    DegradationClassification,
    DegradationInput,
    DegradationSeverityClassifier,
    classify_degradation_severity,
)
from image_preprocessing_detector.classification.document_source_classifier import (
    DocumentSourceClassifier,
    DocumentSourceResult,
    classify_document_source,
)
from image_preprocessing_detector.classification.pdf_image_detector import (
    detect_embedded_images,
)
from image_preprocessing_detector.classification.pdf_text_extractor import (
    extract_text_from_pdf,
)
from image_preprocessing_detector.classification.pdf_type_classifier import (
    classify_pdf_type,
)
from image_preprocessing_detector.classification.text_layer_analyzer import (
    TextLayerAnalysisResult,
    TextLayerAnalyzer,
    analyze_text_layer,
)

__all__ = [
    "DegradationClassification",
    "DegradationInput",
    "DegradationSeverityClassifier",
    "DocumentSourceClassifier",
    "DocumentSourceResult",
    "TextLayerAnalysisResult",
    "TextLayerAnalyzer",
    "analyze_text_layer",
    "classify_degradation_severity",
    "classify_document_source",
    "classify_pdf_type",
    "detect_embedded_images",
    "extract_text_from_pdf",
]
