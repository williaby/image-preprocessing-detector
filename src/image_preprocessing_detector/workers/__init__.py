"""Celery worker pool for distributed document processing.

This module provides distributed task processing for:
- Document IQA analysis
- Batch processing
- ML model inference

Phase 4 Integration - Week 17 Sprint 4.3.5
"""

from image_preprocessing_detector.workers.celery_app import celery_app
from image_preprocessing_detector.workers.tasks import (
    process_batch_documents,
    process_single_document,
    run_iqa_analysis,
)

__all__ = [
    "celery_app",
    "process_batch_documents",
    "process_single_document",
    "run_iqa_analysis",
]
