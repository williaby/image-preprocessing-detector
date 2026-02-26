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

> **Audit Date**: 2026-02-15 | **Grade**: B (87.0/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 91.4 | 15% |  |
| Field Validity | 94.5 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 80.0 | 10% |  |
| Cross-Source Agreement | 62.2 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **87.0** | | **Grade B** |

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

> **Samples Inspected**: 0 | **Corrections**: 3425 | **Passing Accuracy**: 95.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/hiertext/](../../scripts/audit/results/hiertext/)

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

> **Computed**: 2026-02-16 | **Samples**: 11,639 | **Avg Min Confidence**: 0.401

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 4,279 | 36.8% |
| unreliable | 7,360 | 63.2% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain` | 44.5% | 0.485 |
| 2 | `layout_detections` | 37.5% | 0.542 |
| 3 | `has_table` | 18.1% | 0.600 |

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | ~11,639 | Negatives only | Scene photos from Open Images — upright by construction; no rotated splits provided |
| MNV4-H2 | skew_reg | ➖ | ~11,639 | Negatives only | Scene photos are upright; no skew angle labels available |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~11,639 | Derived | Camera variation introduces natural resolution spread; no RQ labels yet (D09 deferred) |
| SIG-G1-1 | blur_score | 🟡 | ~11,639 | Derived/VLM | Camera photos span sharp to blurry scenes; IQA labels not yet computed |
| SIG-G1-2 | noise_score | 🟡 | ~11,639 | Derived/VLM | Outdoor/indoor lighting variation creates natural noise range |
| SIG-G1-3 | contrast_score | 🟡 | ~11,639 | Derived/VLM | Wide contrast range across scene types (outdoor sun to indoor low-light) |
| SIG-G1-4 | skew_score | ➖ | ~11,639 | Negatives only | Images are upright scene photos; skew quality near-zero throughout |
| SIG-G1-5 | compression_score | 🟡 | ~11,639 | Derived/VLM | JPG format with variable compression; compression artifacts possible |
| SIG-G1-6 | overall_quality | 🟡 | ~11,639 | Derived/VLM | Camera photos span real quality variation; requires IQA VLM labeling (prompt v2.0) |
| SIG-G2-1 | script_cls | ✅ | ~11,542 Latn + ~97 other | GT-derived | 99.2% Latn from 20+ languages; minority samples: Cyrl(12), Hant(10), Deva(6), Grek(6), Jpan(17), Hang(5); strong primary for Latn |
| SIG-G3-1 | orientation_cls (post) | ➖ | ~11,639 | Negatives only | All images upright; no post-correction orientation variation |
| SIG-G3-2 | skew_reg (post) | ➖ | ~11,639 | Negatives only | No skew angle labels; scene photos upright by construction |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~11,639 | GT-derived | Gold-standard: 18% images have handwriting (2,095); presence_ratio derivable from word-level `handwritten` flags; maps to NONE/SPARSE/MODERATE/SUBSTANTIAL/DOMINANT |
| SIG-G4-2 | handwriting_legibility_cls | ✅ | ~2,095 | GT-derived | Word-level `legible` flag on handwritten words; legibility_ratio derivable; 6-class mapping requires bucket thresholding |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~2,095 | GT-derived | Binary handwritten flag at word level; content type (note/form/annotation etc.) requires per-image inference from context |
| SIG-G4-4 | presence_reg | ✅ | ~11,639 | GT-derived | Continuous presence_ratio = handwritten_words / total_words; 1.2M word annotations enable precise ratio |
| SIG-G4-5 | legibility_reg | ✅ | ~2,095 | GT-derived | Continuous legibility_ratio = legible_handwritten / handwritten_words; direct from source labels |
| SIG-G5-1 | capture_method_cls | ✅ | ~11,639 | GT (100% real) | 100% camera_smartphone; real images qualify for 100% real requirement; maps to `camera` class |
| SIG-G5-2 | shadow_reg | 🟡 | ~11,639 | Derived | Outdoor scene photos contain natural shadow variation; no shadow severity labels yet |
| SIG-G5-3 | warping_reg | ➖ | ~11,639 | Negatives only | Flat scene photography; negligible page warping (not document scans) |
| SIG-G5-4 | code_cls | 🟡 | ~11,639 | Derived | ~2 images tagged source_code; 2.7% datasheets may contain inline code; marginal contributor |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~11,639 | Derived | Camera images span natural resolution range; RQ labeling not yet run (D09 deferred) |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | Latn 99.2% (11,542), CJK 0.3% (36), Cyrl 0.1% (12), Grek 0.1% (6), Indic 0.1% (11), Other 0.3% (32); 14 distinct ISO 15924 codes |
| 2 | Capture method | ✅ | 100% camera_smartphone (natural scene photography from Open Images) |
| 3 | Document domain | ✅ | ADM 50.5%, TEC 17.8%, FIN 13.0%, EDU 6.7%, PER 4.9%, SCI 3.0%, MED 2.3%, LEG 1.7%; diverse multi-domain |
| 4 | Layout type | 🟡 | Scene text (not structured documents); signs, posters, receipts, books, menus; no formal layout taxonomy applied |
| 5 | Text density | ✅ | Wide range from single-word signs to dense multi-paragraph documents; 1.2M word annotations |
| 6 | Degradation types | 🟡 | Natural camera degradation only (motion blur, noise, low-light); no document-specific degradation; no L2 degradation labels |
| 7 | Resolution/DPI range | 🟡 | Variable natural scene image sizes; no explicit DPI metadata; RQ labeling deferred (D09) |
| 8 | Document age | 🟡 | Mix of modern and historical content (historical_document/record content types present); no explicit age labels |
| 9 | Text scope | ✅ | 100% word-level annotations; also line and paragraph levels in hierarchy |
| 10 | Content flags | ✅ | has_handwriting: 18.0% (2,095), has_table: 2.1% (241); VLM/GT-confirmed |
| 11 | Binarization status | ❌ | All color RGB; no binarized images |
| 12 | Artifact types | 🟡 | Camera artifacts only (JPEG compression, motion blur, noise, lens distortion); no scan/print artifacts |
| 13 | Color mode | ✅ | 100% color RGB (D08 notes scene photos always color; confirmed) |
| 14 | Font variety | ✅ | Extreme variety — natural scenes capture commercial signage, handwriting, print, chalk, neon, painted text |

### 13.3 Corpus Role & Constraints

HierText is the **primary gold-standard source for graded handwriting assessment** (G4-1 through G4-5), providing 1.2M word-level `handwritten` and `legible` binary annotations across 11,639 real camera images that enable derivation of continuous presence/legibility ratios. It also contributes as a strong primary for Latin script (G2-1) with 20+ language varieties, and as the sole 100%-real camera dataset eligible for capture_method_cls (G5-1). The CC-BY-SA-4.0 license requires ShareAlike on derivative works, which constrains how training labels derived from HierText can be redistributed. Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) scripts are absent from this dataset and remain OOD exclusions for G2-1.
