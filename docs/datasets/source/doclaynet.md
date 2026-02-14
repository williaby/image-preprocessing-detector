---
dataset_id: doclaynet
version: "1.0"
license: CDLA-Permissive-1.0
commercial_use: true
iqa_profiles:
  - blur_sensitive
baseline_quality: 9.5
training_suitable: true
benchmark_suitable: true
documentation_status: complete
template_version: "1.4.0"
---

#### DocLayNet

> **Quick Stats**: 81,471 pages | 6 domains | 11 layout classes | Expert-annotated | Born-digital
>
> **License**: CDLA-Permissive-1.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | IBM Research (DS4SD) |
| **Paper** | [DocLayNet (KDD 2022)](https://arxiv.org/abs/2206.01062) |
| **Repository** | [GitHub: DS4SD/DocLayNet](https://github.com/DS4SD/DocLayNet) |
| **HuggingFace** | [ds4sd/DocLayNet](https://huggingface.co/datasets/ds4sd/DocLayNet) |
| **License** | CDLA-Permissive-1.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/doclaynet/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | 1025x1025px page renders from original PDFs |
| **Per-doc GT JSON** | JSON | 81,471 files with word-level `cells[]` (text, bbox, font metadata) + `metadata` (doc_category, page_no, collection) |
| **COCO GT** | JSON | 3 files (train.json, val.json, test.json) with 11-class layout annotations in COCO format |
| **PDF originals** | PDF | Original source documents (6 document categories) |
| **Extras** | JSON | Per-doc JSON with font metadata, page numbering, collection info |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `doclaynet/PNG/` | `ground_truth/coco/train.json` | 69,374 | ✅ |
| **Validation** | `doclaynet/PNG/` | `ground_truth/coco/val.json` | 6,489 | ✅ |
| **Test** | `doclaynet/PNG/` | `ground_truth/coco/test.json` | 4,999 | ✅ |
| **Unknown** | `doclaynet/PNG/` | No COCO annotations | 609 | ⚠️ |

**Split Organization Pattern**: `flat_directory` + `coco_gt_membership`

> **Notes**:
>
> - All images are in a single flat directory (PNG/) -- split determined by COCO GT file membership
> - 609 pages (0.75%) have GT JSON but no COCO annotations, assigned `split=unknown`
> - 1 corrupted GT JSON file (empty file) has no extractable metadata

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Layout Bounding Boxes** | COCO JSON | Element-level | 11-class bounding boxes + polygons |
| **Layout Polygons** | COCO JSON | Element-level | Polygon segmentation for each element |
| **Word-level Text** | Per-doc JSON | Word-level | `cells[].text` with bbox and font metadata |
| **Document Category** | Per-doc JSON | Page-level | `metadata.doc_category` (6 categories) |
| **Font Metadata** | Per-doc JSON | Word-level | `cells[].font` (name, size, color) |
| **Page Metadata** | Per-doc JSON | Page-level | `metadata.page_no`, `metadata.num_pages`, `metadata.collection` |

> **Note**: Extremely rich GT -- word-level text + font metadata + 11-class layout + document category. Enables programmatic derivation of domain, language, script, content flags without VLM.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README | Version, license, citation, download links |
| **Page-level** | Per-doc JSON `metadata` | doc_category, page_no, num_pages, collection |
| **Word-level** | Per-doc JSON `cells[]` | text, bbox, font (name, size, color) |
| **Split-level** | COCO GT filenames | train/val/test membership |
| **Layout-level** | COCO GT annotations | 11 category IDs with bboxes + polygons |

###### 2.5 Annotation Schema Details

> **Format**: Per-document JSON (81,471 files)

```json
{
  "metadata": {
    "doc_category": "financial_reports",
    "collection": "...",
    "page_no": 1,
    "num_pages": 12
  },
  "cells": [
    {
      "bbox": [97.4, 70.4, 18.9, 9.5],
      "text": "The",
      "font": {"color": [0, 0, 0], "name": "Arial", "size": 10.0}
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `metadata.doc_category` | string | Yes | Maps to domain_level1 |
| `metadata.page_no` | int | Yes | Page number in source document |
| `cells` | array | Yes | Word-level annotations |
| `cells[].text` | string | Yes | Word text content |
| `cells[].bbox` | array | Yes | [x, y, w, h] format |
| `cells[].font` | object | Yes | Font metadata (name, size, color) |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ COCO layout annotations | `layout_detections` | **HIGH** | 11 classes, expert-annotated |
| ✅ Word-level text | `text_content.full_text` | **HIGH** | Concatenate cells[].text |
| ✅ Document category | `domain_level1` | **HIGH** | 6 categories -> FIN/SCI/LEG/ADM/TEC |
| ✅ Font metadata | `raw_labels.font_info` | MEDIUM | Name, size, color per word |
| ✅ Split membership | `provenance.split` | HIGH | From COCO GT file membership |
| ✅ Page metadata | `provenance.page_no` | MEDIUM | Page number in source document |
| ⚠️ Language | `iso639_language` | HIGH | Via langdetect on cells text |
| ❌ Quality scores | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### File Format & Storage

| Property | Value |
|----------|-------|
| **Image format** | PNG (lossless) |
| **Annotation format** | JSON (per-doc) + COCO JSON (layout) |
| **Image dimensions** | 1025 x 1025 pixels (fixed, resized from original) |
| **Color depth** | RGB 24-bit |
| **Typical file size** | ~412 KB per image |
| **Total storage** | ~28 GiB (core) + 7.5 GiB (extras) |
| **Compression** | None (lossless PNG) |

##### Dataset Statistics

81,471 page images from 6 professional document categories, with expert human annotations.

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 69,374 | 69,374 | 100% | ✅ Complete |
| **Validation** | 6,489 | 6,489 | 100% | ✅ Complete |
| **Test** | 4,999 | 4,999 | 100% | ✅ Complete |
| **Unknown** | 609 | 609 | 100% | ⚠️ No COCO annotations |
| **Total** | 81,471 | 81,471 | 100% | ✅ All splits |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing or incomplete annotations

> **Note**: 609 pages have GT JSON (word-level text) but no COCO layout annotations. These are pages in the original PDF collection that were not annotated for layout.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 81,471 |
| **Training Split** | 69,374 (85.2%) |
| **Validation Split** | 6,489 (8.0%) |
| **Test Split** | 4,999 (6.1%) |
| **Unknown Split** | 609 (0.7%) |
| **Image Dimensions** | 1025 x 1025 px (fixed) |
| **File Format** | PNG |
| **Annotation Format** | COCO + per-doc JSON |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain Distribution** | FIN 32.2%, TEC 29.4%, SCI 17.4%, LEG 15.6%, ADM 5.4% |
| **Language Distribution** | en 93.6%, de 2.3%, ru 0.6%, fr 0.6%, it 0.4%, ja 0.4%, others <0.3% |
| **Script Distribution** | Latin 98.5%, CJK 0.7%, Cyrillic 0.6%, Greek <0.1%, Arabic <0.1% |
| **Content Flags** | has_table 22.4%, has_figure 25.2%, has_formula 6.9% |
| **Text Direction** | LTR dominant, rare RTL (Arabic/Hebrew content) |
| **Annotation Method** | Expert human annotators (double/triple annotated subset) |

###### 5.1 Document Categories

| Category | Domain Code | Count | Percentage | Description |
|----------|-------------|-------|------------|-------------|
| Financial Reports | FIN | ~26,200 | 32.2% | Annual reports, earnings statements |
| Manuals + Patents | TEC | ~23,900 | 29.4% | Technical documentation, patent filings |
| Scientific Articles | SCI | ~14,200 | 17.4% | Research papers, journals |
| Laws & Regulations | LEG | ~12,700 | 15.6% | Legal documents, statutes |
| Government Tenders | ADM | ~4,400 | 5.4% | Procurement/administrative documents |

###### 5.2 Language Detection Method

Language was detected using `langdetect` on concatenated `cells[].text` per page from GT JSON files:

- **Seed**: `DetectorFactory.seed = 42` for reproducibility
- **Minimum text**: 20 characters required; shorter texts assigned `und` (undetermined)
- **Results**: 161 samples (0.20%) below threshold, assigned `und`
- **Confidence**: Median ~0.95 for non-`und` samples

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (professionally typeset) |
| **Annotation Quality** | **HIGH** - Expert human annotation, redundant labeling |
| **Blur Sensitivity** | MEDIUM - Variable element sizes, fixed 1025x1025 resize |
| **Layout Complexity** | **HIGH** - Multi-column, mixed content types |
| **Skew Sensitivity** | LOW - Born-digital, no rotation |
| **Compression Sensitivity** | LOW - Lossless PNG storage |
| **Key Challenge** | Complex mixed layouts, variable density regions |

##### Benchmark Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Inter-Annotator Gap** | ~10% | Models fall behind human agreement by ~10% mAP |
| **vs. PubLayNet** | More robust | DocLayNet-trained models generalize better |
| **vs. DocBank** | More robust | Better on challenging, diverse layouts |
| **KDD 2022** | Benchmark standard | Preferred for general-purpose document-layout analysis |

*DocLayNet-trained models are the "preferred choice for general-purpose document-layout analysis"*

##### Layout Classes (11)

1. **Caption** - Figure/table captions
2. **Footnote** - Page footnotes
3. **Formula** - Mathematical equations
4. **List-item** - Bulleted/numbered items
5. **Page-footer** - Page numbers, footers
6. **Page-header** - Headers, titles
7. **Picture** - Images, diagrams
8. **Section-header** - Section titles
9. **Table** - Tabular content
10. **Text** - Body text paragraphs
11. **Title** - Document titles

##### Annotation Quality

- **Double/Triple Annotated**: Subset of pages for inter-annotator agreement measurement
- **Crowdsourced**: By well-trained expert annotators
- **Format**: COCO-style with bounding boxes + polygon segmentation
- **Total Layout Annotations**: ~3.5M annotations across 80,862 images (in COCO GT)

##### Training Value

- **Strengths**: Expert annotations, diverse domains (6 categories), industry-standard COCO format, word-level text with font metadata
- **Weaknesses**: Born-digital only, resized images (1025x1025) may lose detail
- **Unique Features**: Polygon segmentation, font metadata in JSON extras, redundant annotation subset, 6 explicit document categories
- **Benchmark Suitability**: **HIGH** - KDD 2022 benchmark for layout detection

##### Project Usage

- **Path**: `01_base_data/documents/doclaynet/`
- **Phase(s)**: Phase 2 (Layout-lite), Phase 7 training
- **Purpose**: Layout-aware IQA training, element detection
- **Parser**: [`parse_doclaynet_labels`](../scripts/annotate_base_metadata.py#L1296) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/documents/doclaynet/` | ✅ Available | 81,471 PNG files |
| **GT JSON** | `ground_truth/json/` | ✅ Available | 81,471 per-doc files with cells[].text + font metadata |
| **COCO GT** | `ground_truth/coco/` | ✅ Available | train.json (69,374), val.json (6,489), test.json (4,999) |
| **Text/GT Extracted** | `metadata_registry/extracted/doclaynet/` | ✅ Converted | GT word text -> page text via `convert_doclaynet_to_extracted.py` |
| **Layout/GT Extracted** | `metadata_registry/extracted/doclaynet/` | ✅ Converted | 11 DocLayNet categories from COCO GT, schema: `doclaynet-gt` |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ Not extracted - Data not yet processed into this format

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 81,471 |
| **File Format** | PNG (100%) |
| **Dimensions** | 1025 x 1025 px (fixed) |
| **Avg File Size** | 412 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | FIN 32.2%, TEC 29.4%, SCI 17.4%, LEG 15.6%, ADM 5.4% |
| **Language** | en 93.6%, de 2.3%, + 20 other languages |
| **Script Family** | Latin 98.5%, CJK 0.7%, Cyrillic 0.6% |
| **Content Flags** | Tables 22.4%, Figures 25.2%, Formulas 6.9% |
| **Text Direction** | LTR dominant, rare mixed LTR+RTL |
| **Orientation** | 0 degrees (born-digital, no rotation) |
| **Handwriting** | None (born-digital professional) |

##### Known Issues & Limitations

| ID | Issue | Severity | Impact | Mitigation |
|----|-------|----------|--------|------------|
| D01 | 609 pages (0.75%) without COCO annotations have `split=unknown` | LOW | Cannot assign to train/val/test | Keep as `unknown`; pages still have GT text and domain |
| D02 | 1 corrupted GT JSON file (empty) | LOW | 1 sample with fallback metadata | Negligible impact on 81K dataset |
| D03 | 161 samples (0.20%) with `iso639_language=und` | LOW | Insufficient text (<20 chars) for language detection | Mostly blank/near-blank pages |
| D04 | 614 samples (0.75%) with `text_has_content=false` | LOW | Pages with empty cells text | 1 corrupted GT + 613 pages with empty cell arrays |
| D05 | 12,368 samples (15.18%) missing layout detections | MEDIUM | No Docling layout for these pages | COCO GT content flags provide functional equivalent |
| D06 | Schema compliance 17.9% | MEDIUM | Docling layout format has structural issues | Compliance limited by Docling format, not data quality |
| D07 | KI-008 (script_family directionality) was applicable | LOW | Re-derived via `get_script_family()` | Resolved in integration |
| D08 | KI-009 (language claims unreliable) was applicable | LOW | Blanket "en" stub replaced by langdetect on GT text | Resolved in integration |

##### Representative Samples

Contact sheets generated for VLM inspection provide representative views:

- `tmp_cleanup/doclaynet_contact_sheets/track_a_tables.jpg` - 20 table/non-table examples
- `tmp_cleanup/doclaynet_contact_sheets/track_a_figures.jpg` - 15 figure examples
- `tmp_cleanup/doclaynet_contact_sheets/track_a_formulas.jpg` - 10 formula examples
- `tmp_cleanup/doclaynet_contact_sheets/track_b_non_english.jpg` - 25 non-English pages
- `tmp_cleanup/doclaynet_contact_sheets/track_c_passing.jpg` - 25 passing validation samples

**Typical characteristics**: Born-digital professional documents across 6 domain categories. Mixed layouts with tables, figures, formulas, multi-column text. Predominantly English (93.6%) with significant German (2.3%), Russian, French, Japanese, and other languages. Fixed 1025x1025px PNG with no rotation or handwriting.

##### Dataset-Specific Notes

###### 10.1 GT Exploitation Strategy

DocLayNet's rich per-document GT files enable programmatic derivation of metadata fields without VLM:

| Field | GT Source | Confidence | Method |
|-------|-----------|------------|--------|
| `domain_level1` | `metadata.doc_category` | 1.0 | Direct mapping (6 categories) |
| `iso639_language` | `cells[].text` | 0.95 | `langdetect` on concatenated cell text |
| `split` | COCO GT membership | 1.0 | Filename -> train/val/test.json lookup |
| `content_flags` | COCO GT categories | 1.0 | Category presence (Table/Picture/Formula) |
| `text_statistics` | `cells[].text` | 1.0 | Character/word/line counts from GT |
| `text_direction` | Unicode analysis of GT text | 0.95 | RTL character detection |

This approach is **reusable** for any dataset with rich ground truth annotations.

###### 10.2 Document Category to Domain Mapping

```python
DOC_CATEGORY_TO_DOMAIN = {
    "financial_reports": "FIN",
    "scientific_articles": "SCI",
    "laws_and_regulations": "LEG",
    "government_tenders": "ADM",
    "manuals": "TEC",
    "patents": "TEC",
}
```

###### 10.3 Scale Considerations

At 81K images, DocLayNet processing requires:

- **GT index extraction**: `ProcessPoolExecutor` with 4 workers, ~462s for 81K files (~176 files/sec)
- **Metadata integration**: Streaming write (112s for 1.65 GB output)
- **COCO GT loading**: Three large JSON files loaded sequentially, ~3.5M annotations total
- **Memory**: GT index (57 MB JSON) + metadata (1.65 GB) fits in memory on dev machine

###### 10.4 COCO GT Layout Annotations

- **Total annotations**: ~3.5M across 80,862 images
- **Not embedded** in Layer 2 metadata due to size (would add ~2 GB)
- **Content flags derived** from COCO GT category presence (functional equivalent at lower storage cost)
- **Docling layout** preserved for 69,103 samples with provenance tracking

##### References

```bibtex
@inproceedings{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation},
  author={Pfitzmann, Birgit and others},
  booktitle={KDD},
  year={2022},
  doi={10.1145/3534678.3539043}
}
```

##### License & Access

| Property | Value |
|----------|-------|
| **License** | CDLA-Permissive-1.0 (Community Data License Agreement) |
| **Commercial use** | Yes |
| **Source** | IBM Research DS4SD |
| **Download** | [GitHub: DS4SD/DocLayNet](https://github.com/DS4SD/DocLayNet) |
| **Registration** | None required |
| **Citation** | Pfitzmann et al., KDD 2022 |

##### Layer 2 Audit Summary

> **Audit Date**: 2026-02-13 | **Auditor**: claude-opus-4-6 | **Methodology**: v2.3.0 | **Tier**: 2 (Scale-adjusted)

###### 11.1 Quality Scorecard

| Dimension | Score | Weight | Notes |
|-----------|-------|--------|-------|
| **Field Coverage** | 98.9 | 0.25 | 15 fields, avg pass rate 98.9% |
| **Field Validity** | 97.0 | 0.25 | 27 fields validated |
| **Doc Completeness** | 100.0 | 0.15 | 11/11 template v1.4.0 sections populated |
| **Defect Rate** | 90.0 | 0.15 | 13 defects (12 resolved, 1 partial), 10.0 penalty |
| **Cross Source Agreement** | 84.4 | 0.10 | Multi-source comparison (GT + LLM + Docling) |
| **VLM Accuracy** | 97.9 | 0.10 | 95 images inspected, 97.9% accuracy |
| **Overall** | **95.7** | | **Grade A** |

###### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | HIGH | RESOLVED | Not derived from COCO GT -- built filename-to-split index |
| D02 | domain_level1 | HIGH | RESOLVED | 100% UNK -- mapped GT doc_category -> domain codes |
| D03 | script_family | HIGH | RESOLVED | KI-008: "ltr" -> re-derived via get_script_family() |
| D04 | iso639_language | MEDIUM | RESOLVED | Blanket "en" -> langdetect on GT cells text (22 languages) |
| D05 | layout_detections | HIGH | PARTIAL | 12,368 (15.2%) missing Docling layout; COCO GT content flags used |
| D06 | text_has_content | MEDIUM | RESOLVED | Empty -> populated from GT cells text |
| D07 | orientation_class | MEDIUM | RESOLVED | Missing -> set 0 (born-digital) |
| D08 | color_mode | LOW | RESOLVED | Missing -> derived from color_space (RGB) |
| D09 | handwriting_present | LOW | RESOLVED | Missing -> set false (born-digital) |
| D10 | text_direction | MEDIUM | RESOLVED | v2.3.0 field -> derived from script direction |
| D11 | text_directions_present | MEDIUM | RESOLVED | v2.3.0 field -> derived from GT text Unicode analysis |
| D12 | schema_version | LOW | RESOLVED | v2.1 -> v2.3.0 upgrade |
| D13 | content_flags | MEDIUM | RESOLVED | Docling soft labels -> COCO GT categories (confidence 1.0) |

###### 11.3 VLM Inspection Summary

| Track | Images | Method | Finding |
|-------|--------|--------|---------|
| A (Content flags) | 45 | Contact sheets (3 sheets) | 100% accuracy -- COCO GT content flags verified |
| B (Non-English language) | 25 | Contact sheet (1 sheet) | 92% accuracy -- 1 potential mismatch, 1 hard to verify |
| C (Passing validation) | 25 | Contact sheet (1 sheet) | 100% accuracy -- all domain/language/fields correct |
| **Overall** | **95** | **5 contact sheets** | **97.9% accuracy** |

**Key findings**:

- COCO GT-derived content flags achieve 100% visual accuracy (Track A)
- GT `doc_category` -> domain mapping is 100% accurate (Track C)
- Language detection via langdetect on GT text is 92% accurate, edge cases in rare languages
- Overall accuracy well above 95% target

###### 11.4 Cross-Dataset Findings

- **KI-007** (domain 100% UNK): Resolved -- GT `doc_category` provides ground-truth domain classification
- **KI-008** (script_family directionality): Resolved -- re-derived from `iso15924_script` via `get_script_family()`
- **KI-009** (blanket "en" language): Resolved -- langdetect on GT text reveals 22 languages
- **GT exploitation** documented as reusable pattern for datasets with rich ground truth

**Audit artifacts**: `scripts/audit/results/doclaynet/`

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 (PRE-INTEGRATION) | **Samples**: 81,471 | **Avg Min Confidence**: 0.255
>
> **Note**: This section reflects pre-integration state. Post-integration (v2, schema 2.3.0),
> 84.35% of prescreening fields pass. Re-materialize with:
> `uv run python3 scripts/materialize_reliability_summary.py --datasets doclaynet --update-docs --force`

**Composite Category Distribution** (pre-integration, to be updated):

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 81,471 | 100.0% |

**Top Bottleneck Fields** (pre-integration, to be updated):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain` | 84.8% | 0.300 |
| 2 | `has_table` | 15.2% | 0.848 |

##### Processing Notes

- **GT extraction**: `scripts/extract_doclaynet_gt_index.py` extracts domain, language, split, content flags, text stats from 81,471 GT JSON files
- **Integration**: `scripts/integrate_doclaynet_enrichments.py` (v2, schema 2.3.0) merges GT index + LLM enrichment + Docling layout
- **Layout standardization**: `scripts/standardize_layout_labels.py --dataset doclaynet` (all 941,123 detections already canonical)
- **Priority chain**: GT sources (confidence 1.0) > LLM enrichment (0.65) > defaults
- **Scale**: GT index extraction ~462s (176 files/sec), integration ~4s processing + ~113s write
- **WSL mount**: Images on `/mnt/e/` require sequential access patterns

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-02-13 | Integration script v2 (schema 2.3.0, GT exploitation, 13 defects resolved) |
| 1.0 | 2026-02-10 | Initial base metadata extraction, Docling layout, LLM enrichment |
| 0.1 | 2026-02-08 | Reliability summary materialized |
