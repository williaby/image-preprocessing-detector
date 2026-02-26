---
owner: docs-team
purpose: 'Documentation for Level 3: Label Parsing & Training Label Generation.'
schema_type: common
status: draft
tags:
- architecture
- documentation
title: 'Level 3: Label Parsing & Training Label Generation'
---

> **Workstream**: WS3 - Data Preparation
> **Component**: Dataset Parsing & Training Label Builder
> **LOC Coverage**: 590 lines (build_training_labels.py) + 850 lines (parsers in annotate_base_metadata.py)
> **Last Updated**: 2025-01-19

---

## Overview

### Purpose

The label parsing and generation system **normalizes heterogeneous dataset formats** into a unified schema and constructs training-ready 45-dimensional feature vectors by merging original labels with ML-generated enrichments.

### Key Responsibilities

1. **Parse 9+ Dataset Formats**: Convert dataset-specific annotations to unified schema
2. **Normalize Quality Scores**: All scores normalized to [0=best, 1=worst] scale
3. **45-Dim Vector Assembly**: Build degradation severity vectors from multiple sources
4. **Anchor Score Selection**: Priority-based selection from multiple label sources
5. **Training Label Construction**: Merge Layer 1 (original) + Layer 2 (enrichment) into Layer 3 (training)
6. **Provenance Tracking**: Record complete lineage from source datasets to training labels

### Architecture Context

```
Dataset Annotations → Parsers → Original Labels (Layer 1)
                                       ↓
                              + Enrichment Data (Layer 2)
                                       ↓
                              Training Label Builder
                                       ↓
                           Training Labels (Layer 3)
                     (45-dim vector + anchor score + metadata)
```

**Source**: `scripts/build_training_labels.py` (Lines 1-590) + `scripts/annotate_base_metadata.py` (Lines 635-852, parsers)

---

## Dataset-Specific Parsers

### Parser Architecture

Each dataset requires a custom parser to handle its unique annotation format. All parsers normalize to a unified schema.

**Common Interface Pattern**:

```python
def parse_{dataset}_labels(metadata_registry: Path, dataset_config: dict) -> dict:
    """Parse dataset-specific labels to unified schema.

    Returns:
        {
            file_id: {
                "mos_score": float,           # If available
                "distortion_type": str,       # If available
                "severity_level": int,        # If available (1-5)
                "bboxes": list,              # If available (COCO format)
                "element_type": str,         # If available
                "confidence": float,         # Label confidence
                "original_format": dict      # Raw annotation preserved
            }
        }
    """
```

### 1. DIQA-5000 Parser

**Dataset**: 5,000 images with human MOS scores (1-5 scale)

**Input Format**: JSON with MOS scores

```json
{
    "image_001.jpg": {
        "mos": 4.2,
        "std": 0.8,
        "num_voters": 25
    }
}
```

**Parser Implementation**:

```python
def parse_diqa_labels(metadata_registry: Path, config: dict) -> dict:
    """Parse DIQA-5000 MOS scores.

    Source: Conceptual from annotate_base_metadata.py parser pattern
    """
    mos_file = config["path"] / config["mos_file"]

    with open(mos_file) as f:
        mos_data = json.load(f)

    labels = {}
    for filename, data in mos_data.items():
        file_id = generate_file_id(filename)

        # Normalize MOS to [0, 1] scale (0=best, 1=worst)
        # DIQA: 5=best, 1=worst
        normalized_score = normalize_diqa_mos(data["mos"])  # (5 - mos) / 4

        # Calculate confidence from std dev
        # Lower std = higher confidence
        confidence = 1.0 / (1.0 + data["std"])

        labels[file_id] = {
            "mos_score": normalized_score,
            "confidence": confidence,
            "source_type": "human_mos",
            "num_voters": data.get("num_voters", 0),
            "original_format": data
        }

    return labels
```

**Normalization**:

- Input: MOS 1-5 (5=best quality)
- Output: 0-1 (0=best quality)
- Formula: `(5 - mos) / 4`

**Code Reference**: `scripts/annotate_base_metadata.py`, Lines 635-700 (DIQA parser pattern)

### 2. LIVE Parser

**Dataset**: 779 images with DMOS scores (0-100 scale)

**Input Format**: MAT file with DMOS matrix

**Parser Implementation**:

```python
def parse_live_labels(metadata_registry: Path, config: dict) -> dict:
    """Parse LIVE database DMOS scores.

    Source: Based on annotate_base_metadata.py parser pattern
    """
    import scipy.io as sio

    dmos_file = config["path"] / "dmos.mat"
    mat_data = sio.loadmat(dmos_file)

    labels = {}
    for idx, (dmos, filename) in enumerate(zip(
        mat_data["dmos"][0],
        mat_data["filenames"][0]
    )):
        file_id = generate_file_id(filename)

        # LIVE: 0=no distortion (best), 100=max distortion (worst)
        normalized_score = dmos / 100.0  # Already 0=best, 1=worst

        labels[file_id] = {
            "dmos_score": normalized_score,
            "confidence": 0.95,  # LIVE has high reliability
            "source_type": "human_mos",
            "distortion_type": mat_data.get("distortion_types", [None])[idx],
            "original_format": {"dmos": float(dmos)}
        }

    return labels
```

**Normalization**:

- Input: DMOS 0-100 (0=best quality)
- Output: 0-1 (0=best quality)
- Formula: `dmos / 100`

**Code Reference**: `scripts/annotate_base_metadata.py`, Lines 700-750 (LIVE parser pattern)

### 3. CSIQ Parser

**Dataset**: 866 images with DMOS scores (0-1 scale)

**Input Format**: CSV with DMOS values

**Parser Implementation**:

```python
def parse_csiq_labels(metadata_registry: Path, config: dict) -> dict:
    """Parse CSIQ DMOS scores.

    Source: Based on annotate_base_metadata.py parser pattern
    """
    import csv

    dmos_file = config["path"] / "csiq_dmos.csv"

    labels = {}
    with open(dmos_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_id = generate_file_id(row["filename"])

            # CSIQ: already 0=best, 1=worst
            normalized_score = float(row["dmos"])

            labels[file_id] = {
                "dmos_score": normalized_score,
                "confidence": 0.90,  # CSIQ has good reliability
                "source_type": "human_mos",
                "distortion_type": row.get("distortion"),
                "original_format": dict(row)
            }

    return labels
```

**Normalization**:

- Input: DMOS 0-1 (0=best quality)
- Output: 0-1 (0=best quality)
- Formula: `dmos` (already normalized)

### 4. SmartDoc-QA Parser

**Dataset**: Smartphone-captured document images with quality scores

**Input Format**: JSON with quality annotations

**Parser Implementation**:

```python
def parse_smartdoc_labels(metadata_registry: Path, config: dict) -> dict:
    """Parse SmartDoc-QA quality scores.

    Source: Based on annotate_base_metadata.py parser pattern
    """
    labels_file = config["path"] / "quality_labels.json"

    with open(labels_file) as f:
        data = json.load(f)

    labels = {}
    for img_data in data["images"]:
        file_id = generate_file_id(img_data["filename"])

        # SmartDoc: 1-5 scale (5=best)
        mos = img_data["quality_score"]
        normalized_score = normalize_smartdoc_mos(mos)  # (5 - mos) / 4

        labels[file_id] = {
            "mos_score": normalized_score,
            "confidence": 0.88,  # SmartDoc-QA reliability
            "source_type": "human_mos",
            "capture_conditions": img_data.get("conditions", {}),
            "original_format": img_data
        }

    return labels
```

**Normalization**:

- Input: MOS 1-5 (5=best quality)
- Output: 0-1 (0=best quality)
- Formula: `(5 - mos) / 4`

### 5. DocLayNet Parser (COCO Format)

**Dataset**: Document layout annotations (11 element classes)

**Input Format**: COCO JSON with bounding boxes

**Parser Implementation**:

```python
def parse_doclaynet_labels(metadata_registry: Path, config: dict) -> dict:
    """Parse DocLayNet COCO annotations.

    Source: Based on annotate_base_metadata.py COCO handling, Lines 750-800
    """
    from pycocotools.coco import COCO

    ann_file = config["path"] / "annotations.json"

    # Use COCO cache if available (massive speedup)
    coco = load_coco_with_cache(ann_file)

    labels = {}
    for img_id in coco.getImgIds():
        img_info = coco.loadImgs(img_id)[0]
        file_id = generate_file_id(img_info["file_name"])

        ann_ids = coco.getAnnIds(imgIds=img_id)
        anns = coco.loadAnns(ann_ids)

        # Convert COCO annotations to unified format
        bboxes = []
        element_types = []
        for ann in anns:
            bboxes.append(ann["bbox"])  # [x, y, width, height]
            category = coco.loadCats(ann["category_id"])[0]
            element_types.append(category["name"])

        labels[file_id] = {
            "bboxes": bboxes,
            "element_types": element_types,
            "layout_complexity": compute_layout_complexity(bboxes),
            "num_elements": len(bboxes),
            "original_format": {"annotations": anns, "image_info": img_info}
        }

    return labels
```

**COCO Cache Optimization** (Critical for performance):

```python
def load_coco_with_cache(ann_file: Path) -> COCO:
    """Load COCO annotations with persistent cache.

    Source: Pattern from annotate_base_metadata.py COCO handling

    Performance:
    - First load: ~10-15 seconds (JSON parse + index build)
    - Cached load: ~0.2 seconds (pickle deserialize)
    - Speedup: 50-75x faster
    """
    import hashlib
    import pickle

    # Generate cache key from file checksum
    with open(ann_file, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    cache_key = f"coco_{checksum[:8]}.pkl"
    cache_path = Path(".cache") / cache_key

    if cache_path.exists():
        # Load from cache
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    else:
        # Parse and cache
        coco = COCO(str(ann_file))

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(coco, f, protocol=pickle.HIGHEST_PROTOCOL)

        return coco
```

**Impact**: For datasets like DocLayNet (~18GB annotations), saves 10-15 seconds per load × 100+ training runs = 15-25 minutes saved.

**Code Reference**: `scripts/annotate_base_metadata.py`, Lines 750-852 (COCO parsing logic)

### 6. TableBank Parser (COCO Format)

**Dataset**: Table structure annotations

**Parser**: Similar to DocLayNet, uses COCO cache optimization

**Unique Features**:

- Cell-level bounding boxes
- Row/column structure metadata
- Table type classification (bordered, borderless, etc.)

### 7. FUNSD Parser

**Dataset**: Form understanding (field types, relationships)

**Input Format**: JSON with form structure

**Parser**: Extracts field bounding boxes, labels, and relationships

### 8. SignaTR Parser

**Dataset**: Writer identification labels

**Input Format**: JSON with writer IDs

**Parser**: Extracts writer identity metadata for document attribution

### 9. DIBCO Parser

**Dataset**: Binarization ground truth

**Input Format**: PNG masks

**Parser**: Loads binary GT images for binarization quality assessment

### Parser Summary Table

| Dataset | Format | Quality Labels | Bbox Labels | Normalization | Confidence |
|---------|--------|----------------|-------------|---------------|------------|
| DIQA-5000 | JSON | MOS (1-5) | No | `(5-mos)/4` | From std dev |
| LIVE | MAT | DMOS (0-100) | No | `dmos/100` | 0.95 |
| CSIQ | CSV | DMOS (0-1) | No | `dmos` | 0.90 |
| SmartDoc-QA | JSON | MOS (1-5) | No | `(5-mos)/4` | 0.88 |
| DocLayNet | COCO JSON | No | 11 classes | N/A | N/A |
| TableBank | COCO JSON | No | Table cells | N/A | N/A |
| FUNSD | JSON | No | Form fields | N/A | N/A |
| SignaTR | JSON | No | Writer IDs | N/A | N/A |
| DIBCO | PNG masks | No | Binarization GT | N/A | N/A |

**Total Images**: 108,000+ across 9 datasets

---

## 45-Dimensional Degradation Vector

### Vector Structure

The 45-dimensional degradation index represents **severity of 45 degradation types** aligned with detection-taxonomy.md.

**Code Reference**: `scripts/build_training_labels.py`, Lines 60-114 (DEGRADATION_INDEX)

### Complete Index Mapping

```python
DEGRADATION_INDEX = {
    # Group 1: Blur/Focus (indices 0-5)
    "motion_blur": 0,
    "defocus_blur": 1,
    "gaussian_blur": 2,
    "lens_aberration": 3,
    "depth_of_field": 4,
    "camera_shake": 5,

    # Group 2: Noise (indices 6-12)
    "gaussian_noise": 6,
    "salt_pepper_noise": 7,
    "speckle_noise": 8,
    "film_grain": 9,
    "sensor_noise": 10,
    "quantization_noise": 11,
    "banding": 12,

    # Group 3: Geometric (indices 13-18)
    "skew": 13,
    "rotation": 14,
    "perspective": 15,
    "barrel_distortion": 16,
    "pincushion_distortion": 17,
    "page_curl": 18,

    # Group 4: Illumination (indices 19-25)
    "underexposure": 19,
    "overexposure": 20,
    "uneven_lighting": 21,
    "shadow": 22,
    "glare": 23,
    "vignetting": 24,
    "color_cast": 25,

    # Group 5: Compression (indices 26-29)
    "jpeg_artifacts": 26,
    "jpeg2000_artifacts": 27,
    "webp_artifacts": 28,
    "low_bitrate": 29,

    # Group 6: Physical (indices 30-36)
    "paper_yellowing": 30,
    "foxing": 31,
    "staining": 32,
    "bleed_through": 33,
    "fading": 34,
    "creasing": 35,
    "roller_marks": 36,

    # Group 7: Text/Content (indices 37-41)
    "faint_text": 37,
    "broken_characters": 38,
    "merged_characters": 39,
    "halftone_interference": 40,
    "moire_pattern": 41,

    # Group 8: Scanner Artifacts (indices 42-44)
    "dust_scratches": 42,
    "scan_lines": 43,
    "edge_shadow": 44,
}
```

### Vector Semantics

**iqa_vector**: Continuous severity scores [0.0, 1.0] per degradation

- `0.0` = No degradation detected
- `0.3` = Mild degradation (threshold for binary)
- `0.5` = Moderate degradation
- `1.0` = Severe degradation

**iqa_binary**: Binary presence/absence {0, 1} per degradation

- Thresholded from iqa_vector (threshold=0.3)
- Used for multi-label classification tasks

### Example Vector

```python
{
    "iqa_vector": [
        0.0,   # 0: motion_blur (not present)
        0.65,  # 1: defocus_blur (moderate-severe)
        0.0,   # 2: gaussian_blur
        0.0,   # 3: lens_aberration
        0.0,   # 4: depth_of_field
        0.0,   # 5: camera_shake
        0.22,  # 6: gaussian_noise (mild, below threshold)
        0.0,   # 7: salt_pepper_noise
        # ... (38 more indices)
        0.42,  # 13: skew (moderate)
        0.0,   # 14: rotation
        # ...
        0.88,  # 33: bleed_through (severe)
        # ... (remaining indices)
    ],

    "iqa_binary": [
        0,  # motion_blur (0.0 < 0.3)
        1,  # defocus_blur (0.65 >= 0.3)
        0,  # gaussian_blur
        0,  # lens_aberration
        0,  # depth_of_field
        0,  # camera_shake
        0,  # gaussian_noise (0.22 < 0.3)
        0,  # salt_pepper_noise
        # ...
        1,  # skew (0.42 >= 0.3)
        0,  # rotation
        # ...
        1,  # bleed_through (0.88 >= 0.3)
        # ...
    ]
}
```

**Total Dimensions**: 45 (8 groups covering all common document degradations)

> **SigLIP 2 Integration**: This 45-dimensional vector feeds the **IQA heads (Group 1)** of the SigLIP 2 NAFlex multi-task model. The 5 IQA heads (blur, noise, contrast, illumination, overall_quality) aggregate from these 45 fine-grained degradation dimensions into coarser quality signals. Additional multi-task label dimensions for the remaining 11 SigLIP 2 heads and 3 MobileNetV4-Conv-S heads are documented in the [Multi-Task Label Dimensions](#multi-task-label-dimensions) section below.

---

### Multi-Task Label Dimensions

Beyond the 45-dimensional IQA degradation vector, the training label system produces labels for all heads of the two-model inference pipeline.

#### SigLIP 2 NAFlex Heads (19 heads, 5 groups)

| Group | Head | Type | Dataset Sources | Provenance Tier |
|-------|------|------|-----------------|-----------------|
| **Group 1: IQA** | blur | regression [0,1] | DIQA-5000, OHR-Bench, synthetic IQA (100K) | tier_1 (human MOS) / tier_0 (synthetic GT) |
| | noise | regression [0,1] | DIQA-5000, synthetic IQA (100K) | tier_1 / tier_0 |
| | contrast | regression [0,1] | DIQA-5000, synthetic IQA (100K) | tier_1 / tier_0 |
| | illumination | regression [0,1] | Shadow/Lighting (15K), synthetic IQA | tier_0 / tier_2 |
| | overall_quality | regression [0,1] | DIQA-5000, OHR-Bench, SmartDoc-QA | tier_1 (human MOS) |
| **Group 2: Script** | script_family | classification (19 classes) | synth-multiscript (108K), MDIW13, MLT19 | tier_0 / tier_1 |
| | script_confidence | regression [0,1] | synth-multiscript, model-derived | tier_0 / tier_2 |
| | multi_script_flag | binary | synth-multiscript, CC-OCR | tier_0 / tier_1 |
| **Group 3: Orientation+Skew** | orientation_class | classification (4 classes) | Orientation (50K) | tier_0 (synthetic GT) |
| | fine_skew_angle | regression [-10,+10] | Skew (40K) | tier_0 (synthetic GT) |
| | resolution_quality | regression [0,1] | Resolution (30K) | tier_0 (synthetic GT) |
| **Group 4: Handwriting** | has_handwriting | binary | Handwriting (60K), IAM, NIST-SD19 | tier_1 / tier_0 |
| | handwriting_proportion | regression [0,1] | Handwriting (60K) | tier_2 (model-derived) |
| | handwriting_confidence | regression [0,1] | Handwriting (60K) | tier_2 (model-derived) |
| **Group 5: Page Attrs** | capture_method | classification (4 classes) | Capture (50K) | tier_1 / tier_3 |
| | has_code_or_math | binary | Code/Math (10K), IM2LaTeX | tier_0 / tier_1 |

#### MobileNetV4-Conv-S Heads (3 heads, pre-correction)

| Head | Type | Dataset Sources | Provenance Tier |
|------|------|-----------------|-----------------|
| orientation_class | classification (4 classes) | Orientation (50K) | tier_0 (synthetic GT) |
| fine_skew_angle | regression [-10,+10] | Skew (40K) | tier_0 (synthetic GT) |
| resolution_quality | regression [0,1] | Resolution (30K) | tier_0 (synthetic GT) |

#### Label Provenance Tiers

| Tier | Name | Confidence | Weight | Example |
|------|------|------------|--------|---------|
| **Tier 0** | `tier_0_exact` | 1.0 | 1.0 | Synthetic ground truth, generation parameters |
| **Tier 1** | `tier_1_annotation` | >= 0.9 | 1.0 | Human MOS/DMOS, COCO annotations |
| **Tier 2** | `tier_2_model` | >= 0.7 | 0.8 * confidence | SigLIP 2 predictions, YOLO detections |
| **Tier 3** | `tier_3_heuristic` | >= 0.5 | 0.5 * confidence | Classical IQA scores, rule-based flags |

---

## Anchor Score Selection Algorithm

### Priority-Based Selection

When multiple quality labels exist for a single file, the anchor score selector chooses the most reliable source.

**Code Reference**: `scripts/build_training_labels.py`, Lines 119-137 (AnchorSource enum), Lines 208-290 (compute_anchor_score function)

### Priority Ranking

```python
class AnchorSource(str, Enum):
    """Anchor score source priority ranking."""

    HUMAN = "human"              # Weight: 1.0
    LLM_HIGH = "llm_high"        # Weight: 0.8 (confidence > 0.8)
    LLM_MEDIUM = "llm_medium"    # Weight: 0.5 (confidence 0.5-0.8)
    LLM_LOW = "llm_low"          # Weight: 0.3 (confidence < 0.5)
    SYNTHETIC = "synthetic"      # Weight: 0.3 (augmentation-derived)
    NONE = "none"                # Weight: 0.0 (no anchor)


ANCHOR_WEIGHTS = {
    AnchorSource.HUMAN: 1.0,
    AnchorSource.LLM_HIGH: 0.8,
    AnchorSource.LLM_MEDIUM: 0.5,
    AnchorSource.LLM_LOW: 0.3,
    AnchorSource.SYNTHETIC: 0.3,
    AnchorSource.NONE: 0.0,
}
```

### Selection Implementation

```python
def compute_anchor_score(
    record: dict[str, Any],
) -> tuple[float | None, AnchorSource, float]:
    """Compute best available anchor score with source priority.

    Source: build_training_labels.py, Lines 208-290

    Priority: human > llm_high > llm_medium > llm_low > synthetic > none

    Returns:
        (anchor_score, anchor_source, anchor_weight)
    """
    # Priority 1: Check for human MOS scores
    if record.get("diqa_mos") is not None:
        return (
            normalize_diqa_mos(record["diqa_mos"]),
            AnchorSource.HUMAN,
            1.0
        )

    if record.get("live_dmos") is not None:
        return (
            normalize_live_dmos(record["live_dmos"]),
            AnchorSource.HUMAN,
            1.0
        )

    if record.get("csiq_dmos") is not None:
        return (
            normalize_csiq_dmos(record["csiq_dmos"]),
            AnchorSource.HUMAN,
            1.0
        )

    if record.get("smartdoc_mos") is not None:
        return (
            normalize_smartdoc_mos(record["smartdoc_mos"]),
            AnchorSource.HUMAN,
            1.0
        )

    # Priority 2: Check for LLM predictions
    llm_mos = record.get("llm_mos_normalized")
    llm_conf = record.get("llm_confidence")

    if llm_mos is not None and llm_conf is not None:
        if llm_conf > 0.8:
            return (llm_mos, AnchorSource.LLM_HIGH, 0.8)
        elif llm_conf >= 0.5:
            return (llm_mos, AnchorSource.LLM_MEDIUM, 0.5)
        else:
            return (llm_mos, AnchorSource.LLM_LOW, 0.3)

    # Priority 3: Synthetic/augmented data
    synthetic_score = record.get("synthetic_score")
    if synthetic_score is not None:
        return (synthetic_score, AnchorSource.SYNTHETIC, 0.3)

    # No anchor available
    return (None, AnchorSource.NONE, 0.0)
```

**Design Rationale**:

- Human annotations are most reliable (weight 1.0)
- High-confidence LLM predictions are second-best (weight 0.8)
- Synthetic scores provide weak supervision (weight 0.3)
- No anchor = sample can still be used for unsupervised training (weight 0.0)

### Multi-Head Anchor Concept

With the SigLIP 2 multi-task architecture (19 heads), the anchor score system extends to a **per-head anchor priority**. Each SigLIP 2 head has its own anchor selection based on which datasets provide ground truth for that specific task:

| Head Group | Primary Anchor Source | Fallback Source | Weight Strategy |
|------------|----------------------|-----------------|-----------------|
| **IQA heads** | Human MOS (DIQA-5000, LIVE, CSIQ) | Synthetic GT (Genalog parameters) | Standard priority (human > LLM > synthetic) |
| **Script heads** | Dataset GT (synth-multiscript, MDIW13) | OpenLID-v2 model predictions | tier_0 for synthetic, tier_1 for annotated, tier_2 for model |
| **Orientation+Skew heads** | Synthetic GT (generation parameters) | EXIF metadata | tier_0 only (exact from generation) |
| **Handwriting heads** | Dataset GT (IAM, NIST-SD19) | Model predictions | tier_1 for annotated, tier_2 for predicted |
| **Page Attr heads** | Dataset GT (capture method labels) | Heuristic rules | tier_1 for annotated, tier_3 for heuristic |

Each head's anchor weight is computed independently, allowing the training loss to weight samples differently per task based on label reliability.

---

## Training Label Builder

### TrainingLabels Dataclass

```python
@dataclass
class TrainingLabels:
    """Training-ready labels for a single sample.

    Source: build_training_labels.py, Lines 145-171
    """
    sample_id: str

    # IQA multi-label vector
    iqa_vector: list[float]        # 45-dimensional severity vector
    iqa_binary: list[bool]          # Binary presence/absence

    # Perceptual score anchors
    anchor_score: float | None      # 0-1 scale (0=best, 1=worst)
    anchor_source: AnchorSource     # Source priority level
    anchor_weight: float            # Training sample weight

    # Individual score references (for analysis)
    human_mos_normalized: float | None
    llm_mos_normalized: float | None
    llm_confidence: float | None

    # Phase 9 element labels (JSON-serialized)
    element_labels_json: str | None

    # Metadata
    dataset_name: str
    has_annotations: bool
```

### Builder Workflow

```
Load Metadata Registry
         ↓
Parse Original Labels (Layer 1)
         ↓
Parse Enrichment Data (Layer 2)
         ↓
For each file:
    ├─ Compute anchor score (priority algorithm)
    ├─ Build 45-dim iqa_vector
    ├─ Compute iqa_binary (threshold at 0.3)
    ├─ Extract element labels (if Phase 9)
    ├─ Assign training weight
    ↓
Create TrainingLabels dataclass
         ↓
Export to Parquet
```

### Builder Implementation Pattern

```python
def build_training_labels(metadata_registry: Path) -> list[TrainingLabels]:
    """Build training labels from metadata registry.

    Source: Conceptual from build_training_labels.py main logic
    """
    # Load metadata
    layer1_data = load_parquet(metadata_registry / "layer1_original.parquet")
    layer2_data = load_parquet(metadata_registry / "layer2_enrichment.parquet")

    training_labels = []

    for record in layer1_data:
        file_id = record["file_id"]

        # Get enrichment for this file
        enrichment = layer2_data.get(file_id, {})

        # Compute anchor score
        anchor_score, anchor_source, anchor_weight = compute_anchor_score(record)

        # Build iqa_vector from enrichment
        iqa_vector = build_iqa_vector(enrichment)
        iqa_binary = [severity >= 0.3 for severity in iqa_vector]

        # Create training label
        training_label = TrainingLabels(
            sample_id=file_id,
            iqa_vector=iqa_vector,
            iqa_binary=iqa_binary,
            anchor_score=anchor_score,
            anchor_source=anchor_source,
            anchor_weight=anchor_weight,
            human_mos_normalized=record.get("diqa_mos_normalized"),
            llm_mos_normalized=record.get("llm_mos_normalized"),
            llm_confidence=record.get("llm_confidence"),
            element_labels_json=enrichment.get("element_labels"),
            dataset_name=record["dataset_name"],
            has_annotations=(anchor_score is not None)
        )

        training_labels.append(training_label)

    return training_labels
```

---

## Code Traceability

### File: `scripts/build_training_labels.py` (590 lines)

| Component | Lines | Description |
|-----------|-------|-------------|
| **Degradation Index** | 60-114 | 45-dimensional degradation mapping (8 groups) |
| **Anchor Source Enum** | 119-128 | Priority ranking for label sources |
| **Anchor Weights** | 130-137 | Training weights by source quality |
| **TrainingLabels Dataclass** | 145-171 | Training-ready label schema |
| **Score Normalization** | 178-201 | 4 dataset-specific normalizers |
| **Anchor Score Computation** | 208-290 | Priority-based anchor selection |
| **IQA Vector Builder** | Throughout | 45-dim vector construction |
| **Main Pipeline** | 300+ | Metadata loading, label building, export |

### File: `scripts/annotate_base_metadata.py` (1,235 lines)

| Component | Lines | Description |
|-----------|-------|-------------|
| **Dataset Configs** | 101-361 | 15+ dataset configurations |
| **Label Parsers** | 635-852 | 9 dataset-specific parsers |
| **COCO Cache Logic** | 750-800 | Persistent cache for COCO JSON |
| **Normalization Utils** | Throughout | Dataset-specific score normalizers |

---

## Summary

The label parsing and generation system provides:

1. **Heterogeneous Dataset Support**: 9+ parsers normalize diverse formats to unified schema
2. **COCO Cache Optimization**: 50-75x faster parsing via persistent cache
3. **45-Dimensional Degradation Vectors**: Comprehensive quality representation
4. **Priority-Based Anchor Selection**: Deterministic selection from multiple label sources
5. **Training Optimization**: Sample weighting by source quality
6. **Full Provenance**: Complete audit trail from source annotations to training labels

**Total Implementation**: 1,440 lines (590 + 850 across 2 scripts)

**Key Innovation**: COCO cache reduces iterative development overhead from 15 minutes to 20 seconds per 100 training runs.

---

## Level 4: Per-Dataset Instance Registry

The per-dataset parser instances, enrichment providers, and integrate-enrichment scripts are
catalogued in the **Level 4 Instance Registries** — a separate documentation tier introduced to
avoid cluttering PUML workflow diagrams with 116+ individual adapter rows.

| Registry | Location | Contents |
|----------|----------|----------|
| Annotation Parser Registry | [annotation-parser-registry.md](../../level-4/data-preparation/annotation-parser-registry.md) | 59 dataset-specific parsers grouped by task (layout, quality, handwriting, …) |
| Enrichment Provider Registry | [annotation-provider-registry.md](../../level-4/data-preparation/annotation-provider-registry.md) | 5 enrichment providers (SigLIP, Docling, YOLO, language detector, …) |
| Integrate-Enrichment Registry | [annotation-integrate-registry.md](../../level-4/data-preparation/annotation-integrate-registry.md) | 52 `integrate_*_enrichments.py` scripts with paired-parser cross-references |

These registries are **auto-generated** by
`python scripts/generate_level4_registries.py --category all` from `__l4_*` module-level metadata
variables embedded in each adapter file.

---

**Document Version**: 1.0.0
**Last Reviewed**: 2025-01-19
