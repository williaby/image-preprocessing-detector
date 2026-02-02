#### docsynth300k

> **Quick Stats**: 300,000 synthetic document pages | 74 layout classes | YOLO polygon annotations | Layout pre-training
>
> **License**: Apache-2.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocSynth300K: Large-Scale Synthetic Document Layout Pre-training Dataset |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | OpenDataLab (juliozhao) |
| **Paper** | [DocLayout-YOLO (arXiv:2410.12628)](https://arxiv.org/abs/2410.12628) |
| **Repository** | [GitHub: opendatalab/DocLayout-YOLO](https://github.com/opendatalab/DocLayout-YOLO) |
| **HuggingFace** | [juliozhao/DocSynth300K](https://huggingface.co/datasets/juliozhao/DocSynth300K) |
| **License** | Apache-2.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/docsynth300k/` |
| **Documentation Status** | Partial |

##### 2. Source Data Inventory

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPEG | 300,000 synthetic document page images |
| **Annotations** | TXT (YOLO polygon) | 300,000 label files (8-coordinate polygons) |
| **Metadata** | Parquet | 30 parquet files with image_data and annotations |
| **Supplementary** | Python script | extract_images.py conversion tool |

###### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `docsynth300k/images/` | `docsynth300k/labels/` | 300,000 | ✅ |
| **Validation** | - | - | 0 | ℹ️ N/A |
| **Test** | - | - | 0 | ℹ️ N/A |

**Split Organization Pattern**: `single_dir_with_manifest` (parquet acts as manifest)

> **Notes**:
>
> - Single split dataset (train only) - no validation or test splits provided
> - All 300K images intended for pre-training
> - Original data stored in 30 parquet files (~113 GB total)
> - Extracted to images/ and labels/ directories

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Polygons** | YOLO 8-coordinate | Element-level | Quadrilateral bounding polygons for layout elements |
| **Class IDs** | Integer (0-73) | Element-level | 74 document layout classes |

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README.md | License, download instructions, conversion tools |
| **Image-level** | Parquet filename column | Image filename mapping |
| **Annotation-level** | Parquet anno_string column | YOLO polygon coordinates + class IDs |

###### 2.5 Annotation Schema Details

**Format**: YOLO polygon format with 8 normalized coordinates

```text
# Parquet Schema
{
  "filename": str,              # e.g., "1720629091_634364.jpg"
  "image_data": bytes,          # Base64-encoded JPEG image
  "anno_string": list[str]      # YOLO annotations (1-32 per image)
}

# YOLO Annotation Format (each string in anno_string list)
<class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>

# Example
23 0.0942 0.5595 0.7866 0.5595 0.7866 0.6310 0.0942 0.6310
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | str | Yes | Links annotation to image in parquet |
| `class_id` | int | Yes | Range 0-73 (74 classes total) |
| `x1-x4, y1-y4` | float | Yes | Normalized [0,1] polygon coordinates |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ YOLO polygons | `layout_annotations` | High | Implemented in DocSynth300KParser |
| ✅ Class IDs (0-73) | `class_name` | High | Requires class taxonomy mapping |
| ⚠️ 74-class taxonomy | - | High | Class definitions not documented |
| ❌ Text GT | - | N/A | Synthetic dataset, no text provided |
| ❌ Reading order | - | Low | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 300,000 |
| **Image Format** | JPEG |
| **Image Dimensions** | ~1240 × 1198 pixels (variable) |
| **Label Files** | 300,000 TXT (YOLO polygon format) |
| **Class Count** | 74 unique classes (IDs 0-73) |
| **Source Format** | 30 Parquet files (~113 GB total) |
| **Extracted Size** | Images: ~35 GB, Labels: ~500 MB |

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 300,000 | [NEEDS_PROFILING] | - | 🔄 Needs Layer 2 metadata |
| **Validation** | 0 | - | - | ℹ️ N/A (no split) |
| **Test** | 0 | - | - | ℹ️ N/A (no split) |
| **Total** | 300,000 | [NEEDS_PROFILING] | - | 🔄 Pending |

**Split Status Legend:**

- 🔄 Needs Layer 2 metadata - Split exists but Layer 2 enrichment not complete
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: DocSynth300K is a single-split dataset (train only) designed for pre-training.
> No validation or test splits are provided. All 300K images should be used for model
> initialization before fine-tuning on downstream datasets (e.g., DocLayNet).

##### Annotation Format

YOLO polygon format with 8 coordinates per element:

```text
<class_id> <x1> <y1> <x2> <y2> <x3> <y3> <x4> <y4>
```

**Sample annotation**:

```text
48 0.1930 0.8719 0.8415 0.8719 0.8415 0.9515 0.1930 0.9515
63 0.2208 0.0743 0.8995 0.0743 0.8995 0.7940 0.2208 0.7940
```

| Field | Description |
|-------|-------------|
| **class_id** | Element class (0-73) |
| **x1-x4, y1-y4** | Normalized quadrilateral polygon coordinates |

##### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of classes/categories used in the dataset annotations.

**[NEEDS_VERIFICATION]**: The DocSynth300K dataset uses 74 unique class IDs (0-73),
but the official class definitions are not documented in the HuggingFace dataset page,
GitHub repository, or ArXiv paper. Class IDs observed in annotations include:

| Class ID | Frequency | Description |
|----------|-----------|-------------|
| 0 | [Unknown] | [NEEDS_VERIFICATION] |
| 1 | [Unknown] | [NEEDS_VERIFICATION] |
| ... | ... | ... |
| 23 | High | [Observed in samples] |
| 48 | Very High | [Observed in samples] |
| ... | ... | ... |
| 73 | [Unknown] | [NEEDS_VERIFICATION] |

**Relationship to DocLayNet**:

The paper states that DocSynth300K pre-training improves DocLayNet fine-tuning
performance (+2.0 mAP), suggesting class alignment. However, DocLayNet uses only
11 classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header,
Picture, Section-Header, Table, Text, Title).

**Possible Scenarios**:

1. 74 classes may be a superset that maps to DocLayNet 11 classes
2. 74 classes may include fine-grained subcategories (e.g., Table-Simple, Table-Complex)
3. Class taxonomy may be defined in DocLayout-YOLO model code

**Action Required**: Contact dataset authors or inspect model configuration for
class name mappings.

> **Notes**:
>
> - Mark catalog entry status as "Partial" until class taxonomy verified
> - Parser currently extracts class IDs but cannot map to semantic names
> - This blocks full Layer 2 enrichment (layout_detections.class_name field)

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetic (born-digital, generated) |
| **Generation Method** | Mesh-candidate BestFit algorithm |
| **Layout Complexity** | **HIGH** - Diverse element arrangements, multi-scale variations |
| **Annotation Quality** | **HIGH** - Programmatically generated (perfect ground truth) |
| **Blur Sensitivity** | LOW - Clean synthetic rendering |
| **Skew Sensitivity** | N/A - Synthetic, no rotation artifacts |
| **Key Challenge** | Domain gap between synthetic and real documents |

##### Training Value

- **Strengths**: Large scale (300K images), perfect annotations, diverse layouts, permissive license
- **Weaknesses**: Synthetic data may not capture all real-world degradations
- **Unique Features**: Designed specifically for DocLayout-YOLO pre-training, polygon annotations
- **Benchmark Suitability**: **PRE-TRAINING** - Not intended as evaluation benchmark, use DocLayNet/DocStructBench for benchmarking
- **Phase Role**: Layout-aware pre-training before fine-tuning on real datasets

##### Project Usage

- **Path**: `01_base_data/layout/docsynth300k/`
- **Phase(s)**: Phase 2 (Layout-lite pre-training), Phase 7 (Layout detection)
- **Purpose**: Pre-training DocLayout-YOLO for document layout detection
- **Parser**: Custom extraction script (`extract_images.py` in dataset folder)
- **Added**: 2025-01-31

##### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`DocSynth300KParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/docsynth300k.py) |
| **Parser Status** | ✅ Complete |
| **Registry** | ✅ Registered in `parsers/layout/__init__.py` |
| **Layer 1 Fields** | `docsynth300k_annotations` (YOLO polygon format) |
| **Layer 2 Auto-Derived** | `layout_detections` (converted from YOLO to COCO bbox), `has_table`, `has_figure` |
| **Config Entry** | Uses parquet-based indexing (module-level cache) |
| **Batch Support** | ✅ Yes (benefits from parquet index) |

**Parser Implementation Notes**:

- Builds filename → annotations index from 30 parquet files on first access
- Index cached at module level for performance
- Converts YOLO 8-coordinate polygons to COCO-style bboxes
- Returns `raw_labels["docsynth300k_annotations"]` with parsed annotations

**Known Limitations**:

- ⚠️ 74-class taxonomy not mapped to DocLayNet 11 classes
- First call expensive (parquet indexing), subsequent calls use cache
- Requires pyarrow dependency for parquet reading

##### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/layout/docsynth300k/images/` | ✅ Available | 300,000 JPEG files |
| **Images (source)** | `01_base_data/layout/docsynth300k/part*.parquet` | ✅ Available | 30 parquet files (~113 GB) |
| **Text/OCR GT** | - | ❌ None | Synthetic dataset, no text GT provided |
| **Text/OCR Extracted** | `annotations/docsynth300k/ocr/` | ❌ Not extracted | Could extract via DocTR/Tesseract |
| **Layout GT** | `01_base_data/layout/docsynth300k/labels/` | ✅ Available | 300,000 TXT (YOLO polygon format) |
| **Layout Extracted** | - | ℹ️ N/A | Original labels already in YOLO format |
| **Layer 2 Metadata** | `metadata_registry/json/docsynth300k_layer2.json` | ❌ Not generated | Needs Layer 2 enrichment run |
| **Extraction Script** | `01_base_data/layout/docsynth300k/extract_images.py` | ✅ Available | Local parquet → images/labels |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- ℹ️ N/A - Not applicable for this dataset type

##### 10. Dataset-Specific Notes

###### 10.1 Annotation Caveats

- **Parquet Format**: Original data stored in 30 parquet files (~113 GB total)
- **Extraction Required**: Images and labels must be extracted from parquet using
  `extract_images.py` or similar conversion script
- **YOLO Polygon Format**: Annotations use 8-coordinate quadrilateral polygons,
  not standard YOLO 5-value bounding boxes
- **Class ID Range**: 74 unique classes (IDs 0-73), but class taxonomy not documented

###### 10.2 Implementation Notes

- **Parser Caching**: `DocSynth300KParser` builds filename → annotations index from
  all 30 parquet files on first access. Index is cached at module level for performance.
  First parsing call may take 30-60 seconds.
- **Coordinate Conversion**: Parser converts YOLO 8-coordinate polygons to COCO-style
  bounding boxes using min/max of quadrilateral corners
- **Batch Processing**: Parser supports batch mode (`supports_batch() = True`) and
  benefits from parquet indexing
- **Dependency**: Requires `pyarrow` for parquet file reading

###### 10.3 External Resources

- **Conversion Tool**: `format_docsynth300k.py` from GitHub repo converts parquet
  to YOLO directory structure (`./layout_data/docsynth300k/`)
- **Pre-training Script**: [assets/script.sh#L2](https://github.com/opendatalab/DocLayout-YOLO/blob/main/assets/script.sh#L2)
  shows 8-GPU pre-training command
- **Known Issue**: YOLO data loading has memory leakage, may require `--resume`
  for interrupted training runs
- **Downstream Datasets**: Designed for pre-training before fine-tuning on:
  - DocLayNet (document layout)
  - D4LA (document understanding)
  - Custom downstream tasks

###### 10.4 Custom Metrics

- **Pre-training Value**: Measured by improvement on downstream tasks:
  - DocLayNet: +2.0 mAP, +0.4 AP50 (from 77.7 → 79.7 mAP)
- **Domain Gap**: Performance gain indicates synthetic→real transfer learning works,
  but domain gap exists (not suitable as evaluation benchmark)

##### References

```bibtex
@article{zhao2024doclayoutyolo,
  title={DocLayout-YOLO: Enhancing Document Layout Analysis through Diverse Synthetic Data and Global-to-Local Adaptive Perception},
  author={Zhao, Zhiyuan and others},
  journal={arXiv preprint arXiv:2410.12628},
  year={2024}
}
```

---
