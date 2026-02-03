---
title: Dataset Data Availability Gaps Report
status: active
created: 2025-01-31
purpose: Track missing images, text, and COCO layout annotations across all datasets
---

# Dataset Data Availability Gaps Report

> **Last Updated**: 2025-02-01
> **Total Datasets Audited**: 50 image datasets (excludes wili_2018, openlid-v2 text corpora)
> **Template Version**: 1.2.0 (DATASET_TEMPLATE.md)
> **Related Docs**: [DATASET_CATALOG.md](../DATASET_CATALOG.md) | [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md) | [DATASET_TEMPLATE.md](../DATASET_TEMPLATE.md)

---

## Executive Summary

| Category | Datasets | Total Images | % of Total |
|----------|----------|--------------|------------|
| **Have Both Text + COCO** | 9 | ~931K | 27% |
| **Have Text Only** | 29 | ~785K | 23% |
| **Have COCO Only** | 2 | ~578K | 17% |
| **Have Neither** | 10 | ~1.08M | 31% |

**Key Finding**: 9 datasets have both text AND COCO layout annotations, making them the most valuable for DocLayout-YOLO style training.

**Recent Discovery (2025-02-01)**: Investigation of original sources revealed:

- ✅ **DocLayNet**: Has 81,471 JSON files with text content (previously undocumented)
- ✅ **CC-OCR**: Has text labels in TSV files (previously undocumented)
- ❌ **TableBank**: Confirmed no text labels available (only bounding boxes)
- ❌ **DocSynth300K**: Confirmed no text labels available (only YOLO layout)

**Second Investigation (2025-02-01)**: Five more datasets investigated (see Section 10):

- ✅ **MIDV500**: Has text in document template JSONs (50 doc types with field values)
- ✅ **receipts_hitl**: Has 193 Supervisely JSONs with transcription tags
- ✅ **pucit_ohul_urdu**: Has 7,487 Urdu text transcriptions in xlsx files
- ❌ **CVSI**: Script classification only (folder structure labels, no text)
- ❌ **signatr6k**: Segmentation masks only (PNG labels, no transcriptions)

**Template Compliance Audit (2025-02-01)**: See Section 9 for detailed findings:

- **48 extra sections** in catalog not defined in template → ✅ **RESOLVED**: Template v1.2.0 adds structured sections (5.2, 5.3, 6.5) and freeform notes (Section 10)
- **28 HIGH-risk sections** with unique content → Now mapped to specific template sections (see Section 9.3)
- **8 template sections** missing from most/all catalog entries (Section 2 Source Data Inventory is new)
- **8 datasets** require special attention due to extensive custom documentation

---

## 1. Datasets Missing Images

**Count**: 0 datasets

All 49 image datasets have accessible image files. No action needed.

---

## 2. Datasets Missing Text

**Count**: 9 datasets (~865K images)

These datasets have no ground truth text AND no extracted OCR text.

### High Priority (Large datasets with existing COCO layout)

| Dataset | Images | Category | Has COCO? | Notes |
|---------|--------|----------|-----------|-------|
| **tablebank** | 278,582 | Tables | ✅ Yes | Has COCO layout, needs OCR extraction |
| **docsynth300k** | 300,000 | Layout | ✅ YOLO | Synthetic, has YOLO layout |

> **Note**: DocLayNet was previously listed here but has text labels - see Section 8.

### Medium Priority

*No datasets in this category after investigation.*

### Low Priority

| Dataset | Images | Category | Has COCO? | Notes |
|---------|--------|----------|-----------|-------|
| **nist_sd19** | 3,669 | Handwriting | ❌ No | Character-level only |
| **tobacco800** | 1,290 | Degraded | ❌ No | Historical documents |
| **dibco** | 343 | IQA/Benchmark | ❌ No | Binarization benchmark |
| **realdae** | 1,200 | IQA | ❌ No | Before/after pairs |
| **nepali_handwritten** | 958 | Language | ❌ No | Handwritten Nepali |
| **signatr6k** | 12,514 | Text Seg | ❌ No | Segmentation masks only (no OCR transcriptions) |
| **historical_degraded** | 1,356 | Degraded | ❌ No | Mixed historical |
| **bhutan_financial** | 125 | Financial | ❌ No | Small sample (10 excluded: blanks/rotated) |
| **cvsi** | 10,715 | Script | ❌ No | Script classification only (folder labels) |

> **Note**: MIDV500, receipts_hitl, and pucit_ohul_urdu were previously listed here but have text labels - see Section 10.

---

## 3. Datasets Missing COCO Layout Annotations

**Count**: 28 datasets (~1.05M images)

These datasets have no COCO-format layout annotations (neither ground truth nor extracted).

### High Priority (Already have OCR text)

| Dataset | Images | Has Text? | Notes |
|---------|--------|-----------|-------|
| **rvl_cdip** | 400,000 | ✅ Extracted | Document classification, has OCR - just needs layout |

### Medium Priority

| Dataset | Images | Has Text? | Notes |
|---------|--------|-----------|-------|
| **iam_handwriting** | 130,212 | ✅ GT | Has XML bboxes, needs YOLO conversion |
| **muharaf** | 25,711 | ✅ GT (24,495 lines) | Has PAGE XML polygons, needs YOLO conversion |
| **mdiw13** | 290,213 | ✅ GT | Script ID, word-level |
| **hasyv2** | 168,233 | ✅ GT | Symbol classification |

### Low Priority (IQA/Benchmark - layout not needed)

| Dataset | Images | Has Text? | Notes |
|---------|--------|-----------|-------|
| **ohr-bench** | 8,561 | ✅ GT | IQA benchmark |
| **nist_sd19** | 3,669 | ❌ | Character images |
| **tobacco800** | 1,290 | ❌ | Could benefit from layout |
| **dibco** | 343 | ❌ | Binarization only |
| **realdae** | 1,200 | ❌ | IQA pairs |

### Low Priority (Language/Script datasets)

| Dataset | Images | Has Text? | Notes |
|---------|--------|-----------|-------|
| **yarmouk_ocr** | 4,633 | ✅ GT | Arabic text |
| **arabic_docs_ocr** | 10,045 | ✅ GT | Arabic OCR |
| **cc_ocr** | 7,058 | ✅ GT | CJK mixed - has text in TSV (see Section 8) |
| **nepali_handwritten** | 958 | ❌ | Handwritten |
| **pucit_ohul_urdu** | 7,401 | ✅ GT | Urdu transcriptions in xlsx (see Section 10) |
| **midv500** | 15,000+ | ✅ GT | ID field values in JSON (see Section 10) |
| **synth_multiscript** | 27,000 | 🔄 | Generating |

### Not Applicable (Metadata/Benchmark only)

| Dataset | Images | Has Text? | Notes |
|---------|--------|-----------|-------|
| **omnidocbench** | metadata | ✅ GT | Benchmark only |
| **financebench** | 368 PDFs | ✅ GT | PDF corpus |

---

## 4. Datasets with Complete Data (Text + COCO)

These 9 datasets have both text annotations AND COCO layout - most valuable for training:

| Dataset | Images | Text Source | COCO Source |
|---------|--------|-------------|-------------|
| **doclaynet** | 81,471 | GT (81K JSON with cell text) | GT COCO JSON |
| **funsd** | 199 | GT + GCS OCR | GT annotations |
| **pubtabnet** | 568,000 | GT (HTML cells) | GT JSONL |
| **fintabnet** | 97,475 | GT (XML structure) | GT JSON |
| **cocotext** | 63,686 | GT (64K instances) | GT COCO JSON |
| **hiertext** | 11,639 | GT (1.4GB JSONL) | GT Polygon |
| **mlt19** | 20,000 | GT (10K TXT) | GT Text boxes |
| **sroie** | 2,043 | Extracted OCR | Extracted layout |
| **invoices_kaggle** | 1,414 | GT + Extracted | Extracted layout |

**Total**: ~845K images with complete annotations

> **Note**: DocLayNet added after discovery of text content in per-document JSON files.

---

## 5. Extracted Annotations Inventory

**Location**: `/mnt/e/image_detection/annotations/`

| Dataset | Layout Annotations | OCR Documents | GCS OCR |
|---------|-------------------|---------------|---------|
| diqa-5000 | 57,763 | 5,500 | ❌ |
| funsd | ❌ | 1,338 | ✅ 14 files |
| invoices-kaggle | 18,462 | 1,414 | ❌ |
| mobile-receipts-voxel51 | 4,839 | 713 | ❌ |
| nist-sd2 | 36,311 | 5,590 | ❌ |
| nist-sd6 | 37,158 | 5,595 | ❌ |
| rvl-cdip | 144,976 | 16,000 | ❌ |
| smartdoc-qa | 2,762 | 3,000 | ❌ |
| sroie | 12,568 | 2,043 | ✅ 22 files |
| **TOTAL** | **314,839** | **41,193** | **2 datasets** |

---

## 6. Recommended Actions (Priority Order)

### Immediate (High ROI)

1. **Update DATASET_CATALOG.md** to reflect DocLayNet and CC-OCR text availability
   - DocLayNet: Add text label status (81,471 JSON files with cell text)
   - CC-OCR: Add text label status (39 TSV files with answer column)
   - Estimated effort: 30 minutes

2. **Extract OCR for tablebank** (278K images)
   - Already has COCO layout annotations
   - Large volume, high training value
   - Estimated effort: 3-5 days batch processing

3. **Extract Layout for rvl_cdip** (400K images)
   - Already has extracted OCR (16K docs processed)
   - Largest document classification dataset
   - Estimated effort: 5-7 days batch processing

> **Note**: DocLayNet OCR extraction removed - already has GT text in per-document JSONs.

### Short-term

1. **Convert XML to YOLO for iam_handwriting** (130K images)
   - ✅ Full dataset downloaded (words, lines, forms, XML, ASCII labels)
   - ✅ Ground truth text available in `ascii/words.txt`
   - ✅ XML bounding boxes available (need YOLO format conversion)
   - Estimated effort: 1 day (script to convert XML → YOLO)

2. **Convert PAGE XML to YOLO for muharaf** (25K images)
   - ✅ Full dataset downloaded (457 page JPGs, 24,495 line PNGs)
   - ✅ Ground truth Arabic text (24,495 TXT files for line images)
   - ✅ PAGE XML annotations (1,216 files with polygon coords)
   - ✅ JSON annotations (3,648 files with region metadata)
   - ❌ No YOLO/COCO format labels
   - Estimated effort: 1 day (script to convert PAGE XML polygons → YOLO bboxes)

3. **Complete synth_multiscript generation** (250K target, 27K done)
   - Script detection training
   - Already in progress

### Long-term

1. Process remaining language/script datasets as needed
2. Consider whether IQA datasets (realdae, dibco) need layout

---

## 7. Changelog

| Date | Changes |
|------|---------|
| 2025-02-01 | **Template v1.2.0**: Added Section 5.2 (Class/Category Definitions), 5.3 (Language & Script Coverage), 6.5 (Benchmark Results), and Section 10 (Dataset-Specific Notes) based on compliance audit |
| 2025-02-01 | **Second Text Investigation**: MIDV500, receipts_hitl, pucit_ohul_urdu have text; CVSI, signatr6k confirmed no text |
| 2025-02-01 | **Template Compliance Audit**: Added Section 9 documenting 48 extra sections in catalog not in template |
| 2025-02-01 | **Text Label Investigation**: Discovered DocLayNet has 81,471 JSON files with text; CC-OCR has text in TSV files |
| 2025-02-01 | Added Muharaf: 25K images (457 pages + 24,495 lines), GT Arabic text, PAGE XML polygons, needs YOLO conversion |
| 2025-02-01 | Updated IAM Handwriting: full dataset downloaded (130K images, GT text, XML bboxes) |
| 2025-01-31 | Initial report created from comprehensive dataset audit |

---

## 8. Text Label Investigation Results (2025-02-01)

Investigation of four datasets previously listed as having no ground truth text labels.

### DocLayNet ✅ HAS TEXT LABELS

**Finding**: DocLayNet contains per-document JSON files with text content.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/documents/doclaynet/ground_truth/json/` |
| **File Count** | 81,471 JSON files (one per page) |
| **Format** | JSON with `cells` array containing `text`, `bbox`, `font` fields |

**Sample structure**:

```json
{
  "metadata": {...},
  "cells": [
    {
      "bbox": [97.44, 70.39, 18.92, 9.48],
      "text": "The",
      "font": {"color": [0,0,0,255], "name": "/OECHKF+Univers-Bold", "size": 1}
    },
    ...
  ]
}
```

**Action Required**: Update DATASET_CATALOG.md to mark DocLayNet as having text GT.

---

### TableBank ❌ NO TEXT LABELS AVAILABLE

**Finding**: Confirmed - TableBank only has bounding box annotations for table detection.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/tables/tablebank/TableBank/Detection/annotations/` |
| **Format** | COCO JSON with table bounding boxes only |
| **Original Source** | [GitHub: doc-analysis/TableBank](https://github.com/doc-analysis/TableBank) |

**From original source**: "HTML tag sequences representing row and column layout structure" - this is structural markup only, not textual content.

**Action Required**: OCR extraction needed if text labels are required.

---

### DocSynth300K ❌ NO TEXT LABELS AVAILABLE

**Finding**: Confirmed - DocSynth300K only has YOLO-format layout annotations.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/layout/docsynth300k/` |
| **Format** | Parquet files with `filename`, `image_data`, `anno_string` (YOLO coords) |
| **Original Source** | [HuggingFace: juliozhao/DocSynth300K](https://huggingface.co/datasets/juliozhao/DocSynth300K) |

**Sample anno_string**: `"23 0.094 0.559 0.786 0.559 0.786 0.631..."` (class_id + polygon coordinates)

**Action Required**: This is a synthetic layout dataset - text extraction is not applicable.

---

### CC-OCR ✅ HAS TEXT LABELS

**Finding**: CC-OCR contains text labels in the TSV annotation files.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/language/huggingface_downloads/CC-OCR/` |
| **File Count** | 39 TSV files across 4 tracks (7,058 images total) |
| **Format** | TSV with columns: `index`, `image`, `image_name`, `question`, `answer`, `category`, `l2-category`, `split` |

**Text label column**: The `answer` column contains the OCR ground truth text.

**Sample**:

```text
answer: 非本协议另有规定或双方另有其它书面约定，租金...
answer: \section*{English First Paper} Subject code: 107...
```

**Action Required**: Update DATASET_CATALOG.md to mark CC-OCR as having text GT.

---

*This report should be updated when extraction jobs complete or new datasets are added.*

---

## 9. Template Compliance Gaps (2025-02-01)

> **Purpose**: Identify catalog entries with sections NOT in the template that would be lost if blindly reformatted.
> **Template Version**: 1.2.0 (with Section 2 "Source Data Inventory", Section 5.2-5.3, Section 6.5, Section 10)

### 9.1 Sections in Catalog NOT in Template

These sections appear in catalog entries but are **not defined in DATASET_TEMPLATE.md**. They contain valuable information that must be preserved during template alignment.

#### High-Risk (Unique dataset-specific content)

| Section Name | Datasets Using | Content Type | Risk if Lost |
|--------------|----------------|--------------|--------------|
| **Composition by Source** | TableBank | Train/val/test counts by LaTeX vs Word | HIGH - Split statistics |
| **Benchmark Performance** | TableBank, PubTabNet, FinTabNet, DocLayNet, RVL-CDIP, FUNSD, SROIE, HASYv2, NIST SD-19, DIQA-5000, DIBCO, im2latex, RealDAE, OmniDocBench | Model F1/mAP scores, competition results | HIGH - Evaluation baselines |
| **Document Categories** | DocLayNet | 6 categories (Financial, Scientific, Laws, etc.) | HIGH - Domain taxonomy |
| **Layout Classes** | DocLayNet | 11 classes (Caption, Footnote, Formula, etc.) | HIGH - Label definitions |
| **Document Classes** | RVL-CDIP | 16 classes (Letter, Form, Email, etc.) | HIGH - Classification taxonomy |
| **Form Types Included** | NIST SD-2, SD-6 | Tax form types (1040, W-2, etc.) | MEDIUM - Form taxonomy |
| **Entity Types** | FUNSD, SROIE | NER tags (question, answer, header, etc.) | HIGH - NER label definitions |
| **Data Provenance** | RVL-CDIP | Legacy Tobacco origin, historical context | MEDIUM - Provenance tracking |
| **Data Quality Notes** | Bhutan Financial | Exclusion details (blank pages, rotated) | HIGH - Quality filtering info |
| **Annotation Notes** | FinTabNet | Limitations (no row positions, empty cells) | HIGH - Annotation caveats |
| **Annotation Quality** | DocLayNet | Double/triple annotated, crowdsourced quality | MEDIUM - Quality indicators |
| **Text Labels** | DocLayNet | JSON cell text structure details | HIGH - Parser implementation details |
| **Problem Versions** | MathVerse | 6 problem types | MEDIUM - Task variants |
| **Legibility Assessment** | Muharaf | Legibility scoring methodology | HIGH - Quality metrics |
| **Scripts Included** | MDIW-13 | 13 script list | HIGH - Script taxonomy |
| **Languages Included** | MLT-19 | 10 language list | HIGH - Language taxonomy |
| **Script Classes** | SIW-13, CVSI-2015, MLe2e | Script classification labels | HIGH - Classification taxonomy |
| **Cyrillic Coverage** | MIDV-500 | Countries with Cyrillic script | MEDIUM - Coverage details |
| **Tracks** | CC-OCR | Task tracks (scene, document, handwriting, etc.) | HIGH - Task organization |
| **Distortion Types** | DIQA-5000 | 5 distortion types (blur, noise, etc.) | HIGH - Degradation taxonomy |
| **OCR Noise Types Evaluated** | OHR-Bench | Noise types tested | MEDIUM - Evaluation scope |
| **Document Domains** | OHR-Bench | 8 domain categories | MEDIUM - Domain coverage |
| **Document Sources** | OmniDocBench | Source document categories | MEDIUM - Provenance |
| **Document Types** | FinanceBench | Financial document types | MEDIUM - Taxonomy |
| **Data Structure** | FinanceBench | JSON structure with evidence fields | HIGH - Schema details |
| **Hierarchical Structure** | HierText | Word → Line → Paragraph hierarchy | HIGH - Annotation structure |
| **Use Cases** | HierText | Word spotting, text detection, etc. | MEDIUM - Application notes |
| **Graded Assessment Derivation** | HierText | Legibility → handwritten grade mapping | HIGH - Quality scoring |
| **Score Conversion** | OCR-Quality | Word/char error rate mappings | HIGH - Metric conversion |
| **Annotation Schema** | OCR-Quality | iqa_score, ocr_confidence, degradation_type | HIGH - Schema details |
| **GCS Exclusion Note** | Doc3D | Why excluded from GCS upload | LOW - Infrastructure note |
| **Competition Tasks** | SROIE | ICDAR 2019 tasks | MEDIUM - Competition context |
| **Ground Truth (UMD)** | Tobacco-800 | UMD ground truth details | HIGH - External GT reference |
| **Benchmark Tasks** | Tobacco-800 | What it's used for | MEDIUM - Use case |
| **Sub-Datasets Included** | Historical Degraded | Component datasets | HIGH - Composition |
| **Degradation Types Present** | RealDAE, Historical Degraded | Types of degradation | HIGH - Degradation taxonomy |
| **Task-Specific Splits** | RealDAE | Enhancement/denoising splits | HIGH - Split organization |
| **Associated Model** | RealDAE | GAN model info | MEDIUM - Model reference |
| **Quality Tier Distribution** | Synthetic Multi-Script | Quality tier percentages | HIGH - Quality stratification |
| **Resolution Tiers** | Synthetic Multi-Script | NaFlex resolution tiers | HIGH - Resolution design |
| **IQA Labels (8 Dimensions)** | Synthetic Multi-Script | IQA label definitions | HIGH - Label schema |
| **Document Composition** | Synthetic Multi-Script | Layout statistics | MEDIUM - Composition stats |
| **Script-Confusable Pairs** | OpenLID-v2 | Confusable script pairs | HIGH - Script confusion matrix |
| **Key Features** | OpenLID-v2, Synthetic | Key capabilities | LOW - Summary |
| **Download Instructions** | MLT-19, FinanceBench | How to obtain data | MEDIUM - Acquisition |
| **External References** | OpenLID-v2 | Related papers/resources | LOW - References |
| **Dataset Variants** | HASYv2 | Original vs fold versions | MEDIUM - Version tracking |
| **Label Structure** | HASYv2 | CSV label format | HIGH - Parser implementation |

#### Summary by Risk Level

| Risk Level | Count | Action Required |
|------------|-------|-----------------|
| HIGH | 28 sections | Must preserve - add to template or document separately |
| MEDIUM | 16 sections | Should preserve - consider template expansion |
| LOW | 4 sections | Optional - can be summarized or moved to notes |

### 9.2 Template Sections Missing from Catalog Entries

These template sections are **not consistently present** in catalog entries:

| Template Section | Present In | Missing From | Action |
|------------------|------------|--------------|--------|
| **2. Source Data Inventory** (NEW) | 0 entries | ALL entries | Backfill during sprint |
| **2.2 Dataset Split Locations** (NEW) | 0 entries | ALL entries | Backfill during sprint |
| **3c. Data Locations table** | ~15 entries | ~35 entries | Partial - needs expansion |
| **4.1 Split Coverage** (NEW) | 0 entries | ALL entries | Backfill during sprint |
| **6.1-6.4 IQA Subsections** | 0 entries | ALL entries | Currently flat "IQA Profile" |
| **7. Known Issues & Limitations** | ~5 entries | ~45 entries | Rarely documented |
| **8. Representative Samples** | 0 entries | ALL entries | No images referenced |
| **Training/Val/Test Split Paths** | ~5 entries | ~45 entries | Critical gap identified |

### 9.3 Template Updates Implemented (v1.2.0)

Based on this analysis, the following sections were added to DATASET_TEMPLATE.md v1.2.0:

#### ✅ Added to Template (Structured Sections)

| New Section | Purpose | Maps From Catalog Sections |
|-------------|---------|---------------------------|
| **5.2 Class/Category Definitions** | Standardized taxonomy table | Document Categories, Document Classes, Layout Classes, Script Classes, Entity Types, Form Types, Distortion Types, Document Domains |
| **5.3 Language & Script Coverage** | Multilingual dataset documentation | Scripts Included, Languages Included, Cyrillic Coverage, Script-Confusable Pairs |
| **6.5 Benchmark Results** | Published model performance | Benchmark Performance (14 datasets), Competition Tasks |

#### ✅ Added to Template (Freeform Notes Section)

| New Section | Purpose | Maps From Catalog Sections |
|-------------|---------|---------------------------|
| **10.1 Annotation Caveats** | Dataset-specific limitations | Data Quality Notes, Annotation Notes, Annotation Quality, Legibility Assessment |
| **10.2 Implementation Notes** | Parser-specific details | Text Labels, Label Structure, Data Structure, Hierarchical Structure, Annotation Schema |
| **10.3 External Resources** | Associated models, competition context | Associated Model, Ground Truth (UMD), External References, Download Instructions, Key Features |
| **10.4 Custom Metrics** | Dataset-specific scoring | Graded Assessment Derivation, Score Conversion, Quality Tier Distribution, Resolution Tiers, IQA Labels, Task-Specific Splits |

#### Mapping Summary

| Category | Original Sections | Template Location | Action |
|----------|-------------------|-------------------|--------|
| **Taxonomies** (15 sections) | Document Categories, Classes, Entity Types, etc. | Section 5.2 | Standardize to table format |
| **Multilingual** (4 sections) | Scripts, Languages, Cyrillic Coverage | Section 5.3 | Standardize to table format |
| **Benchmarks** (14 datasets) | Benchmark Performance, Competition Tasks | Section 6.5 | Standardize to table format |
| **Caveats** (5 sections) | Quality Notes, Annotation Notes, etc. | Section 10.1 | Preserve as-is |
| **Implementation** (5 sections) | Text Labels, Label Structure, etc. | Section 10.2 | Preserve as-is |
| **Resources** (5 sections) | Associated Model, Download Instructions, etc. | Section 10.3 | Preserve as-is |
| **Custom Metrics** (6 sections) | Quality Tiers, Resolution Tiers, etc. | Section 10.4 | Preserve as-is |
| **Low-value** (4 sections) | GCS Exclusion Note, Key Features, etc. | Section 10.3 or omit | Optional |

### 9.4 Sprint Checklist: Per-Dataset Review

When reviewing each dataset, check for:

- [ ] **Source Data Inventory** (Section 2): Document what original labels/metadata are provided
- [ ] **Split Locations** (Section 2.2): Add train/val/test paths
- [ ] **Parser Potential** (Section 2.6): What can be extracted
- [ ] **Split Coverage** (Section 4.1): Verify counts match Layer 2
- [ ] **Extra Sections**: Identify any unique content to preserve
- [ ] **Missing Sections**: Note which standard sections are missing

### 9.5 Datasets Requiring Special Attention

These datasets have extensive custom sections that need careful preservation:

| Dataset | Custom Sections | Notes |
|---------|----------------|-------|
| **DocLayNet** | 5 extra sections | Document Categories, Layout Classes, Annotation Quality, Text Labels, Benchmark Performance |
| **RVL-CDIP** | 4 extra sections | Document Classes, Data Provenance, Benchmark Performance |
| **Synthetic Multi-Script** | 6 extra sections | Quality Tier, Resolution Tiers, IQA Labels, etc. |
| **HierText** | 4 extra sections | Hierarchical Structure, Use Cases, Graded Assessment |
| **OpenLID-v2** | 4 extra sections | Language-Script Coverage, Script-Confusable Pairs, Key Features |
| **FUNSD** | 3 extra sections | Entity Types, Benchmark Performance |
| **SROIE** | 3 extra sections | Entity Types, Benchmark Performance, Competition Tasks |
| **FinanceBench** | 3 extra sections | Document Types, Data Structure, Key Research Finding |

---

## 10. Second Text Label Investigation Results (2025-02-01)

Investigation of five additional datasets previously listed as having no ground truth text labels.

### MIDV500 ✅ HAS TEXT LABELS

**Finding**: MIDV500 contains text field values in document template JSON files.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/language/midv500_data/midv500/*/ground_truth/*.json` |
| **Template Files** | 50 document types (one template JSON per ID document type) |
| **Frame Files** | 15,050 JSON files (quad coordinates for document detection per video frame) |
| **Format** | JSON with `field##` entries containing `quad` (bbox) and `value` (text) |

**Sample structure** (from `01_alb_id.json`):

```json
{
  "field01": {"quad": [[334, 122], [410, 122], [410, 152], [334, 152]], "value": "Sojli"},
  "field02": {"quad": [[334, 179], [438, 179], [438, 207], [334, 207]], "value": "Monika"},
  "field03": {"quad": [[334, 237], [619, 237], [619, 269], [334, 269]], "value": "Shqiptare/Albanian"},
  "field05": {"quad": [[334, 353], [513, 353], [513, 378], [334, 378]], "value": "01-01-1980"},
  "field08": {"quad": [[693, 236], [863, 236], [863, 264], [693, 264]], "value": "200000907"}
}
```

**Text Content**: Names, nationalities, dates, document numbers, gender, etc.

**Note**: Individual frame JSONs only contain `quad` coordinates - text values are in the per-document-type template.

---

### receipts_hitl ✅ HAS TEXT LABELS

**Finding**: receipts_hitl contains text transcriptions in Supervisely-format JSON annotation files.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/forms/receipts_hitl/ds0/ann/` |
| **File Count** | 193 JSON annotation files |
| **Image Count** | 192 receipt images |
| **Format** | Supervisely JSON with `objects` array containing `tags` with transcriptions |

**Sample structure**:

```json
{
  "objects": [
    {
      "classTitle": "Text",
      "geometryType": "rectangle",
      "points": {"exterior": [[226.0, 54.0], [457.0, 76.0]]},
      "tags": [
        {"name": "Transcription", "value": "Katana Sushi"},
        {"name": "Category", "value": "Business name"}
      ]
    }
  ]
}
```

**Categories available**: Business name, Business address, Business phone, Business other information, Time and date, Item information, Subtotal, Tax, Total, Other

---

### pucit_ohul_urdu ✅ HAS TEXT LABELS

**Finding**: PUCIT-OHUL contains Urdu text transcriptions in Excel spreadsheets.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/language/pucit_ohul_urdu/Pucit/` |
| **Train Labels** | `train_labels_v2.xlsx` (6,489 rows) |
| **Test Labels** | `test_labels_v2.xlsx` (998 rows) |
| **Total** | 7,487 labeled line images |
| **Format** | Excel with columns: `Num` (image ID), `Caption` (original text), `Revised` (corrected text) |

**Sample rows**:

| Num | Caption | Revised |
|-----|---------|---------|
| 1-1 | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان |
| 1-2 | کے سفارت کارانہ اور دیرینہ کاروباری اور | کے سفارت کارانہ اور دیرینہ کاروباری اور |

**Note**: Image filenames correspond to `Num` column (e.g., `1-1.png` for row with Num="1-1")

---

### CVSI ❌ NO TEXT LABELS AVAILABLE

**Finding**: Confirmed - CVSI only has script classification labels encoded in folder structure.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/language/cvsi/` |
| **Structure** | `Training/`, `Validation/`, `Testing/` → Script folders (Arabic, Bengali, etc.) |
| **Scripts** | 10 scripts: Arabic, Bengali, English, Gujrathi, Hindi, Kannada, Oriya, Punjabi, Tamil, Telegu |
| **Image Count** | 10,715 images total |
| **Format** | Images organized by script folder (no annotation files) |

**Purpose**: Script identification task - classify which script is present in an image. No OCR text transcription provided or applicable.

---

### signatr6k ❌ NO TEXT LABELS AVAILABLE

**Finding**: Confirmed - SignaTR6K only has segmentation masks, not text transcriptions.

| Attribute | Value |
|-----------|-------|
| **Location** | `/mnt/e/image_detection/01_base_data/handwriting/signatr6k/` |
| **Structure** | `train/`, `validation/`, `test/` → `crop/` (images) + `label/` (masks) |
| **Train Images** | 5,169 image/mask pairs |
| **Format** | PNG images with corresponding PNG segmentation masks |
| **Labels** | Pixel-level segmentation masks (signature vs text vs background) |

**Purpose**: Handwritten and printed text segmentation task. The "labels" are segmentation masks showing which pixels belong to signatures, printed text, or handwritten text - NOT OCR transcriptions of what the text says.

**Paper**: [Handwritten and Printed Text Segmentation (arXiv:2307.07887)](https://arxiv.org/abs/2307.07887)

---

*This report should be updated when extraction jobs complete or new datasets are added.*
