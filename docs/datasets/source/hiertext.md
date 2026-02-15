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

##### File Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | JPG |
| **Dimensions** | Variable (natural scene images) |
| **Color Space** | RGB |
| **Annotation Format** | JSON (single object per file, despite .jsonl extension) |
| **Total Size** | ~2.5 GB |

##### IQA Sensitivity

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Natural scene photographs (Open Images) |
| **Baseline Quality** | Variable outdoor/indoor scenes |
| **Blur Sensitivity** | HIGH - Small text in natural scenes needs sharpness |
| **Noise Sensitivity** | MEDIUM - Outdoor lighting creates noise |
| **Resolution Impact** | HIGH - Word-level annotations require sufficient resolution |
| **Key Challenge** | Wide range of text sizes, orientations, and legibility levels |

##### Known Limitations

- Scene text focus (not document images) - limited transfer to document pipelines
- JSONL extension is misleading - files contain single JSON object, not line-delimited
- No per-instance language labels despite being multilingual
- Inter-annotator agreement metrics not reported in source paper
- Polygon annotations require bbox conversion for standard detection frameworks

##### License & Citation

| Attribute | Value |
|-----------|-------|
| **License** | CC-BY-SA-4.0 |
| **Commercial Use** | Yes (with attribution + ShareAlike) |
| **Citation** | Long et al. (2022). Towards Rich Hierarchical Scene Text. ECCV 2022. arXiv:2203.15143 |

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

##### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | Google Research team |
| **Inter-Annotator Agreement** | (Not reported in source) |
| **Quality Assurance** | Expert annotation review |
| **GT Label Coverage** | 100% (all 11,639 images with hierarchical text annotations) |

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

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/text_detection/hiertext/` | ✅ Available | 11,641 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSONL: Word & line-level text (`words[].text`, `lines[].text` in gt/*.jsonl) |
| **Text/GT Converted** | `metadata_registry/extracted/hiertext/` | ✅ Converted | GT conversion: 11,639 images, 1,116,661 annotations, 4.8M chars, 3 categories (paragraph/line/word) |
| **Layout GT Converted** | `metadata_registry/extracted/hiertext/layout_batch_*.json` | ✅ Converted | COCO-style hierarchical layout with polygon→bbox conversion, handwritten flags preserved |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (81.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 99.7 | 25% |  |
| Field Validity | 94.5 | 25% |  |
| Doc Completeness | 36.4 | 15% | Below threshold |
| Defect Rate | 80.0 | 15% |  |
| Cross-Source Agreement | 62.2 | 10% | Below threshold |
| VLM Accuracy | 95.0 | 10% |  |
| **Overall** | **81.7** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 13 defects (3 resolved, 10 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | CRITICAL | OPEN | Split field not populated. Must be derived from GT folder structure (train/valid |
| D02 | capture_method | LOW | RESOLVED | Already correct as camera_smartphone. No action needed. |
| D03 | iso639_language | CRITICAL | OPEN | Language field empty/null for all samples. LLM enrichment covers 8,278 samples ( |
| D04 | script_family | HIGH | OPEN | Script family not populated. Must derive from iso15924_script using KI-008 patte |
| D05 | handwriting_present | HIGH | OPEN | Handwriting fields all null despite HierText providing gold-standard word-level  |
| D06 | orientation_class | HIGH | OPEN | Orientation not populated. LLM enrichment may have partial coverage. VLM will pr |
| D07 | text_has_content | HIGH | OPEN | Text content field empty. Parser GT provides word-level text for all annotated i |
| D08 | image_properties_color_mode | MEDIUM | OPEN | Color mode not populated. Scene photos are always color. |
| D09 | text_direction | LOW | RESOLVED | Text direction currently passing prescreening (defaults acceptable). Will be pro |
| D10 | text_directions_present | LOW | RESOLVED | Text directions present currently passing. Will be enhanced with parser GT verti |
| D11 | layout_detections | CRITICAL | OPEN | Layout detection labels have wrong casing (KI-001). Schema compliance shows 3.7% |
| D12 | domain_level1 | CRITICAL | OPEN | Domain field empty despite appearing in base metadata. Prescreening shows 100% f |
| D13 | has_figure (KI-003) | HIGH | OPEN | Docling layout detects 'Picture' class in ~86% of scene text images. Cross-sourc |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 3425 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/hiertext/](../../scripts/audit/results/hiertext/)

---

##### Processing Notes

- Parser: `HiertextParser` from multilingual package
- GT conversion: 11,639 images, 1,116,661 annotations, 4.8M chars, 3 categories (paragraph/line/word)
- Polygon-to-bbox conversion applied during layout GT extraction
- Handwriting flags preserved from source annotations at word level
- Language enrichment covers 8,278/11,639 samples (71.1%)

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2022-03 | Initial dataset release (Google Research) |
| L2 v1 | 2026-02-10 | Layer 2 metadata annotation |
| L2 v2 | 2026-02-14 | Scorecard v2.0 audit, defect catalog created |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 11,639 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 11,639 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 100.0% | 0.000 |
