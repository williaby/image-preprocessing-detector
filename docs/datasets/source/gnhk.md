---
canonical_name: gnhk
display_name: GNHK (GoodNotes Handwriting Knowledge)
source_url: https://github.com/GoodNotes/gnhk-dataset
license: CC-BY-4.0
total_images: 687
format: JPG + JSON annotations
status: training-ready
documentation_status: complete
---

# GNHK (GoodNotes Handwriting Knowledge)

## 1. Overview

GoodNotes Handwriting Knowledge dataset containing 687 handwritten document images
with word-level polygon annotations. Primarily English handwriting across diverse
writing styles, captured on tablets. Valuable for handwriting detection, legibility
classification, and text region localization.

## 2. Source & Access

| Field | Value |
|-------|-------|
| **Publisher** | GoodNotes |
| **URL** | <https://github.com/GoodNotes/gnhk-dataset> |
| **Format** | JPG images + per-image JSON annotations |
| **License** | CC-BY-4.0 |
| **Download Size** | ~960 MB (train: 691MB, test: 273MB) |
| **Citation** | Lee et al., "GNHK: A Dataset for English Handwriting in the Wild", ICDAR 2021 |

## 3. Dataset Composition

| Metric | Value |
|--------|-------|
| **Total Images** | 687 |
| **Train** | 515 |
| **Test** | 172 |
| **Image Type** | Full-page handwritten documents |
| **Annotation Level** | Word-level polygons with text transcription |

## 4. Label Schema

Each image has a corresponding JSON file with an array of word annotations:

- `text`: Transcription (or `%math%` for mathematical content)
- `polygon`: 4-point polygon (`x0,y0` through `x3,y3`)
- `line_idx`: Line number the word belongs to
- `type`: `"H"` for handwritten

## 5. Language & Script Coverage

| Script | ISO 15924 | Count | Notes |
|--------|-----------|-------|-------|
| Latin | Latn | 687 | English handwriting |

## 6. IQA Profile

| Degradation | Prevalence | Notes |
|-------------|-----------|-------|
| Ink variation | High | Diverse writing instruments |
| Skew | Medium | Free-form handwriting |
| Occlusion | Low | Some overlapping text |

## 7. Training Relevance

| Head | Applicable | Reason |
|------|-----------|--------|
| Handwriting Detection | **Primary** | 100% handwritten with word polygons |
| Legibility | **Primary** | Scribble-tagged regions for illegibility |
| Script Detection | Secondary | English Latin only |
| IQA | No | Clean digital captures |

## 8. SigLIP 2 Head Coverage

| SIG ID | Head | Applicable | Count | Tier | Notes |
|--------|------|-----------|-------|------|-------|
| SIG-G4-1 | handwriting_presence_cls | Yes | ~687 | tier_0_exact | 100% handwritten |
| SIG-G4-2 | handwriting_legibility_cls | Yes | ~687 | tier_1_annotation | Word-level quality from transcription |
| SIG-G4-5 | handwriting_content_cls | Yes | ~687 | tier_1_annotation | Text transcriptions available |
| SIG-G2-1 | script_cls | Yes | ~687 | tier_0_exact | 100% Latin (English) |

## 9. Known Limitations

- **English only**: No multilingual coverage
- **Small dataset**: 687 images (useful for calibration, not primary training)
- **Digital capture**: Not representative of scanned or printed documents

## 10. Local Storage

| Item | Path |
|------|------|
| **Train images** | `/mnt/e/image_detection/01_base_data/handwriting/gnhk/paper/train/` |
| **Test images** | `/mnt/e/image_detection/01_base_data/handwriting/gnhk/paper/test/` |
| **Paper format (alt)** | `/mnt/e/image_detection/01_base_data/handwriting/gnhk/paper_format/` |
