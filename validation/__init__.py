"""Validation framework for IQA detectors."""

from validation.synthetic_generator import SyntheticImageGenerator
from validation.validate_detectors import DetectorValidator, ValidationMetrics

__all__ = ["SyntheticImageGenerator", "DetectorValidator", "ValidationMetrics"]
