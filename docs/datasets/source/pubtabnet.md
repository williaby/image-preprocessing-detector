---
dataset_id: pubtabnet
version: "2.0.0"
license: CDLA-Sharing-1.0
commercial_use: true
iqa_profiles:
  - compression_sensitive
  - blur_sensitive
baseline_quality: 9.0
training_suitable: true
benchmark_suitable: true
documentation_status: complete
template_version: "1.4.0"
---

#### PubTabNet

> **Quick Stats**: 519,030 images | Born-digital | Scientific tables | Compression-sensitive
>
> **License**: CDLA-Sharing-1.0 | **Commercial Use**: Yes (PMC Open Access)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PubTabNet: Image-based Table Recognition Dataset |
| **Version** | 2.0.0 (with bounding boxes) |
| **Release Date** | 2019 (v1), July 2020 (v2) |
| **Maintainer** | IBM Research AI |
| **Paper** | [Image-based table recognition: data, model, and evaluation (ECCV 2020)](https://arxiv.org/abs/1911.10683) |
| **Repository** | [GitHub: ibm-aur-nlp/PubTabNet](https://github.com/ibm-aur-nlp/PubTabNet) |
| **HuggingFace** | [ajimeno/PubTabNet](https://huggingface.co/datasets/ajimeno/PubTabNet) |
| **License** | CDLA-Sharing-1.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/pubtabnet/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Table region images extracted from PDFs |
| **Annotations** | JSONL | Single file (PubTabNet_2.0.0.jsonl) with HTML structure and cell bboxes |
| **Supplementary** | MD / TXT | README, LICENSE files in GitHub repo |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `pubtabnet/train/` | `PubTabNet_2.0.0.jsonl` (filtered by split field) | 500,777 | ✅ |
| **Validation** | `pubtabnet/val/` | `PubTabNet_2.0.0.jsonl` (filtered by split field) | 9,115 | ✅ |
| **Test** | `pubtabnet/test/` | `PubTabNet_2.0.0.jsonl` (filtered by split field) | 9,138 | ✅ |

**Split Organization Pattern**: `by_folder` + `single_jsonl_with_split_field`

> **Notes**:
>
> - All annotations are in a single JSONL file (4.1 GB)
> - Split information is in each JSONL entry's "split" field
> - Images are organized in train/val/test folders

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | Custom JSON | Cell-level | Cell bounding boxes in [x1, y1, x2, y2] format |
| **HTML Structure** | Custom JSON | Table-level | HTML tokens representing table structure (<thead>, <tr>, <td>, etc.) |
| **Text Transcriptions** | JSON tokens | Cell-level | Cell text as array of tokens |
| **Split Information** | JSON field | Image-level | Dataset split (train/val/test) |

> **Note**: No quality scores, reading order, or page-level layout provided.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README.md (GitHub) | Version, license, citation, download links |
| **Image-level** | JSONL filename field | Image filename for lookup |
| **Annotation-level** | JSONL split field | Dataset split assignment |

###### 2.5 Annotation Schema Details

> **Format**: JSONL (one JSON object per line)

```json
{
  "filename": "PMC1234567_table_0.png",
  "split": "train",
  "html": {
    "structure": {
      "tokens": ["<thead>", "<tr>", "<td>", "</td>", "<td>", "</td>", "</tr>", "</thead>"]
    },
    "cells": [
      {
        "tokens": ["Age", "Group"],
        "bbox": [10, 10, 50, 20]
      },
      {
        "tokens": ["18-25"],
        "bbox": [60, 10, 90, 20]
      }
    ]
  }
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | string | Yes | Links to image file |
| `split` | string | Yes | "train", "val", or "test" |
| `html.structure.tokens` | array | Yes | HTML tag tokens |
| `html.cells` | array | Yes | Cell annotations |
| `html.cells[].tokens` | array | Yes | Cell text as tokens |
| `html.cells[].bbox` | array | Yes | [x1, y1, x2, y2] format |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Cell bboxes | `layout_detections` | **HIGH** | Need to map to COCO format [x,y,w,h] |
| ✅ Cell text | `text_content.full_text` | **HIGH** | Concatenate cell tokens |
| ✅ HTML structure | `raw_labels.table_html` | MEDIUM | Currently stored as string |
| ✅ Split info | `provenance.split` | HIGH | Already extracted |
| ⚠️ Table hierarchy | `layout_detections.hierarchy` | LOW | Can infer from HTML tokens |
| ❌ Reading order | - | LOW | Not provided |
| ❌ Quality scores | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Automatic Extraction |
| **Provenance Tier** | Tier 0 (Exact - programmatic extraction from PDF/XML alignment) |
| **Quality Assurance** | Automatic PDF/XML alignment with verification |
| **GT Label Coverage** | 100% (all 568K table images with HTML structure labels) |

##### File Format & Storage

| Property | Value |
|----------|-------|
| **Image format** | PNG (lossless) |
| **Annotation format** | JSONL (single 4.1 GB file) |
| **Image dimensions** | Variable (200-800px width, table crops) |
| **Color depth** | RGB 24-bit |
| **Typical file size** | 5-50 KB per image |
| **Total storage** | ~15 GB (images + annotations) |
| **Compression** | None (lossless PNG) |

##### Dataset Statistics

519,030 total images across 3 splits from PubMed Central scientific table extraction.

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 500,777 | 500,777 | 100% | ✅ Complete |
| **Validation** | 9,115 | 9,115 | 100% | ✅ Complete |
| **Test** | 9,138 | 9,138 | 100% | ✅ Complete |
| **Total** | 519,030 | 519,030 | 100% | ✅ All splits |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: All splits are fully covered in Layer 2 metadata. Split information is extracted
> from the "split" field in the JSONL annotations.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 519,030 |
| **Training Split** | 500,777 (96.5%) |
| **Validation Split** | 9,115 (1.8%) |
| **Test Split** | 9,138 (1.8%) |
| **Image Width Range** | 64 - 1,220 pixels |
| **File Format** | PNG |
| **Annotation Format** | JSONL (HTML structure + cell bboxes) |
| **Download Size** | ~5 GB (Parquet) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Scientific publications |
| **Source** | PubMed Central Open Access Subset |
| **Language** | English (scientific) |
| **Table Complexity** | Simple to complex multi-row/column spans |
| **Annotation Method** | Automatic (PDF/XML matching) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (PDF extraction) |
| **Baseline Quality** | Clean, publication-quality |
| **Blur Sensitivity** | **HIGH** - Small subscripts/superscripts extremely fragile |
| **Noise Sensitivity** | LOW - High-quality source material |
| **Skew Sensitivity** | LOW - Born-digital, no rotation artifacts |
| **Compression Sensitivity** | **HIGH** - Mathematical notation destroyed by JPEG |
| **Key Challenge** | Variable font sizes (8pt-14pt), dense notation |

##### Benchmark Performance

| Metric | Description |
|--------|-------------|
| **TEDS** | Tree-Edit-Distance-based Similarity - primary evaluation metric |
| **EDD Model** | Encoder-Dual-Decoder achieves **+9.7% TEDS** over prior state-of-the-art |
| **Competition** | ICDAR 2021 Scientific Literature Parsing benchmark dataset |

*Note: TEDS handles multi-hop cell misalignment and OCR errors better than prior metrics*

##### Training Value

- **Strengths**: Largest table dataset, scientific domain coverage, cell-level bboxes (v2.0+)
- **Weaknesses**: Limited to scientific domain, born-digital only
- **Unique Features**: HTML structure representation, TEDS evaluation metric, ICDAR competition standard
- **Benchmark Suitability**: **HIGH** - ICDAR 2021 competition standard

##### Project Usage

- **Path**: `01_base_data/tables/pubtabnet/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Scientific table IQA training, structure recognition baseline
- **Parser**: [`parse_pubtabnet_labels`](../scripts/annotate_base_metadata.py#L1714) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/tables/pubtabnet/` | ✅ Available | 519,030 PNG files |
| **Text/GT** | Native annotations | ✅ Available | JSONL: Cell-level text as token arrays (`html.cells[].tokens`) |
| **Text/GT Extracted** | `metadata_registry/extracted/pubtabnet/` | ✅ Converted | GT cell text → page text via `convert_pubtabnet_to_extracted.py` (509K images) |
| **Layout/GT Extracted** | `metadata_registry/extracted/pubtabnet/` | ✅ Converted | Cell bboxes → COCO format, schema: `pubtabnet-gt` |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ Not extracted - Data not yet processed into this format
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 519,030 |
| **File Format** | PNG (100%) |
| **Dimensions** | 161-697 × 44-665 px (avg: 450 × 209) |
| **Avg File Size** | 21 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Tables: ✅ 100% |

##### Known Issues & Limitations

| ID | Issue | Severity | Impact | Mitigation |
|----|-------|----------|--------|------------|
| 1 | Test split (9,138) lacks extracted layout annotations and OCR text | LOW | 1.76% of dataset missing `layout_detections` and `text_has_content` | Expected — test split not in extracted layout batches; content flags still populated via defaults |
| 2 | Language enrichment covers only 0.19% (1,000/519,030) | LOW | Remaining samples use default `en`/`Latn` | Born-digital PubMed Central — English-dominant assumption is well-justified |
| 3 | Layout stored as summary format (count + reference) not full bboxes | INFO | `layout_bbox_valid` prescreening check fails at 98.24% | Deliberate optimization — full COCO bboxes in `metadata_registry/extracted/pubtabnet/layout_batch_*.json` |
| 4 | KI-008 (script_family directionality) applicable | LOW | Script family re-derived via `get_script_family()` | Resolved in integration script |
| 5 | KI-009 (language claims unreliable) applicable | LOW | Doc says "English" but 10+ languages detected at low confidence | VLM confirms ~95% English; multilingual tables still Latin script |

##### Representative Samples

Contact sheets generated for VLM inspection provide representative views:

- `tmp_cleanup/pubtabnet_contact_sheets/contact_sheet_001.jpg` through `contact_sheet_007.jpg`
- 105 images across 7 sheets (5x3 grid, 300x120px thumbnails)
- Manifest: `tmp_cleanup/pubtabnet_contact_sheets/manifest.json`

**Typical characteristics**: Clean born-digital tables, white background, variable width (64-1220px), short height (44-665px), mixed font sizes (8-14pt), occasional colored cell backgrounds, scientific notation in values.

##### Dataset-Specific Notes

###### 10.1 HTML Structure Representation

PubTabNet uniquely represents table structure as HTML token sequences:

- Structure tokens: `<thead>`, `<tbody>`, `<tr>`, `<td>`, `<td colspan="N">`, `<td rowspan="N">`
- Cell text stored as token arrays within `html.cells[].tokens`
- This HTML representation enables the TEDS (Tree-Edit-Distance-based Similarity) metric

###### 10.2 Cell Bounding Box Format

- Source format: `[x1, y1, x2, y2]` (top-left, bottom-right)
- Converted to COCO format `[x, y, w, h]` in `metadata_registry/extracted/pubtabnet/`
- Conversion script: `scripts/convert_pubtabnet_to_extracted.py`
- 509,892 images have extracted cell bboxes (train + val splits)

###### 10.3 Text Extraction

- GT cell text extracted via `scripts/pubtabnet_text_extractor.py`
- Concatenates cell tokens with space separator
- OCR batch files in `metadata_registry/extracted/pubtabnet/ocr_batch_*.json`

###### 10.4 Scale Considerations

At 519K images, PubTabNet is the largest dataset in the audit pipeline. Processing requires:

- **Batch-oriented I/O** over WSL network mount (sequential file access, not random)
- **Streaming contact sheet generation** (one sheet at a time, gc.collect() between)
- **Summary format** for layout detections (count + reference instead of 25M+ cell annotations)
- **Pre-computed text statistics** during OCR loading (discard raw text to save ~500MB)

##### References

```bibtex
@inproceedings{zhong2020image,
  title={Image-based table recognition: data, model, and evaluation},
  author={Zhong, Xu and ShafieiBavani, Elaheh and Jimeno Yepes, Antonio},
  booktitle={ECCV},
  year={2020}
}
```

##### License & Access

| Property | Value |
|----------|-------|
| **License** | CDLA-Sharing-1.0 (Community Data License Agreement) |
| **Commercial use** | Yes |
| **Source** | PubMed Central Open Access Subset |
| **Download** | [GitHub: ibm-aur-nlp/PubTabNet](https://github.com/ibm-aur-nlp/PubTabNet) |
| **Registration** | None required |
| **Citation** | Zhong et al., ECCV 2020 |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-15 | **Grade**: B (90.1/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 91.2 | 15% |  |
| Field Validity | 96.4 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 80.0 | 10% |  |
| Cross-Source Agreement | 60.0 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **90.1** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 10 defects (10 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | CRITICAL | OPEN |  |
| D02 | script_family | CRITICAL | OPEN |  |
| D03 | layout_detections | HIGH | OPEN |  |
| D04 | text_has_content | HIGH | OPEN |  |
| D05 | orientation_class | MEDIUM | OPEN |  |
| D06 | image_properties_color_mode | MEDIUM | OPEN |  |
| D07 | handwriting_present | MEDIUM | OPEN |  |
| D08 | text_direction | LOW | OPEN |  |
| D09 | text_directions_present | LOW | OPEN |  |
| D10 | content_flags_confidence | LOW | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 100.0%

###### 11.4 Cross-Dataset Findings

- **KI-008**: OPEN --

**Audit Artifacts**: [scripts/audit/results/pubtabnet/](../../scripts/audit/results/pubtabnet/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 519,030 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 519,030 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 100.0% | 0.000 |

##### Processing Notes

- **Parser**: `pubtabnet` parser in `annotation/parsers/pubtabnet.py` extracts from single JSONL
- **Layout conversion**: `scripts/convert_pubtabnet_to_extracted.py` converts cell bboxes to COCO format
- **Text extraction**: `scripts/pubtabnet_text_extractor.py` concatenates cell tokens into full text
- **Integration**: `scripts/integrate_pubtabnet_enrichments.py` (v2, schema 2.3.0) merges all sources
- **Scale**: At 519K samples, all processing must be streaming/batched (no full-dataset in-memory load)
- **WSL mount**: Images on `/mnt/e/` require sequential access patterns due to WSL network mount latency

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-02-13 | Integration script v2 (schema 2.3.0, text_direction, script_family) |
| 1.0 | 2026-02-12 | Initial base metadata extraction and language enrichment |
| 0.1 | 2026-02-10 | Layout conversion and text extraction |

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | ~519K | Derived (all 0°) | Born-digital table crops, no rotation; provides UPRIGHT negatives only |
| MNV4-H2 | skew_reg | ➖ | ~519K | Derived (all ~0°) | Born-digital, no physical skew; near-zero regression negatives only |
| MNV4-H3 | resolution_quality_reg | ➖ | ~519K | Computed | Very small table crop images (avg 450×209px); limited utility — character heights may be below optimal range at small sizes |
| SIG-G1-1 | blur_score | ➖ | ~509K | Computed | Small table crops (64–1220px wide) with variable font sizes; blur assessment complicated by crop size variability — low utility |
| SIG-G1-2 | noise_score | ➖ | ~509K | Computed | Born-digital, no noise; provides zero-noise negatives but small image size limits representativeness |
| SIG-G1-3 | contrast_score | ➖ | ~509K | Computed | High contrast born-digital tables; useful only as high-contrast reference — limited domain breadth |
| SIG-G1-4 | skew_score | ➖ | ~519K | Derived (all ~0°) | Born-digital, no skew; zero-skew regression anchors only |
| SIG-G1-5 | compression_score | ➖ | ~509K | Computed | Lossless PNG; zero-compression baseline; very small crops have limited value as IQA training examples |
| SIG-G1-6 | overall_quality | ➖ | ~509K | Computed | High-quality table crops; narrow domain (scientific only) limits overall quality head diversity |
| SIG-G2-1 | script_cls | 🟡 | ~518K Latn | GT-derived | 99.97% Latin; trace CJK (0.02%), Devanagari (0.003%) — effectively single-script Latin contributor |
| SIG-G3-1 | orientation_cls (post) | ➖ | ~519K | Derived (all 0°) | All table crops upright; UPRIGHT class negatives only |
| SIG-G3-2 | skew_reg (post) | ➖ | ~519K | Derived (all ~0°) | No skew present; near-zero regression negatives only |
| SIG-G4-1 | handwriting_presence_cls | ➖ | ~519K | GT-derived | 100% printed born-digital; provides large NONE-class negative pool for handwriting presence |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No handwriting content; not applicable |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No handwriting content; not applicable |
| SIG-G4-4 | presence_reg | ➖ | ~519K | GT-derived | All samples score 0.0 presence; large zero-handwriting regression anchor pool |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No handwriting content; not applicable |
| SIG-G5-1 | capture_method_cls | ✅ | ~519K | GT label | 100% born_digital (confirmed from stats); very large clean single-class pool for BORN_DIGITAL |
| SIG-G5-2 | shadow_reg | ➖ | ~519K | Computed | No shadows in born-digital renders; large zero-shadow regression anchor pool |
| SIG-G5-3 | warping_reg | ➖ | ~519K | Computed | No warping in born-digital renders; large zero-warping regression anchor pool |
| SIG-G5-4 | code_cls | ➖ | ~519K | Derived | Table crops only — no surrounding paper context captured; code blocks excluded from table region images |
| SIG-G5-5 | resolution_quality_reg | ➖ | ~509K | Computed | Very small crop images (avg 450×209px); many crops fall below optimal character-height range — limited utility for resolution quality training |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | 99.97% Latin; trace CJK and Devanagari — effectively mono-script, not useful for multi-script training |
| 2 | Capture method | 🟡 | 100% born_digital; provides a very large BORN_DIGITAL pool but no scanner/camera representation |
| 3 | Document domain | ❌ | 100% SCI (scientific/PubMed Central); no domain diversity — single-domain bias |
| 4 | Layout type | ❌ | Table crops only; no page-level layout variation — all images are isolated table regions |
| 5 | Text density | 🟡 | Variable cell density (sparse to dense tables); limited range as all content is tabular |
| 6 | Degradation types | ❌ | No degradation present; all born-digital clean PNG renders |
| 7 | Resolution/DPI range | ❌ | Variable crop sizes (64–1220px width) but all born-digital at PDF render resolution; no DPI tier variation |
| 8 | Document age | ❌ | Contemporary scientific publications only; no historical or aged documents |
| 9 | Text scope | ❌ | Table-region crops only, not full-page scope; text scope is sub-page/element level |
| 10 | Content flags | 🟡 | has_table 100%; single content flag — no figures, formulas, or code represented at page level |
| 11 | Binarization status | ❌ | All RGB PNG; no binarized versions available |
| 12 | Artifact types | ❌ | No artifacts; clean born-digital source — zero artifact variety |
| 13 | Color mode | 🟡 | RGB 100%; occasional colored cell backgrounds but no grayscale or binarized variants |
| 14 | Font variety | 🟡 | Scientific paper fonts (8–14pt mixed sizes, subscripts, superscripts, math notation); limited to academic typography |

### 13.3 Corpus Role & Constraints

PubTabNet's primary training value is as a **large-scale BORN_DIGITAL negative pool** for SIG-G5-1 capture_method_cls (~519K labels) and as a **large handwriting-absence pool** for SIG-G4-1/G4-4. Its contribution to IQA heads (G1 group) and resolution quality (MNV4-H3, SIG-G5-5) is limited by the small table-crop image size and single-domain scientific bias. License is CDLA-Sharing-1.0 (share-alike commercial use permitted). No OOD script exclusions apply — the trace non-Latin samples (<0.04%) are negligible.
