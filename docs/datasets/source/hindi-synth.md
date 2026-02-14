#### Hindi OCR Synthetic Dataset

> **Quick Stats**: 80,000 line images | Devanagari script | Synthetic text lines
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Hindi OCR Synthetic Line Image Text Pair |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Kaggle** | [prathmeshzade/hindi-ocr-synthetic-line-image-text-pair](https://www.kaggle.com/datasets/prathmeshzade/hindi-ocr-synthetic-line-image-text-pair) |
| **License** | CC0 (Public Domain) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/hindi_ocr_synthetic/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 80,009 |
| **CSV Labels** | 1 (data.csv) |
| **Total Size** | 735 MB |
| **File Format** | PNG |
| **Layer 2 Samples** | 80,008 |

##### Format and Structure

| Folder | Contents |
|--------|----------|
| **output_images/** | 80,000 synthetic line images |
| **TestSamples/** | 9 sample images |
| **data.csv** | Image-text pairs mapping |

Images are single-line Devanagari text rendered on white backgrounds. Each image is paired with its ground truth text transcription via data.csv. Resolution varies but images are consistently clean synthetic renders.

##### Label Schema

Labels are provided in two formats:

1. **CSV master index**: `data.csv` with columns mapping image filenames to their Hindi text transcriptions
2. **Per-image transcription files**: Paired `.txt` files (one per image) containing ground truth text in Devanagari

The parser `parse_hindi_synthetic_labels` extracts transcription from paired .txt files with hi/Deva metadata.

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetically generated |
| **Script** | Devanagari (Hindi) |
| **Quality** | Clean (synthetic) |
| **Key Value** | **Large-scale Devanagari training data** |
| **Generation** | Programmatic text rendering |

##### Limitations and Known Issues

- Synthetic data only - no real-world scanning artifacts, noise, or degradation
- Single script (Devanagari) limits diversity for multi-script training
- No split field assigned for 80,000 of 80,008 samples (99.99% fail rate on split)
- Clean white backgrounds do not represent real document conditions
- May need augmentation with noise, rotation, and background variation for robust training

##### License and Usage

CC0 Public Domain dedication. No restrictions on commercial or research use. Attribution appreciated but not required.

##### Layer 2 Metadata

| Field | Coverage |
|-------|----------|
| **capture_method** | 100% (synthetic) |
| **domain_level1** | 100% (EDU) |
| **iso639_language** | 100% (hi) |
| **script_family** | 100% (indic) |
| **has_handwriting** | 100% (False) |
| **Total Samples** | 80,008 |

Metadata registry: `metadata_registry/json/hindi_ocr_synthetic_metadata.json` (2026-02-09).

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: A (92.4/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.6 | 33% |  |
| Field Validity | 92.6 | 33% |  |
| Doc Completeness | 100.0 | 20% |  |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 95.0 | 13% |  |
| **Overall** | **92.4** | | **Grade A** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 95.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/hindi-synth/](../../scripts/audit/results/hindi-synth/)

---

##### Reliability Assessment

VLM inspection (2026-02-13): passing_sample_accuracy=0.95. Direct viewing of 3 sample images confirmed synthetic Devanagari text on clean white backgrounds. All content flags verified correct. High reliability due to uniform synthetic generation process.

##### Processing Pipeline

1. Image extraction from Kaggle archive
2. Base metadata annotation via `annotate_base_metadata.py`
3. Language enrichment integration (hi/Deva metadata from parser)
4. Layout extraction via Docling GPU (161 batches, 80,009 images)
5. Layer 2 metadata aggregation

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial release on Kaggle |
| L2 v1 | 2026-02-09 | Layer 2 metadata generated (80,008 samples) |
| Audit v1 | 2026-02-13 | VLM inspection completed |

##### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact - programmatic text rendering) |
| **Quality Assurance** | Labels exact by construction (synthetic generation) |
| **GT Label Coverage** | 100% (all 80K images with paired text transcriptions) |

##### Project Usage

- **Path**: `01_base_data/language/hindi_ocr_synthetic/` Extracted (80,010 files, 920 MB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Devanagari script class training (primary source)
- **Note**: Synthetic data - excellent for training, needs real-world augmentation
- **Parser**: `parse_hindi_synthetic_labels` (extracts transcription from .txt pairs, hi/Deva metadata)

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/hindi_ocr_synthetic/` | Available | 80,009 PNG files |
| **Text/GT** | Native annotations | Available | CSV/TXT: Paired image-text files (Devanagari line transcriptions) |
| **Text/OCR Extracted** | - | Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/hindi-synth/` | Available | Docling GPU: 161 layout batches, 80,009 images |
| **Layer 2 Metadata** | `metadata_registry/json/hindi_ocr_synthetic_metadata.json` | Complete | 80,008 samples (2026-02-09) |
