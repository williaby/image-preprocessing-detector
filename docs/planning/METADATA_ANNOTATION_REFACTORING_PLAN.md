---
title: "Metadata Annotation System Refactoring Plan"
schema_type: planning
status: in-progress
owner: core-maintainer
purpose: >
  Convert the monolithic annotate_base_metadata.py (~3,800 LOC) into a modular,
  maintainable package that supports dataset extensibility, schema evolution, and ML integration.
component: "Strategy"
source: "Phase 10A planning session"
last_updated: "2025-01-26"
tags:
  - planning
  - schema
---

## Executive Summary

This plan addresses **15 critical issues** identified by multi-model consensus analysis (5 models,
average score 8.4/10) and establishes a foundation for:

1. **Easy dataset addition** - Plugin-based parser architecture
2. **Schema evolution** - Versioned migrations with backward compatibility
3. **ML integration** - Provider pattern for weak labeling (SigLIP, VLMs, etc.)
4. **Production reliability** - Atomic operations, checkpointing, validation

**Estimated Effort**: 6-7 weeks (phased delivery)
**Risk Level**: Medium (existing functionality preserved through compatibility layer)

### Consensus Review Summary

| Model | Score | Key Validation |
|-------|-------|----------------|
| Gemini 2.5 Pro | 9/10 | Architecture strongly endorsed |
| Gemini 3 Pro Preview | 9/10 | Critical GPU/hash issues identified |
| GPT-5.2 | 7/10 | Operational semantics strengthened |
| DeepSeek R1 | 9/10 | Production resilience gaps addressed |
| Grok 4 | 8/10 | Error handling framework added |

---

## Implementation Status

> **Last Updated**: 2025-01-26

| Phase | Status | Completion | Notes |
|-------|--------|------------|-------|
| Phase 1: Foundation | ✅ **COMPLETE** | 25/27 tasks | 2 tasks deferred to Phase 2 |
| Phase 2: Core Refactoring | ❌ Not Started | 0/36 tasks | - |
| Phase 3: Extensibility | ❌ Not Started | 0/21 tasks | - |
| Phase 4: ML Integration | ❌ Not Started | 0/18 tasks | - |
| Phase 5: Production Hardening | ❌ Not Started | 0/24 tasks | - |

### Phase 1 Implementation Summary (2025-01-26)

**Completed Tasks**: 25/27 (93%)

**Deferred to Phase 2**:

- 1.2.5: Add Pydantic validation using schema_utils patterns (better done with full parser system)
- 1.4.3: Migrate DATASET_CONFIGS to config/datasets.py (requires parser registry first)

**Test Coverage**: 108 unit tests passing

- test_imports.py: Import validation (3 test classes)
- test_schemas.py: Schema dataclasses (6 test classes)
- test_hashing.py: Integrity operations (3 test classes)
- test_atomic.py: Atomic file operations (4 test classes)
- test_config.py: Configuration system (6 test classes)

**Multi-Model Consensus Validation** (5 models, average 9.2/10):

| Model | Score | Key Feedback |
|-------|-------|--------------|
| Gemini 2.5 Pro | 10/10 | "Excellent foundation, critical fixes properly implemented" |
| Gemini 3 Pro Preview | 10/10 | "Full-file hashing and atomic writes exactly right" |
| GPT-5.2 | 8/10 | "Good structure, consider runtime validation and frozen dataclasses" |
| DeepSeek R1 | 9/10 | "Solid implementation, temp file uniqueness could be improved" |
| Grok-4 | 9/10 | "Well-architected, unified config loader would help" |

**Breaking Change Documented**: CHANGELOG.md updated with full-file SHA256 migration notice.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Target Architecture](#target-architecture)
3. [Phase 1: Foundation](#phase-1-foundation-week-1-2)
4. [Phase 2: Core Refactoring](#phase-2-core-refactoring-week-2-4)
5. [Phase 3: Extensibility](#phase-3-extensibility-week-4-5)
6. [Phase 4: ML Integration](#phase-4-ml-integration-week-5-6)
7. [Phase 5: Production Hardening](#phase-5-production-hardening-week-6-7)
8. [Migration Strategy](#migration-strategy)
9. [Testing Strategy](#testing-strategy)
10. [Risk Mitigation](#risk-mitigation)
11. [Issue Traceability Matrix](#issue-traceability-matrix)

---

## Current State Analysis

### Problems Identified (Multi-Model Consensus)

| ID | Severity | Issue | Impact | Phase | Status |
|----|----------|-------|--------|-------|--------|
| P0-1 | 🔴 Critical | SHA256 partial hashing (64KB only) | Data integrity risk, hash collisions | 1.3 | ✅ Fixed |
| P0-2 | 🔴 Critical | Parquet overwrite on per-dataset runs | Data loss in incremental mode | 2.4 | ❌ |
| P0-3 | 🔴 Critical | shlex.quote bug in incremental wrapper | Broken --dataset matching | 2.5 | ❌ |
| P0-4 | 🔴 Critical | FUNSD type mismatch (dict vs list) | Runtime crashes | 1.2 | ✅ Fixed |
| P1-1 | ⚠️ High | Monolithic 3,800 LOC single file | Maintainability debt | 1.1, 2.x | 🔄 Started |
| P1-2 | ⚠️ High | Global mutable state (3 caches) | Testability issues | 2.2, 5.1 | ❌ |
| P1-3 | ⚠️ High | Random UUIDs prevent deduplication | Incremental updates broken | 1.3 | ✅ Fixed |
| P1-4 | ⚠️ High | Dataset-level only checkpointing | 99% failure restarts from 0% | 3.3 | ❌ |
| P1-5 | ⚠️ High | Memory OOM with 500K+ samples | Process crashes | 5.1 | ❌ |
| P2-1 | 🟡 Medium | Zero unit test coverage | Regression risk | 5.4 | 🔄 Started |
| P2-2 | 🟡 Medium | No atomic state file writes | Corruption on crash | 1.3 | ✅ Fixed |
| P2-3 | 🟡 Medium | Hardcoded paths | Portability issues | 1.4 | ✅ Fixed |
| P2-4 | 🟡 Medium | Parser duplication | Code smell | 2.1 | ❌ |
| P2-5 | 🟡 Medium | No schema version migration | Upgrade friction | 3.2 | ❌ |
| P2-6 | 🟡 Medium | Per-image YOLO without batching | Performance | 2.3, 5.2 | ❌ |

### Current File Structure

```text
scripts/
├── annotate_base_metadata.py          # 3,853 lines - THE MONOLITH
├── annotate_base_metadata_incremental.py  # 287 lines - wrapper
└── build_training_labels.py           # 590 lines - Layer 3

src/image_preprocessing_detector/
├── schema.py                          # Pydantic models
├── schema_utils/                      # 8 utility modules (good pattern - REUSE)
│   ├── __init__.py
│   ├── bbox_utils.py
│   ├── degradation_mapping.py
│   ├── iso_language_script.py
│   ├── iso_paper_sizes.py
│   ├── text_scope.py
│   ├── dataset_source.py
│   └── validation.py                  # Reuse for runtime validation
└── ...
```

---

## Target Architecture

### Proposed Package Structure

```text
src/image_preprocessing_detector/annotation/
├── __init__.py                     # Public API + create_orchestrator() factory
├── schemas/
│   ├── __init__.py
│   ├── enums.py                    # CaptureMethod, DomainLevel1, etc.
│   ├── immutable.py                # OriginalFileMetadata, OriginalLabels
│   ├── enrichment.py               # EnrichmentData, EnrichmentVersion
│   ├── sample.py                   # SampleMetadata (aggregate)
│   └── migrations.py               # Schema version migrations + rollback
├── config/
│   ├── __init__.py
│   ├── datasets.py                 # DATASET_CONFIGS registry
│   ├── tiers.py                    # TIER_0_DATASETS, TIER_1_DATASETS
│   └── settings.py                 # Configurable settings
├── integrity/
│   ├── __init__.py
│   ├── hashing.py                  # Full-file SHA256, content hashing
│   ├── checkpointing.py            # Intra-dataset checkpoints (hash-based resume)
│   └── atomic.py                   # Atomic file operations (os.replace)
├── parsers/
│   ├── __init__.py                 # Parser registry + explicit registration
│   ├── base.py                     # BaseParser protocol
│   ├── registry.py                 # Factory with explicit registration
│   ├── quality/                    # Quality score parsers
│   ├── layout/                     # Layout annotation parsers
│   ├── handwriting/                # Handwriting/signature parsers
│   ├── multilingual/               # Script/language parsers
│   └── document/                   # Document type parsers
├── enrichment/
│   ├── __init__.py
│   ├── tiering.py                  # Tier classification
│   ├── content_flags.py            # Content derivation
│   ├── errors.py                   # Structured errors (NEW)
│   ├── manager.py                  # Provider orchestration with validation
│   └── providers/                  # ML integration point
│       ├── __init__.py
│       ├── base.py                 # EnrichmentProvider + QualityScoreProvider protocols
│       ├── yolo.py                 # DocLayout-YOLO provider
│       └── siglip.py               # SigLIP weak labeling
├── storage/
│   ├── __init__.py
│   ├── json_writer.py              # Per-dataset JSON output
│   ├── parquet_writer.py           # Partitioned Parquet (dataset_name=X/) (REDESIGNED)
│   └── cache.py                    # LRU-bounded annotation cache
├── workflow/
│   ├── __init__.py
│   ├── pipeline.py                 # CPU/GPU separated pipeline (NEW - CRITICAL)
│   ├── scanner.py                  # Batch-aware dataset scanner
│   ├── orchestrator.py             # Multi-dataset coordination
│   └── progress.py                 # Progress tracking
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                  # Prometheus metrics (NEW)
│   └── logging.py                  # Structured logging
├── cli.py                          # Click CLI interface
└── compat.py                       # Backward compatibility shim

scripts/
├── annotate_base_metadata.py       # Thin wrapper → annotation.cli
└── annotate_base_metadata_incremental.py  # Thin wrapper → annotation.workflow
```

### Key Design Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: No global state, use `create_orchestrator()` factory
3. **Protocol-Based**: Use `typing.Protocol` for extensibility
4. **Configuration-Driven**: External YAML/env for paths and settings
5. **Fail-Fast**: Explicit errors > silent defaults
6. **Reuse-First**: Import from `schema_utils/` - NO duplication
7. **CPU/GPU Separation**: Parallel CPU work, batched single-thread GPU inference

### Architecture Documentation

This refactoring plan aligns with the Level 2 Data Preparation architecture documentation:

| Document | Status | Purpose |
|----------|--------|---------|
| [index.md](../architecture/diagrams/level-2/data-preparation/index.md) | V1 (Current) | Documents existing monolithic implementation |
| [index.v2-draft.md](../architecture/diagrams/level-2/data-preparation/index.v2-draft.md) | V2 Draft | Documents target modular architecture |

**Documentation Lifecycle**:

1. **During Implementation**: V2 draft serves as target reference
2. **Phase 5 Completion**: Finalize V2, retire V1
3. **Post-Migration**: V2 becomes the authoritative architecture document

---

## ⚠️ BREAKING CHANGE NOTICE

### Hash Discontinuity (P0-1 Fix Impact)

**The fix for P0-1 (full-file SHA256 hashing) will change ALL existing sample IDs.**

**Impact**:

- Every image in the system gets a new deterministic ID
- Downstream systems relying on sample IDs will break
- "Incremental" runs will not match pre-migration data

**Required Action**:

- **FULL re-processing of ALL datasets is required** upon release
- Incremental updates against pre-migration data are NOT supported
- Plan for ~24-48 hour full re-annotation run after deployment

---

## Phase 1: Foundation (Week 1-2) ✅ COMPLETE

> **Status**: Complete (2025-01-26) | 25/27 tasks | 108 tests passing

### 1.1 Create Package Structure ✅

**Objective**: Establish module skeleton with public API

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| 1.1.1 | Create `annotation/` package with all subpackage `__init__.py` files | 2h | ✅ |
| 1.1.2 | Define public API in top-level `__init__.py` with `__all__` exports | 2h | ✅ |
| 1.1.3 | Create `create_orchestrator()` factory function stub | 2h | ✅ |
| 1.1.4 | Add to `pyproject.toml` entry points for CLI | 1h | ✅ |
| 1.1.5 | Write import validation tests | 1h | ✅ |

**Deliverables**:

- Empty package structure with documentation
- Import test: `from image_preprocessing_detector.annotation import create_orchestrator`
- Factory function signature defined

**Total**: ~8h (2 work chunks)

---

### 1.2 Migrate Schemas ✅

**Objective**: Move dataclasses to dedicated schema modules

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| 1.2.1 | Extract enums to `schemas/enums.py` (CaptureMethod, DomainLevel1, ResolutionCategory, EnrichmentTier) | 3h | ✅ |
| 1.2.2 | Extract immutable layer to `schemas/immutable.py` (OriginalFileMetadata, OriginalLabels) with P0-4 fix | 4h | ✅ |
| 1.2.3 | Extract enrichment layer to `schemas/enrichment.py` (LayoutDetection, EnrichmentData, EnrichmentVersion) | 4h | ✅ |
| 1.2.4 | Extract sample aggregate to `schemas/sample.py` (SampleMetadata with all methods) | 4h | ✅ |
| 1.2.5 | Add Pydantic validation using existing `schema_utils/validation.py` patterns | 3h | ⏳ Deferred |
| 1.2.6 | Create `schemas/migrations.py` stub with rollback support | 2h | ✅ |
| 1.2.7 | Write unit tests for all schema classes | 4h | ✅ |

**Critical Fix - P0-4 (FUNSD type mismatch)**:

```python
# In schemas/immutable.py
@dataclass
class OriginalLabels:
    """Original labels from dataset source."""
    # Fix: Type annotation clarity - FUNSD is dict, not list
    funsd_annotations: dict | None = None  # NOT list - FUNSD format is object
    doclaynet_annotations: list[dict] | None = None  # COCO format is list
    tablebank_annotations: list[dict] | None = None  # COCO format is list
    pubtabnet_annotations: list[dict] | None = None  # COCO format is list
```

**Deliverables**:

- All schema classes migrated with type safety
- P0-4 fix verified with unit tests
- Pydantic validation integrated

**Total**: ~24h (4-5 work chunks)

---

### 1.3 Fix Critical Data Integrity Issues ✅

**Objective**: Address P0-1 (hashing), P1-3 (deterministic IDs), P2-2 (atomic writes)

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| 1.3.1 | Create `integrity/hashing.py` with full-file SHA256 | 3h | ✅ |
| 1.3.2 | Implement deterministic `compute_sample_id()` function | 2h | ✅ |
| 1.3.3 | Create `integrity/atomic.py` with `os.replace()` (cross-platform) | 3h | ✅ |
| 1.3.4 | Add fsync option for critical data integrity | 2h | ✅ |
| 1.3.5 | Write comprehensive unit tests for hashing edge cases | 3h | ✅ |
| 1.3.6 | Write tests for atomic operations (including failure scenarios) | 3h | ✅ |
| 1.3.7 | Document hash discontinuity breaking change in CHANGELOG | 1h | ✅ |

**Implementation - integrity/hashing.py**:

```python
import hashlib
from pathlib import Path

def compute_full_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of ENTIRE file content.

    BREAKING CHANGE: This replaces partial 64KB hashing.
    All existing sample IDs will change.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def compute_sample_id(
    dataset_name: str,
    relative_path: str,
    file_hash: str,
) -> str:
    """Deterministic sample ID for deduplication.

    Args:
        dataset_name: Name of the source dataset
        relative_path: Path relative to dataset root
        file_hash: Full SHA256 hash of file content

    Returns:
        32-character deterministic hex ID
    """
    content = f"{dataset_name}:{relative_path}:{file_hash}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]
```

**Implementation - integrity/atomic.py**:

```python
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

@contextmanager
def atomic_write(path: Path, fsync: bool = False) -> Iterator[Path]:
    """Write to temp file, then atomic rename.

    Uses os.replace() for cross-platform atomic overwrites.

    Args:
        path: Target file path
        fsync: If True, call fsync before rename for durability

    Yields:
        Temporary file path to write to

    Raises:
        Original exception if write fails (temp file cleaned up)
    """
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        yield temp_path
        if fsync:
            # Ensure data is on disk before rename
            fd = os.open(str(temp_path), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        os.replace(temp_path, path)  # Atomic on all platforms
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
```

**Deliverables**:

- Full-file hashing implementation
- Deterministic sample ID generation
- Cross-platform atomic file operations
- Breaking change documented

**Total**: ~17h (3-4 work chunks)

---

### 1.4 Create Configuration System ✅

**Objective**: Externalize hardcoded paths and settings

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| 1.4.1 | Create `config/settings.py` with `AnnotationSettings` dataclass | 3h | ✅ |
| 1.4.2 | Implement `from_env()` classmethod for environment loading | 2h | ✅ |
| 1.4.3 | Migrate `DATASET_CONFIGS` to `config/datasets.py` | 4h | ⏳ Deferred |
| 1.4.4 | Migrate tier definitions to `config/tiers.py` | 2h | ✅ |
| 1.4.5 | Create YAML config loader as alternative to env vars | 3h | ✅ |
| 1.4.6 | Write validation for configuration completeness | 2h | ✅ |
| 1.4.7 | Write unit tests for configuration loading | 2h | ✅ |

**Implementation - config/settings.py**:

```python
from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass(frozen=True)
class AnnotationSettings:
    """Configurable annotation settings.

    All paths and thresholds externalized for portability.
    """
    # Paths
    e_drive_root: Path = field(default_factory=lambda: Path("/mnt/e/image_detection"))
    metadata_root: Path = field(default_factory=lambda: Path("/mnt/e/image_detection/metadata_registry"))
    checkpoint_dir: Path = field(default_factory=lambda: Path("/mnt/e/image_detection/metadata_registry/.checkpoints"))

    # Processing
    cache_size_limit: int = 10_000  # LRU cache entries
    batch_size: int = 100  # Images per batch for GPU inference
    checkpoint_interval: int = 100  # Batches between checkpoints
    workers: int = 4  # CPU worker processes

    # Integrity
    hash_full_file: bool = True  # P0-1 fix - always True
    atomic_fsync: bool = False  # Enable for critical data

    # ML Providers
    yolo_confidence_threshold: float = 0.25
    yolo_model_path: Path | None = None
    siglip_batch_size: int = 32

    @classmethod
    def from_env(cls) -> "AnnotationSettings":
        """Load from environment variables with ANNOTATION_ prefix."""
        return cls(
            e_drive_root=Path(os.getenv("ANNOTATION_E_DRIVE_ROOT", "/mnt/e/image_detection")),
            metadata_root=Path(os.getenv("ANNOTATION_METADATA_ROOT", "/mnt/e/image_detection/metadata_registry")),
            cache_size_limit=int(os.getenv("ANNOTATION_CACHE_SIZE", "10000")),
            batch_size=int(os.getenv("ANNOTATION_BATCH_SIZE", "100")),
            workers=int(os.getenv("ANNOTATION_WORKERS", "4")),
            yolo_confidence_threshold=float(os.getenv("ANNOTATION_YOLO_CONFIDENCE", "0.25")),
        )
```

**Deliverables**:

- Centralized configuration system
- Environment variable support
- YAML config alternative
- All hardcoded paths externalized

**Total**: ~18h (3-4 work chunks)

---

## Phase 2: Core Refactoring (Week 2-4)

### 2.1 Parser Architecture

**Objective**: Plugin-based parser system with explicit registration

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 2.1.1 | Create `parsers/base.py` with `DatasetParser` protocol | 3h | - |
| 2.1.2 | Create `parsers/registry.py` with explicit registration (not pkgutil) | 4h | - |
| 2.1.3 | Migrate quality parsers (diqa, smartdoc, ocr_quality) | 6h | - |
| 2.1.4 | Migrate layout parsers (doclaynet, tablebank, pubtabnet, funsd) | 8h | - |
| 2.1.5 | Migrate handwriting parsers (signatr, nist_sd19, pucit_ohul) | 6h | - |
| 2.1.6 | Migrate multilingual parsers (mdiw, cc_ocr, multilingual_scripts) | 6h | - |
| 2.1.7 | Migrate document parsers (rvl_cdip, omnidocbench) | 4h | - |
| 2.1.8 | Write unit tests for each parser | 8h | - |
| 2.1.9 | Write integration test for parser registry | 3h | - |

**Implementation - parsers/base.py**:

```python
from typing import Protocol, runtime_checkable, Any
from pathlib import Path

from ..schemas.immutable import OriginalLabels

@runtime_checkable
class DatasetParser(Protocol):
    """Protocol for dataset-specific label parsers.

    Implementations should be stateless and thread-safe.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Dataset names this parser handles."""
        ...

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image.

        Args:
            dataset_path: Root path of the dataset
            image_path: Absolute path to the image file
            config: Dataset configuration from DATASET_CONFIGS

        Returns:
            Populated OriginalLabels instance
        """
        ...

    def supports_batch(self) -> bool:
        """Whether this parser supports batch operations."""
        return False

    def parse_batch(
        self,
        dataset_path: Path,
        image_paths: list[Path],
        config: dict[str, Any],
    ) -> list[OriginalLabels]:
        """Parse labels for multiple images (optional optimization)."""
        return [self.parse(dataset_path, p, config) for p in image_paths]
```

**Implementation - parsers/registry.py**:

```python
from typing import Type
from .base import DatasetParser

class ParserRegistry:
    """Parser registry with explicit registration.

    Uses explicit registration instead of pkgutil auto-discovery
    to avoid import-order issues and improve testability.
    """

    def __init__(self):
        self._parsers: dict[str, DatasetParser] = {}

    def register(self, parser: DatasetParser) -> None:
        """Register a parser for its dataset names."""
        for name in parser.dataset_names:
            if name in self._parsers:
                raise ValueError(f"Parser already registered for dataset: {name}")
            self._parsers[name] = parser

    def get_parser(self, dataset_name: str) -> DatasetParser | None:
        """Get parser for dataset, or None if not found."""
        return self._parsers.get(dataset_name)

    def list_datasets(self) -> list[str]:
        """List all registered dataset names."""
        return sorted(self._parsers.keys())

    @classmethod
    def create_default(cls) -> "ParserRegistry":
        """Create registry with all standard parsers registered."""
        registry = cls()

        # Quality parsers
        from .quality.diqa import DIQAParser
        from .quality.smartdoc import SmartDocParser
        registry.register(DIQAParser())
        registry.register(SmartDocParser())

        # Layout parsers
        from .layout.doclaynet import DocLayNetParser
        from .layout.funsd import FUNSDParser
        registry.register(DocLayNetParser())
        registry.register(FUNSDParser())

        # ... register all parsers

        return registry
```

**Deliverables**:

- Protocol-based parser architecture
- All 38+ parsers migrated to subpackages
- Explicit registration for testability
- Comprehensive parser tests

**Total**: ~48h (8-10 work chunks)

---

### 2.2 Enrichment Provider System

**Objective**: Pluggable enrichment sources with structured errors

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 2.2.1 | Create `enrichment/errors.py` with structured exception classes | 3h | - |
| 2.2.2 | Create `enrichment/providers/base.py` with protocols | 4h | - |
| 2.2.3 | Migrate YOLO code to `enrichment/providers/yolo.py` with batching | 6h | - |
| 2.2.4 | Create `enrichment/manager.py` with validation integration | 5h | - |
| 2.2.5 | Add retry logic for transient ML failures | 3h | - |
| 2.2.6 | Write unit tests for enrichment system | 4h | - |

**Implementation - enrichment/errors.py**:

```python
"""Structured errors for enrichment system."""

class EnrichmentError(Exception):
    """Base class for enrichment errors."""
    pass

class ParserError(EnrichmentError):
    """Error during label parsing."""
    def __init__(self, dataset_name: str, image_path: str, cause: Exception):
        self.dataset_name = dataset_name
        self.image_path = image_path
        self.cause = cause
        super().__init__(f"Failed to parse {image_path} in {dataset_name}: {cause}")

class ModelInferenceError(EnrichmentError):
    """Error during ML model inference."""
    def __init__(self, provider_name: str, batch_size: int, cause: Exception):
        self.provider_name = provider_name
        self.batch_size = batch_size
        self.cause = cause
        super().__init__(f"Inference failed for {provider_name} (batch={batch_size}): {cause}")

class ProviderUnavailableError(EnrichmentError):
    """ML provider is not available (e.g., GPU not found)."""
    def __init__(self, provider_name: str, reason: str):
        self.provider_name = provider_name
        self.reason = reason
        super().__init__(f"Provider {provider_name} unavailable: {reason}")

class ValidationError(EnrichmentError):
    """Enrichment data failed validation."""
    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for {field}={value}: {reason}")
```

**Implementation - enrichment/providers/base.py**:

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass
from pathlib import Path

from ...schemas.enrichment import EnrichmentData, EnrichmentTier

@runtime_checkable
class EnrichmentProvider(Protocol):
    """Protocol for enrichment data providers."""

    @property
    def name(self) -> str:
        """Provider identifier."""
        ...

    @property
    def tier(self) -> EnrichmentTier:
        """Enrichment tier this provider produces."""
        ...

    def is_available(self) -> bool:
        """Check if provider is available (e.g., GPU present)."""
        ...

    def can_process(self, image_path: Path, config: dict) -> bool:
        """Check if provider can process this image."""
        ...

    def enrich_batch(
        self,
        image_paths: list[Path],
        existing: list[EnrichmentData | None],
    ) -> list[EnrichmentData]:
        """Batch enrichment for performance.

        CRITICAL: This is the primary method. Single-image enrich()
        is implemented in terms of this for consistency.
        """
        ...

@dataclass
class QualityPrediction:
    """Quality score prediction with uncertainty."""
    score: float  # 0-1 normalized
    confidence: float  # 0-1
    model_name: str
    dimensions: dict[str, float] | None = None  # e.g., sharpness, color

@runtime_checkable
class QualityScoreProvider(Protocol):
    """Protocol for continuous quality score providers."""

    def predict_quality(
        self,
        image_paths: list[Path],
    ) -> list[QualityPrediction]:
        """Predict quality scores for images."""
        ...
```

**Deliverables**:

- Structured error hierarchy
- Provider protocols with availability checks
- YOLO provider with batching
- Retry logic for transient failures

**Total**: ~25h (5 work chunks)

---

### 2.3 CPU/GPU Pipeline Separation (CRITICAL)

**Objective**: Separate CPU-bound parsing from GPU-bound inference

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 2.3.1 | Design pipeline architecture with clear stage separation | 4h | - |
| 2.3.2 | Create `workflow/pipeline.py` with `AnnotationPipeline` class | 6h | - |
| 2.3.3 | Implement CPU stage (parallel hashing + parsing) | 5h | - |
| 2.3.4 | Implement GPU stage (single-thread batched inference) | 5h | - |
| 2.3.5 | Implement IO stage (batch writing) | 3h | - |
| 2.3.6 | Add queue-based communication between stages | 4h | - |
| 2.3.7 | Write integration tests for pipeline | 5h | - |

**Implementation - workflow/pipeline.py**:

```python
"""CPU/GPU separated annotation pipeline.

CRITICAL: ML providers MUST NOT run inside ProcessPoolExecutor.
GPU models cannot be pickled/forked - they must run in main thread
or a dedicated GPU process.

Pipeline Architecture:
  Stage 1 (CPU Pool): Hash files + parse labels → emit ParsedSample
  Stage 2 (GPU Thread): Batch inference → emit EnrichedSample
  Stage 3 (IO Thread): Write results → checkpoint
"""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Iterator
import threading

from ..config.settings import AnnotationSettings
from ..parsers.registry import ParserRegistry
from ..enrichment.manager import EnrichmentManager
from ..integrity.checkpointing import CheckpointManager
from ..schemas.sample import SampleMetadata

@dataclass
class ParsedSample:
    """Output from CPU parsing stage."""
    image_path: Path
    file_hash: str
    original_labels: OriginalLabels
    dataset_config: dict

@dataclass
class EnrichedSample:
    """Output from GPU enrichment stage."""
    parsed: ParsedSample
    enrichment: EnrichmentData

class AnnotationPipeline:
    """Three-stage pipeline with CPU/GPU separation.

    Stage 1 (CPU): Parallel file hashing and label parsing
    Stage 2 (GPU): Single-thread batched ML inference
    Stage 3 (IO): Batch result writing with checkpointing
    """

    def __init__(
        self,
        settings: AnnotationSettings,
        parser_registry: ParserRegistry,
        enrichment_manager: EnrichmentManager,
        checkpoint_manager: CheckpointManager,
    ):
        self.settings = settings
        self.parsers = parser_registry
        self.enrichment = enrichment_manager
        self.checkpoints = checkpoint_manager

        # Inter-stage queues
        self._parse_queue: Queue[list[ParsedSample] | None] = Queue(maxsize=2)
        self._enrich_queue: Queue[list[EnrichedSample] | None] = Queue(maxsize=2)

    def process_dataset(
        self,
        dataset_name: str,
        image_paths: list[Path],
        dataset_config: dict,
    ) -> list[SampleMetadata]:
        """Process dataset through three-stage pipeline."""

        # Get resume point from checkpoint
        resume_info = self.checkpoints.get_resume_point(dataset_name)
        if resume_info:
            # Resume by finding the last processed file
            start_idx = self._find_resume_index(image_paths, resume_info)
            image_paths = image_paths[start_idx:]

        # Start pipeline stages as threads
        results: list[SampleMetadata] = []
        errors: list[tuple[Path, Exception]] = []

        # Stage 3: IO writer thread
        io_thread = threading.Thread(
            target=self._io_stage,
            args=(dataset_name, results, errors),
        )
        io_thread.start()

        # Stage 2: GPU enrichment thread (MUST be single thread)
        gpu_thread = threading.Thread(
            target=self._gpu_stage,
        )
        gpu_thread.start()

        # Stage 1: CPU parsing (parallel workers)
        self._cpu_stage(dataset_name, image_paths, dataset_config)

        # Wait for pipeline to drain
        gpu_thread.join()
        io_thread.join()

        return results

    def _cpu_stage(
        self,
        dataset_name: str,
        image_paths: list[Path],
        config: dict,
    ) -> None:
        """Stage 1: Parallel CPU parsing and hashing."""
        parser = self.parsers.get_parser(dataset_name)
        if not parser:
            raise ValueError(f"No parser for dataset: {dataset_name}")

        with ProcessPoolExecutor(max_workers=self.settings.workers) as executor:
            for batch in self._batches(image_paths, self.settings.batch_size):
                # Submit batch to workers
                futures = [
                    executor.submit(self._parse_single, p, parser, config)
                    for p in batch
                ]

                # Collect results
                parsed_batch = []
                for future, path in zip(futures, batch):
                    try:
                        parsed_batch.append(future.result())
                    except Exception as e:
                        # Log error but continue processing
                        logger.error(f"Parse failed for {path}: {e}")

                # Send to GPU stage
                if parsed_batch:
                    self._parse_queue.put(parsed_batch)

        # Signal end of CPU stage
        self._parse_queue.put(None)

    def _gpu_stage(self) -> None:
        """Stage 2: Single-thread GPU batched inference.

        CRITICAL: Runs in single thread - GPU models cannot be parallelized
        via ProcessPoolExecutor (pickle/fork issues with CUDA).
        """
        while True:
            batch = self._parse_queue.get()
            if batch is None:
                break

            # Run ML enrichment on batch
            image_paths = [p.image_path for p in batch]
            existing = [None] * len(batch)

            try:
                enrichments = self.enrichment.enrich_batch(image_paths, existing)

                enriched_batch = [
                    EnrichedSample(parsed=p, enrichment=e)
                    for p, e in zip(batch, enrichments)
                ]
                self._enrich_queue.put(enriched_batch)

            except Exception as e:
                logger.error(f"GPU enrichment failed for batch: {e}")
                # Put samples without enrichment
                enriched_batch = [
                    EnrichedSample(parsed=p, enrichment=EnrichmentData())
                    for p in batch
                ]
                self._enrich_queue.put(enriched_batch)

        # Signal end of GPU stage
        self._enrich_queue.put(None)

    def _io_stage(
        self,
        dataset_name: str,
        results: list[SampleMetadata],
        errors: list[tuple[Path, Exception]],
    ) -> None:
        """Stage 3: Write results with checkpointing."""
        batch_count = 0

        while True:
            batch = self._enrich_queue.get()
            if batch is None:
                break

            # Convert to SampleMetadata
            for sample in batch:
                metadata = self._create_sample_metadata(sample)
                results.append(metadata)

            batch_count += 1

            # Checkpoint every N batches
            if batch_count % self.settings.checkpoint_interval == 0:
                last = batch[-1]
                self.checkpoints.save_checkpoint(
                    dataset_name=dataset_name,
                    processed_count=len(results),
                    last_path=str(last.parsed.image_path),
                    last_hash=last.parsed.file_hash,
                )

    @staticmethod
    def _batches(items: list, size: int) -> Iterator[list]:
        """Yield successive batches from items."""
        for i in range(0, len(items), size):
            yield items[i:i + size]
```

**Deliverables**:

- Three-stage pipeline architecture
- CPU/GPU cleanly separated
- Queue-based inter-stage communication
- No ProcessPoolExecutor for GPU work

**Total**: ~32h (6-7 work chunks)

---

### 2.4 Partitioned Parquet Storage (P0-2 Fix)

**Objective**: Scalable Parquet storage without read-modify-write

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 2.4.1 | Design partitioned Parquet schema (dataset_name=X/part.parquet) | 3h | - |
| 2.4.2 | Create `storage/parquet_writer.py` with partitioned writes | 5h | - |
| 2.4.3 | Implement dataset view using pyarrow.dataset | 4h | - |
| 2.4.4 | Add atomic partition replacement | 3h | - |
| 2.4.5 | Write migration script for existing Parquet data | 4h | - |
| 2.4.6 | Write unit and integration tests | 4h | - |

**Implementation - storage/parquet_writer.py**:

```python
"""Partitioned Parquet writer for scalable storage.

CRITICAL: Does NOT read entire Parquet into memory.
Uses partitioned datasets: metadata_registry/parquet/dataset_name=X/part-0000.parquet

Benefits:
- O(1) per-dataset writes (no read-modify-write)
- Atomic per-dataset replacement
- pyarrow.dataset provides unified view
"""

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
from pathlib import Path

from ..integrity.atomic import atomic_write
from ..schemas.sample import SampleMetadata

class PartitionedParquetWriter:
    """Write samples to partitioned Parquet dataset.

    Structure:
        parquet_root/
        ├── dataset_name=diqa-5000/
        │   └── part-0000.parquet
        ├── dataset_name=smartdoc-qa/
        │   └── part-0000.parquet
        └── ...
    """

    def __init__(self, parquet_root: Path):
        self.parquet_root = parquet_root
        self.parquet_root.mkdir(parents=True, exist_ok=True)

    def write_dataset(
        self,
        dataset_name: str,
        samples: list[SampleMetadata],
    ) -> None:
        """Write samples for a single dataset (atomic replacement).

        Replaces all existing data for this dataset partition.
        Does NOT touch other dataset partitions.
        """
        if not samples:
            return

        # Create partition directory
        partition_dir = self.parquet_root / f"dataset_name={dataset_name}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Convert to Arrow table
        table = self._samples_to_table(samples)

        # Write atomically
        output_path = partition_dir / "part-0000.parquet"
        with atomic_write(output_path) as temp_path:
            pq.write_table(
                table,
                temp_path,
                compression="snappy",
                write_statistics=True,
            )

    def get_dataset(self) -> ds.Dataset:
        """Get unified view of all partitions.

        Returns pyarrow Dataset that can be queried efficiently.
        """
        return ds.dataset(
            self.parquet_root,
            format="parquet",
            partitioning=ds.partitioning(
                pa.schema([("dataset_name", pa.string())]),
                flavor="hive",
            ),
        )

    def read_all(self) -> pa.Table:
        """Read all data as single table (for compatibility)."""
        dataset = self.get_dataset()
        return dataset.to_table()

    def read_dataset(self, dataset_name: str) -> pa.Table:
        """Read single dataset partition efficiently."""
        dataset = self.get_dataset()
        return dataset.to_table(
            filter=ds.field("dataset_name") == dataset_name
        )

    def delete_dataset(self, dataset_name: str) -> None:
        """Delete a dataset partition."""
        partition_dir = self.parquet_root / f"dataset_name={dataset_name}"
        if partition_dir.exists():
            import shutil
            shutil.rmtree(partition_dir)

    def _samples_to_table(self, samples: list[SampleMetadata]) -> pa.Table:
        """Convert samples to Arrow table."""
        # Implementation converts dataclasses to columnar format
        ...
```

**Deliverables**:

- Partitioned Parquet storage
- No read-modify-write operations
- Atomic per-dataset replacement
- pyarrow.dataset unified view

**Total**: ~23h (4-5 work chunks)

---

### 2.5 Fix Incremental Wrapper (P0-3)

**Objective**: Direct library import instead of subprocess

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 2.5.1 | Create `workflow/orchestrator.py` with direct API | 4h | - |
| 2.5.2 | Implement `create_orchestrator()` factory function | 2h | - |
| 2.5.3 | Update `annotate_base_metadata_incremental.py` to use direct import | 3h | - |
| 2.5.4 | Remove subprocess/shlex.quote code | 1h | - |
| 2.5.5 | Write integration tests for orchestrator | 3h | - |

**Implementation - workflow/orchestrator.py**:

```python
"""Multi-dataset annotation orchestrator.

Replaces subprocess-based incremental wrapper with direct library calls.
Fixes P0-3 (shlex.quote bug) by eliminating subprocess entirely.
"""

from dataclasses import dataclass
from pathlib import Path

from ..config.settings import AnnotationSettings
from ..config.datasets import DATASET_CONFIGS
from ..parsers.registry import ParserRegistry
from ..enrichment.manager import EnrichmentManager
from ..storage.parquet_writer import PartitionedParquetWriter
from ..storage.json_writer import JSONWriter
from ..integrity.checkpointing import CheckpointManager
from .pipeline import AnnotationPipeline
from .progress import ProgressTracker

@dataclass
class DatasetResult:
    """Result of processing a single dataset."""
    dataset_name: str
    success: bool
    samples_processed: int
    errors: list[str]
    duration_seconds: float

class AnnotationOrchestrator:
    """Orchestrate multi-dataset annotation.

    Direct replacement for subprocess-based incremental processing.
    All configuration and state managed in-process.
    """

    def __init__(
        self,
        settings: AnnotationSettings,
        parser_registry: ParserRegistry,
        enrichment_manager: EnrichmentManager,
    ):
        self.settings = settings
        self.parsers = parser_registry
        self.enrichment = enrichment_manager
        self.checkpoints = CheckpointManager(settings.checkpoint_dir)
        self.parquet_writer = PartitionedParquetWriter(
            settings.metadata_root / "parquet"
        )
        self.json_writer = JSONWriter(settings.metadata_root / "json")
        self.progress = ProgressTracker()

    def process_dataset(
        self,
        dataset_name: str,
        use_yolo: bool = True,
    ) -> DatasetResult:
        """Process single dataset (directly callable - no subprocess)."""
        if dataset_name not in DATASET_CONFIGS:
            return DatasetResult(
                dataset_name=dataset_name,
                success=False,
                samples_processed=0,
                errors=[f"Unknown dataset: {dataset_name}"],
                duration_seconds=0,
            )

        config = DATASET_CONFIGS[dataset_name]
        start_time = time.time()

        # Build pipeline
        pipeline = AnnotationPipeline(
            settings=self.settings,
            parser_registry=self.parsers,
            enrichment_manager=self.enrichment if use_yolo else EnrichmentManager([]),
            checkpoint_manager=self.checkpoints,
        )

        # Discover images
        dataset_path = config["path"]
        pattern = config["pattern"]
        image_paths = sorted(dataset_path.glob(pattern))

        # Process through pipeline
        try:
            samples = pipeline.process_dataset(dataset_name, image_paths, config)

            # Write outputs
            self.json_writer.write_dataset(dataset_name, samples)
            self.parquet_writer.write_dataset(dataset_name, samples)

            return DatasetResult(
                dataset_name=dataset_name,
                success=True,
                samples_processed=len(samples),
                errors=[],
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return DatasetResult(
                dataset_name=dataset_name,
                success=False,
                samples_processed=0,
                errors=[str(e)],
                duration_seconds=time.time() - start_time,
            )

    def process_all(
        self,
        resume: bool = True,
        use_yolo: bool = True,
    ) -> list[DatasetResult]:
        """Process all pending datasets."""
        results = []

        for dataset_name in DATASET_CONFIGS:
            if resume and self.progress.is_completed(dataset_name):
                continue

            result = self.process_dataset(dataset_name, use_yolo)
            results.append(result)

            if result.success:
                self.progress.mark_completed(dataset_name)
            else:
                self.progress.mark_failed(dataset_name, result.errors)

        return results


def create_orchestrator(
    settings: AnnotationSettings | None = None,
    use_yolo: bool = True,
) -> AnnotationOrchestrator:
    """Factory function to create fully-configured orchestrator.

    Centralizes dependency creation for testability.
    """
    if settings is None:
        settings = AnnotationSettings.from_env()

    # Create parser registry
    parser_registry = ParserRegistry.create_default()

    # Create enrichment manager with providers
    providers = []
    if use_yolo:
        from ..enrichment.providers.yolo import YOLOProvider
        yolo = YOLOProvider(
            model_path=settings.yolo_model_path,
            confidence=settings.yolo_confidence_threshold,
        )
        if yolo.is_available():
            providers.append(yolo)

    enrichment_manager = EnrichmentManager(providers)

    return AnnotationOrchestrator(
        settings=settings,
        parser_registry=parser_registry,
        enrichment_manager=enrichment_manager,
    )
```

**Deliverables**:

- Direct API for dataset processing
- Factory function for dependency injection
- No subprocess calls
- P0-3 completely eliminated

**Total**: ~13h (2-3 work chunks)

---

## Phase 3: Extensibility (Week 4-5)

### 3.1 Dataset Addition System

**Objective**: Make adding new datasets trivial

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 3.1.1 | Create `parsers/template.py` with template generator | 3h | - |
| 3.1.2 | Create dataset config validator with clear error messages | 3h | - |
| 3.1.3 | Create `add-dataset` CLI command with interactive mode | 4h | - |
| 3.1.4 | Write documentation for adding new datasets | 2h | - |
| 3.1.5 | Write tests for template generation | 2h | - |

**Implementation - parsers/template.py**:

```python
"""Parser template generator for new datasets."""

from pathlib import Path
from string import Template

PARSER_TEMPLATE = Template('''"""Parser for ${dataset_name} dataset.

Dataset Information:
    - Source: ${url}
    - License: ${license}
    - Domain: ${domain}
    - Samples: ${sample_count}

Label Format:
    ${label_description}
"""

from pathlib import Path
from typing import Any

from image_preprocessing_detector.annotation.parsers.base import DatasetParser
from image_preprocessing_detector.annotation.schemas.immutable import OriginalLabels


class ${class_name}Parser(DatasetParser):
    """Parser for ${dataset_name} dataset."""

    @property
    def dataset_names(self) -> list[str]:
        return ["${dataset_slug}"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels for a single image.

        Args:
            dataset_path: Root path of the dataset
            image_path: Absolute path to the image file
            config: Dataset configuration from DATASET_CONFIGS

        Returns:
            OriginalLabels with extracted fields
        """
        labels = OriginalLabels()

        # TODO: Implement parsing logic
        # Common patterns:
        # - labels.transcription = self._load_transcription(image_path)
        # - labels.human_mos = self._parse_quality_score(image_path)
        # - labels.raw_labels = {"custom_field": value}

        return labels

    def supports_batch(self) -> bool:
        """Whether this parser supports efficient batch operations."""
        return False
''')

def generate_parser(
    dataset_name: str,
    output_dir: Path,
    url: str = "TODO",
    license: str = "TODO",
    domain: str = "TODO",
    sample_count: str = "TODO",
    label_description: str = "TODO: Describe label format",
) -> Path:
    """Generate parser template for new dataset.

    Args:
        dataset_name: Human-readable dataset name (e.g., "DIQA-5000")
        output_dir: Directory to write parser file
        url: Dataset source URL
        license: License type
        domain: Domain category
        sample_count: Approximate sample count
        label_description: Description of label format

    Returns:
        Path to generated parser file
    """
    # Generate class name and slug
    class_name = dataset_name.title().replace("-", "").replace("_", "")
    dataset_slug = dataset_name.lower().replace("_", "-")

    content = PARSER_TEMPLATE.substitute(
        dataset_name=dataset_name,
        class_name=class_name,
        dataset_slug=dataset_slug,
        url=url,
        license=license,
        domain=domain,
        sample_count=sample_count,
        label_description=label_description,
    )

    output_file = output_dir / f"{dataset_slug.replace('-', '_')}.py"
    output_file.write_text(content)

    return output_file
```

**Deliverables**:

- Parser template generator
- Dataset config validator
- CLI for adding datasets
- Clear documentation

**Total**: ~14h (3 work chunks)

---

### 3.2 Schema Evolution System with Rollback

**Objective**: Support schema changes with rollback capability

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 3.2.1 | Create `schemas/migrations.py` with rollback support | 5h | - |
| 3.2.2 | Implement backup-before-migrate pattern | 3h | - |
| 3.2.3 | Create migration from v2.0 to v2.1 as example | 3h | - |
| 3.2.4 | Create `migrate` CLI command with --dry-run | 3h | - |
| 3.2.5 | Write property-based tests for migration invariants | 4h | - |

**Implementation - schemas/migrations.py**:

```python
"""Schema migration system with rollback support.

CRITICAL: Always backup before migration.
Failed migrations should be recoverable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import shutil
import json

@dataclass
class SchemaMigration:
    """Single schema migration with metadata."""
    from_version: str
    to_version: str
    description: str
    migrate_fn: Callable[[dict], dict]

class MigrationError(Exception):
    """Migration failed."""
    def __init__(self, from_version: str, to_version: str, cause: Exception):
        self.from_version = from_version
        self.to_version = to_version
        self.cause = cause
        super().__init__(f"Migration {from_version} → {to_version} failed: {cause}")

class SchemaMigrator:
    """Apply schema migrations with backup and rollback.

    IMPORTANT: Creates backup before any migration.
    Backup path: {original}.bak_v{version}
    """

    MIGRATIONS: list[SchemaMigration] = [
        SchemaMigration(
            from_version="2.0",
            to_version="2.1",
            description="Add text_scope and paper_size fields",
            migrate_fn=lambda d: _migrate_2_0_to_2_1(d),
        ),
        # Future migrations added here
    ]

    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir

    def migrate_file(
        self,
        file_path: Path,
        target_version: str,
        dry_run: bool = False,
    ) -> dict:
        """Migrate a single JSON file to target version.

        Args:
            file_path: Path to JSON file
            target_version: Target schema version
            dry_run: If True, return migrated data without writing

        Returns:
            Migrated data dictionary

        Raises:
            MigrationError: If migration fails (backup preserved)
        """
        # Load current data
        with open(file_path) as f:
            data = json.load(f)

        current = data.get("record_meta", {}).get("schema_version", "1.0")

        if current == target_version:
            return data

        # Create backup BEFORE migration
        if not dry_run:
            backup_path = self._create_backup(file_path, current)

        try:
            # Apply migrations
            for migration in self.MIGRATIONS:
                if self._needs_migration(current, migration, target_version):
                    data = migration.migrate_fn(data)
                    current = migration.to_version

                    # Update schema version in data
                    if "record_meta" not in data:
                        data["record_meta"] = {}
                    data["record_meta"]["schema_version"] = current

            # Write migrated data
            if not dry_run:
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)

            return data

        except Exception as e:
            raise MigrationError(current, target_version, e)

    def rollback_file(self, file_path: Path, version: str) -> bool:
        """Rollback file to a previous backup.

        Args:
            file_path: Path to file to rollback
            version: Version to rollback to

        Returns:
            True if rollback succeeded, False if backup not found
        """
        backup_path = file_path.with_suffix(f".bak_v{version}")

        if not backup_path.exists():
            return False

        shutil.copy(backup_path, file_path)
        return True

    def _create_backup(self, file_path: Path, version: str) -> Path:
        """Create backup before migration."""
        backup_path = file_path.with_suffix(f"{file_path.suffix}.bak_v{version}")
        shutil.copy(file_path, backup_path)
        return backup_path

    def _needs_migration(
        self,
        current: str,
        migration: SchemaMigration,
        target: str,
    ) -> bool:
        """Check if migration should be applied."""
        # Simple string comparison - could use semver
        return (
            migration.from_version == current and
            migration.to_version <= target
        )


def _migrate_2_0_to_2_1(data: dict) -> dict:
    """Migration: 2.0 → 2.1 - Add text_scope and paper_size fields."""
    enrichment = data.get("enrichment", {})

    # Add text_scope if missing
    if "text_scope" not in enrichment:
        enrichment["text_scope"] = None

    # Add paper_size if missing
    if "paper_size" not in enrichment:
        enrichment["paper_size"] = None

    data["enrichment"] = enrichment
    return data
```

**Deliverables**:

- Migration system with backup/rollback
- Example migration implementation
- CLI for migrations
- Property-based tests

**Total**: ~18h (3-4 work chunks)

---

### 3.3 Hash-Based Checkpointing System (P1-4 Fix)

**Objective**: Resume from exact failure point using hash-based markers

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 3.3.1 | Create `integrity/checkpointing.py` with hash-based resume | 5h | - |
| 3.3.2 | Implement batch-aware checkpointing (every N batches) | 3h | - |
| 3.3.3 | Add checkpoint validation on resume | 2h | - |
| 3.3.4 | Write tests for checkpoint edge cases | 3h | - |

**Implementation - integrity/checkpointing.py**:

```python
"""Intra-dataset checkpointing with hash-based resume.

CRITICAL: Resume uses file hash + path, NOT just count.
This handles cases where file list changes between runs.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
import json

from .atomic import atomic_write

@dataclass
class DatasetCheckpoint:
    """Checkpoint for dataset processing.

    Resume is based on last_processed_hash + last_processed_path,
    not just processed_count. This handles:
    - Files added/removed between runs
    - File ordering changes
    """
    dataset_name: str
    total_images: int
    processed_count: int
    last_processed_path: str
    last_processed_hash: str  # Used for validation on resume
    timestamp: str
    batch_size: int
    schema_version: str = "1.0"

class CheckpointManager:
    """Manage intra-dataset checkpoints with hash-based resume."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_resume_point(
        self,
        dataset_name: str,
        image_paths: list[Path] | None = None,
    ) -> tuple[int, str, str] | None:
        """Get resume point (index, path, hash) or None to start fresh.

        If image_paths provided, validates checkpoint against actual files.

        Returns:
            Tuple of (start_index, last_path, last_hash) or None
        """
        checkpoint = self._load_checkpoint(dataset_name)
        if checkpoint is None:
            return None

        # If no paths provided, trust checkpoint count
        if image_paths is None:
            return (
                checkpoint.processed_count,
                checkpoint.last_processed_path,
                checkpoint.last_processed_hash,
            )

        # Validate: find the checkpoint file in current list
        target_path = checkpoint.last_processed_path
        target_hash = checkpoint.last_processed_hash

        for idx, path in enumerate(image_paths):
            if str(path) == target_path or path.name == Path(target_path).name:
                # Found the file - resume from next
                return (idx + 1, target_path, target_hash)

        # Checkpoint file not found - start fresh
        return None

    def save_checkpoint(
        self,
        dataset_name: str,
        processed_count: int,
        last_path: str,
        last_hash: str,
        total_images: int = 0,
        batch_size: int = 100,
    ) -> None:
        """Save checkpoint atomically."""
        checkpoint = DatasetCheckpoint(
            dataset_name=dataset_name,
            total_images=total_images,
            processed_count=processed_count,
            last_processed_path=last_path,
            last_processed_hash=last_hash,
            timestamp=datetime.now(UTC).isoformat(),
            batch_size=batch_size,
        )

        checkpoint_path = self._checkpoint_path(dataset_name)
        with atomic_write(checkpoint_path) as temp:
            with open(temp, "w") as f:
                json.dump(asdict(checkpoint), f, indent=2)

    def clear_checkpoint(self, dataset_name: str) -> None:
        """Clear checkpoint for dataset (on successful completion)."""
        checkpoint_path = self._checkpoint_path(dataset_name)
        checkpoint_path.unlink(missing_ok=True)

    def _checkpoint_path(self, dataset_name: str) -> Path:
        """Get checkpoint file path for dataset."""
        safe_name = dataset_name.replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{safe_name}.checkpoint.json"

    def _load_checkpoint(self, dataset_name: str) -> DatasetCheckpoint | None:
        """Load checkpoint from disk."""
        checkpoint_path = self._checkpoint_path(dataset_name)
        if not checkpoint_path.exists():
            return None

        with open(checkpoint_path) as f:
            data = json.load(f)

        return DatasetCheckpoint(**data)
```

**Deliverables**:

- Hash-based checkpoint resume
- Batch-aware checkpointing
- Checkpoint validation
- Comprehensive tests

**Total**: ~13h (2-3 work chunks)

---

## Phase 4: ML Integration (Week 5-6)

### 4.1 SigLIP Integration Framework

**Objective**: Enable weak labeling via vision-language models

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 4.1.1 | Create `enrichment/providers/siglip.py` with batch inference | 6h | - |
| 4.1.2 | Implement GPU availability detection | 2h | - |
| 4.1.3 | Add fallback for CPU-only environments | 3h | - |
| 4.1.4 | Write integration tests with mock model | 4h | - |

**Implementation - enrichment/providers/siglip.py**:

```python
"""SigLIP-based quality score prediction provider."""

import torch
from pathlib import Path
from PIL import Image

from ..errors import ModelInferenceError, ProviderUnavailableError
from .base import EnrichmentProvider, QualityScoreProvider
from ...schemas.enrichment import EnrichmentData, EnrichmentTier

class SigLIPProvider(EnrichmentProvider, QualityScoreProvider):
    """SigLIP-based quality score prediction.

    Uses SigLIP2-IQA model for document quality assessment.
    Supports batch inference for efficiency.
    """

    def __init__(
        self,
        model_path: Path | str | None = None,
        device: str | None = None,
        batch_size: int = 32,
    ):
        self._model = None
        self._processor = None
        self.model_path = model_path
        self.batch_size = batch_size

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

    @property
    def name(self) -> str:
        return "siglip_iqa"

    @property
    def tier(self) -> EnrichmentTier:
        return EnrichmentTier.TIER_2_MODEL

    def is_available(self) -> bool:
        """Check if SigLIP model is available."""
        if self.model_path is None:
            return False

        model_path = Path(self.model_path)
        if not model_path.exists():
            return False

        # Check GPU for reasonable performance
        if self.device == "cuda" and not torch.cuda.is_available():
            return False

        return True

    def can_process(self, image_path: Path, config: dict) -> bool:
        """Check if this image should be processed."""
        # Process images without existing quality scores
        return True

    def _ensure_loaded(self) -> None:
        """Lazy-load model on first use."""
        if self._model is not None:
            return

        if not self.is_available():
            raise ProviderUnavailableError(
                self.name,
                f"Model not found at {self.model_path}"
            )

        try:
            from transformers import AutoModel, AutoProcessor

            self._processor = AutoProcessor.from_pretrained(self.model_path)
            self._model = AutoModel.from_pretrained(self.model_path)
            self._model = self._model.to(self.device)
            self._model.eval()

        except Exception as e:
            raise ProviderUnavailableError(self.name, str(e))

    def enrich_batch(
        self,
        image_paths: list[Path],
        existing: list[EnrichmentData | None],
    ) -> list[EnrichmentData]:
        """Batch inference for efficiency."""
        self._ensure_loaded()

        results = []

        # Process in batches
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i:i + self.batch_size]
            batch_existing = existing[i:i + self.batch_size]

            try:
                batch_results = self._process_batch(batch_paths, batch_existing)
                results.extend(batch_results)
            except Exception as e:
                # On failure, return existing data unchanged
                for ex in batch_existing:
                    results.append(ex or EnrichmentData())
                # Log error but continue
                import logging
                logging.error(f"SigLIP batch failed: {e}")

        return results

    def _process_batch(
        self,
        paths: list[Path],
        existing: list[EnrichmentData | None],
    ) -> list[EnrichmentData]:
        """Process a single batch."""
        # Load images
        images = []
        for p in paths:
            try:
                img = Image.open(p).convert("RGB")
                images.append(img)
            except Exception:
                images.append(Image.new("RGB", (224, 224)))  # Placeholder

        # Preprocess
        inputs = self._processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = self._model(**inputs)
            scores = outputs.logits.softmax(dim=-1)

        # Build results
        results = []
        for i, (path, base) in enumerate(zip(paths, existing)):
            enrichment = base or EnrichmentData()
            enrichment.llm_predicted_mos = float(scores[i, 1])
            enrichment.llm_prediction_confidence = float(scores[i].max())
            enrichment.llm_model_name = "siglip2-iqa"
            results.append(enrichment)

        return results
```

**Deliverables**:

- SigLIP provider with batch inference
- GPU/CPU fallback
- Lazy model loading
- Error handling

**Total**: ~15h (3 work chunks)

---

### 4.2 Provider Orchestration with Validation

**Objective**: Coordinate multiple enrichment providers with runtime validation

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 4.2.1 | Create `enrichment/manager.py` with tier-ordered execution | 4h | - |
| 4.2.2 | Add runtime validation using `schema_utils/validation.py` | 3h | - |
| 4.2.3 | Implement provider fallback chain | 3h | - |
| 4.2.4 | Add dead-letter queue for failed samples | 3h | - |
| 4.2.5 | Write unit tests for orchestration | 3h | - |

**Implementation - enrichment/manager.py**:

```python
"""Enrichment provider orchestration with validation."""

from dataclasses import dataclass, field
from pathlib import Path

from .providers.base import EnrichmentProvider
from .errors import EnrichmentError, ValidationError
from ..schemas.enrichment import EnrichmentData, EnrichmentTier
# Reuse existing validation from schema_utils
from ..schema_utils.validation import validate_enrichment

@dataclass
class EnrichmentResult:
    """Result of enrichment with optional errors."""
    data: EnrichmentData
    errors: list[str] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)

class EnrichmentManager:
    """Manage multiple enrichment providers with validation.

    Features:
    - Tier-ordered execution (lower tier = higher priority)
    - Provider fallback chain
    - Runtime validation using schema_utils
    - Dead-letter tracking for failed samples
    """

    def __init__(
        self,
        providers: list[EnrichmentProvider],
        validate: bool = True,
    ):
        self.providers = providers
        self.validate = validate
        self._tier_priority = {
            EnrichmentTier.TIER_0_EXACT: 0,
            EnrichmentTier.TIER_1_ANNOTATION: 1,
            EnrichmentTier.TIER_2_MODEL: 2,
            EnrichmentTier.TIER_3_HEURISTIC: 3,
        }
        self.dead_letter: list[tuple[Path, Exception]] = []

    def enrich_batch(
        self,
        image_paths: list[Path],
        existing: list[EnrichmentData | None] | None = None,
    ) -> list[EnrichmentResult]:
        """Apply all applicable providers in tier order.

        Args:
            image_paths: Paths to images
            existing: Optional existing enrichment data

        Returns:
            List of EnrichmentResult with data and any errors
        """
        if existing is None:
            existing = [None] * len(image_paths)

        # Initialize results
        results = [
            EnrichmentResult(data=e or EnrichmentData())
            for e in existing
        ]

        # Sort providers by tier priority
        sorted_providers = sorted(
            [p for p in self.providers if p.is_available()],
            key=lambda p: self._tier_priority.get(p.tier, 99),
        )

        for provider in sorted_providers:
            # Find applicable images
            applicable_indices = [
                i for i, (path, result) in enumerate(zip(image_paths, results))
                if provider.can_process(path, {})
            ]

            if not applicable_indices:
                continue

            # Extract batch for this provider
            batch_paths = [image_paths[i] for i in applicable_indices]
            batch_existing = [results[i].data for i in applicable_indices]

            try:
                # Run provider
                enriched = provider.enrich_batch(batch_paths, batch_existing)

                # Update results
                for idx, enrichment in zip(applicable_indices, enriched):
                    results[idx].data = enrichment
                    results[idx].providers_used.append(provider.name)

            except Exception as e:
                # Log to dead letter but continue
                for idx in applicable_indices:
                    results[idx].errors.append(f"{provider.name}: {e}")
                    self.dead_letter.append((image_paths[idx], e))

        # Validate results if enabled
        if self.validate:
            for result in results:
                validation_errors = validate_enrichment(result.data)
                result.errors.extend(validation_errors)

        return results

    def get_dead_letter_queue(self) -> list[tuple[Path, Exception]]:
        """Get samples that failed enrichment."""
        return list(self.dead_letter)

    def clear_dead_letter_queue(self) -> None:
        """Clear the dead letter queue."""
        self.dead_letter.clear()
```

**Deliverables**:

- Tier-ordered provider execution
- Runtime validation integration
- Dead-letter queue
- Provider fallback

**Total**: ~16h (3 work chunks)

---

## Phase 5: Production Hardening (Week 6-7)

### 5.1 Memory Management (P1-5 Fix)

**Objective**: Bounded caches for large datasets

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.1.1 | Create `storage/cache.py` with LRU-bounded cache | 3h | - |
| 5.1.2 | Add streaming JSONL parser for PubTabNet (500K+ entries) | 4h | - |
| 5.1.3 | Replace global caches with bounded instances | 3h | - |
| 5.1.4 | Add lint rule for "no module-level caches" | 2h | - |
| 5.1.5 | Write memory benchmarks for large datasets | 3h | - |

**Implementation - storage/cache.py**:

```python
"""LRU-bounded caches for annotation data."""

from collections import OrderedDict
from typing import Any, TypeVar, Generic

T = TypeVar("T")

class BoundedCache(Generic[T]):
    """LRU-bounded cache for annotations.

    Prevents OOM on large datasets (500K+ samples).
    """

    def __init__(self, max_size: int = 10_000):
        self.max_size = max_size
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> T | None:
        """Get item, updating LRU order."""
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, key: str, value: T) -> None:
        """Put item, evicting oldest if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()

    @property
    def stats(self) -> dict:
        """Cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
        }


class StreamingJSONLReader:
    """Streaming reader for large JSONL files.

    Used for PubTabNet (500K+ entries) to avoid OOM.
    """

    def __init__(self, file_path: Path, cache_size: int = 1000):
        self.file_path = file_path
        self.cache = BoundedCache(max_size=cache_size)
        self._index: dict[str, int] = {}  # filename -> line offset
        self._indexed = False

    def build_index(self) -> None:
        """Build filename → offset index for random access."""
        self._index.clear()
        with open(self.file_path) as f:
            offset = 0
            for line in f:
                data = json.loads(line)
                filename = data.get("filename", data.get("file_name"))
                if filename:
                    self._index[filename] = offset
                offset = f.tell()
        self._indexed = True

    def get(self, filename: str) -> dict | None:
        """Get annotation for filename with caching."""
        # Check cache first
        cached = self.cache.get(filename)
        if cached is not None:
            return cached

        # Build index if needed
        if not self._indexed:
            self.build_index()

        # Seek to offset and read
        offset = self._index.get(filename)
        if offset is None:
            return None

        with open(self.file_path) as f:
            f.seek(offset)
            line = f.readline()
            data = json.loads(line)
            self.cache.put(filename, data)
            return data
```

**Deliverables**:

- LRU-bounded cache implementation
- Streaming JSONL reader
- Memory benchmarks
- No module-level caches

**Total**: ~15h (3 work chunks)

---

### 5.2 Batch-Aware Scanner

**Objective**: Scanner that properly leverages batching

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.2.1 | Create `workflow/scanner.py` with batch accumulation | 4h | - |
| 5.2.2 | Implement batch-aware checkpointing (every N batches) | 3h | - |
| 5.2.3 | Add progress reporting for long-running scans | 2h | - |
| 5.2.4 | Write performance benchmarks | 3h | - |

**Deliverables**:

- Batch-accumulating scanner
- Batch-level checkpointing
- Progress reporting

**Total**: ~12h (2-3 work chunks)

---

### 5.3 Monitoring Integration

**Objective**: Prometheus metrics and structured logging

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.3.1 | Create `monitoring/metrics.py` with Prometheus metrics | 4h | - |
| 5.3.2 | Create `monitoring/logging.py` with structured logging | 3h | - |
| 5.3.3 | Add metrics to pipeline stages | 3h | - |
| 5.3.4 | Add Grafana dashboard template | 2h | - |

**Implementation - monitoring/metrics.py**:

```python
"""Prometheus metrics for annotation pipeline."""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create a custom registry to avoid conflicts
REGISTRY = CollectorRegistry()

# Counters
IMAGES_PROCESSED = Counter(
    "annotation_images_processed_total",
    "Total images processed",
    ["dataset", "status"],
    registry=REGISTRY,
)

BATCHES_PROCESSED = Counter(
    "annotation_batches_processed_total",
    "Total batches processed",
    ["dataset", "stage"],
    registry=REGISTRY,
)

ERRORS_TOTAL = Counter(
    "annotation_errors_total",
    "Total errors by type",
    ["dataset", "error_type"],
    registry=REGISTRY,
)

# Histograms
BATCH_DURATION = Histogram(
    "annotation_batch_duration_seconds",
    "Batch processing duration",
    ["dataset", "stage"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

IMAGE_DURATION = Histogram(
    "annotation_image_duration_seconds",
    "Per-image processing duration",
    ["dataset"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Gauges
CURRENT_DATASET = Gauge(
    "annotation_current_dataset_info",
    "Currently processing dataset",
    ["dataset"],
    registry=REGISTRY,
)

CHECKPOINT_PROGRESS = Gauge(
    "annotation_checkpoint_progress",
    "Checkpoint progress (0-1)",
    ["dataset"],
    registry=REGISTRY,
)

def get_metrics_text() -> str:
    """Get metrics in Prometheus text format."""
    from prometheus_client import generate_latest
    return generate_latest(REGISTRY).decode("utf-8")
```

**Deliverables**:

- Prometheus metrics
- Structured logging
- Grafana dashboard template

**Total**: ~12h (2-3 work chunks)

---

### 5.4 Comprehensive Testing

**Objective**: 80%+ coverage with unit and integration tests

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.4.1 | Create test fixtures (sample images, mock parsers) | 4h | - |
| 5.4.2 | Write unit tests for all schema classes | 4h | - |
| 5.4.3 | Write unit tests for integrity module | 3h | - |
| 5.4.4 | Write unit tests for parsers (representative sample) | 4h | - |
| 5.4.5 | Write unit tests for enrichment providers | 4h | - |
| 5.4.6 | Write unit tests for storage module | 3h | - |
| 5.4.7 | Write integration tests for pipeline | 5h | - |
| 5.4.8 | Write E2E tests for full workflows | 4h | - |
| 5.4.9 | Write property-based tests for migrations | 3h | - |
| 5.4.10 | Set up coverage reporting and enforcement | 2h | - |

**Deliverables**:

- Comprehensive test suite
- 80%+ coverage
- CI integration

**Total**: ~36h (6-7 work chunks)

---

### 5.5 Pre-flight Checks and Validation

**Objective**: Runtime validation and startup checks

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.5.1 | Implement pre-flight checks (disk, paths, models) | 3h | - |
| 5.5.2 | Add configuration validation | 2h | - |
| 5.5.3 | Add provider availability checks | 2h | - |
| 5.5.4 | Write tests for validation | 2h | - |

**Deliverables**:

- Pre-flight check system
- Configuration validation
- Clear error messages

**Total**: ~9h (2 work chunks)

---

### 5.6 Documentation Finalization

**Objective**: Finalize V2 architecture documentation and retire V1

| Task ID | Task | Estimate | Assignee |
|---------|------|----------|----------|
| 5.6.1 | Review and update V2 draft with implementation details | 3h | - |
| 5.6.2 | Update source file traceability with actual LOC counts | 2h | - |
| 5.6.3 | Verify all code references and links in V2 | 2h | - |
| 5.6.4 | Update PlantUML diagrams if pipeline changed | 3h | - |
| 5.6.5 | Add deprecation notice to V1 index.md | 1h | - |
| 5.6.6 | Rename index.v2-draft.md → index.md (atomic replace) | 1h | - |
| 5.6.7 | Archive V1 as index.v1-archived.md | 1h | - |
| 5.6.8 | Update all cross-references in related Level 2 docs | 2h | - |
| 5.6.9 | Run architecture link validation script | 1h | - |

**Documentation Lifecycle**:

```text
Current State:
  index.md (V1) ← Active
  index.v2-draft.md ← Draft for target architecture

After 5.6.5:
  index.md (V1) ← Deprecated notice added
  index.v2-draft.md ← Ready for promotion

After 5.6.6-5.6.7:
  index.v1-archived.md ← Archived (read-only reference)
  index.md (V2) ← Active (promoted from draft)
```

**Deliverables**:

- Finalized V2 architecture documentation
- V1 archived with deprecation notice
- All cross-references updated
- Link validation passing

**Total**: ~16h (3-4 work chunks)

---

## Migration Strategy

### Phase 1: Parallel Operation (Week 1-2)

1. New package in `src/image_preprocessing_detector/annotation/`
2. Original scripts unchanged
3. Run both in parallel, compare outputs with canonicalization

**Output Equivalence Testing**:

```python
def compare_outputs(old_json: Path, new_json: Path) -> list[str]:
    """Compare old and new outputs with tolerance."""
    differences = []

    old = json.load(open(old_json))
    new = json.load(open(new_json))

    # Canonicalize for comparison
    old_canonical = canonicalize(old)
    new_canonical = canonicalize(new)

    # Compare with float tolerance
    if not deep_equals(old_canonical, new_canonical, float_tolerance=1e-6):
        differences.append(f"Content mismatch: {old_json}")

    return differences
```

### Phase 2: Compatibility Shim (Week 3-4)

1. Update `scripts/annotate_base_metadata.py` to import from new package
2. Maintain CLI compatibility
3. Deprecation warnings for direct script usage

### Phase 3: Full Migration (Week 5+)

1. Remove duplicated code from scripts
2. Scripts become thin CLI wrappers
3. Update documentation
4. **Full re-processing of all datasets** (hash discontinuity)

### Backward Compatibility Guarantees

- Schema version remains compatible (migrations for changes)
- Output JSON/Parquet format unchanged
- CLI arguments preserved
- Environment variables preserved

---

## Testing Strategy

### Test Categories

| Category | Coverage Target | Focus |
|----------|-----------------|-------|
| Unit Tests | 90%+ | Individual functions, classes |
| Integration Tests | 80%+ | Module interactions, pipeline |
| E2E Tests | 70%+ | Full workflows |
| Property Tests | Key schemas | Migration invariants |

### Test Structure

```text
tests/
├── unit/
│   └── annotation/
│       ├── test_schemas.py
│       ├── test_hashing.py
│       ├── test_atomic.py
│       ├── test_checkpointing.py
│       ├── test_parsers/
│       ├── test_enrichment/
│       └── test_storage/
├── integration/
│   └── annotation/
│       ├── test_pipeline.py
│       ├── test_workflow.py
│       └── test_parquet_merge.py
├── e2e/
│   └── annotation/
│       └── test_full_pipeline.py
├── property/
│   └── annotation/
│       └── test_migrations.py
└── fixtures/
    └── annotation/
        ├── sample_images/
        ├── sample_annotations/
        └── conftest.py
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Regression in existing functionality | Medium | High | Parallel operation phase, output comparison tests |
| Performance degradation | Low | Medium | Benchmark tests, profile comparison |
| Memory increase from abstractions | Low | Low | Bounded caches, lazy loading |
| Migration breaks existing workflows | Medium | High | Compatibility shim, gradual rollout |
| ML provider failures cascade | Low | Medium | Provider isolation, dead-letter queue, fallback chain |
| GPU memory OOM | Medium | Medium | Single-thread GPU, batch size limits |
| Hash discontinuity breaks downstream | High | High | **Document breaking change, plan full re-process** |

---

## Issue Traceability Matrix

| Issue ID | Phase | Task IDs | Status |
|----------|-------|----------|--------|
| P0-1 | 1.3 | 1.3.1, 1.3.2, 1.3.5, 1.3.7 | 🔵 Planned |
| P0-2 | 2.4 | 2.4.1-2.4.6 | 🔵 Planned |
| P0-3 | 2.5 | 2.5.1-2.5.5 | 🔵 Planned |
| P0-4 | 1.2 | 1.2.2, 1.2.7 | 🔵 Planned |
| P1-1 | 1.1, 2.x | 1.1.1-1.1.5, 2.1.1-2.1.9 | 🔵 Planned |
| P1-2 | 2.2, 5.1 | 2.2.1-2.2.6, 5.1.1-5.1.4 | 🔵 Planned |
| P1-3 | 1.3 | 1.3.2, 1.3.5 | 🔵 Planned |
| P1-4 | 3.3 | 3.3.1-3.3.4 | 🔵 Planned |
| P1-5 | 5.1 | 5.1.1-5.1.5 | 🔵 Planned |
| P2-1 | 5.4 | 5.4.1-5.4.10 | 🔵 Planned |
| P2-2 | 1.3 | 1.3.3-1.3.4, 1.3.6 | 🔵 Planned |
| P2-3 | 1.4 | 1.4.1-1.4.7 | 🔵 Planned |
| P2-4 | 2.1 | 2.1.1-2.1.9 | 🔵 Planned |
| P2-5 | 3.2 | 3.2.1-3.2.5 | 🔵 Planned |
| P2-6 | 2.3, 5.2 | 2.3.1-2.3.7, 5.2.1-5.2.4 | 🔵 Planned |

**Documentation Tasks** (not issue-driven):

| Task Area | Phase | Task IDs | Status |
|-----------|-------|----------|--------|
| Arch Doc Finalization | 5.6 | 5.6.1-5.6.9 | 🔵 Planned |

---

## Success Metrics

### Technical Metrics

- [ ] Zero critical bugs in production (P0 issues resolved)
- [ ] 80%+ test coverage
- [ ] <100ms overhead per image vs. current
- [ ] Memory usage bounded to 4GB for largest dataset
- [ ] GPU memory stable (no OOM with batching)

### Process Metrics

- [ ] New dataset addition: <2 hours (vs. current 4+ hours)
- [ ] Schema update: <1 hour with migration
- [ ] Bug fix deployment: <30 minutes

### Quality Metrics

- [ ] All 15 identified issues resolved
- [ ] No hardcoded paths in production code
- [ ] Full type coverage (BasedPyright strict)
- [ ] No module-level global caches
- [ ] V2 architecture documentation finalized (V1 archived)

---

## Appendix A: CLI Commands

```bash
# Dataset annotation
imgprep annotation scan --dataset diqa-5000 --use-yolo
imgprep annotation scan --all --parallel 4
imgprep annotation scan --resume

# Dataset management
imgprep annotation add-dataset --name new-dataset --interactive
imgprep annotation validate-config
imgprep annotation list-datasets

# Schema management
imgprep annotation migrate --target-version 2.2 --dry-run
imgprep annotation migrate --target-version 2.2 --apply
imgprep annotation rollback --version 2.0 --file path/to/file.json

# Utilities
imgprep annotation stats
imgprep annotation export --format parquet
imgprep annotation verify-integrity
imgprep annotation metrics  # Prometheus metrics endpoint
```

---

## Appendix B: Configuration File Example

```yaml
# config/annotation.yaml
annotation:
  paths:
    e_drive_root: /mnt/e/image_detection
    metadata_root: /mnt/e/image_detection/metadata_registry
    checkpoint_dir: /mnt/e/image_detection/metadata_registry/.checkpoints

  processing:
    workers: 4
    batch_size: 100
    checkpoint_interval: 10  # batches
    cache_size_limit: 10000

  integrity:
    hash_full_file: true  # MUST be true (P0-1 fix)
    atomic_fsync: false
    verify_on_write: true

  enrichment:
    yolo:
      enabled: true
      model_path: models/doclayout_yolo_docstructbench.pt
      confidence_threshold: 0.25
    siglip:
      enabled: false
      model_path: null
      batch_size: 32

  monitoring:
    prometheus_enabled: true
    prometheus_port: 9090
    structured_logging: true
```

---

## Appendix C: Work Chunk Summary

| Phase | Total Hours | Work Chunks (4-6h) |
|-------|-------------|-------------------|
| Phase 1: Foundation | ~67h | 12-14 chunks |
| Phase 2: Core Refactoring | ~141h | 24-28 chunks |
| Phase 3: Extensibility | ~45h | 8-10 chunks |
| Phase 4: ML Integration | ~31h | 6-7 chunks |
| Phase 5: Production Hardening (5.1-5.5) | ~84h | 15-17 chunks |
| Phase 5: Documentation Finalization (5.6) | ~16h | 3-4 chunks |
| **Total** | **~384h** | **68-80 chunks** |

**Estimated Duration**: 6-7 weeks with 2-3 developers working in parallel

---

*Document generated from multi-model consensus analysis (5 models, 8.4/10 average score)
and repository structure exploration. Updated with all consensus-identified improvements.*
