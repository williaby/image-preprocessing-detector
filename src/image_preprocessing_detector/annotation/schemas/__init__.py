# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Schema definitions for the three-layer metadata architecture.

Layer Architecture:
    1. IMMUTABLE LAYER (immutable.py): Original labels preserved exactly
       as provided by source datasets. Never modified after creation.

    2. ENRICHMENT LAYER (enrichment.py): Derived annotations with full
       provenance tracking. Versioned for reproducibility.

    3. SAMPLE AGGREGATE (sample.py): Combined view of immutable +
       enrichment layers for a single sample.

Enums (enums.py):
    - CaptureMethod: How the document was captured
    - DomainLevel1: Primary document domain
    - ResolutionCategory: Resolution bins
    - EnrichmentTier: Source tier for provenance

Migrations (migrations.py):
    - Schema version tracking
    - Forward/backward migration support
    - Rollback capabilities

Validators (validators.py):
    - Pydantic-based runtime validation
    - Field validators for all schema types
    - ValidationResult for error reporting

Example:
    >>> from image_preprocessing_detector.annotation.schemas import (
    ...     CaptureMethod,
    ...     EnrichmentTier,
    ...     OriginalFileMetadata,
    ...     EnrichmentData,
    ...     SampleMetadata,
    ...     validate_sample_metadata,
    ...     ValidationResult,
    ... )
"""

from __future__ import annotations

# Phase 1.2.3: Enrichment layer
from .enrichment import EnrichmentData, EnrichmentVersion, LayoutDetection

# Phase 1.2.1: Enums
from .enums import CaptureMethod, DomainLevel1, EnrichmentTier, ResolutionCategory

# Phase 1.2.2: Immutable layer
from .immutable import OriginalFileMetadata, OriginalLabels

# Phase 1.2.6: Migrations
from .migrations import (
    CURRENT_VERSION,
    MIN_SUPPORTED_VERSION,
    Migration,
    MigrationRegistry,
    get_migration_path,
    migrate_sample,
    register_migration,
    rollback_sample,
)

# Phase 1.2.4: Sample aggregate
from .sample import SCHEMA_VERSION, SCRIPT_VERSION, SampleMetadata

# Phase 1.2.5: Validators
from .validators import (
    BboxValidator,
    ConfidenceValidator,
    DpiValidator,
    FileHashValidator,
    IsoDateValidator,
    MosScoreValidator,
    OcrQualityScoreValidator,
    PixelDimensionsValidator,
    SampleIdValidator,
    ValidationResult,
    validate_enrichment_data,
    validate_enrichment_version,
    validate_original_file_metadata,
    validate_original_labels,
    validate_sample_metadata,
)

__all__: list[str] = [
    # Migrations (Phase 1.2.6)
    "CURRENT_VERSION",
    "MIN_SUPPORTED_VERSION",
    "SCHEMA_VERSION",
    "SCRIPT_VERSION",
    # Validators (Phase 1.2.5)
    "BboxValidator",
    # Enums (Phase 1.2.1)
    "CaptureMethod",
    "ConfidenceValidator",
    "DomainLevel1",
    "DpiValidator",
    "EnrichmentData",
    "EnrichmentTier",
    "EnrichmentVersion",
    "FileHashValidator",
    "IsoDateValidator",
    # Enrichment layer (Phase 1.2.3)
    "LayoutDetection",
    "Migration",
    "MigrationRegistry",
    "MosScoreValidator",
    "OcrQualityScoreValidator",
    # Immutable layer (Phase 1.2.2)
    "OriginalFileMetadata",
    "OriginalLabels",
    "PixelDimensionsValidator",
    "ResolutionCategory",
    "SampleIdValidator",
    # Sample aggregate (Phase 1.2.4)
    "SampleMetadata",
    "ValidationResult",
    "get_migration_path",
    "migrate_sample",
    "register_migration",
    "rollback_sample",
    "validate_enrichment_data",
    "validate_enrichment_version",
    "validate_original_file_metadata",
    "validate_original_labels",
    "validate_sample_metadata",
]
