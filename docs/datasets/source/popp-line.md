---
canonical_name: popp-line
display_name: POPP-line (French Census Handwriting)
source_url: https://huggingface.co/datasets/Teklia/POPP-line
license: CC-BY-4.0
total_images: 4794
format: Arrow/Parquet (images + text labels)
capture_method: scanner
domain: GOV
status: training-ready
documentation_status: complete
---

# POPP-line (French Census Handwriting)

## 1. Overview

POPP-line contains 4,794 line-level handwritten text images from French census
records (19th-20th century). Each line image has a French text transcription.
Part of the POPP (Population, Occupation, Professional data from the Past)
project for historical demography. Valuable for mixed typed+handwritten content
detection and French handwriting recognition.

## 2. Source & Access

| Field | Value |
|-------|-------|
| **Publisher** | Teklia / POPP Project |
| **URL** | <https://huggingface.co/datasets/Teklia/POPP-line> |
| **Format** | Apache Arrow (HuggingFace datasets, image + text columns) |
| **License** | CC-BY-4.0 |
| **Download Size** | ~298 MB |
| **Citation** | Constum et al., "POPP: A Framework for Population Registry Records", 2022 |

## 3. Dataset Composition

| Metric | Value |
|--------|-------|
| **Total Images** | 4,794 |
| **Train** | 3,835 |
| **Validation** | 480 |
| **Test** | 479 |
| **Image Type** | Line-level crops from census forms |
| **Color Mode** | RGB (PNG) |

## 4. Label Schema

Each record contains:

- `image`: PIL Image (line crop from census page)
- `text`: French text transcription of the handwritten line

Text format examples:

- `"Joly Ernest 88 Indre M par Employe Roblot!18377"`
- `"Vallet Etienne 1900 P M ch o cheminot"`
- `"d° Jeannine 17 P f"`

Content includes names, ages, locations, occupations, and abbreviations typical
of French census enumeration.

## 5. Language & Script Coverage

| Script | ISO 15924 | Count | Notes |
|--------|-----------|-------|-------|
| Latin | Latn | 4,794 | French handwriting |

**Language**: French (fr)

## 6. IQA Profile

| Degradation | Prevalence | Notes |
|-------------|-----------|-------|
| Ink variation | High | Historical handwriting instruments |
| Low contrast | Medium | Aged paper |
| Skew | Low | Line-level crops well-aligned |

## 7. Training Relevance

| Head | Applicable | Reason |
|------|-----------|--------|
| Handwriting Detection | **Primary** | 100% handwritten census lines |
| Script Detection | Secondary | French Latin only |
| Legibility | Partial | Variable historical quality |
| IQA | No | Line-level crops |

## 8. SigLIP 2 Head Coverage

| SIG ID | Head | Applicable | Count | Tier | Notes |
|--------|------|-----------|-------|------|-------|
| SIG-G4-1 | handwriting_presence_cls | Yes | ~4,794 | tier_0_exact | 100% handwritten |
| SIG-G4-3 | handwriting_content_cls | Yes | ~4,794 | tier_1_annotation | Census content classification |
| SIG-G2-1 | script_cls | Yes | ~4,794 | tier_0_exact | 100% Latin (French) |

## 9. Known Limitations

- **Line-level only**: Individual text lines, not full pages
- **French only**: No multilingual coverage
- **Historical period**: 19th-20th century census records only
- **No spatial layout**: Text transcriptions only (no bounding boxes)

## 10. Local Storage

| Item | Path |
|------|------|
| **Arrow cache** | `/mnt/e/image_detection/01_base_data/forms/popp-datasets/hf_cache/` |
| **Extracted images** | `/mnt/e/image_detection/01_base_data/forms/popp-datasets/extracted_images/` |
| **Layer 1 metadata** | `/mnt/e/image_detection/metadata_registry/json/popp-line_metadata.json` |
