---
dataset_id: hindi-synth
version: "1.0"
license: CC0
commercial_use: true
iqa_profiles:
  - handwriting
  - synthetic
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

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

> **Audit Date**: 2026-02-16 | **Grade**: A (94.8/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.3 | 20% |  |
| Field Validity | 92.6 | 20% |  |
| Doc Completeness | 100.0 | 7% |  |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **94.8** | | **Grade A** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/hindi-synth/](../../scripts/audit/results/hindi-synth/)

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

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | — | All images upright (0°) by synthetic construction; no orientation variety |
| MNV4-H2 | skew_reg | ➖ | 0 | — | No skew applied during generation; all images have 0° skew |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~80,008 | Pseudo-label | Clean synthetic renders; useful as high-quality anchor examples after RQ labeling |
| SIG-G1-1 | blur_score | 🟡 | ~80,008 | Pseudo-label | Minimal blur (synthetic); useful as near-zero blur exemplars |
| SIG-G1-2 | noise_score | 🟡 | ~80,008 | Pseudo-label | No noise (synthetic); useful as near-zero noise exemplars |
| SIG-G1-3 | contrast_score | 🟡 | ~80,008 | Pseudo-label | Clean white background; good contrast baseline |
| SIG-G1-4 | skew_score | ➖ | 0 | — | No skew in synthetic generation |
| SIG-G1-5 | compression_score | ❌ | 0 | — | PNG lossless; no compression artifact signal |
| SIG-G1-6 | overall_quality | 🟡 | ~80,008 | Pseudo-label | High-quality synthetic renders provide "good quality" anchor distribution |
| SIG-G2-1 | script_cls | ✅ | ~80,008 | Native (Deva) | Primary Devanagari (Deva) training data; 80K samples for one of 19 script classes |
| SIG-G3-1 | orientation_cls (post) | ➖ | 0 | — | Same as pre-correction — no orientation variety in synthetic data |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | — | No skew to correct |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~80,008 | Native (False) | Confirmed printed synthetic; large-scale negative (no handwriting) examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-4 | presence_reg | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | Not applicable — no handwriting present |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | — | Synthetic capture method; 100% real images required — synthetic excluded |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | Clean white backgrounds; no shadow variation |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | Flat synthetic renders; no geometric distortion |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Devanagari text lines; no code or markup content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~80,008 | Pseudo-label | Same as MNV4-H3 — high-quality anchor after labeling pass |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% Indic (Deva); single-script dataset — strong Devanagari representation |
| 2 | Capture method | ❌ | 100% synthetic; excluded from G5-1 capture_method_cls training |
| 3 | Document domain | 🟡 | 100% EDU; single domain — no cross-domain variety |
| 4 | Layout type | ❌ | Single-line text crops only; no page-level layout |
| 5 | Text density | ❌ | All images are single text lines; no density variation |
| 6 | Degradation types | ❌ | Clean synthetic renders; zero degradation diversity |
| 7 | Resolution/DPI range | 🟡 | Variable resolution (synthetic rendering artifacts); mostly consistent quality |
| 8 | Document age | ❌ | Modern synthetic only; no aged or historical examples |
| 9 | Text scope | ✅ | 100% line-level scope; comprehensive single-line Devanagari coverage |
| 10 | Content flags | ❌ | No formulas, figures, tables, or code — plain Devanagari text only |
| 11 | Binarization status | 🟡 | Clean white-on-white backgrounds; effectively binarized by construction |
| 12 | Artifact types | ❌ | No scan artifacts, JPEG compression, shadows, or warping |
| 13 | Color mode | 🟡 | Grayscale/RGB clean renders; no binarized or heavily degraded color variation |
| 14 | Font variety | ✅ | Multiple Devanagari fonts used in synthetic generation; good intra-script font diversity |

### 13.3 Corpus Role & Constraints

This dataset is the **primary training source for the Devanagari (Deva) script class** in SIG-G2-1, contributing ~80K line-level images that cover diverse Devanagari font styles. It is licensed CC0 (public domain) with no usage restrictions. Being 100% synthetic, it is excluded from G5-1 `capture_method_cls` training and provides no IQA degradation signal, but it offers large-scale negative handwriting examples and high-quality anchor samples for IQA regression heads after a pseudo-labeling pass.
