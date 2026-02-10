---
schema_type: common
title: "Level 2: Data Preparation"
description: "Detailed data preparation workflow for dataset ingestion, cataloging,
  and metadata management - Post-refactoring modular architecture"
tags:
- architecture
- diagrams
- plantuml
- level_2
- data_preparation
- workstream_3
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the refactored data preparation pipeline with modular annotation
  package, three-layer metadata architecture, and production-hardened storage strategy."
---

> **POST-REFACTORING**: This document describes the completed architecture after implementing
> the [Metadata Annotation Refactoring Plan](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md).
> Phases 1-5 are complete. V1 architecture is archived.

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
| **Core Implementation** | `annotate_base_metadata.py` (3,853 LOC monolith) | `annotation/` package (~19,600 LOC modular) |
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

The data preparation pipeline implements a versioned metadata schema with three distinct layers.

**Schema Visualizations** (Mermaid diagrams with ER, class, and data flow views):

- [Layer 2 Enrichment Schema](../../../../schema/layer2_enrichment_schema.md) - Derived annotations with provenance tracking
- [Document Metadata Schema](../../../../schema/document_metadata_schema.md) - Project A → Project B handoff schema

**JSON Schema Definitions**:

- [layer2_enrichment.schema.json](../../../../schema/layer2_enrichment.schema.json)
- [document_metadata.schema.json](../../../../schema/document_metadata.schema.json)

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
| `EnrichmentData` | `annotation/schemas/enrichment.py` | capture_method, resolution_category, domain_level1-3, text_density, layout_type, degradations, llm_predicted_mos, color_mode (binarized/grayscale/color), document_age (modern/aged/historical) | Computed metadata |
| `EnrichmentVersion` | `annotation/schemas/enrichment.py` | version, created_at, created_by, method, description | Version provenance |

**Enrichment Methods** (via Provider Pattern):

| Provider | Module | Tier | Purpose |
|----------|--------|------|---------|
| `YOLOProvider` | `annotation/enrichment/providers/yolo.py` | Tier 2 | Layout detection (multi-schema via LayoutTaxonomy, 57 canonical classes) |
| `SigLIPProvider` | `annotation/enrichment/providers/siglip.py` | Tier 2 | SigLIP 2 multi-task enrichment (16 heads across 5 groups: IQA, Script, Orientation+Skew, Handwriting, Page Attrs) |
| Built-in | `annotation/enrichment/tiering.py` | Tier 0-1 | Dataset-derived metadata |

**Schema Utilities** (config-driven converters):

| Utility | Module | Config | Purpose |
|---------|--------|--------|---------|
| `ScriptMLMapping` | `schema_utils/script_ml_mapping.py` | `config/script_ml_classes.yaml` | ISO 15924 → ML class mapping |
| `LayoutTaxonomy` | `schema_utils/layout_taxonomy.py` | `config/layout_taxonomy.yaml` | 6-schema layout label conversion (~57 canonical classes) |

### Label Provenance System

All labels in the enrichment pipeline are tagged with a provenance tier that determines confidence and training weight:

| Tier | Name | Source | Confidence | Training Weight | Example |
|------|------|--------|------------|-----------------|---------|
| **Tier 0** | `tier_0_exact` | Synthetic ground truth | 1.0 (exact) | 1.0 | Genalog degradation parameters, orientation from generation script |
| **Tier 1** | `tier_1_annotation` | Human annotation | >= 0.9 | 1.0 | DIQA MOS scores, LIVE DMOS, COCO bounding boxes |
| **Tier 2** | `tier_2_model` | Model-predicted | >= 0.7 | 0.8 * confidence | SigLIP 2 quality predictions, YOLO layout detections |
| **Tier 3** | `tier_3_heuristic` | Rule-based derivation | >= 0.5 | 0.5 * confidence | Classical IQA detector scores, heuristic content flags |

The provenance tier flows through all three metadata layers and is used by the training label builder to compute per-sample anchor weights.

### Global Split Registry

To prevent train/test leakage across the 10 purpose-built training datasets, a **Global Split Registry** ensures cross-dataset split consistency:

- **Key**: SHA256 hash of the image file content
- **Assignment**: Each unique image is assigned exactly one split (train/val/test) at first encounter
- **Consistency**: If the same image appears in multiple datasets (e.g., orientation + skew), it receives the same split assignment everywhere
- **Ratios**: Default 80/10/10 (train/val/test), configurable per dataset
- **Storage**: Registry persisted as a Parquet file keyed by SHA256 hash

See [DATASET_DIVERSITY_REQUIREMENTS.md](../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md) for per-dataset diversity specifications.

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

## Three-Tier Script Architecture (Stream 1)

The annotation system uses a three-tier architecture for script (writing system) handling:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    Three-Tier Script Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │   Tier 1         │    │   Tier 2         │    │   Tier 3         │   │
│  │   STORAGE        │───▶│   ML TRAINING    │───▶│   ROUTING        │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘   │
│         │                        │                        │              │
│  Full ISO 15924           Grouped ML              OCR Engine             │
│  codes stored             classes                 selection              │
│  (e.g., "Latn",          (e.g., "LATN",         (e.g., rapidocr,       │
│   "Gujr", "Deva")         "INDIC_OTHER")         paddleocr, tesseract)  │
│                                                                          │
│  ──────────────────────────────────────────────────────────────────────  │
│  Config:                 Config:                 Config:                 │
│  schema.py               script_ml_classes.yaml  script_routing.yaml    │
│  (ISO15924Script enum)   (iso15924_to_ml_class)  (routing_rules)        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Storage (ISO 15924)

Full ISO 15924 4-letter script codes are stored in metadata, never aggregated.

| Data Class | Module | Field | Purpose |
|------------|--------|-------|---------|
| `OriginalLabels` | `annotation/schemas/immutable.py` | `iso15924_script_code` | Standardized script code |
| `LanguageInfo` | `schema.py` | `script` (ISO15924Script enum) | Schema-level storage |

**Key Implementation**:

- [`src/image_preprocessing_detector/schema_utils/iso_language_script.py`](../../../../../src/image_preprocessing_detector/schema_utils/iso_language_script.py) - ISO15924Script enum
- Validation helpers: `is_valid_iso15924_code()`, `get_iso15924_script()`, `validate_script_code_for_ml()`

### Tier 2: ML Training (Grouped Classes)

Scripts are grouped into ~19 ML classes for training via configurable mapping.

| Class | Module | Purpose |
|-------|--------|---------|
| `ScriptMLMapping` | `schema_utils/script_ml_mapping.py` | ISO 15924 → ML class mapping |

**Configuration**: [`config/script_ml_classes.yaml`](../../../../../config/script_ml_classes.yaml)

```yaml
ml_classes: [LATN, CYRL, GREK, ARAB, HEBR, DEVA, BENG, TAML, TELU,
             HANS, HANT, JPAN, KORE, THAI, TIBT, INDIC_OTHER,
             SE_ASIAN_OTHER, OTHER, UNKNOWN]

iso15924_to_ml_class:
  Latn: LATN
  Gujr: INDIC_OTHER  # Gujarati → grouped class
  Hans: HANS
  # ... 200+ mappings
```

**Key Features**:

- Hot-reload without restart (`ScriptMLMapping.reload()`)
- Class weights for imbalanced training
- Bidirectional lookup (code → class, class → all codes)

### Tier 3: Routing (OCR Engine Selection)

ML classes are routed to specific OCR engines with optimized configurations.

| Class | Module | Purpose |
|-------|--------|---------|
| `ScriptRouter` | `routing/script_router.py` | Script → OCR engine routing |

**Configuration**: [`config/script_routing.yaml`](../../../../../config/script_routing.yaml)

```yaml
routing_rules:
  LATN:
    engine: "rapidocr"
    batch_size: 8
  HANS:
    engine: "paddleocr"
    batch_size: 2
    lang_hint: "ch"
  ARAB:
    engine: "tesseract"
    rtl: true

vlm_escalation:
  confidence_threshold: 0.5
  always_escalate: ["Tibt", "Ethi"]
```

**Key Features**:

- Priority system: ISO 15924 override → ML class rule → defaults
- VLM escalation for low-confidence or unsupported scripts
- RTL handling flags
- Engine-specific configurations

### Parser Integration

Multilingual parsers populate the `iso15924_script_code` field:

```python
# In annotation/parsers/multilingual/*.py
labels = OriginalLabels()
labels.script_name = "Arabic"           # Human-readable name
labels.iso15924_script_code = "Arab"    # ISO 15924 code (Tier 1)
```

**Updated Parsers**: mlt19, arabic_docs, tibhcr, nepali_handwritten, yarmouk, cvsi, siw13, mle2e, cc_ocr, mdiw13, hindi_ocr_synthetic, pucit_ohul, multilingual_scripts

---

## Layout Label Taxonomy (Cross-Schema Conversion)

The annotation system uses a hub-and-spoke canonical superset for normalizing layout detection labels across six different schemas. This complements the Three-Tier Script Architecture (above) by solving the equivalent problem for layout labels rather than writing system codes.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                  Layout Label Taxonomy (Hub-and-Spoke)                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐   │
│  │ DocLayNet │ │ DocStruct │ │ PubLayNet │ │  Docling  │ │  DocSynth    │   │
│  │ (11 cls)  │ │ Bench(10) │ │  (5 cls)  │ │ (23 cls)  │ │  300K (10)   │   │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬───────┘   │
│        │             │             │             │              │             │
│        │       ┌─────┴─────┐       │       ┌─────┴─────┐       │             │
│        │       │   D4LA    │       │       │           │       │             │
│        │       │ (27 cls)  │       │       │           │       │             │
│        │       └─────┬─────┘       │       │           │       │             │
│        ▼             ▼             ▼       ▼           ▼       ▼             │
│  ┌────────────────────────────────────────────────────────────────────┐      │
│  │               Canonical Superset (57 classes)                      │      │
│  │     11 DocLayNet top-level + 46 extensions (tree hierarchy)        │      │
│  └────────────────────────────────────────────────────────────────────┘      │
│        │                                                                     │
│        ├── to_canonical(label, schema) → canonical name                      │
│        ├── from_canonical(canonical, target) → ConversionResult              │
│        ├── convert(label, source, target) → with loss tracking               │
│        ├── to_doclaynet(canonical) → coarsen via parent chain                │
│        ├── build_mask_index_map(schema) → configurable mask channels         │
│        └── build_doclaynet_index_map() → all labels → DocLayNet 0-10        │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Supported Schemas (6 total)

| Schema | Classes | Source | Config Key |
|--------|---------|--------|------------|
| **DocLayNet** | 11 | IBM DocLayNet dataset | `doclaynet` |
| **DocStructBench** | 10 | DocLayout-YOLO training data | `docstructbench` |
| **PubLayNet** | 5 | PubLayNet dataset | `publaynet` |
| **Docling (DocItemLabel)** | 23 | `docling-core` library | `docling` |
| **D4LA** | 27 | VGT/ICCV 2023 | `d4la` |
| **DocSynth300K** | 10 | Synthetic (DocStructBench names) | `docsynth300k` |

### Canonical Class Hierarchy (57 classes)

The canonical superset organizes all layout labels into a tree with DocLayNet as root:

| DocLayNet Parent | Extensions (child classes) | Source Schemas |
|-----------------|---------------------------|----------------|
| **CAPTION** (0) | FIGURE_CAPTION, TABLE_CAPTION, FORMULA_CAPTION, TABLE_NAME, FIGURE_NAME | DocStructBench, D4LA |
| **FOOTNOTE** (1) | TABLE_FOOTNOTE, REFERENCE | DocStructBench, Docling, D4LA |
| **FORMULA** (2) | ISOLATE_FORMULA, EQUATION | DocStructBench, D4LA |
| **LIST_ITEM** (3) | LIST_TEXT, REGION_LIST, DOCUMENT_INDEX, CATALOG, ORDERED_LIST, UNORDERED_LIST | D4LA, Docling |
| **PAGE_FOOTER** (4) | PAGE_FOOTER_D4LA, PAGE_NUMBER | D4LA |
| **PAGE_HEADER** (5) | PAGE_HEADER_D4LA, LETTERHEAD | D4LA |
| **PICTURE** (6) | FIGURE, CHART | DocStructBench, PubLayNet, Docling, D4LA |
| **SECTION_HEADER** (7) | PARA_TITLE, REGION_TITLE | D4LA |
| **TABLE** (8) | *(no extensions)* | All 6 schemas |
| **TEXT** (9) | PLAIN_TEXT, PARA_TEXT, OTHER_TEXT, CODE, HANDWRITTEN_TEXT, PARAGRAPH, KEY_VALUE_REGION, LETTER_DEAR, LETTER_SIGN, ABSTRACT, AUTHOR, DATE, NUMBER, QUESTION, REGION_KV | DocStructBench, Docling, D4LA |
| **TITLE** (10) | DOC_TITLE | D4LA |
| **FORM** (new) | CHECKBOX_SELECTED, CHECKBOX_UNSELECTED, GRADING_SCALE, EMPTY_VALUE | Docling |
| **ABANDONED** (new) | *(standalone)* | DocStructBench, DocSynth300K |
| **UNKNOWN** (new) | *(standalone)* | Fallback for unrecognized labels |

**Coarsening rule**: Any extended class maps to its DocLayNet parent by walking the `parent` chain. For example, `FIGURE_CAPTION` → `CAPTION` (index 0). Classes under FORM, ABANDONED, and UNKNOWN have no DocLayNet ancestor and map to `UNKNOWN` when coarsened.

### Core Implementation

| Class | Module | Purpose |
|-------|--------|---------|
| `LayoutTaxonomy` | `schema_utils/layout_taxonomy.py` | Config-driven conversion engine |
| `ConversionResult` | `schema_utils/layout_taxonomy.py` | Frozen dataclass with loss tracking |
| `get_default_taxonomy()` | `schema_utils/layout_taxonomy.py` | Module-level singleton |

**Configuration**: [`config/layout_taxonomy.yaml`](../../../../../config/layout_taxonomy.yaml)

**Key Features**:

- Hot-reload without restart (`LayoutTaxonomy.reload()`)
- Lossy conversion tracking (`ConversionResult.is_lossy`, `.loss_description`)
- Configurable mask channels (`get_mask_channel_count("docling")` returns 23)
- All-schema alias normalization (e.g., `list-item`, `list_item`, `listitem` all resolve)
- DocLayNet index map includes all known labels from all schemas (144 entries -> 0-10)
- Batch annotation conversion (`convert_annotations()` for annotation list processing)

### Production Runtime Integration

The taxonomy integrates with four production modules:

| Module | Integration | Purpose |
|--------|-------------|---------|
| `DocLayoutClass` | `.to_canonical()` method | Normalize YOLO model output to canonical names |
| `LayoutMaskGenerator` | Taxonomy-driven `CLASS_MAPPING` via `build_doclaynet_index_map()` or `build_mask_index_map(schema)` | Configurable mask channels per schema |
| `DocLayoutIntegration` | `_normalize_to_canonical()` | Canonical complexity weights for structural scoring |
| `ElementCategory` | `.from_canonical()` classmethod | Schema-level taxonomy bridge |

**LayoutMaskGenerator schema configurability**: The mask generator accepts a `target_schema` parameter (default `"doclaynet"`) to control how many mask channels are produced and which class-to-index mapping is used. When `target_schema="doclaynet"`, it produces 11-channel masks using `build_doclaynet_index_map()` (all schema labels mapped to 0-10). For other schemas (e.g., `"docling"` with 23 channels), it uses `build_mask_index_map(schema)`.

**ELEMENT_COMPLEXITY_WEIGHTS**: Complexity scoring in `DocLayoutIntegration` uses canonical taxonomy class names as keys (e.g., `TABLE`, `FIGURE`, `ISOLATE_FORMULA`, `CHART`, `HANDWRITTEN_TEXT`), enabling consistent weighting regardless of which detection model or schema produced the labels.

### Standardization Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `imgprep layout list` | `cli_layout.py` | Show all schemas and class counts |
| `imgprep layout compare <src> <tgt>` | `cli_layout.py` | Side-by-side mapping with loss indicators |
| `standardize_layout_labels.py` | `scripts/` | Batch enrichment of existing metadata |
| `audit_layout_labels.py` | `scripts/` | Coverage audit report across all datasets |

### Tests

- **File**: [`tests/unit/test_layout_taxonomy.py`](../../../../../tests/unit/test_layout_taxonomy.py)
- **Count**: 147 tests covering all 6 schemas, round-trips, lossy flagging, aliases, mask indices

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
│   ├── parquet_writer.py           # Partitioned Parquet storage (628 LOC)
│   └── cache.py                    # LRU-bounded cache + streaming JSONL (582 LOC)
├── workflow/
│   ├── __init__.py
│   ├── pipeline.py                 # CPU/GPU separated pipeline (737 LOC)
│   ├── scanner.py                  # Batch-aware scanner with checkpointing (628 LOC)
│   ├── orchestrator.py             # Multi-dataset coordination (527 LOC)
│   ├── preflight.py                # Pre-flight validation checks (744 LOC)
│   └── progress.py                 # Progress tracking (311 LOC)
├── monitoring/
│   ├── __init__.py
│   ├── metrics.py                  # Prometheus metrics + dashboard (636 LOC)
│   └── logging.py                  # Structured logging (512 LOC)
├── cli.py                          # Click CLI interface (772 LOC)
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

**Last Updated**: 2026-01-26

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

## Layer 2 Metadata Aggregation

**Purpose**: Compute dataset-level statistics from Layer 2 enrichment metadata for documentation and training planning.

**Added**: 2025-01-30 (Stream 1 integration)
**Script**: [`scripts/aggregate_layer2_metadata.py`](../../../../../scripts/aggregate_layer2_metadata.py)
**Output**: `metadata_registry/aggregates/{dataset_name}_stats.json`

### Architecture Integration

```text
Layer 2 Enrichment Metadata      Aggregation Script           Dataset Documentation
─────────────────────────        ──────────────────           ─────────────────────
/mnt/e/.../metadata_registry/                                 docs/
├── json/                    →   aggregate_layer2_      →    ├── DATASET_QUICK_REFERENCE.md
│   ├── tablebank_meta.json      metadata.py                 │   (metadata-enriched tables)
│   ├── fintabnet_meta.json                                  ├── DATASET_PROCESSING_STATUS.md
│   └── ...                                                   └── DATASET_CATALOG.md
└── aggregates/              ←   Output JSON stats
    ├── tablebank_stats.json     (capture, domain,
    ├── fintabnet_stats.json      quality, content flags)
    └── ...
```

### Computed Statistics

For each dataset with Layer 2 metadata, the aggregation script computes:

| Statistic Category | Fields Extracted | Example Output | Use Case |
|-------------------|------------------|----------------|----------|
| **Capture Method** | `capture_method` from each sample | `{"born_digital": 100%}` | Predict degradation patterns |
| **Domain Coverage** | `domain_level1` from each sample | `{"FIN": 100%}` | Domain-specific training |
| **Quality Distribution** | `overall_score` from QualityInfo | `min: 0.85, max: 1.0, mean: 0.93` | Dataset difficulty assessment |
| **Degradation Types** | `degradations[]` from QualityInfo | `{"compression": 12%, "blur": 8%}` | Degradation coverage |
| **Content Flags** | `has_table`, `has_formula`, etc. | `{"has_table": 100%}` | Content type filtering |
| **Script/Language** | `script_code`, `language_code` | `{"Latn": 95%, "Zyyy": 5%}` | Multilingual coverage |
| **Layout Types** | `layout_type` from StructureInfo | `{"tabular": 100%}` | Layout diversity |
| **Text Density** | `text_density` from StructureInfo | `{"dense": 70%, "moderate": 25%}` | Text coverage |
| **Text Scope** | `scope` from TextScopeInfo | `{"page": 100%}` | Granularity assessment |
| **Paper Sizes** | `detected_size` from PaperSizeInfo | `{"A4": 40%, "Letter": 55%}` | Regional coverage |

### Workflow

```bash
# 1. Complete Layer 2 annotation for dataset(s)
imgprep annotation scan --dataset tablebank --use-yolo

# 2. Run aggregation script
PYTHONPATH=$PWD:$PYTHONPATH python scripts/aggregate_layer2_metadata.py \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --output-dir metadata_registry/aggregates \
    --verbose

# 3. Use aggregates to update documentation
# (Manual or automated script to update DATASET_QUICK_REFERENCE.md)
```

### Current Aggregation Status (as of 2025-01-30)

**Processed**: 20/40 datasets with Layer 2 metadata

| Dataset | Samples | Capture Method | Domain | Content Flags | Notes |
|---------|---------|----------------|--------|---------------|-------|
| fintabnet | 97,475 | Born-digital (100%) | FIN (100%) | has_table (100%) | ⭐⭐⭐ Complete metadata |
| pubtabnet | 519,030 | Born-digital (100%) | SCI (100%) | has_table (100%) | ⭐⭐⭐ Complete metadata |
| tablebank | 10 | Born-digital (100%) | SCI (100%) | has_table (100%) | ⭐⭐⭐ Complete metadata (sample) |
| doclaynet | 80,863 | Born-digital (100%) | Mixed | has_table (varies) | ⭐⭐⭐ Complete metadata |
| realdae | 583 | Camera (100%) | UNK | - | ⭐⭐ Partial (no content flags) |
| smartdoc-qa | 4,260 | Camera (100%) | UNK | - | ⭐⭐ Partial (no content flags) |
| dibco | 212 | Scanner (100%) | UNK | - | ⭐⭐ Partial (no content flags) |
| funsd | 199 | Scanner (100%) | UNK | - | ⭐⭐ Partial (no content flags) |
| sroie | 973 | Camera/Scanner | FIN | - | ⭐⭐ Partial (needs Layer 2 rebuild) |
| tobacco800 | 1,290 | Scanner (100%) | UNK | - | ⭐⭐ Partial (no content flags) |
| ohr-bench | 8,303 | Unknown | UNK | - | ⭐ Minimal metadata |
| ... | ... | ... | ... | ... | 10 more with minimal metadata |

**Metadata Coverage**:

- ⭐⭐⭐ **Good**: 4 datasets (capture + domain + content flags)
- ⭐⭐ **Partial**: 6 datasets (capture + domain only)
- ⭐ **Minimal**: 10 datasets (domain only or unknown capture)

### Integration with Dataset Documentation

The aggregated statistics are used in three-tier dataset documentation:

1. **[DATASET_QUICK_REFERENCE.md](../../../../DATASET_QUICK_REFERENCE.md)** (~800 lines, ~8K tokens)
   - Training tables enhanced with capture method, domain, content flags
   - Metadata coverage indicators (⭐⭐⭐/⭐⭐/⭐)
   - Token-optimized for training planning discussions

2. **[DATASET_PROCESSING_STATUS.md](../../../../DATASET_PROCESSING_STATUS.md)** (~500 lines, ~5K tokens)
   - Tracks format conversion and label extraction progress
   - Shows which datasets need enrichment completion

3. **[DATASET_CATALOG.md](../../../../DATASET_CATALOG.md)** (~4,300 lines, ~45K tokens)
   - Comprehensive per-dataset documentation
   - Deep technical details (used only when needed)

**Token Efficiency**: 70-85% reduction for typical dataset queries vs loading full catalog

### Pending Enrichment Tasks

**Priority**: Complete enrichment for training-critical datasets

| Priority | Datasets | Missing Fields | Impact |
|----------|----------|----------------|--------|
| **P0 (IQA Training)** | ohr-bench, diqa-5000, realdae | Quality scores, degradation types | Cannot show quality profiles in Quick Reference |
| **P1 (Script Detection)** | synth-multiscript-250k, mdiw13, mlt19 | Language/script codes | Cannot show script coverage statistics |
| **P2 (Layout Detection)** | All layout datasets | Layout types, text density | Cannot show layout diversity |
| **P3 (Content Characterization)** | 16 datasets with UNK domain | Domain classification | Cannot filter by domain accurately |

**Expected Timeline**: As Layer 2 enrichment pipeline adds quality assessment and script detection, re-run aggregation to populate missing fields.

### Aggregation Script Reference

**Location**: [`scripts/aggregate_layer2_metadata.py`](../../../../../scripts/aggregate_layer2_metadata.py)

**Key Features**:

- Processes single-file metadata format (`{dataset}_metadata.json`)
- Extracts from `samples[].enrichments.versions[-1].data` (latest version)
- Computes percentages, min/max/mean statistics
- Handles missing fields gracefully (partial metadata)
- Outputs JSON for programmatic consumption

**Output Schema**:

```json
{
  "dataset_name": "tablebank",
  "total_samples": 278582,
  "capture_methods_pct": {"born_digital": 100.0},
  "domains_pct": {"SCI": 85.0, "TEC": 15.0},
  "content_flags_pct": {"has_table": 100.0, "has_formula": 15.0},
  "quality_summary": {"min": 0.85, "max": 1.00, "mean": 0.93},
  "top_degradations": [{"type": "compression", "percentage": 12.0}],
  "top_scripts": [{"script": "Latn", "percentage": 95.0}]
}
```

**Related Documentation**:

- [DATASET_METADATA_AGGREGATION_GUIDE.md](../../../../DATASET_METADATA_AGGREGATION_GUIDE.md) - Complete usage guide
- [DATASET_AGGREGATION_SUMMARY.md](../../../../DATASET_AGGREGATION_SUMMARY.md) - Current aggregation results
- [DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md](../../../../DATASET_QUICK_REFERENCE_ENHANCED_PROPOSAL.md) - Future enhancements

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

# Layout taxonomy
imgprep layout list                              # Show 6 schemas with class counts
imgprep layout compare docstructbench doclaynet  # Side-by-side mapping with loss indicators
imgprep layout compare docling d4la --format json
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
| `schema_utils.layout_taxonomy` | 2 | Cross-schema layout label conversion | `schema_utils/layout_taxonomy.py` |
| `annotation.storage.parquet_writer` | Output | Partitioned Parquet | `annotation/storage/parquet_writer.py` |
| `build_training_labels.py` | 3 | Training-ready labels | `scripts/build_training_labels.py` |

### Layout Standardization Scripts

| Script | Purpose | CLI |
|--------|---------|-----|
| [`standardize_layout_labels.py`](../../../../../scripts/standardize_layout_labels.py) | Batch enrich metadata with canonical layout labels | `--dataset X --source-schema Y --dry-run` |
| [`audit_layout_labels.py`](../../../../../scripts/audit_layout_labels.py) | Coverage audit across all datasets | `--metadata-dir /mnt/e/.../json --output report.txt` |

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

This section maps workflow steps to implementation files with actual LOC counts (as of Phase 5 completion).

| Workflow Step | Source Files | Actual LOC | Purpose |
|---------------|--------------|------------|---------|
| **Schemas** | `annotation/schemas/*.py` | ~2,400 | Dataclasses, enums, migrations, validators |
| **Configuration** | `annotation/config/*.py` | ~2,500 | Settings, dataset configs, validators, tiers |
| **Integrity** | `annotation/integrity/*.py` | ~900 | Hashing, checkpoints, atomic ops |
| **Parsers** | `annotation/parsers/**/*.py` | ~3,500 | 38+ dataset-specific parsers + registry |
| **Enrichment** | `annotation/enrichment/**/*.py` | ~1,600 | Provider protocols, manager, errors, providers |
| **Storage** | `annotation/storage/*.py` | ~1,200 | JSON writer, Parquet writer, LRU cache |
| **Workflow** | `annotation/workflow/*.py` | ~2,950 | Pipeline, orchestrator, scanner, preflight, progress |
| **Monitoring** | `annotation/monitoring/*.py` | ~1,150 | Prometheus metrics, structured logging |
| **CLI** | `annotation/cli.py` | ~770 | Click interface |
| **Layer 3** | `scripts/build_training_labels.py` | ~590 | Training label construction |
| **Package Total** | **~70 modules** | **~19,600** | — |

### Key Modules by Size

| Module | LOC | Category | Purpose |
|--------|-----|----------|---------|
| `schemas/migrations.py` | 830 | Schemas | Schema version migrations |
| `config/datasets.py` | 777 | Config | Dataset registry (24 datasets) |
| `cli.py` | 772 | CLI | Click command interface |
| `workflow/preflight.py` | 744 | Workflow | Pre-flight validation checks |
| `schemas/validators.py` | 741 | Schemas | Field validators, type coercion |
| `workflow/pipeline.py` | 737 | Workflow | CPU/GPU separated pipeline |
| `integrity/checkpointing.py` | 686 | Integrity | Intra-dataset checkpoints |
| `monitoring/metrics.py` | 636 | Monitoring | Prometheus instrumentation |
| `workflow/scanner.py` | 628 | Workflow | Batch-aware scanner |
| `storage/parquet_writer.py` | 628 | Storage | Partitioned Parquet output |
| `storage/cache.py` | 582 | Storage | LRU-bounded caches |
| `config/validators.py` | 565 | Config | Configuration validators |
| `parsers/template.py` | 538 | Parsers | Parser template generator |
| `workflow/orchestrator.py` | 527 | Workflow | Multi-dataset coordination |
| `monitoring/logging.py` | 512 | Monitoring | Structured logging |
| `enrichment/providers/siglip.py` | 477 | Enrichment | SigLIP quality prediction |

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

| Category | Target | Actual (Phase 5) | Focus |
|----------|--------|------------------|-------|
| Unit Tests | 90%+ | 88% | Individual functions, classes |
| Integration Tests | 80%+ | 85% | Module interactions, pipeline |
| E2E Tests | 70%+ | N/A | Full workflows (Phase 6) |
| Property Tests | Key schemas | ✅ | Migration invariants |

**Test Statistics (Phase 5 Complete)**:

- **Total Tests**: 833 annotation tests
- **Pass Rate**: 100% (all green)
- **Coverage Threshold**: 80% enforced in CI

---

## Workstream Dependencies

### Upstream Dependencies

| Workstream | Dependency | Description |
|------------|------------|-------------|
| **None** | N/A | Data Preparation is the starting point |

### Downstream Consumers

| Workstream | Consumed Artifacts | Purpose |
|------------|--------------------|---------|
| **2. Production Model Training** | `parquet/`, images | Train MobileNetV4-Conv-S + SigLIP 2 NAFlex multi-task models on 10 purpose-built datasets (~503K total) |
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
| `schema_utils/layout_taxonomy.py` | Layout Label Taxonomy |
| `build_training_labels.py` | Layer 3, Degradation Index, Anchor Score |

---

*V2 Architecture - Post-refactoring implementation. Phases 1-5 of
[METADATA_ANNOTATION_REFACTORING_PLAN.md](../../../../planning/METADATA_ANNOTATION_REFACTORING_PLAN.md) are complete.
This document supersedes [index.v1-archived.md](index.v1-archived.md).*
