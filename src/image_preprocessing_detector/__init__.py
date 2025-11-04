"""
Image Preprocessing Detector for RAG Applications.

An intelligent image preprocessing pipeline that analyzes documents (PDFs, images)
and automatically detects required preprocessing steps before vector database ingestion.
"""

__version__ = "0.1.0"
__author__ = "Byron Williams"
__email__ = "byronawilliams@gmail.com"

from image_preprocessing_detector.schema import (
    DetectedIssue,
    DocumentElement,
    PageMetadata,
    PlannedAction,
    ProcessingVersion,
    TransformHistory,
)

__all__ = [
    "DetectedIssue",
    "DocumentElement",
    "PageMetadata",
    "PlannedAction",
    "ProcessingVersion",
    "TransformHistory",
    "__version__",
]
