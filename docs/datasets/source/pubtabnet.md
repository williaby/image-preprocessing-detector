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

##### Layer 2 Audit Summary

> **Audit Date**: 2026-02-13/14 | **Auditor**: claude-opus-4-6 | **Methodology**: v2.3.0 | **Tier**: 1 (Standard)

###### 11.1 Quality Scorecard

| Dimension | Score | Weight | Notes |
|-----------|-------|--------|-------|
| **Field Coverage** | 93.2 | 0.25 | 15 fields, avg pass rate 93.2% |
| **Field Validity** | 96.4 | 0.25 | 27 fields validated; layout_detections at 1.8% (test split) |
| **Doc Completeness** | 100.0 | 0.15 | 11/11 template v1.4.0 sections populated |
| **Defect Rate** | 80.0 | 0.15 | 10 defects cataloged (20.0 penalty) |
| **Cross Source Agreement** | 60.0 | 0.10 | Limited by 2 enrichment sources |
| **VLM Accuracy** | 100.0 | 0.10 | 165 images inspected, 0 corrections needed |
| **Overall** | **90.4** | | **Grade A** |

###### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | HIGH | RESOLVED | Split field empty — populated from JSONL annotations |
| D02 | script_family | HIGH | RESOLVED | Empty — re-derived via get_script_family(Latn) |
| D03 | layout_detections | HIGH | RESOLVED | Empty — integrated from extracted COCO layout batches |
| D04 | text_has_content | HIGH | RESOLVED | Empty — integrated from extracted OCR batches |
| D05 | orientation_class | MEDIUM | RESOLVED | Empty — set to 0 (born-digital, no rotation) |
| D06 | image_properties | MEDIUM | RESOLVED | color_mode empty — set to RGB |
| D07 | handwriting_present | MEDIUM | RESOLVED | Empty — set to false (born-digital) |
| D08 | text_direction | LOW | RESOLVED | v2.3.0 field — set to ltr |
| D09 | text_directions_present | LOW | RESOLVED | v2.3.0 field — set to ["ltr"] |
| D10 | content_flags | LOW | RESOLVED | Only has_table populated — added has_formula/figure/handwriting/code |

###### 11.3 VLM Inspection Summary

| Track | Images | Method | Finding |
|-------|--------|--------|---------|
| A (Content flags) | 40 | Individual reads | 0 FP, all flags correct |
| B (Batch classification) | 105 | 7 contact sheets | 100% born-digital, Latin, English, upright |
| C (Passing validation) | 20 | Individual reads | 100% accuracy (160/160 field checks) |

**Adaptive expansion**: Not triggered (FP rate = 0%)

###### 11.4 Cross-Dataset Findings

- **KI-008** (script_family directionality): Applicable, resolved by re-deriving from iso15924_script
- **KI-009** (language claims unreliable): Applicable but low impact — VLM confirms English-dominant

**Audit artifacts**: `scripts/audit/results/pubtabnet/`

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 (PRE-INTEGRATION) | **Samples**: 519,030 | **Avg Min Confidence**: 0.000
>
> **Note**: This section reflects pre-integration state. Post-integration (v2, schema 2.3.0),
> 93.2% of prescreening fields pass. Re-materialize with:
> `uv run python3 scripts/materialize_reliability_summary.py --datasets pubtabnet --update-docs --force`

**Composite Category Distribution** (pre-integration, to be updated):

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 519,030 | 100.0% |

**Top Bottleneck Fields** (pre-integration, to be updated):

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
