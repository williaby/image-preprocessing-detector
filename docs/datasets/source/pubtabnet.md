#### PubTabNet

> **Quick Stats**: 568,000+ images | Born-digital | Scientific tables | Compression-sensitive
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

##### Dataset Statistics

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

##### References

```bibtex
@inproceedings{zhong2020image,
  title={Image-based table recognition: data, model, and evaluation},
  author={Zhong, Xu and ShafieiBavani, Elaheh and Jimeno Yepes, Antonio},
  booktitle={ECCV},
  year={2020}
}
```

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 519,030 | **Avg Min Confidence**: 0.000

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
