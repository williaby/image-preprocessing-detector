"""
OCR routing recommendation engine for RAG Pipeline.

Analyzes document characteristics and recommends optimal OCR engine routing.
"""

from image_preprocessing_detector.routing.recommendation_engine import (
    recommend_ocr_routing,
)

__all__ = ["recommend_ocr_routing"]
