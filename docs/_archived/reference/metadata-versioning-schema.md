---
schema_type: common
title: "Metadata Versioning Schema - Original vs Enriched Labels"
tags:
  - reference
  - schema
  - metadata
status: published
owner: docs-team
purpose: Define versioned metadata structure that preserves original dataset labels while tracking Project A enrichments.
---

**Version**: 1.0
**Date**: 2025-12-17
**Status**: Draft

## Purpose

This document defines a **versioned metadata schema** that:

1. **Preserves original labels**: Exactly as provided by source datasets (immutable)
2. **Tracks enrichments**: Our derived annotations with full provenance
3. **Supports rollback**: Can revert to any previous annotation version
4. **Enables auditing**: Full history of who/what changed labels and when

## Design Principles

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                     Sample Metadata Record                       │
├─────────────────────────────────────────────────────────────────┤
│  IMMUTABLE LAYER (original)                                      │
│  ├── Source dataset labels (never modified)                     │
│  ├── Original file metadata                                      │
│  └── Dataset-provided annotations                                │
├─────────────────────────────────────────────────────────────────┤
│  ENRICHMENT LAYER (versioned)                                    │
│  ├── v1: Initial enrichment (classical CV)                      │
│  ├── v2: ML-based enrichment                                     │
│  ├── v3: LLM scoring                                             │
│  └── v_current: Active version pointer                          │
├─────────────────────────────────────────────────────────────────┤
│  TRAINING LAYER (derived)                                        │
│  ├── Computed from enrichment + original                         │
│  ├── Training-ready vectors                                      │
│  └── Anchor weights and priorities                               │
└─────────────────────────────────────────────────────────────────┘
```

### Key Rules

1. **Original labels are IMMUTABLE** - Never modify, only preserve
2. **Enrichments are VERSIONED** - Each change creates a new version
3. **Training labels are DERIVED** - Computed on-demand from original + enrichment
4. **Provenance is MANDATORY** - Every enrichment includes source/method/date

---

## Complete Metadata Schema

```yaml
# Sample Metadata Record v1.0
# One record per image in the dataset

sample:
  # === Identity (Immutable) ===
  id: string                      # UUID generated on first ingestion
  file_hash: string               # SHA-256 of original file (deduplication key)

  # === Source Information (Immutable) ===
  source:
    dataset_name: string          # e.g., "TableBank", "DIQA-5000", "DocLayNet"
    dataset_version: string       # e.g., "1.0", "2023-release"
    original_path: string         # Path within source dataset
    original_filename: string     # Original filename
    download_date: datetime       # When we acquired it
    download_url: string | null   # Source URL if applicable

  # === Original Labels (Immutable - preserved exactly as provided) ===
  original_labels:
    # --- Dataset-Specific Labels (raw, unmodified) ---
    # These fields vary by source dataset - preserve whatever they provided

    # For DIQA-5000:
    diqa:
      mos: float | null           # 1-5 Mean Opinion Score
      mos_std: float | null       # Standard deviation across annotators
      annotator_count: int | null
      distortion_type: string | null  # Original distortion category

    # For LIVE IQA:
    live:
      dmos: float | null          # 0-100 Differential MOS
      dmos_std: float | null
      distortion_type: string | null
      ref_image: string | null    # Reference image path

    # For DocLayNet:
    doclaynet:
      annotations: list[object] | null  # COCO-format annotations
      category_ids: list[int] | null
      image_info: object | null   # Original COCO image metadata

    # For TableBank:
    tablebank:
      table_annotations: list[object] | null
      source_type: string | null  # "latex" or "word"

    # For SmartDoc-QA:
    smartdoc:
      mos: float | null           # 1-5 scale
      capture_device: string | null
      lighting_condition: string | null

    # For FUNSD/FUNSD+:
    funsd:
      form_annotations: list[object] | null
      entity_labels: list[object] | null

    # For SignaTR6K:
    signatr:
      signature_id: string | null
      writer_id: string | null
      is_genuine: boolean | null

    # --- Generic Fallback (for datasets without specific schema) ---
    raw_labels: object | null     # Store any labels not captured above

  # === Original File Metadata (Immutable) ===
  original_file:
    format: string                # "png", "jpg", "tiff", "pdf"
    width_px: int
    height_px: int
    channels: int                 # 1=grayscale, 3=RGB, 4=RGBA
    bit_depth: int                # 8, 16, etc.
    file_size_bytes: int
    dpi: int | null               # If available from metadata
    color_space: string | null    # "sRGB", "grayscale", etc.
    exif: object | null           # Raw EXIF if available

  # === Enrichment History (Versioned - append-only) ===
  enrichments:
    current_version: int          # Points to active enrichment version
    versions:
      - version: 1
        created_at: datetime
        created_by: string        # "classical_cv_pipeline_v1.0"
        method: string            # "automated" | "manual" | "llm"
        description: string       # Human-readable description

        # Enrichment data (structure matches detection-taxonomy.md)
        data:
          # Capture method detection
          capture:
            method: enum[born_digital, scanner_flatbed, scanner_adf,
                        camera_professional, camera_smartphone, fax, unknown]
            confidence: float
            detection_method: string  # "pdf_metadata", "artifact_analysis", etc.

          # Resolution analysis
          resolution:
            detected_dpi: int
            dpi_category: enum[low_<150, medium_150-299, standard_300, high_>300]
            upscaled: boolean
            upscale_factor: float | null
            original_dimensions: [int, int]

          # Domain classification
          domain:
            level1: string
            level2: string | null
            level3: string | null
            confidence: float

          # Structure analysis
          structure:
            text_density: enum[sparse, moderate, dense]
            layout_type: enum[single_column, multi_column, mixed, form_based, tabular]
            element_types: list[string]
            confidence: float

          # Quality/degradation detection
          quality:
            overall_score: float    # 0-1 composite
            degradations:
              - type: string        # From 45-type taxonomy
                severity: enum[none, mild, moderate, severe]
                severity_numeric: float
                confidence: float
                detection_method: string  # "laplacian", "hough", "resnet18", etc.
                location: enum[global, localized]
                region: [x, y, w, h] | null

          # Language detection
          language:
            primary: string         # ISO 639-1
            confidence: float
            script_type: string

      # Additional versions appended here...
      - version: 2
        created_at: datetime
        created_by: string        # "iqa_resnet18_v1.0"
        method: string
        description: string
        # Only include fields that changed from previous version
        data:
          quality:
            # Updated degradation scores from ML model
            degradations:
              - type: "blur"
                severity: moderate
                severity_numeric: 0.65
                confidence: 0.92
                detection_method: "resnet18_student"

      - version: 3
        created_at: datetime
        created_by: string        # "llama3.2-vision-diqa-ft-v1"
        method: "llm"
        description: "LLM MOS prediction"
        data:
          perceptual_scores:
            llm:
              has_score: true
              model_name: "llama3.2-vision-diqa-ft-v1"
              predicted_mos: 3.2
              predicted_normalized: 0.45
              prediction_confidence: 0.88

  # === Computed Training Labels (Derived - regenerated on demand) ===
  # These are NOT stored - computed from original + enrichments at training time
  # Shown here for documentation purposes
  training_labels:
    # Computed by merging original labels with current enrichment version
    # See "Training Label Computation" section below

  # === Metadata About This Record ===
  record_meta:
    created_at: datetime          # When this record was first created
    last_modified: datetime       # When any enrichment was added
    schema_version: string        # "1.0" - for future schema migrations
    ingestion_batch: string       # Batch ID for bulk operations
```

---

## Original Label Preservation

### Per-Dataset Label Mapping

Each source dataset has different label formats. We preserve them exactly:

| Source Dataset | Original Label Fields | Notes |
|----------------|----------------------|-------|
| **DIQA-5000** | `mos`, `mos_std`, `distortion_type` | Human MOS 1-5 scale |
| **LIVE IQA** | `dmos`, `dmos_std`, `ref_image` | DMOS 0-100, has reference |
| **CSIQ** | `dmos` | DMOS 0-1 scale |
| **DocLayNet** | `annotations` (COCO format) | Layout bounding boxes |
| **TableBank** | `table_annotations`, `source_type` | Table regions |
| **SmartDoc-QA** | `mos`, `capture_device`, `lighting` | Document-specific |
| **FUNSD/FUNSD+** | `form_annotations`, `entity_labels` | Form understanding |
| **SignaTR6K** | `signature_id`, `writer_id`, `is_genuine` | Signature verification |
| **DIBCO** | Binary ground truth masks | Binarization challenge |

### Immutability Enforcement

```python
# Enforcement pattern in ingestion pipeline
class SampleMetadata:
    def __init__(self, source_data: dict):
        # Original labels are frozen at creation
        self._original_labels = freeze(source_data.get("labels", {}))
        self._original_file = freeze(source_data.get("file_metadata", {}))

    @property
    def original_labels(self) -> FrozenDict:
        """Original labels are read-only."""
        return self._original_labels

    def add_enrichment(self, enrichment: Enrichment) -> int:
        """Add new enrichment version. Returns version number."""
        new_version = len(self.enrichments.versions) + 1
        enrichment.version = new_version
        enrichment.created_at = datetime.utcnow()
        self.enrichments.versions.append(enrichment)
        self.enrichments.current_version = new_version
        return new_version
```

---

## Enrichment Versioning

### Version Types

| Version Type | Created By | Trigger | Example |
|--------------|------------|---------|---------|
| **Initial (v1)** | Ingestion pipeline | First import | Basic file metadata, DPI detection |
| **Classical CV** | Classical detectors | Batch enrichment | Skew angle, blur score, contrast |
| **ML IQA** | ResNet-18/50 | Model inference | Multi-head severity scores |
| **LLM Scoring** | Fine-tuned VLM | LLM pipeline | Predicted MOS, confidence |
| **Manual Review** | Human annotator | QA process | Corrected labels |
| **Re-enrichment** | Updated pipeline | Model update | New model version results |

### Version Diff Strategy

To minimize storage, versions store **diffs** not full copies:

```yaml
# Version 1: Full initial enrichment
enrichments.versions[0]:
  version: 1
  data:
    capture: { method: "scanner_adf", confidence: 0.85 }
    resolution: { detected_dpi: 200, dpi_category: "medium_150-299" }
    quality:
      overall_score: 0.65
      degradations:
        - { type: "skew", severity: "mild", severity_numeric: 0.25 }
        - { type: "blur", severity: "none", severity_numeric: 0.05 }

# Version 2: Only updated fields
enrichments.versions[1]:
  version: 2
  data:
    quality:
      degradations:
        - { type: "blur", severity: "moderate", severity_numeric: 0.58 }
        # skew unchanged, not repeated
```

### Resolving Current State

```python
def get_current_enrichment(sample: SampleMetadata) -> dict:
    """Merge all versions up to current_version."""
    result = {}
    for v in sample.enrichments.versions:
        if v.version <= sample.enrichments.current_version:
            deep_merge(result, v.data)
    return result
```

---

## Training Label Computation

Training labels are **computed on-demand**, not stored. This ensures:

- Always up-to-date with latest enrichment
- No stale cached values
- Clear separation of concerns

### Computation Logic

```python
def compute_training_labels(sample: SampleMetadata) -> TrainingLabels:
    """Compute training labels from original + enrichments."""

    original = sample.original_labels
    enriched = get_current_enrichment(sample)

    # 1. Determine anchor score (priority: human > llm_high > llm_med > synthetic)
    anchor_score, anchor_source, anchor_weight = compute_anchor(original, enriched)

    # 2. Build degradation vector (45-dimensional)
    iqa_vector = build_degradation_vector(enriched.quality.degradations)

    # 3. Threshold to binary
    iqa_binary = [v > 0.1 for v in iqa_vector]

    return TrainingLabels(
        iqa_vector=iqa_vector,
        iqa_binary=iqa_binary,
        anchor_score=anchor_score,
        anchor_source=anchor_source,
        anchor_weight=anchor_weight,
        human_mos_normalized=normalize_human_mos(original),
        llm_mos_normalized=enriched.perceptual_scores.llm.predicted_normalized,
        llm_confidence=enriched.perceptual_scores.llm.prediction_confidence,
    )


def compute_anchor(original: dict, enriched: dict) -> tuple[float, str, float]:
    """Determine best available perceptual score anchor."""

    # Priority 1: Human ground truth
    if original.get("diqa", {}).get("mos"):
        score = (original["diqa"]["mos"] - 1) / 4  # Normalize to 0-1
        return score, "human", 1.0

    if original.get("live", {}).get("dmos"):
        score = original["live"]["dmos"] / 100
        return score, "human", 1.0

    if original.get("smartdoc", {}).get("mos"):
        score = (original["smartdoc"]["mos"] - 1) / 4
        return score, "human", 1.0

    # Priority 2-4: LLM predictions (by confidence)
    llm = enriched.get("perceptual_scores", {}).get("llm", {})
    if llm.get("has_score"):
        conf = llm["prediction_confidence"]
        score = llm["predicted_normalized"]
        if conf >= 0.8:
            return score, "llm_high", 0.8
        elif conf >= 0.5:
            return score, "llm_medium", 0.5
        else:
            return score, "llm_low", 0.2

    # Priority 5: Synthetic (computed from degradation vector)
    synthetic_score = compute_synthetic_score(enriched.get("quality", {}))
    return synthetic_score, "synthetic", 0.3
```

---

## Storage Format

### File Organization

```
datasets/
├── 01_base_data/
│   └── [dataset_name]/
│       ├── images/                    # Original images (unchanged)
│       └── metadata/
│           ├── original/              # Original labels from source
│           │   └── labels.json        # Preserved exactly as downloaded
│           └── enriched/              # Our enrichments (versioned)
│               ├── v1/
│               │   └── enrichments.parquet
│               ├── v2/
│               │   └── enrichments.parquet
│               └── current -> v2      # Symlink to active version
│
├── metadata_registry/                  # Central index
│   ├── samples.parquet                # Sample ID -> file location mapping
│   ├── version_history.json           # Global version changelog
│   └── schema_migrations/             # Schema evolution scripts
```

### Parquet Schema

For efficient storage and querying, enrichments use Parquet:

```python
# Parquet schema for enrichments
ENRICHMENT_SCHEMA = pa.schema([
    ("sample_id", pa.string()),
    ("version", pa.int32()),
    ("created_at", pa.timestamp("us")),
    ("created_by", pa.string()),
    ("method", pa.string()),

    # Nested enrichment data
    ("capture_method", pa.string()),
    ("capture_confidence", pa.float32()),
    ("detected_dpi", pa.int32()),
    ("domain_level1", pa.string()),
    ("quality_overall", pa.float32()),

    # Degradation list (as JSON string for flexibility)
    ("degradations_json", pa.string()),

    # LLM scores
    ("llm_predicted_mos", pa.float32()),
    ("llm_confidence", pa.float32()),
    ("llm_model_name", pa.string()),
])
```

---

## Rollback and Auditing

### Rollback to Previous Version

```python
def rollback_enrichment(sample_id: str, target_version: int) -> None:
    """Roll back to a previous enrichment version."""
    sample = load_sample(sample_id)

    if target_version > len(sample.enrichments.versions):
        raise ValueError(f"Version {target_version} does not exist")

    # Simply update the pointer - versions are preserved
    sample.enrichments.current_version = target_version
    save_sample(sample)

    log.info(f"Rolled back {sample_id} to enrichment v{target_version}")
```

### Audit Trail

```python
def get_enrichment_history(sample_id: str) -> list[dict]:
    """Get full enrichment history for auditing."""
    sample = load_sample(sample_id)

    return [
        {
            "version": v.version,
            "created_at": v.created_at,
            "created_by": v.created_by,
            "method": v.method,
            "description": v.description,
            "is_current": v.version == sample.enrichments.current_version,
        }
        for v in sample.enrichments.versions
    ]
```

---

## Migration from Existing Labels

### One-Time Migration Script

For existing datasets already in our pipeline:

```python
def migrate_existing_dataset(dataset_path: Path) -> None:
    """Migrate existing dataset to versioned metadata schema."""

    for image_path in dataset_path.glob("images/*"):
        sample_id = generate_uuid()
        file_hash = compute_sha256(image_path)

        # 1. Extract original labels (if any)
        original_labels = extract_original_labels(dataset_path, image_path)

        # 2. Extract file metadata
        original_file = extract_file_metadata(image_path)

        # 3. Create initial enrichment from any existing computed labels
        existing_enrichment = extract_existing_enrichment(dataset_path, image_path)

        # 4. Build new metadata record
        metadata = SampleMetadata(
            id=sample_id,
            file_hash=file_hash,
            source={
                "dataset_name": dataset_path.name,
                "original_path": str(image_path.relative_to(dataset_path)),
                "original_filename": image_path.name,
            },
            original_labels=original_labels,
            original_file=original_file,
            enrichments={
                "current_version": 1 if existing_enrichment else 0,
                "versions": [existing_enrichment] if existing_enrichment else [],
            },
        )

        save_metadata(metadata, dataset_path / "metadata" / "enriched")
```

---

## Integration with Detection Taxonomy

This schema maps directly to [detection-taxonomy.md](detection-taxonomy.md):

| Taxonomy Section | Metadata Location |
|------------------|-------------------|
| Axis 1-3: Domain/Structure/Production | `enrichments.data.domain`, `enrichments.data.structure` |
| Axis 4: Capture Method | `enrichments.data.capture` |
| Axis 5: Quality/Degradations | `enrichments.data.quality` |
| Axis 6: Language | `enrichments.data.language` |
| Axis 7: Perceptual Scores | `original_labels.*` + `enrichments.data.perceptual_scores.llm` |
| Training Labels | Computed from above at training time |

---

## References

- [detection-taxonomy.md](detection-taxonomy.md) - Faceted taxonomy definitions
- [document-type-taxonomy.md](document-type-taxonomy.md) - Domain classification
- [DATASET_CATALOG.md](../DATASET_CATALOG.md) - Dataset inventory

---

**Created**: 2025-12-17 (Phase 7 - Metadata Versioning)
**Status**: Draft
**Next Steps**:

1. Implement Parquet storage layer
2. Create migration scripts for existing datasets
3. Build enrichment pipeline with version tracking
**Next Review**: Phase 7 Week 2
