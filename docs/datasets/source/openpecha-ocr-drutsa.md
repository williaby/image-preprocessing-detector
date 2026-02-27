---
canonical_name: openpecha-ocr-drutsa
display_name: OpenPecha OCR Drutsa
source_url: https://huggingface.co/datasets/OpenPecha/OCR-Drutsa
license: CC-BY-4.0
total_images: 32364
format: parquet (images + labels)
capture_method: scanner
domain: UNK
status: training-ready
documentation_status: complete
---

# OpenPecha OCR Drutsa

## 1. Overview

Tibetan line-level OCR dataset from the OpenPecha project containing 32,364 line images
with Unicode Tibetan text transcriptions. Covers woodblock prints, manuscript pages, and
modern Tibetan typography — a critical resource for Tibetan script detection training.

## 2. Source & Access

| Field | Value |
|-------|-------|
| **Publisher** | OpenPecha |
| **URL** | <https://huggingface.co/datasets/OpenPecha/OCR-Drutsa> |
| **Format** | Apache Parquet (2 shards, image + label columns) |
| **License** | CC-BY-4.0 |
| **Download Size** | ~2.5 GB (parquet) |
| **Citation** | OpenPecha Project, 2024 |

## 3. Dataset Composition

| Metric | Value |
|--------|-------|
| **Total Images** | 32,364 |
| **Train Split** | 32,364 (no explicit train/test split) |
| **Image Type** | Line-level crops from manuscript/print pages |
| **Resolution** | Variable (width 100-3000px, height 40-150px typical) |
| **Color Mode** | RGB |
| **File Format** | PNG (extracted from parquet binary) |

## 4. Label Schema

Each record contains:

- `id`: Unique identifier (e.g., `KS_11-061_line_9874_4`)
- `image`: Binary image data
- `label`: Unicode Tibetan text transcription

**Label Type**: OCR ground truth text (Unicode Tibetan script)

## 5. Language & Script Coverage

| Script | ISO 15924 | Count | Notes |
|--------|-----------|-------|-------|
| Tibetan | Tibt | 32,364 | 100% Tibetan script |

**Language**: Tibetan (bo / bod)

## 6. IQA Profile

| Degradation | Prevalence | Notes |
|-------------|-----------|-------|
| Low contrast | Medium | Woodblock prints often faded |
| Ink bleed | Low-Medium | Manuscript sources |
| Skew | Low | Line-level crops generally well-aligned |
| Noise | Low | Clean digital scans |

## 7. Training Relevance

| Head | Applicable | Reason |
|------|-----------|--------|
| Script Detection | **Primary** | Tibetan script — unique abugida system |
| Handwriting Detection | Partial | Mix of handwritten manuscripts and woodblock prints |
| IQA | Secondary | Historical document quality variation |
| Orientation | No | Line crops have fixed orientation |

## 8. SigLIP 2 Head Coverage

| SIG ID | Head | Applicable | Count | Tier | Notes |
|--------|------|-----------|-------|------|-------|
| SIG-G2-1 | script_cls | Yes | ~32,364 | tier_0_exact | 100% Tibetan (Tibt) |
| SIG-G4-1 | handwriting_presence_cls | Partial | ~32,364 | tier_2_model | Mix of handwritten and print |
| SIG-G1-1 | blur_score | No | -- | N/A | Line-level crops |
| SIG-G1-2 | noise_score | No | -- | N/A | N/A |
| SIG-G3-1 | orientation_cls | No | -- | N/A | Fixed orientation |

## 9. Known Limitations

- **Line-level only**: Images are individual text lines, not full pages
- **No train/test split**: Dataset ships as a single training set
- **Variable quality**: Mix of clean modern prints and degraded historical sources
- **No bounding box annotations**: Text-only labels (no spatial layout info)

## 10. Local Storage

| Item | Path |
|------|------|
| **Parquet files** | `/mnt/e/image_detection/01_base_data/language/openpecha-ocr-drutsa/data/` |
| **Extracted images** | `/mnt/e/image_detection/01_base_data/language/openpecha-ocr-drutsa/extracted_images/` |
| **Layer 1 metadata** | `/mnt/e/image_detection/metadata_registry/json/openpecha-ocr-drutsa_metadata.json` |
