---
canonical_name: signverod
display_name: SignverOD (Signature Verification Object Detection)
source_url: https://www.kaggle.com/datasets/victordibia/signverod
license: CC0-1.0
total_images: 2765
format: PNG + CSV annotations
status: training-ready
documentation_status: complete
---

# SignverOD (Signature Verification Object Detection)

## 1. Overview

SignverOD contains 2,765 scanned document images with bounding box annotations for
signatures, initials, redactions, and dates. Documents sourced from NIST (government
forms) and GSA (contract documents). Valuable for signature/handwriting presence
detection and mixed typed+handwritten content classification.

## 2. Source & Access

| Field | Value |
|-------|-------|
| **Publisher** | Victor Dibia |
| **URL** | <https://www.kaggle.com/datasets/victordibia/signverod> |
| **Format** | PNG images + CSV annotations (normalized COCO-style bounding boxes) |
| **License** | CC0-1.0 (Public Domain) |
| **Download Size** | ~1.4 GB (Kaggle zip) |
| **Citation** | Dibia, V., "SignverOD: Signature Verification via Object Detection" |

## 3. Dataset Composition

| Metric | Value |
|--------|-------|
| **Total Images** | 2,765 |
| **Train Images** | 1,939 (by annotation reference) |
| **Test Images** | 354 (by annotation reference) |
| **Annotation Entries** | 9,215 (7,549 train + 1,666 test) |
| **Image Type** | Full-page scanned documents |
| **Resolution** | Mostly 2560x3300 or 3400x4400 |
| **Color Mode** | RGB |

## 4. Label Schema

Annotations in `train.csv` and `test.csv` with columns:

- `area`: Normalized bounding box area (fraction of image)
- `bbox`: `[x, y, width, height]` normalized to [0,1]
- `category_id`: 1=signature, 2=initials, 3=redaction, 4=date
- `id`: Annotation ID
- `image_id`: References `image_ids.csv`

Image metadata in `image_ids.csv`:

- `height`, `width`, `id`, `file_name`

Categories in `categories.csv`:

- 1: signature (5,044 annotations)
- 2: initials (1,163 annotations)
- 3: redaction (2,308 annotations)
- 4: date (700 annotations)

## 5. Language & Script Coverage

| Script | ISO 15924 | Count | Notes |
|--------|-----------|-------|-------|
| Latin | Latn | 2,765 | English government/contract documents |

## 6. IQA Profile

| Degradation | Prevalence | Notes |
|-------------|-----------|-------|
| Scanner artifacts | Medium | Typical office scanner output |
| Low contrast | Low | Some faded documents |
| Redaction marks | High | Black-out redactions common |

## 7. Training Relevance

| Head | Applicable | Reason |
|------|-----------|--------|
| Handwriting Detection | **Primary** | Signature/initial presence detection |
| Script Detection | Secondary | English Latin only |
| IQA | No | Clean scans |
| Orientation | No | Standard portrait orientation |

## 8. SigLIP 2 Head Coverage

| SIG ID | Head | Applicable | Count | Tier | Notes |
|--------|------|-----------|-------|------|-------|
| SIG-G4-1 | handwriting_presence_cls | Yes | ~2,765 | tier_1_annotation | Signature/initials = handwriting presence |
| SIG-G4-3 | handwriting_content_cls | Yes | ~2,765 | tier_1_annotation | Mixed typed + handwritten |
| SIG-G2-1 | script_cls | Yes | ~2,765 | tier_0_exact | 100% Latin (English) |

## 9. Known Limitations

- **English only**: US government and contract documents
- **Signature-focused**: Handwriting limited to signatures/initials (not full text)
- **No transcriptions**: Bounding boxes only, no text content

## 10. Local Storage

| Item | Path |
|------|------|
| **Images** | `/mnt/e/image_detection/01_base_data/handwriting/signverod/images/` |
| **Train annotations** | `/mnt/e/image_detection/01_base_data/handwriting/signverod/train.csv` |
| **Test annotations** | `/mnt/e/image_detection/01_base_data/handwriting/signverod/test.csv` |
| **Image metadata** | `/mnt/e/image_detection/01_base_data/handwriting/signverod/image_ids.csv` |
| **Categories** | `/mnt/e/image_detection/01_base_data/handwriting/signverod/categories.csv` |
