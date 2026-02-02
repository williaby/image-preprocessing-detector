#### HierText

> **Quick Stats**: 11,639 images | 1.2M word annotations | Word-level handwriting + legibility labels
>
> **License**: CC-BY-SA-4.0 | **Commercial Use**: Yes (with attribution + ShareAlike)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | HierText: Hierarchical Text Detection and Recognition |
| **Version** | 1.0 |
| **Release Date** | March 2022 |
| **Maintainer** | Google Research |
| **Paper** | [HierText: Towards Rich Hierarchical Scene Text](https://arxiv.org/abs/2203.15143) |
| **Repository** | [google-research-datasets/hiertext](https://github.com/google-research-datasets/hiertext) |
| **License** | CC-BY-SA-4.0 |
| **Local Path** | `01_base_data/text_detection/hiertext/` |
| **GCS Path** | `gs://image_detection_b/01_base_data/text_detection/hiertext/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Natural scene images from Open Images Dataset |
| **Annotations** | JSONL | Hierarchical text annotations (paragraph → line → word) |
| **Metadata** | JSON | Embedded in annotation files (version, date) |
| **Supplementary** | MD | GitHub repository README, license file |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `hiertext/train/` | `hiertext/gt/train.jsonl` | 8,281 | ✅ |
| **Validation** | `hiertext/validation/` | `hiertext/gt/validation.jsonl` | 1,724 | ✅ |
| **Test** | `hiertext/test/` | `hiertext/gt/test.jsonl` | 1,634 | ✅ |

**Split Organization Pattern**: `by_folder`

> **Notes**:
>
> - JSONL extension is misleading - files contain single JSON object, not line-delimited JSON
> - Images downloaded from S3 bucket referenced in official repository
> - All splits fully annotated with hierarchical text regions

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Polygons** | Custom JSON | Word / Line / Paragraph | Arbitrary polygon vertices (not 4-point) |
| **Text Transcriptions** | JSON | Word / Line | Ground truth text content |
| **Handwriting Labels** | JSON (bool) | Word / Line | Binary handwriting detection flag |
| **Legibility Labels** | JSON (bool) | Word / Line | Binary legibility assessment |
| **Orientation Labels** | JSON (bool) | Word / Line | Vertical text flag |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | `gt/*.jsonl` "info" key | Version (v1.0), creation date |
| **Image-level** | Filename | 16-char hex image ID |
| **Annotation-level** | Inline in annotations | Handwriting, legibility, orientation flags |

##### 2.5 Annotation Schema Details

**Format**: Single JSON object per file (not line-delimited despite .jsonl extension)

```json
{
  "info": {"date": "...", "version": "v1.0"},
  "annotations": [
    {
      "image_id": "0006289e4f292bcd",
      "paragraphs": [
        {
          "vertices": [[x, y], ...],
          "legible": true,
          "lines": [
            {
              "vertices": [[x, y], ...],
              "text": "MOZART",
              "legible": true,
              "handwritten": false,
              "vertical": false,
              "words": [
                {
                  "vertices": [[x, y], ...],
                  "text": "MOZART",
                  "legible": true,
                  "handwritten": false,
                  "vertical": false
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | string | Yes | 16-char hex ID, matches image filename |
| `vertices` | list | Yes | Polygon coordinates [[x,y], ...], arbitrary point count |
| `text` | string | Yes | Ground truth transcription (word/line level) |
| `handwritten` | bool | Yes | Binary handwriting flag |
| `legible` | bool | Yes | Binary legibility flag |
| `vertical` | bool | Yes | Text orientation flag |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Polygons | `layout_detections.polygon` | High | Arbitrary-point polygons, requires bbox derivation |
| ✅ Text GT | `text_content.full_text` | High | Word-level transcriptions |
| ✅ Handwriting | Custom field | High | Binary classification, derive graded presence |
| ✅ Legibility | Custom field | High | Binary classification, derive graded legibility |
| ✅ Orientation | Custom field | Medium | Vertical text flag |
| ❌ Quality scores | - | N/A | Not provided by source |
| ❌ Reading order | - | N/A | Not provided by source |
| ❌ Language labels | - | Low | Multi-language dataset but not per-instance |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 11,639 |
| **Train Images** | 8,281 |
| **Validation Images** | 1,724 |
| **Test Images** | 1,634 |
| **Word Annotations** | ~1.2M |
| **Format** | JSON (single file per split) |
| **Image Source** | Open Images Dataset |

##### Annotation Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| **handwritten** | bool | Word/line-level handwriting detection |
| **legible** | bool | Word/line-level legibility assessment |
| **text** | string | Transcribed text content |
| **vertices** | polygon | Polygon coordinates (not bbox) |
| **vertical** | bool | Vertical text orientation |

##### Hierarchical Structure

```text
image
└── paragraphs[]
    ├── legible: bool
    └── lines[]
        ├── text: string
        ├── handwritten: bool
        ├── legible: bool
        ├── vertical: bool
        └── words[]
            ├── text: string
            ├── handwritten: bool
            ├── legible: bool
            └── vertices: [[x,y], ...]
```

##### Use Cases

- **Strengths**: GOLD STANDARD for graded handwriting assessment - explicit `handwritten` + `legible` labels at word level
- **Weaknesses**: Scene text focus (not documents), requires polygon-to-bbox conversion
- **Complementary Datasets**: COCO-Text, Total-Text, TextOCR

##### Graded Assessment Derivation

| Derived Metric | Formula |
|----------------|---------|
| **presence_ratio** | handwritten_words / total_words |
| **legibility_ratio** | legible_handwritten / handwritten_words |
| **presence_category** | NONE/SPARSE/MODERATE/SUBSTANTIAL/DOMINANT based on ratio |

##### Project Usage

- **Path**: `01_base_data/text_detection/hiertext/`
- **Phase(s)**: Graded handwriting assessment training
- **Purpose**: Train SigLIP v2 NaFlex multi-task head for presence/legibility/content_type
- **Parser**: ✅ `HiertextParser` (multilingual package)

---
