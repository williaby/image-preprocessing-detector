"""Enumeration definitions for the annotation schema.

This module contains all enumeration types used in the three-layer
metadata architecture. Enums are implemented as (str, Enum) for
JSON serialization compatibility.

Taxonomy References:
    - CaptureMethod: Axis 4 from detection-taxonomy.md
    - DomainLevel1: Axis 1 from document-type-taxonomy.md

Example:
    >>> from image_preprocessing_detector.annotation.schemas.enums import (
    ...     CaptureMethod,
    ...     DomainLevel1,
    ...     EnrichmentTier,
    ... )
    >>>
    >>> method = CaptureMethod.SCANNER_FLATBED
    >>> print(method.value)  # "scanner_flatbed"
    >>>
    >>> # JSON-serializable
    >>> import json
    >>> json.dumps({"method": method.value})
"""

from __future__ import annotations

from enum import Enum


class CaptureMethod(str, Enum):
    """Capture method taxonomy (Axis 4 from detection-taxonomy.md).

    Describes how the original document was captured/digitized.

    Attributes:
        BORN_DIGITAL: Created digitally (PDF, Word, etc.)
        SCANNER_FLATBED: Flatbed scanner capture
        SCANNER_ADF: Automatic document feeder scanner
        CAMERA_PROFESSIONAL: Professional camera setup
        CAMERA_SMARTPHONE: Smartphone camera capture
        FAX: Fax machine transmission
        SYNTHETIC: Synthetically generated document (e.g., for training data)
        UNKNOWN: Unknown capture method
    """

    BORN_DIGITAL = "born_digital"
    SCANNER_FLATBED = "scanner_flatbed"
    SCANNER_ADF = "scanner_adf"
    CAMERA_PROFESSIONAL = "camera_professional"
    CAMERA_SMARTPHONE = "camera_smartphone"
    FAX = "fax"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class DomainLevel1(str, Enum):
    """Primary domain codes (Axis 1 from document-type-taxonomy.md).

    High-level document domain classification using 3-letter codes.

    Attributes:
        TAX: Tax-related documents (forms, returns, schedules)
        LEGAL: Legal documents (contracts, filings, briefs)
        FINANCIAL: Financial documents (statements, reports)
        TECHNICAL: Technical documents (manuals, specs)
        SCIENTIFIC: Scientific documents (papers, research)
        ADMINISTRATIVE: Administrative documents (memos, letters)
        MEDICAL: Medical documents (records, prescriptions)
        EDUCATIONAL: Educational documents (textbooks, exams)
        PERSONAL: Personal documents (IDs, certificates)
        UNKNOWN: Unknown or unclassified domain
    """

    TAX = "TAX"
    LEGAL = "LEG"
    FINANCIAL = "FIN"
    TECHNICAL = "TEC"
    SCIENTIFIC = "SCI"
    ADMINISTRATIVE = "ADM"
    MEDICAL = "MED"
    EDUCATIONAL = "EDU"
    PERSONAL = "PER"
    UNKNOWN = "UNK"


class ResolutionCategory(str, Enum):
    """Resolution category bins for image quality assessment.

    Categorizes images by their effective DPI/resolution.

    Attributes:
        LOW: Below 150 DPI - poor quality
        MEDIUM: 150-299 DPI - acceptable quality
        STANDARD: 300 DPI - standard scanning resolution
        HIGH: Above 300 DPI - high quality
    """

    LOW = "low_<150"
    MEDIUM = "medium_150-299"
    STANDARD = "standard_300"
    HIGH = "high_>300"


class EnrichmentTier(str, Enum):
    """Enrichment source tier for provenance tracking.

    Indicates the confidence/source of derived annotations.
    Lower tier numbers indicate higher confidence.

    Attributes:
        TIER_0_EXACT: Dataset IS 100% this content type by construction.
            Example: TableBank images are guaranteed to contain tables.
        TIER_1_ANNOTATION: Derived from existing COCO/JSON annotations
            provided by the source dataset.
        TIER_2_MODEL: Derived from ML model inference (e.g., DocLayout-YOLO).
        TIER_3_HEURISTIC: Dataset-level defaults applied as fallback when
            no specific annotations or model inference available.
    """

    TIER_0_EXACT = "tier_0_exact"
    TIER_1_ANNOTATION = "tier_1_annotation"
    TIER_2_MODEL = "tier_2_model"
    TIER_3_HEURISTIC = "tier_3_heuristic"


__all__ = [
    "CaptureMethod",
    "DomainLevel1",
    "EnrichmentTier",
    "ResolutionCategory",
]
