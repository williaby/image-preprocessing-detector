---
owner: docs-team
purpose: Template for creating consistent dataset documentation documents.
schema_type: common
status: draft
tags:
- datasets
title: Dataset Documentation Template
---

> **Version**: 1.5.0
> **Last Updated**: 2026-02-14
> **Purpose**: Standardized template for comprehensive IQA dataset documentation
> **Consensus**: Validated by Gemini 3 Pro (9/10) and Claude Sonnet 4.5 (8/10)

---

## Template Structure

Each dataset entry should follow this structure. For the main DATASET_CATALOG.md, use the
**Quick Reference** format. For detailed documentation, create individual files in `docs/datasets/`.

---

## Quick Reference Format (for DATASET_CATALOG.md)

Use this condensed format in the main catalog for rapid dataset selection:

```markdown
### [Dataset Name]

> **Quick Stats**: [count] images | [source_type] | [primary IQA characteristics]
>
> **License**: [license] | **Commercial Use**: Yes/No/Restricted

- **Path**: `01_base_data/category/dataset_name/`
- **Paper**: [Title (Year)](link)
- **IQA Profile**: [blur_sensitive, high_contrast, etc.]
- **Project Usage**: Phase X training/validation/benchmark
- **Parser**: [`parse_xxx_labels`](../scripts/annotate_base_metadata.py#LXXX) | ✅/⚠️/❌/ℹ️

**Data Locations**:
| Type | Path | Status |
|------|------|--------|
| Images | `01_base_data/category/dataset/` | ✅ |
| Text/OCR | `annotations/dataset/ocr/` or GT path | ✅/❌ |
| Layout (COCO) | `annotations/dataset/layout/` or GT path | ✅/❌ |

[2-3 sentence description of dataset and its IQA relevance]
```

**Parser Status Legend**:

- ✅ Complete - Full label extraction implemented
- ⚠️ Partial - Some fields extracted, others pending
- ❌ Not Implemented - Labels available but no parser yet
- ℹ️ Not Applicable - Dataset has no ground truth labels

---

## Detailed Dataset Card Template

For individual dataset files (`docs/datasets/[dataset_name].md`):

```markdown
---
# YAML Frontmatter (machine-readable)
dataset_id: dataset_name
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - blur_sensitive
  - high_contrast
baseline_quality: 8.2
training_suitable: true
benchmark_suitable: false
documentation_status: complete  # complete | partial | inferred
---
```

### [Dataset Name]

> **Quick Stats**: 260,025 images | Born-digital | High contrast | Blur-sensitive | Grid lines

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Complete official dataset name |
| **Version** | Version number (e.g., v1.0, v2.1) |
| **Release Date** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Maintainer** | Organization (e.g., Microsoft Research) |
| **Paper** | [Citation Title (Year)](paper_url) |
| **Repository** | [Official Source](repo_url) |
| **License** | License type with [link](license_url) |
| **Commercial Use** | Yes / No / Restricted (explain) |
| **Documentation Status** | Complete / Partial / Inferred |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG / TIFF / PDF | Primary document images |
| **Annotations** | JSON / XML / CSV / TXT | Label/annotation files |
| **Metadata** | JSON / YAML / CSV | Dataset or per-image metadata |
| **Supplementary** | PDF / TXT / MD | Documentation, readme, license |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `dataset/train/images/` | `dataset/train/labels.json` | 10,000 | ✅ |
| **Validation** | `dataset/val/images/` | `dataset/val/labels.json` | 1,000 | ✅ |
| **Test** | `dataset/test/images/` | `dataset/test/labels.json` | 1,000 | ✅ |
| **Unlabeled** | `dataset/unlabeled/` | - | 5,000 | ⚠️ |

**Split Organization Pattern**: `by_folder` / `by_file_list` / `single_dir_with_manifest`

> **Notes**:
>
> - If splits use file lists instead of folders, document the list file path (e.g., `train.txt`)
> - Mark status: ✅ Available | ⚠️ Partial | ❌ Missing | 🔄 Processing
> - Include unlabeled/extra data if provided by source

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | COCO / PASCAL VOC / YOLO / Custom | Page / Region / Word / Character | Object detection coordinates |
| **Polygons** | COCO / Custom | Region / Character | Non-rectangular region boundaries |
| **Text Transcriptions** | TXT / JSON | Page / Line / Word | Ground truth text content |
| **Layout Classes** | JSON / XML | Region | Semantic labels (table, figure, text, etc.) |
| **Reading Order** | JSON / XML | Page | Sequential reading sequence |
| **Quality Scores** | JSON / CSV | Image / Region | IQA or quality assessments |
| **Segmentation Masks** | PNG / NPY | Pixel-level | Binary or instance masks |

> **Note**: Delete rows that don't apply. Add custom rows for dataset-specific label types.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / JSON | Version, license, citation, splits |
| **Image-level** | Filename / JSON / CSV | Dimensions, DPI, source document |
| **Annotation-level** | Inline / Separate file | Confidence scores, annotator ID |
| **Document-level** | JSON / XML | Page count, language, document type |

##### 2.5 Annotation Schema Details

> **Format**: Describe the annotation file structure for parser implementation

```text
# Example: COCO format
{
  "images": [{"id": int, "file_name": str, "width": int, "height": int}],
  "annotations": [{"id": int, "image_id": int, "category_id": int, "bbox": [x,y,w,h]}],
  "categories": [{"id": int, "name": str}]
}

# Or describe custom format structure here
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | int/str | Yes | Links annotation to image |
| `bbox` | list | Varies | Coordinate format: [x,y,w,h] or [x1,y1,x2,y2] |
| `category` | str/int | Varies | Class label or ID |
| `text` | str | Varies | Transcription content |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Layout boxes | `layout_annotations` | High | COCO format, direct mapping |
| ✅ Text GT | `ground_truth_text` | High | Line-level transcriptions |
| ⚠️ Quality scores | - | Medium | Custom format needs mapping |
| ❌ Reading order | - | Low | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.
> See [GROUND_TRUTH_SUMMARY.md](GROUND_TRUTH_SUMMARY.md) for cross-dataset overview.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert / Crowdsourced / Synthetic / Automatic Extraction / Paired GT / Mixed |
| **Provenance Tier** | Tier 0 (Exact) / Tier 1 (Annotation) / Tier 2 (Model) / Tier 3 (Heuristic) |
| **Annotator Details** | Number of annotators, expertise level (if known) |
| **Inter-Annotator Agreement** | IAA metric and value (if measured) |
| **Quality Assurance** | QA process (double annotation, review rounds, adjudication, etc.) |
| **GT Label Coverage** | Percentage of images with ground truth labels |

> **Notes**:
>
> - For synthetic datasets, document the generation method instead of annotator details
> - For paired GT datasets, note the clean reference capture method
> - Delete rows that don't apply. Use `[NEEDS_VERIFICATION]` for unconfirmed information
> - See `annotation/schemas/enums.py` for `EnrichmentTier` definitions

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training |
| **Purpose** | Training / Validation / Testing / Benchmark |
| **Local Path** | `01_base_data/tables/tablebank/` |
| **Subset Used** | Full dataset / Specific subset (explain) |
| **Preprocessing** | Required steps before use |
| **Dataloader** | `src/data/tablebank_loader.py` |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`parse_tablebank_labels`](../../scripts/annotate_base_metadata.py#L1333) |
| **Parser Status** | ✅ Complete / ⚠️ Partial / ❌ Not Implemented / ℹ️ Not Applicable |
| **Layer 1 Fields** | `tablebank_annotations` (COCO format) |
| **Layer 2 Auto-Derived** | `has_table=True`, `script_family`, `iso639_language` |
| **Config Entry** | [`DATASET_CONFIGS["tablebank"]`](../../scripts/annotate_base_metadata.py#L284) |

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/tables/tablebank/` | ✅ Available | Primary image files |
| **Images (alt)** | - | - | If images extracted elsewhere |
| **Text/OCR GT** | - | ❌ None | Original dataset ground truth text |
| **Text/OCR Extracted** | `annotations/tablebank/ocr/` | ❌ Not extracted | DocLayout-YOLO / GCS extraction |
| **Layout GT** | `01_base_data/tables/tablebank/*.json` | ✅ COCO format | Original COCO annotations |
| **Layout Extracted** | `annotations/tablebank/layout/` | ❌ Not extracted | DocLayout-YOLO extraction |
| **Layer 2 Metadata** | `metadata_registry/json/tablebank_layer2.json` | ✅ Available | Enrichment metadata |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 208,000 | 208,000 | 100% | ✅ Complete |
| **Validation** | 26,000 | 26,000 | 100% | ✅ Complete |
| **Test** | 26,025 | 26,025 | 100% | ✅ Complete |
| **Total** | 260,025 | 260,025 | 100% | ✅ All splits |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: If any split shows less than 100% coverage, file an issue to re-process
> the dataset with the missing split. Use the `split` field in sample source metadata
> to track which split each sample belongs to.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 260,025 |
| **Training Split** | 208,000 (80%) |
| **Validation Split** | 26,000 (10%) |
| **Test Split** | 26,025 (10%) |
| **Image Dimensions** | 600-2000px (variable) |
| **Resolution (DPI)** | 72-300 (variable) |
| **File Format(s)** | JPG |
| **Color Space** | RGB / Grayscale |
| **Total Size on Disk** | 45.2 GB |
| **Annotation Format** | JSON / XML / None |

##### 4.3 Text Statistics (if ground truth text available)

> **Source**: Computed from ground truth text labels
> **Availability**: ✅ Available / ❌ Not Available / ⚠️ Partial

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | 850 ± 420 | 12 | 5,200 | 520 / 780 / 1,100 |
| **Word Count** | 145 ± 72 | 2 | 890 | 88 / 132 / 188 |
| **Sentence Count** | 8.2 ± 4.5 | 1 | 45 | 5 / 7 / 11 |
| **Paragraph Count** | 2.1 ± 1.8 | 1 | 12 | 1 / 2 / 3 |
| **Avg Word Length** | 5.8 ± 1.2 | 3.2 | 9.4 | 5.1 / 5.7 / 6.4 |
| **Avg Sentence Length** | 17.6 ± 6.3 | 4 | 52 | 13 / 16 / 21 |

**Text Source**: `ground_truth` / `ocr_tesseract` / `ocr_doctr` / `transcription` / `synthetic`

> **Note**: Text statistics are only populated when actual text content is available from ground
> truth labels, OCR output, or transcriptions. See Layer 2 schema `TextStatistics` definition.

##### Directory Structure

```text
tablebank/
├── train/
│   ├── word/           # 78K Word-extracted tables
│   └── latex/          # 130K LaTeX-rendered tables
├── val/
└── test/
```

##### Baseline Quality Metrics

> **Source**: [Empirically Derived] from 1000-sample profiling

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Entropy** | 7.2 ± 0.8 | 5.1 | 7.9 | 6.7 / 7.3 / 7.8 |
| **Edge Density** | 0.15 ± 0.06 | 0.02 | 0.34 | 0.11 / 0.14 / 0.19 |
| **Contrast Ratio** | 45 ± 12 | 18 | 89 | 38 / 44 / 52 |
| **Laplacian Variance** | 320 ± 180 | 12 | 890 | 185 / 290 / 420 |
| **Aspect Ratio** | 1.2 ± 0.4 | 0.5 | 3.2 | 0.9 / 1.1 / 1.4 |

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Scientific publications, financial documents |
| **Document Types** | Tables only (isolated table regions) |
| **Language(s)** | English (98%), Other (2%) |
| **Temporal Range** | 2010-2020 publications |
| **Acquisition Method** | Word document extraction, LaTeX rendering |

##### 5.1 Class/Category Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| Word-extracted | 78,000 | 30% |
| LaTeX-rendered | 182,025 | 70% |

##### 5.2 Class/Category Definitions (if applicable)

> **Purpose**: Define the taxonomy of classes/categories used in the dataset annotations.
> **Applicability**: Layout detection, document classification, NER, script identification datasets.

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Table | 1 | Tabular data region | - |
| Figure | 2 | Charts, graphs, images | - |
| Text | 3 | Body text paragraphs | - |
| Title | 4 | Document/section titles | - |
| List-Item | 5 | Bulleted/numbered items | - |

> **Notes**:
>
> - Include all classes defined in the annotation schema
> - Add "Parent" column for hierarchical taxonomies
> - Reference official documentation for class definitions
> - Delete this section if dataset has no class taxonomy

##### 5.3 Language & Script Coverage (if multilingual)

> **Purpose**: Document language and script distribution for multilingual datasets.
> **Applicability**: OCR, script detection, multilingual document datasets.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Latin | Latn | 45,000 | 60% | Primary script |
| Arabic | Arab | 15,000 | 20% | Right-to-left |
| Devanagari | Deva | 10,000 | 13% | Hindi, Sanskrit |
| Han (Chinese) | Hans/Hant | 5,000 | 7% | Simplified + Traditional |

**Script Families Present**: Latin, Arabic, Indic, CJK

> **Notes**:
>
> - Use ISO 15924 codes for scripts, ISO 639-1/3 for languages
> - Delete this section for monolingual datasets
> - Include script-confusable pairs if documented (e.g., Latin O vs Cyrillic О)

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital (rendered, not scanned) |
| **Capture Device** | N/A (programmatic extraction) |
| **Original Quality** | Clean, no scanning artifacts |
| **Compression** | JPEG quality 85-95 |
| **Known Artifacts** | Minor JPEG blocking on some samples |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Grid lines and small text extremely sensitive |
| **Noise** | MEDIUM | High contrast masks moderate noise |
| **Skew** | HIGH | Cell alignment degrades rapidly with rotation |
| **Contrast** | LOW | Already high contrast (black on white) |
| **Compression** | HIGH | JPEG artifacts destroy thin lines |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | 8-14pt typical | Small text sensitive to blur |
| **Line/Grid Density** | High | Grid lines are blur detection targets |
| **Font Diversity** | Low (standard fonts) | Consistent OCR behavior expected |
| **Mathematical Notation** | Common in LaTeX subset | Subscripts/superscripts fragile |
| **Color Usage** | Minimal (B&W) | Grayscale processing sufficient |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large volume, clean ground truth for table quality |
| **Unique Characteristics** | Grid line detection, cell boundary sharpness |
| **Complementary Datasets** | Combine with PubTabNet for scientific tables |
| **Benchmark Suitability** | MEDIUM - Born-digital only, lacks real scan artifacts |
| **Known Limitations** | No handwritten content, limited degradation variety |

##### 6.5 Benchmark Results (if applicable)

> **Purpose**: Document published model performance on this dataset for baseline comparison.
> **Applicability**: Datasets used as standard benchmarks in competitions or papers.

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| YOLOv8-DocLayout | Table Detection | mAP@50 | 0.95 | [Paper 2023](url) |
| TableFormer | Table Recognition | TEDS | 0.89 | [Paper 2022](url) |
| Faster R-CNN | Table Detection | F1 | 0.92 | Original Paper |

**Competition Results** (if applicable):

| Competition | Year | Winning Score | Winner |
|-------------|------|---------------|--------|
| ICDAR 2019 Table Detection | 2019 | 0.94 F1 | Team X |

> **Notes**:
>
> - Include top 3-5 benchmark results from papers/leaderboards
> - Delete this section if no published benchmarks exist
> - Link to [Papers With Code](https://paperswithcode.com) leaderboard if available

#### 7. Known Issues & Limitations

- **Quality Bias**: Born-digital only; doesn't represent scanned document quality
- **Domain Bias**: Heavy scientific/financial focus; limited document variety
- **Annotation Gaps**: Table structure annotations exist but not IQA-specific labels
- **Class Imbalance**: 70% LaTeX vs 30% Word creates rendering style bias
- **Resolution Variance**: Wide DPI range requires normalization

#### 8. Representative Samples

> Include 2-3 example images showing typical quality and any notable artifacts

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| ![Sample 1](../assets/datasets/tablebank_sample1_thumb.png) | Typical LaTeX table | Clean grid, standard font |
| ![Sample 2](../assets/datasets/tablebank_sample2_thumb.png) | Complex nested table | Dense content, small text |
| ![Sample 3](../assets/datasets/tablebank_sample3_thumb.png) | Financial table | Decimal alignment, footnotes |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: Table Benchmark for Image-based Table Detection and Recognition},
  author={Li, Minghao and others},
  booktitle={LREC},
  year={2020}
}
```

##### Related Works

- [PubTabNet](pubtabnet.md) - Complementary scientific table dataset
- [FinTabNet](fintabnet.md) - Financial tables with similar structure

##### Leaderboards

- [Papers With Code - Table Detection](https://paperswithcode.com/task/table-detection)

#### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset that don't fit standard template sections. This is a **freeform section** - content varies by dataset.

##### 10.1 Annotation Caveats (if applicable)

> Document dataset-specific annotation limitations, quality notes, or known issues.

- Example: "Bounding boxes may extend beyond table borders by 2-5 pixels"
- Example: "Cell text not available for merged cells"
- Example: "10% of samples excluded due to rotation >15°"

##### 10.2 Implementation Notes (if applicable)

> Document parser-specific details, schema quirks, or file format notes.

- Example: "JSON uses non-standard bbox format [y1, x1, y2, x2]"
- Example: "Hierarchical structure: Word → Line → Paragraph"
- Example: "Quality scores range 1-5, map to 0-1 via (score-1)/4"

##### 10.3 External Resources (if applicable)

> Document associated models, competition context, or acquisition instructions.

- Example: "Associated GAN model available at [repo_url]"
- Example: "Part of ICDAR 2019 competition Track A"
- Example: "Requires registration at [source_url] to download"

##### 10.4 Custom Metrics (if applicable)

> Document dataset-specific scoring, tier definitions, or conversion tables.

- Example: "Quality tiers: Tier 1 (excellent) = 90-100, Tier 2 (good) = 70-89"
- Example: "Legibility grades derived from character error rate thresholds"

> **Notes**:
>
> - Delete subsections that don't apply to this dataset
> - Add custom subsections as needed (e.g., "Cyrillic Coverage", "Distortion Types")
> - This section is intentionally flexible to preserve dataset-unique information

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).
>
> **Applicability**: Required for all datasets that have completed a Layer 2 audit.
> Delete this section if no audit has been performed.

##### 11.1 Quality Scorecard

> **Audit Date**: YYYY-MM-DD | **Grade**: X (NN.N/100) | **Auditor**: model-name

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 0.0 | 0.278 | |
| Field Validity | 0.0 | 0.278 | |
| Doc Completeness | 0.0 | 0.167 | |
| Defect Rate | 0.0 | 0.167 | |
| VLM Accuracy | 0.0 | 0.111 | |
| **Overall** | **0.0** | | **Grade ?** |

##### 11.2 Key Defects

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | field_name | critical/high/medium/low | RESOLVED/DEFERRED | Brief description |

##### 11.3 VLM Inspection Summary

| Flag | Inspected | FP Rate | Notes |
|------|----------:|--------:|-------|
| has_formula | 0 | 0% | |
| has_table | 0 | 0% | |
| has_handwriting | 0 | 0% | |
| has_figure | 0 | 0% | |

**Track C Passing Accuracy**: 0% (0/0 samples)

##### 11.4 Cross-Dataset Findings

> List any Known Issues (KI-NNN) discovered or confirmed during this audit.

- None

**Audit Artifacts**: [scripts/audit/results/{dataset}/](../../scripts/audit/results/{dataset}/)

---

#### 12. Reliability & Bottlenecks

> **Purpose**: Auto-generated composite reliability summary identifying the weakest enrichment fields per dataset. Populated by `materialize_reliability_summary.py`.
>
> **Methodology**: Each enrichment field is assigned a confidence score (0.0-1.0). Missing/unrun fields get confidence=0.0. The composite min_confidence across all fields determines each sample's overall reliability category.

##### 12.1 Composite Category Distribution

> **Computed**: YYYY-MM-DD | **Samples**: N | **Avg Min Confidence**: 0.XXX

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 0 | 0.0% |

**Category Thresholds**: hard_label >= 0.9, soft_label >= 0.7, active_learning >= 0.5, unreliable < 0.5

##### 12.2 Top Bottleneck Fields

> The fields most frequently responsible for the lowest per-sample confidence.

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `field_name` | XX.X% | 0.XXX |
| 2 | `field_name` | XX.X% | 0.XXX |
| 3 | `field_name` | XX.X% | 0.XXX |

> **Improving Reliability**: Run the corresponding backfill script for the top bottleneck:
>
> - `text_quality` -> `backfill_text_quality_confidence.py`
> - `language` -> `backfill_language_confidence.py`
> - `layout_detections` -> Re-run DocLayout-YOLO inference
> - `capture_method`, `domain` -> Update dataset config / re-run annotation

---

## Documentation Status Markers

Use these markers to indicate documentation completeness:

| Marker | Meaning |
|--------|---------|
| `[Official]` | Information from official documentation/paper |
| `[Empirically Derived]` | Computed from actual dataset samples |
| `[Inferred]` | Reasoned from available evidence |
| `[NEEDS_PROFILING]` | Section requires empirical analysis |
| `[NEEDS_VERIFICATION]` | Information needs confirmation |

---

## Automation Notes

### Profiling Script

For datasets lacking official documentation, use the profiling script:

```bash
# Generate baseline quality metrics for a dataset
python scripts/profile_dataset.py \
  --input /mnt/e/image_detection/01_base_data/tables/tablebank/ \
  --sample-size 1000 \
  --output docs/datasets/tablebank_profile.json
```

### Metrics Computed

The profiling script computes:

- **Entropy**: Shannon entropy of grayscale histogram
- **Edge Density**: Canny edge pixel ratio
- **Contrast Ratio**: (max - min) / mean intensity
- **Laplacian Variance**: Blur proxy (higher = sharper)
- **Aspect Ratio**: Width / height distribution
- **File Size per Pixel**: Compression quality indicator

---

## Template Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.5.0 | 2026-02-14 | Added Section 2.7 "Ground Truth Provenance" for annotation methodology, IAA metrics, and QA documentation. See GROUND_TRUTH_SUMMARY.md for cross-dataset overview |
| 1.4.0 | 2026-02-12 | Added Section 11 "Layer 2 Audit Summary" for post-audit quality scorecard, VLM inspection results, key defects, and cross-dataset findings. Renumbered "Reliability & Bottlenecks" to Section 12 |
| 1.3.0 | 2026-02-09 | Added Section 11 "Reliability & Bottlenecks" (now Section 12) for auto-generated composite reliability summary with category distribution and top bottleneck fields per dataset |
| 1.2.0 | 2025-02-01 | Added Section 5.2 "Class/Category Definitions" for taxonomy documentation; Added Section 5.3 "Language & Script Coverage" for multilingual datasets; Added Section 6.5 "Benchmark Results" for published model performance; Added Section 10 "Dataset-Specific Notes" as freeform section for dataset-unique content (annotation caveats, implementation notes, external resources, custom metrics) |
| 1.1.0 | 2025-02-01 | Added Section 2 "Source Data Inventory" with subsections for file types, split locations (train/test/val paths), labels, metadata, schema details, and parser potential |
| 1.0.0 | 2025-12-17 | Initial template based on Gemini/Claude consensus |
