---
schema_type: common
title: "Level 2: Data Preparation (V2 - Post-Refactoring)"
description: "Detailed data preparation workflow for dataset ingestion, cataloging,
  and metadata management - Refactored modular architecture"
tags:
- architecture
- diagrams
- plantuml
- level_2
- data_preparation
- workstream_3
status: draft
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the refactored data preparation pipeline with modular annotation
  package, three-layer metadata architecture, and production-hardened storage strategy."
---

> **DRAFT DOCUMENT**: This document describes the target architecture after completing
> the [Metadata Annotation Refactoring Plan](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md).
> For current state, see [index.md](index.md) (V1).

This level provides comprehensive documentation for the Data Preparation workstream, which handles dataset ingestion and cataloging. Datasets are kept in their **original form** without normalization to maintain standardization and reusability across different training configurations.

---

## Workstream Overview

**Purpose**: Ingest, catalog, and prepare datasets for downstream workstreams (Model Training, Pseudo-Labeling, Synthetic Generation).

**Key Principles**:

- **NO DPI normalization** - Datasets remain in original resolution for maximum reusability
- **Three-layer metadata architecture** - Immutable, Enrichment, Training layers
- **Provenance tracking** - Full lineage for every sample
- **Strict separation** - Training data vs. benchmark data
- **Modular extensibility** - Plugin-based parser architecture
- **Production reliability** - Atomic operations, checkpointing, validation

---

## Architecture Changes (V1 → V2)

| Aspect | V1 (Current) | V2 (Post-Refactoring) |
|--------|--------------|----------------------|
| **Core Implementation** | `annotate_base_metadata.py` (3,853 LOC monolith) | `annotation/` package (~4,500 LOC modular) |
| **Parser Architecture** | Inline functions in single file | Plugin registry with `DatasetParser` protocol |
| **Hashing** | Partial SHA256 (64KB only) | Full-file SHA256 (breaking change) |
| **Storage** | Single `samples.parquet` file | Partitioned Parquet (`dataset_name=X/`) |
| **Checkpointing** | Dataset-level only | Hash-based intra-dataset resume |
| **ML Integration** | Direct YOLO calls | Provider pattern with batching |
| **Configuration** | Hardcoded paths | External YAML/env configuration |
| **Testing** | Zero coverage | 80%+ coverage with unit/integration/E2E |
| **Monitoring** | Print statements | Prometheus metrics + structured logging |

---

## Technical Diagrams

### Training Data Ingestion Pipeline

High-level flow for collecting, normalizing, and splitting training datasets.

![Training Data Ingestion](project-a-training-data-ingestion.svg)

*PlantUML source: [`project-a-training-data-ingestion.puml`](project-a-training-data-ingestion.puml)*

---

### Automated Data Labeling Pipeline

Three-layer pipeline for dataset annotation and label management implementing the metadata versioning schema.

![Automated Data Labeling Pipeline](automated-data-labeling-pipeline.svg)

*PlantUML source: [`automated-data-labeling-pipeline.puml`](automated-data-labeling-pipeline.puml)*

---

## Three-Layer Metadata Architecture

The data preparation pipeline implements a versioned metadata schema with three distinct layers:

### Layer 1: IMMUTABLE (Original Labels)

Preserves source dataset labels exactly as provided, ensuring reproducibility.

| Data Class | Module | Fields | Purpose |
|------------|--------|--------|---------|
| `OriginalFileMetadata` | `annotation/schemas/immutable.py` | format, width_px, height_px, channels, bit_depth, file_size_bytes, dpi, color_space | Image file characteristics |
| `OriginalLabels` | `annotation/schemas/immutable.py` | diqa_mos, live_dmos, csiq_dmos, doclaynet_annotations, tablebank_annotations, funsd_annotations | Source-specific labels |

**Key Implementation**: [`src/image_preprocessing_detector/annotation/schemas/immutable.py`](../../../../../src/image_preprocessing_detector/annotation/schemas/immutable.py)

### Layer 2: ENRICHMENT (Derived Annotations)

Our derived annotations with full provenance tracking and versioning.

| Data Class | Module | Fields | Purpose |
|------------|--------|--------|---------|
| `EnrichmentData` | `annotation/schemas/enrichment.py` | capture_method, resolution_category, domain_level1-3, text_density, layout_type, degradations, llm_predicted_mos | Computed metadata |
| `EnrichmentVersion` | `annotation/schemas/enrichment.py` | version, created_at, created_by, method, description | Version provenance |

**Enrichment Methods** (via Provider Pattern):

| Provider | Module | Tier | Purpose |
|----------|--------|------|---------|
| `YOLOProvider` | `annotation/enrichment/providers/yolo.py` | Tier 2 | Layout detection (11 DocLayNet classes) |
| `SigLIPProvider` | `annotation/enrichment/providers/siglip.py` | Tier 2 | Quality score prediction |
| Built-in | `annotation/enrichment/tiering.py` | Tier 0-1 | Dataset-derived metadata |

### Layer 3: TRAINING (Computed On-Demand)

Training-ready labels computed from original + enrichment layers.

| Data Class | Module | Fields | Purpose |
|------------|--------|--------|---------|
| `TrainingLabels` | `scripts/build_training_labels.py` | iqa_vector (45-dim), iqa_binary, anchor_score, anchor_weight, element_labels | Model training inputs |

**Key Implementation**: [`scripts/build_training_labels.py`](../../../../../scripts/build_training_labels.py) - Lines 145-410

**Anchor Score Priority**:

1. `human` (weight: 1.0) - Ground-truth MOS/DMOS
2. `llm_high` (weight: 0.8) - LLM confidence > 0.8
3. `llm_medium` (weight: 0.5) - LLM confidence 0.5-0.8
4. `llm_low` (weight: 0.3) - LLM confidence < 0.5
5. `synthetic` (weight: 0.3) - Augmentation-derived
6. `none` (weight: 0.0) - No anchor available

---

## Modular Package Architecture (V2)

### Package Structure

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
│   ├── checkpointing.py            # Intra-dataset checkpoints (hash-based)
│   └── atomic.py                   # Atomic file operations (os.replace)
├── parsers/
│   ├── __init__.py                 # Parser registry + explicit registration
│   ├── base.py                     # DatasetParser protocol
│   ├── registry.py                 # Factory with explicit registration
│   ├── quality/                    # DIQA, SmartDoc, OCR_Quality parsers
│   ├── layout/                     # DocLayNet, TableBank, PubTabNet, FUNSD
│   ├── handwriting/                # SignaTR, NIST_SD19, PUCIT-OHUL
│   ├── multilingual/               # MDIW, CC-OCR, multilingual scripts
│   └── document/                   # RVL-CDIP, OmniDocBench
├── enrichment/
│   ├── __init__.py
│   ├── tiering.py                  # Tier classification
│   ├── content_flags.py            # Content derivation
│   ├── errors.py                   # Structured error hierarchy
│   ├── manager.py                  # Provider orchestration + validation
│   └── providers/
│       ├── __init__.py
│       ├── base.py                 # EnrichmentProvider protocol
│       ├── yolo.py                 # DocLayout-YOLO provider
│       └── siglip.py               # SigLIP weak labeling
├── storage/
│   ├── __init__.py
│   ├── json_writer.py              # Per-dataset JSON output
│   ├── parquet_writer.py           # Partitioned Parquet storage
│   └── cache.py                    # LRU-bounded annotation cache
├── workflow/
│   ├── __init__.py
│   ├── pipeline.py                 # CPU/GPU separated pipeline
│   ├── scanner.py                  # Batch-aware dataset scanner
│   ├── orchestrator.py             # Multi-dataset coordination
│   └── progress.py                 # Progress tracking
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                  # Prometheus metrics
│   └── logging.py                  # Structured logging
├── cli.py                          # Click CLI interface
└── compat.py                       # Backward compatibility shim
```

### Key Design Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: No global state, use `create_orchestrator()` factory
3. **Protocol-Based**: Use `typing.Protocol` for extensibility
4. **Configuration-Driven**: External YAML/env for paths and settings
5. **Fail-Fast**: Explicit errors > silent defaults
6. **Reuse-First**: Import from `schema_utils/` - NO duplication
7. **CPU/GPU Separation**: Parallel CPU work, batched single-thread GPU inference

---

## Parser Architecture (V2)

### DatasetParser Protocol

```python
@runtime_checkable
class DatasetParser(Protocol):
    """Protocol for dataset-specific label parsers."""

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
        """Parse labels for a single image."""
        ...

    def supports_batch(self) -> bool:
        """Whether this parser supports batch operations."""
        return False
```

### Parser Registry

| Category | Parsers | Datasets |
|----------|---------|----------|
| **Quality** | `DIQAParser`, `SmartDocParser`, `OCRQualityParser` | diqa-5000, smartdoc-qa, ocr_quality |
| **Layout** | `DocLayNetParser`, `TableBankParser`, `PubTabNetParser`, `FUNSDParser` | doclaynet, tablebank, pubtabnet, funsd |
| **Handwriting** | `SignaTRParser`, `NISTParser`, `MathsHandwritingParser` | signatr6k, nist_sd19, maths_handwriting |
| **Multilingual** | `MDIWParser`, `CCOCRParser` | mdiw, cc_ocr |
| **Document** | `RVLCDIPParser`, `OmniDocBenchParser` | rvl_cdip, omnidocbench |

**Adding a New Dataset**:

```bash
# Generate parser template
imgprep annotation add-dataset --name my-dataset --interactive

# Register parser (in parsers/registry.py)
from .quality.my_dataset import MyDatasetParser
registry.register(MyDatasetParser())
```

---

## Pipeline Architecture (V2)

### Three-Stage CPU/GPU Separated Pipeline

```text
┌─────────────────────────────────────────────────────────────────┐
│                    AnnotationPipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  CPU Stage  │───▶│  GPU Stage  │───▶│  IO Stage   │         │
│  │ (Parallel)  │    │ (Single)    │    │ (Thread)    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│        │                   │                   │                │
│  ProcessPool-        Single thread       ThreadPool-            │
│  Executor            batched GPU         Executor               │
│  (workers=4)         inference           (writer)               │
│                                                                 │
│  • File hashing      • YOLO batches     • Parquet writes        │
│  • Label parsing     • SigLIP batches   • JSON writes           │
│  • Validation        • Quality scores   • Checkpoints           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Design Decision**: GPU models (YOLO, SigLIP) run in a **single thread** to avoid CUDA pickle/fork issues. Only CPU-bound work (hashing, parsing) uses ProcessPoolExecutor.

### Checkpointing Strategy

| Aspect | V1 | V2 |
|--------|----|----|
| **Granularity** | Per-dataset only | Per-batch (every N batches) |
| **Resume Key** | Processed count | `last_path + last_hash` |
| **File Changes** | Full restart required | Automatic adjustment |
| **Atomicity** | `os.rename()` | `os.replace()` with optional fsync |

---

## Storage Strategy (V2)

### Partitioned Parquet Architecture

**V1 Problem**: Single `samples.parquet` file requires read-modify-write for incremental updates, causing OOM on large datasets (500K+ samples).

**V2 Solution**: Partitioned Parquet with Hive-style partitioning.

```text
metadata_registry/
├── json/                           # Full detail per dataset (unchanged)
│   ├── diqa-5000/
│   ├── doclaynet/
│   └── ...
└── parquet/                        # Partitioned by dataset
    ├── dataset_name=diqa-5000/
    │   └── part-0000.parquet
    ├── dataset_name=doclaynet/
    │   └── part-0000.parquet
    └── ...
```

**Benefits**:

- O(1) per-dataset writes (atomic partition replacement)
- No read-modify-write (no OOM risk)
- `pyarrow.dataset` provides unified view for queries
- Compatible with Spark, DuckDB, Polars

**Query Example**:

```python
import pyarrow.dataset as ds

# Read all data (unified view)
dataset = ds.dataset("metadata_registry/parquet/", partitioning="hive")
table = dataset.to_table()

# Read single dataset efficiently
filtered = dataset.to_table(filter=ds.field("dataset_name") == "doclaynet")
```

### Dual-Storage Architecture

| Tier | Location | Size | Purpose |
|------|----------|------|---------|
| **Local** | `data/` (symlinks) | ~1 MB | Development access via NFS symlinks |
| **NFS Primary** | `/mnt/unraid/training_data/image_detection/` | ~235 GB | All datasets, training, and metadata |
| **GCS Backup** | `gs://image_detection_b/` | ~287 GB | Cloud backup and Colab training |
| **E: Drive** | `/mnt/e/image_detection/` | ~200 GB | Base data and benchmark-only datasets |

### Directory Structure

```text
/mnt/e/image_detection/
├── 01_base_data/                   # Training-eligible datasets
│   ├── degraded/                   # tobacco800, historical_degraded
│   ├── documents/                  # rvl_cdip, doclaynet
│   ├── forms/                      # nist_db2, nist_sd6, funsd, funsd_plus, sroie
│   ├── tables/                     # tablebank, pubtabnet
│   ├── handwriting/                # nist_sd19, signatr6k, maths_handwriting
│   ├── formulas/                   # im2latex, mathverse
│   └── educational/                # multimodal_textbook
├── 02_benchmark_only/              # Evaluation-only datasets (human MOS labels)
│   ├── diqa-5000/                  # Ground-truth quality scores
│   ├── live/                       # LIVE IQA benchmark
│   ├── csiq/                       # CSIQ IQA benchmark
│   ├── smartdoc-qa/                # Mobile document capture
│   └── dibco/                      # Document binarization
└── metadata_registry/              # Output artifacts (V2 structure)
    ├── json/                       # Full detail per dataset
    ├── parquet/                    # Partitioned by dataset_name
    └── .checkpoints/               # Intra-dataset checkpoints
```

---

## Dataset Inventory

### Benchmark Datasets (Evaluation Only)

| Dataset | Size | Samples | License | Human Labels | Purpose |
|---------|------|---------|---------|--------------|---------|
| **DIQA-5000** | 5.4 GB | 5,500 | Research | MOS | Document quality benchmark |
| **LIVE** | ~1 GB | 779 | Research | DMOS | Classical IQA reference |
| **CSIQ** | ~2 GB | 866 | Research | DMOS | Classical IQA reference |
| **SmartDoc-QA** | ~2 GB | 1,162 | Research | MOS | Mobile capture quality |
| **OmniDocBench** | 5.95 GB | Varies | Apache-2.0 | Multi-task | Comprehensive benchmark |
| **OHR-Bench** | 1.8 GB | Varies | HuggingFace | OCR quality | Handwriting recognition |

### Training Datasets (Base Data)

| Dataset | Size | Samples | License | Content Flags | Domain |
|---------|------|---------|---------|---------------|--------|
| **DocLayNet** | 40.97 GB | 80k+ | CDLA-1.0 | table, formula | Scientific |
| **TableBank** | 46.38 GB | 424k | Apache-2.0 | table | Scientific |
| **PubTabNet** | 16 GB | 500k | MIT | table | Scientific |
| **FUNSD/FUNSD+** | ~0.5 GB | 1,113 | MIT | form, handwriting, signature | Administrative |
| **RVL-CDIP** | ~40 GB | 400k | Research | mixed | Administrative |
| **SignaTR6K** | 142 MB | 6k | CC BY 4.0 | signature | Personal |
| **IM2LaTeX** | Varies | 100k+ | Open | formula | Scientific |

---

## Current Status: Layer 2 Annotation

**Last Updated**: 2025-01-26

### Annotation Completion: 24 of 24 datasets (100%)

All datasets have been successfully annotated with three-layer metadata (immutable, enrichment, training).

**Output Location**: `/mnt/e/image_detection/metadata_registry/json/`
**Total Size**: 2.2 GB
**Schema Version**: 2.0

> **Note**: Post-refactoring, all datasets will require re-annotation due to hash discontinuity
> (full-file SHA256 replaces partial 64KB hashing). See [METADATA_ANNOTATION_REFACTORING_PLAN.md](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md#breaking-change-notice).

| Dataset | Samples | Output Size | Enrichment Tier | Status |
|---------|---------|-------------|-----------------|--------|
| dibco | 219 | 423 KB | Tier 2 (YOLO) | ✅ Complete |
| diqa-5000 | 5,500 | 1.1 MB | Tier 1 (MOS) | ✅ Complete |
| doclaynet | 81,471 | 152 MB | Tier 1 (COCO) | ✅ Complete |
| fintabnet | Large | 193 MB | Tier 2 (YOLO) | ✅ Complete |
| funsd | 149 | 8.7 KB | Tier 1 (COCO) | ✅ Complete |
| funsd_plus | 1,139 | 2.2 MB | Tier 2 (YOLO) | ✅ Complete |
| historical_degraded | 1,662 | 3.3 MB | Tier 2 (YOLO) | ✅ Complete |
| im2latex | 10,000 | 20 MB | Tier 0 (formula) | ✅ Complete |
| maths_handwriting | 16,000 | 30 MB | Tier 0 (formula+hand) | ✅ Complete |
| mathverse | 8,000 | 14 MB | Tier 0 (formula) | ✅ Complete |
| multimodal_textbook | 1,113 | 2.7 MB | Tier 2 (YOLO) | ✅ Complete |
| nist_db2 | 6,200 | 12 MB | Tier 0 (handwriting) | ✅ Complete |
| nist_sd19 | 4,000 | 7.5 MB | Tier 0 (handwriting) | ✅ Complete |
| nist_sd6 | 6,100 | 12 MB | Tier 0 (handwriting) | ✅ Complete |
| ocr_quality | 1,170 | 2.2 MB | Tier 1 (OCR GT) | ✅ Complete |
| omnidocbench | 500 | 996 KB | Tier 2 (YOLO) | ✅ Complete |
| pubtabnet | 519,030 | 1.0 GB | Tier 0 (table) | ✅ Complete |
| realdae | 850 | 1.6 MB | Tier 2 (YOLO) | ✅ Complete |
| rvl_cdip | 18,000 | 34 MB | Tier 2 (YOLO) | ✅ Complete |
| signatr6k | 13,000 | 25 MB | Tier 0 (signature) | ✅ Complete |
| smartdoc-qa | 5,280 | 9.7 MB | Tier 2 (YOLO) | ✅ Complete |
| sroie | 2,400 | 4.5 MB | Tier 2 (YOLO) | ✅ Complete |
| tablebank | 384,000 | 646 MB | Tier 1 (COCO) | ✅ Complete |
| tobacco800 | 1,400 | 2.7 MB | Tier 2 (YOLO) | ✅ Complete |

**Enrichment Tier Distribution**:

- **Tier 0** (by construction): 8 datasets - Content known from dataset purpose
- **Tier 1** (existing annotations): 5 datasets - COCO, MOS, or OCR ground truth
- **Tier 2** (YOLO inference): 11 datasets - DocLayout-YOLO layout detection

---

## Key Scripts and Components (V2)

### CLI Interface

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

### Dataset Download Scripts

| Script | Purpose | Datasets |
|--------|---------|----------|
| [download_all_datasets.py](../../../../../scripts/download_all_datasets.py) | Master download orchestrator | All datasets |
| [download_iqa_datasets.py](../../../../../scripts/download_iqa_datasets.py) | IQA benchmarks | LIVE, CSIQ, LIVE Challenge |
| [download_omnidocbench.py](../../../../../scripts/download_omnidocbench.py) | Multi-task benchmark | OmniDocBench |
| [download_table_datasets.py](../../../../../scripts/download_table_datasets.py) | Table datasets | TableBank, PubTabNet |
| [download_phase3_datasets.py](../../../../../scripts/download_phase3_datasets.py) | ML training datasets | Phase 3 specific |

### Metadata Processing (V2 Modules)

| Module | Layer | Purpose | Location |
|--------|-------|---------|----------|
| `annotation.workflow.orchestrator` | 1 & 2 | Multi-dataset coordination | `annotation/workflow/orchestrator.py` |
| `annotation.workflow.pipeline` | 1 & 2 | CPU/GPU separated pipeline | `annotation/workflow/pipeline.py` |
| `annotation.parsers.*` | 1 | Dataset-specific parsing | `annotation/parsers/` |
| `annotation.enrichment.manager` | 2 | Provider orchestration | `annotation/enrichment/manager.py` |
| `annotation.storage.parquet_writer` | Output | Partitioned Parquet | `annotation/storage/parquet_writer.py` |
| `build_training_labels.py` | 3 | Training-ready labels | `scripts/build_training_labels.py` |

### Compatibility Layer

For backward compatibility during migration, thin wrapper scripts are preserved:

| Script | V2 Behavior |
|--------|-------------|
| `scripts/annotate_base_metadata.py` | Imports from `annotation.cli`, preserves CLI interface |
| `scripts/annotate_base_metadata_incremental.py` | Imports from `annotation.workflow`, preserves progress tracking |

---

## Data Flow (V2)

```text
External Sources                    Annotation Package                 Storage / Downstream
─────────────────                   ──────────────────                 ────────────────────

┌──────────────┐                    ┌─────────────────────────────┐
│ HuggingFace  │───download_*.py───▶│ annotation.workflow         │
│ GCS Bucket   │                    │   .orchestrator             │
│ Direct URLs  │                    │   .pipeline (CPU/GPU sep)   │
└──────────────┘                    └────────────┬────────────────┘
                                                 │
                                    ┌────────────▼────────────────┐
                                    │ annotation.parsers          │
                                    │   .registry.get_parser()    │
                                    │   ├── quality/              │
                                    │   ├── layout/               │
                                    │   ├── handwriting/          │
                                    │   └── document/             │
                                    └────────────┬────────────────┘
                                                 │
                                    ┌────────────▼────────────────┐
                                    │ annotation.enrichment       │
                                    │   .manager (tier-ordered)   │
                                    │   .providers/               │
                                    │     ├── yolo.py (batched)   │
                                    │     └── siglip.py           │
                                    └────────────┬────────────────┘
                                                 │
                                    ┌────────────▼────────────────┐
                                    │ annotation.storage          │
                                    │   .json_writer (per-dataset)│
                                    │   .parquet_writer           │───▶ Workstream 5
                                    │     (partitioned)           │     (Labeling Models)
                                    └────────────┬────────────────┘
                                                 │
                                    ┌────────────▼────────────────┐
                                    │ build_training_labels.py    │───▶ Workstream 2
                                    │   (Layer 3 computation)     │     (Prod Training)
                                    └────────────┬────────────────┘
                                                 │
                                    ┌────────────▼────────────────┐
                                    │ HybridIQADataset            │───▶ Workstream 4
                                    │ (PyTorch DataLoader)        │     (Pseudo-Labeling)
                                    └─────────────────────────────┘
```

---

## Configuration System (V2)

### Environment Variables

```bash
# Core paths
export ANNOTATION_E_DRIVE_ROOT=/mnt/e/image_detection
export ANNOTATION_METADATA_ROOT=/mnt/e/image_detection/metadata_registry

# Processing
export ANNOTATION_WORKERS=4
export ANNOTATION_BATCH_SIZE=100
export ANNOTATION_CACHE_SIZE=10000

# ML Providers
export ANNOTATION_YOLO_CONFIDENCE=0.25
export ANNOTATION_SIGLIP_ENABLED=false
```

### YAML Configuration

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

## Monitoring Integration (V2)

### Prometheus Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `annotation_images_processed_total` | Counter | dataset, status | Total images processed |
| `annotation_batches_processed_total` | Counter | dataset, stage | Total batches by stage |
| `annotation_errors_total` | Counter | dataset, error_type | Errors by type |
| `annotation_batch_duration_seconds` | Histogram | dataset, stage | Batch processing time |
| `annotation_checkpoint_progress` | Gauge | dataset | Checkpoint progress (0-1) |

### Structured Logging

```json
{
  "timestamp": "2025-01-26T10:30:00Z",
  "level": "INFO",
  "event": "batch_completed",
  "dataset": "doclaynet",
  "batch_size": 100,
  "batch_number": 42,
  "duration_ms": 1234,
  "stage": "gpu",
  "provider": "yolo"
}
```

---

## Error Handling (V2)

### Structured Error Hierarchy

```text
EnrichmentError (base)
├── ParserError           # Label parsing failures
├── ModelInferenceError   # ML provider failures
├── ProviderUnavailableError  # GPU not found, model missing
└── ValidationError       # Schema validation failures
```

### Dead-Letter Queue

Failed samples are tracked for later retry:

```python
# Get failed samples
dlq = enrichment_manager.get_dead_letter_queue()
for path, error in dlq:
    logger.error(f"Failed: {path} - {error}")

# Retry failed samples
enrichment_manager.retry_dead_letter()
```

---

## Source File Traceability (V2)

This section maps workflow steps to implementation files with estimated LOC counts.

| Workflow Step | Source Files | Est. LOC | Purpose |
|---------------|--------------|----------|---------|
| **Schemas** | `annotation/schemas/*.py` | ~600 | Dataclasses, enums, migrations |
| **Configuration** | `annotation/config/*.py` | ~400 | Settings, dataset configs |
| **Integrity** | `annotation/integrity/*.py` | ~350 | Hashing, checkpoints, atomic ops |
| **Parsers** | `annotation/parsers/**/*.py` | ~1,200 | 38+ dataset-specific parsers |
| **Enrichment** | `annotation/enrichment/**/*.py` | ~800 | Provider protocols, manager, errors |
| **Storage** | `annotation/storage/*.py` | ~500 | JSON writer, Parquet writer, cache |
| **Workflow** | `annotation/workflow/*.py` | ~650 | Pipeline, orchestrator, scanner |
| **Monitoring** | `annotation/monitoring/*.py` | ~300 | Metrics, logging |
| **CLI** | `annotation/cli.py` | ~200 | Click interface |
| **Layer 3** | `scripts/build_training_labels.py` | ~590 | Training label construction |
| **Package Total** | **~30 modules** | **~4,500** | — |

---

## Testing Strategy (V2)

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

### Coverage Targets

| Category | Target | Focus |
|----------|--------|-------|
| Unit Tests | 90%+ | Individual functions, classes |
| Integration Tests | 80%+ | Module interactions, pipeline |
| E2E Tests | 70%+ | Full workflows |
| Property Tests | Key schemas | Migration invariants |

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Dependency | Description |
|------------|------------|-------------|
| **None** | N/A | Data Preparation is the starting point |

### Downstream Consumers

| Workstream | Consumed Artifacts | Purpose |
|------------|--------------------|---------|
| **2. Production Model Training** | `parquet/`, images | Train ResNet teacher/student |
| **4. Pseudo-Labeling** | `parquet/`, images | Apply ensemble labeling |
| **5. Labeling & Benchmarking Models** | Raw images, metadata | Train labeling models |
| **8. Synthetic Data Generation** | Clean images | Degradation source material |

---

## Migration Guide: V1 → V2

### Breaking Changes

1. **Sample ID Discontinuity**: Full-file SHA256 hashing changes ALL sample IDs
   - **Impact**: Downstream systems relying on sample IDs will break
   - **Action**: Full re-processing of ALL datasets required (~24-48 hours)

2. **Parquet Structure**: Single file → partitioned directory
   - **Impact**: Existing queries may need adjustment
   - **Action**: Use `pyarrow.dataset` for unified view

3. **Configuration**: Hardcoded paths → external config
   - **Impact**: Environment variables required
   - **Action**: Set `ANNOTATION_*` env vars or provide YAML config

### Migration Steps

1. Deploy new `annotation/` package alongside existing scripts
2. Run parallel validation (compare outputs with canonicalization)
3. Update downstream consumers to use new sample IDs
4. Migrate Parquet data to partitioned structure
5. Switch scripts to thin wrappers
6. Run full re-annotation for hash consistency
7. Retire V1 architecture documentation

---

## Related Documentation

| Level | Diagram | Description |
|-------|---------|-------------|
| **Level 0** | [RAG Pipeline Overview](../../level-0/index.md) | Multi-project pipeline context |
| **Level 1** | [Project A Architecture](../../level-1/index.md) | System architecture |
| **Level 2** | [Pseudo-Labeling](../pseudo-labeling/index.md) | Downstream: ensemble labeling |
| **Level 2** | [Model Training](../model-training/index.md) | Downstream: production training |
| **Level 2** | [Synthetic Generation](../synthetic-generation/index.md) | Downstream: data augmentation |
| **Level 2** | [Labeling & Benchmarking](../labeling-benchmarking/index.md) | Downstream: labeling models |
| **Planning** | [Refactoring Plan](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md) | Implementation roadmap |

---

## Source Files

### Diagrams

- **Training Ingestion**: [`project-a-training-data-ingestion.puml`](project-a-training-data-ingestion.puml)
- **Labeling Pipeline**: [`automated-data-labeling-pipeline.puml`](automated-data-labeling-pipeline.puml)

### Core Package (V2)

- **Public API**: [`src/image_preprocessing_detector/annotation/__init__.py`](../../../../../src/image_preprocessing_detector/annotation/__init__.py)
- **Pipeline**: [`src/image_preprocessing_detector/annotation/workflow/pipeline.py`](../../../../../src/image_preprocessing_detector/annotation/workflow/pipeline.py)
- **Orchestrator**: [`src/image_preprocessing_detector/annotation/workflow/orchestrator.py`](../../../../../src/image_preprocessing_detector/annotation/workflow/orchestrator.py)

### Legacy Scripts (Compatibility)

- **Download Master**: [`scripts/download_all_datasets.py`](../../../../../scripts/download_all_datasets.py) (471 lines)
- **Metadata Wrapper**: [`scripts/annotate_base_metadata.py`](../../../../../scripts/annotate_base_metadata.py) (thin wrapper)
- **Training Labels**: [`scripts/build_training_labels.py`](../../../../../scripts/build_training_labels.py) (590 lines)

### Data Documentation

- **Data README**: [`data/README.md`](../../../../../data/README.md) (731 lines)
- **Dataset Locations**: [`docs/DATASET_LOCATIONS.md`](../../../../DATASET_LOCATIONS.md)

---

## Traceability

| Source Module | This Document Section |
|---------------|----------------------|
| `annotation/schemas/enums.py` | Capture Method Taxonomy, Domain Taxonomy |
| `annotation/config/datasets.py` | Dataset Configuration System |
| `annotation/schemas/immutable.py`, `enrichment.py` | Three-Layer Metadata Architecture |
| `annotation/parsers/**/*.py` | Parser Architecture, Label Parsers |
| `annotation/workflow/pipeline.py` | Pipeline Architecture |
| `annotation/storage/parquet_writer.py` | Storage Strategy |
| `annotation/monitoring/metrics.py` | Monitoring Integration |
| `build_training_labels.py` | Layer 3, Degradation Index, Anchor Score |

---

*V2 Draft - Post-refactoring architecture. This document will replace [index.md](index.md) upon
completion of [METADATA_ANNOTATION_REFACTORING_PLAN.md](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md) Phase 5.*
