---
owner: docs-team
purpose: Track dataset format conversion, label extraction, and processing status
schema_type: common
status: active
tags:
- datasets
- processing
- status-tracking
title: Dataset Processing Status
---

> **Last Updated**: 2026-02-09
> **Purpose**: Operational tracking of dataset processing pipeline
> **Usage**: Check current state, identify blockers, track conversion progress
> **Audience**: Development team working on dataset preparation

---

## Processing Pipeline Overview

```text
Source Format              Format Conversion         Label Extraction          Training-Ready
─────────────              ─────────────────         ────────────────          ──────────────
PDF/Parquet/JPG/PNG   →   Standardize to JPG/PNG  → Parse source labels  →   ✅ Ready for training
                                                      + Layer 2 enrichment
```

**Current Status**: 37/48 datasets training-ready (77.1%), 1 benchmark-ready

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| ✅ **Training-Ready** | 37 | 77.1% | Format standardized + labels extracted |
| ✅ **Benchmark-Ready** | 1 | 2.1% | Evaluation-only (license restrictions) |
| 🔄 **In Progress** | 8 | 16.7% | Format conversion, label extraction, or generating |
| 📚 **Non-Image Corpus** | 1 | 2.1% | Text-only corpus (openlid-v2, used for generation) |
| ❌ **Blocked** | 1 | 2.1% | Fundamental issue preventing use |

---

## Processing Status by Dataset

### ✅ Training-Ready (36 datasets)

Format standardized to JPG/PNG, labels extracted and mapped to Layer 2 schema.

| Dataset | Images | Format | Labels | Layer 2 Status | Notes |
|---------|--------|--------|--------|----------------|-------|
| arabic_docs_ocr | 10,045 | ✅ JPG | ✅ OCR text | ✅ Complete | Arabic word-level |
| bhutan-afs | 125 | ✅ PNG | ✅ Extracted | ✅ Complete | Annual reports (10 excluded: 3 blank + 7 rotated) |
| cc_ocr | 7,058 | ✅ PNG | ✅ OCR text (TSV) | ❌ Needs parser fix | CJK mixed (benchmark-only) |
| cvsi | 10,715 | ✅ PNG | ✅ Scene text boxes | ✅ Complete | Video scene text |
| diqa-5000 | 5,500 | ✅ JPG | ✅ MOS scores | ✅ Complete | IQA benchmark |
| doclaynet | 80,863 | ✅ PNG | ✅ COCO boxes | ✅ Complete | 11 DocLayNet classes |
| fintabnet | 97,475 | ✅ PNG | ✅ COCO + structure | ✅ Complete | Financial tables |
| funsd | 199 | ✅ PNG | ✅ COCO + OCR | ✅ Complete | Noisy forms |
| funsd_plus | 1,139 | ✅ PNG | ✅ COCO + OCR | ✅ Complete | Extended FUNSD |
| hasyv2 | 168,233 | ✅ PNG | ✅ Symbol labels | ✅ Complete | Math symbols |
| hindi_ocr_synthetic | 80,009 | ✅ PNG | ✅ OCR text | ✅ Complete | Synthetic Hindi |
| im2latex | 10,000 | ✅ PNG | ✅ Formula labels | ✅ Complete | Math formulas |
| invoices_kaggle | 1,414 | ✅ JPG | ✅ Extracted | ✅ Complete | Mixed formats |
| mathverse | 6,940 | ✅ PNG | ✅ Math labels | ✅ Complete | Multi-modal math |
| mdiw13 | 290,213 | ✅ PNG | ✅ Script labels | ✅ Complete | 13 scripts |
| midv500 | 3,612 | ✅ PNG | ✅ Mobile capture | ✅ Complete | ID documents |
| mle2e | 1,816 | ✅ JPG | ✅ Script labels | ⚠️ Partial | 4 scripts (pre-segmented crops), text transcriptions pending |
| muharaf | 25,711 | ✅ JPG/PNG | ✅ Arabic transcriptions | ✅ Complete | Arabic handwriting (457 pages + 24,495 lines), parser + Layer 2 metadata |
| midv500_data | 15,050 | ✅ PNG | ✅ Mobile capture | ✅ Complete | Extended MIDV-500 |
| mlt19 | 20,000 | ✅ JPG | ✅ Word boxes + script | ✅ Complete | 10 languages |
| multilingual_scripts | 3,279 | ✅ PNG | ✅ Script labels | ✅ Complete | 27 scripts synthetic |
| multimodal-textbook | 1,113 | ✅ PNG | ⚠️ Sample only | ⚠️ Partial | STEM content (sample, no Parquet) |
| nepali_handwritten | 958 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Devanagari handwriting |
| nist-sd2 | 5,590 | ✅ PNG | ✅ Form labels (.fmt) | ✅ Complete | Tax forms, splits created |
| nist-sd6 | 5,595 | ✅ PNG | ✅ Form + handwriting | ✅ Complete | Forms with handprint |
| nist-sd19 | 3,669 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Digits + letters |
| ocr-quality | 1,000 | ✅ JPG | ✅ Quality scores | ✅ Complete | Multilingual |
| ohr-bench | 8,303 | ✅ PNG | ✅ Quality scores + OCR | ✅ Complete | 7 domains, Layer 2 metadata generated (2026-02-09) |
| pucit-ohul | 7,401 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Urdu handwriting |
| pubtabnet | 519,030 | ✅ PNG | ✅ COCO + structure | ✅ Complete | Research papers |
| realdae | 1,200 | ✅ PNG | ✅ Before/after + scores | ✅ Complete | Camera-captured GT |
| rvl_cdip | 16,000 | ✅ PNG | ✅ Document class | ✅ Complete | 16 document types |
| signatr6k | 12,514 | ✅ PNG | ✅ Segmentation | ✅ Complete | Text segmentation |
| siw13 | 16,291 | ✅ PNG | ✅ Script labels | ✅ Complete | 13 scripts |
| smartdoc-qa | 4,280 | ✅ JPG | ✅ Quality + mobile | ✅ Complete | Mobile capture QA |
| sroie | 973 | ✅ JPG | ✅ Quad + OCR + Entities | ✅ Complete | Malaysian receipts (ICDAR 2019) |
| synthetic_iqa | 9 | ✅ PNG | ✅ Quality scores | ✅ Complete | Prototype samples |
| tablebank | 278,582 | ✅ JPG | ✅ COCO boxes | ✅ Complete | Table regions |
| tibhcr | 141,698 | ✅ JPG | ✅ Character labels | ✅ Complete | 47 Tibetan classes, 235 writers |
| tobacco800 | 1,290 | ✅ PNG | ✅ Degradation labels | ✅ Complete | Archival scans |
| yarmouk_ocr | 15,062 | ✅ PNG | ✅ OCR text | ✅ Complete | Arabic documents |

---

### ✅ Benchmark-Ready (1 dataset)

Datasets ready for benchmark evaluation but not for training (license restrictions or benchmark integrity).

| Dataset | Format | Images | Status | Notes |
|---------|--------|--------|--------|-------|
| **financebench** | PNG | 54,120 | ✅ Extracted | Benchmark-only (CC-BY-NC-4.0), parser implemented |

**Conversion Complete**:

- ✅ PDF→PNG conversion at 300 DPI
- ✅ Parser implemented (`FinanceBenchParser`)
- ✅ JSONL metadata available
- ❌ Layer 2 processing deferred (benchmark use only)

---

### 🔄 In Progress (9 datasets)

Format conversion, label extraction, or generation currently underway.

| Dataset | Images | Format Status | Labels Status | Blocker | Next Steps | ETA |
|---------|--------|---------------|---------------|---------|------------|-----|
| **synth-multiscript-250k** | 250,000 | 🔄 Generating | ✅ Auto-generated | Generation in progress (40/250K) | 1. Complete synthetic generation<br>2. Generated from OpenLID v2 text corpus<br>3. 27 scripts + 8 IQA dimensions | Week 2-3 |
| **cocotext** | 63,686 | ✅ Images downloaded | ✅ Labels extracted | None | Images from MS-COCO 2014 | Complete |
| **doc3d** | 100,000 | 🔄 ZIP→PNG (not extracted) | ✅ 7 GT types available | 16 ZIPs (209GB), user-defined splits | 1. Extract 16 ZIP files<br>2. Verify mesh ID structure<br>3. Decision: Parser needed? | Deferred (P3 priority) |
| **hiertext** | 11,639 | ✅ Training-Ready | ✅ Word-level labels | None | Gold standard for graded handwriting | Complete |
| **docsynth300k** | 300,000 | 🔄 Parquet→PNG | ⚠️ Needs extraction | Parquet huge (15GB+) | 1. Batch parquet conversion (chunked)<br>2. Extract synthetic labels | Week 3-4 |
| **iam** | 130,212 | ✅ Images Ready | ❌ Parser needed | 6.4 GB PNG already extracted | 1. Implement parser (XML + TXT formats)<br>2. Generate/locate split files<br>3. Extract to Layer 2 metadata | Week 2-3 |
| **mobile_receipts** | Unknown | 🔄 Parquet→JPG | ⚠️ Needs extraction | Parquet format | 1. Assess parquet size<br>2. Convert to JPG<br>3. Extract receipt labels | Week 3 |
| **omnidocbench** | Metadata | 🔄 Parquet→PNG | ⚠️ Framework metadata | Complex benchmark | 1. Understand benchmark structure<br>2. Extract relevant images<br>3. Map to our schema | Week 4+ |
| **yarmouk_source** | Unknown | 🔄 PDF→PNG | ⚠️ Needs extraction | Original PDFs | 1. Convert source PDFs<br>2. Note: yarmouk_ocr already complete | Deprioritized |
| **jssoda** | 2,000 | ✅ Images Ready | ✅ Available in manifest | Parser not implemented | 1. Implement manifest.json parser<br>2. Extract text + orientation metadata<br>3. Generate Layer 2 metadata | Week 2 |
| **dzongkha-digits** | 1,000 | ✅ HuggingFace | ✅ Class labels | Local download pending | 1. Download from HuggingFace<br>2. Enhance parser for digit labels<br>3. Generate Layer 2 metadata | Week 2-3 |

**Priority Order**:

1. **P0 (SigLIP Training)**: synth-multiscript-250k (250,000 images) - script detection critical
2. **P0 (IQA Training)**: ohr-bench (8,561 images) - already have labels
3. **P1 (Text Detection)**: cocotext (63,686 images) - scene text critical
4. **P1 (Handwriting)**: iam (130,212 images) - LARGEST handwriting corpus, parser needed
5. **P2 (Financial)**: financebench (54,121 images) - financial domain coverage
6. **P3 (Synthetic)**: docsynth300k (300,000 images) - large but synthetic
7. **P3 (Dewarping)**: doc3d (100,000 images) - specialized 3D geometry GT, large size (209GB), deferred
8. **P3 (Receipts)**: mobile_receipts (size unknown) - assess priority
9. **P4 (Benchmark)**: omnidocbench (metadata framework) - complex, defer

---

### 📚 Non-Image Corpus (1 dataset)

Text-only corpora used for synthetic dataset generation.

| Dataset | Samples | Languages | Usage | Notes |
|---------|---------|-----------|-------|-------|
| **openlid-v2** | 116M+ text samples | 201 language varieties | Source for synth-multiscript-250k generation | Text-only corpus, no images. Used to generate 250K synthetic multi-script documents for SigLIP training. |

---

### ❌ Blocked (1 dataset)

Fundamental issues preventing use for image-based training.

| Dataset | Status | Issue | Resolution |
|---------|--------|-------|------------|
| **wili_2018** | ❌ Text-only | No visual component (text corpus only) | **Cannot use for image training**. Useful for language ID if needed, but not applicable to visual IQA/layout tasks. |

---

## Format Conversion Details

### Parquet → JPG/PNG Conversion

**Datasets Requiring Conversion**: 7 datasets, ~510K images

| Dataset | Images | Parquet Size | Conversion Script | Storage Target | Status |
|---------|--------|--------------|-------------------|----------------|--------|
| cocotext | 63,686 | ~3.2 GB | `scripts/convert_parquet_to_images.py` | `01_base_data/cocotext/` | 🔄 Queued |
| docsynth300k | 300,000 | ~15 GB | `scripts/convert_parquet_to_images.py --chunked` | `01_base_data/docsynth300k/` | 🔄 Queued |
| ohr-bench | 8,561 | ~2.1 GB | `scripts/convert_parquet_to_images.py` | `02_benchmark_only/ohr-bench/` | 🔄 In Progress |
| mobile_receipts | Unknown | Unknown | `scripts/convert_parquet_to_images.py` | `01_base_data/mobile_receipts/` | 🔄 Assess first |
| omnidocbench | Unknown | Unknown | Custom script needed | `02_benchmark_only/omnidocbench/` | ⚠️ Needs analysis |

**Conversion Command**:

```bash
# Standard conversion
python scripts/convert_parquet_to_images.py \
  --input /path/to/dataset.parquet \
  --output 01_base_data/dataset_name/ \
  --format png

# Chunked conversion for large files (>10GB)
python scripts/convert_parquet_to_images.py \
  --input /path/to/large_dataset.parquet \
  --output 01_base_data/dataset_name/ \
  --format png \
  --chunked \
  --chunk_size 50000
```

**Storage Estimate**:

- cocotext: ~6 GB (JPG)
- docsynth300k: ~30 GB (PNG)
- iam: Already extracted (6.4 GB PNG)
- ohr-bench: ~4 GB (PNG)
- **Total**: ~50 GB additional storage

---

### PDF → PNG Conversion

**Datasets Requiring Conversion**: 2 datasets, ~54K pages

| Dataset | Pages | PDF Size | Conversion Script | Storage Target | Status |
|---------|-------|----------|-------------------|----------------|--------|
| financebench | 54,121 | ~8 GB | `scripts/convert_pdf_to_images.py` | `01_base_data/financebench/` | 🔄 Queued |
| yarmouk_source | Unknown | Unknown | `scripts/convert_pdf_to_images.py` | Deprioritized | ❌ Skip |

**Conversion Command**:

```bash
# Batch PDF conversion
python scripts/convert_pdf_to_images.py \
  --input 06_staging/financebench_pdfs/ \
  --output 01_base_data/financebench/ \
  --dpi 300 \
  --format png \
  --workers 8
```

**Storage Estimate**:

- financebench: ~50 GB (300 DPI PNG)

---

## Text & Layout Extraction Status

Uniform text + layout extraction across all datasets for training/testing, language/script enrichment, and confidence gap analysis.

### Extraction Methods

| Method | Description | Speed | Output Schema |
|--------|-------------|-------|---------------|
| **Docling GPU** | Full OCR + native layout (23 categories) on VPS A100 | ~1.8s/image | `docling-native` |
| **GT Conversion** | Convert existing GT annotations to page-level text + COCO layout | ~0.1ms/image | `{dataset}-gt` |

### Extraction Coverage by Dataset

| Dataset | Images | Text Extracted | Layout Extracted | Method | Status |
|---------|--------|----------------|------------------|--------|--------|
| **pubtabnet** | 509,892 | ✅ Page text | ✅ Cell bboxes | GT Conversion | ✅ Complete |
| **fintabnet** | 97,486 | ✅ Page text | ✅ Cell + structure bboxes (7 classes) | GT Conversion | ✅ Complete |
| **doclaynet** | 81,471 | ✅ Page text | ✅ 11 semantic categories | GT Conversion | ✅ Complete |
| **arabic-docs** | 10,045 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **bhutan-afs** | 125 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **cvsi** | 10,715 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **dibco** | 1,300 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **realdae** | 1,200 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **signatr6k** | 12,514 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **siw13** | 16,291 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **tobacco800** | 1,290 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **nist-sd2** | 5,590 | ✅ OCR text | ✅ Docling 23-cat layout | Docling GPU | ✅ Complete |
| **diqa-5000** | 5,500 | ✅ OCR text (5,500) | ✅ Docling 12-cat layout (5,499 images, 67K ann) | Docling GPU | ✅ Complete |
| **smartdoc-qa** | 4,280 | ⚠️ OCR text (3,000/4,280 = 70%) | ⚠️ Docling 14-cat layout (2,305/4,280 = 54%) | Docling GPU | ⚠️ Partial - 30% images failed/skipped |
| **financebench** | 54,120 | 🔄 In progress | 🔄 In progress | Docling GPU | 🔄 Running on VPS |
| **ohr-bench** | 8,561 | ✅ OCR text (1,259) | ✅ Docling 14-cat layout (1,259 images, 136K ann) | Docling GPU | ✅ Complete |
| **omnidocbench** | 1,358 | ✅ OCR text (1,358) | ✅ Docling 14-cat layout (1,357 images, 28.6K ann) | Docling GPU | ✅ Complete |
| **funsd** | 199 | ✅ Page text | ✅ Form entity bboxes (4 classes) | GT Conversion | ✅ Complete |
| **funsd_plus** | 1,139 | ✅ Page text | ✅ Word bboxes (4 classes) | GT Conversion | ✅ Complete |
| **sroie** | 973 | ✅ Page text | ✅ Text region bboxes | GT Conversion | ✅ Complete |
| **mlt19** | 10,000 | ✅ Page text | ✅ Word bboxes (10 scripts) | GT Conversion | ✅ Complete |
| **hiertext** | 11,639 | ✅ Page text | ✅ Line + word bboxes | GT Conversion | ✅ Complete |
| **tablebank** | 278,582 | ❌ Not extracted | ❌ Not extracted | Docling GPU | Pending (no text GT) |
| **doc3d** | 102,000 | ❌ Not extracted | ❌ Not extracted | Docling GPU | Pending |
| **docsynth300k** | 300,000 | ❌ Layout only | ❌ Not extracted | N/A | No text in parquet metadata |

### GT Conversion Scripts

| Script | Dataset | Input Format | Output |
|--------|---------|--------------|--------|
| `scripts/convert_pubtabnet_to_extracted.py` | PubTabNet | JSONL (cell tokens + bboxes) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_fintabnet_to_extracted.py` | FinTabNet | JSON (cell text + PDF bboxes) + XML (structure) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_doclaynet_to_extracted.py` | DocLayNet | JSON (word text + font) + COCO (11 categories) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_funsd_to_extracted.py` | FUNSD | JSON (entity text + XYXY bboxes) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_funsd_plus_to_extracted.py` | FUNSD+ | Arrow (word text + XYWH bboxes) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_sroie_to_extracted.py` | SROIE | JSON (quad bboxes + OCR text + entities) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_mlt19_to_extracted.py` | MLT-19 | TXT (quad coords + script + text) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |
| `scripts/convert_hiertext_to_extracted.py` | HierText | JSON (hierarchical paragraphs/lines/words + polygons) | `ocr_batch_N.jsonl` + `layout_batch_N.json` |

### Extraction Output Location

All extracted text + layout stored at: `metadata_registry/extracted/{dataset_name}/`

| File Pattern | Content |
|-------------|---------|
| `ocr_batch_N.jsonl` | One JSON line per image: source, text, confidence, tables_found |
| `layout_batch_N.json` | COCO-style: categories, images, annotations (bboxes) |

### Post-Processing Applied

- **BBox normalization**: Fixed 146,398 annotations across 8 Docling datasets (negative heights from PDF coordinate system)
- **Fields added**: `bbox_raw` (original coordinates) + `coord_origin` (bottom-left/top-left/pdf-points) for traceability
- **Script**: `scripts/fix_docling_bboxes.py`

---

## Label Extraction Pipeline

### Extraction Status by Label Type

| Label Type | Datasets Complete | Datasets Pending | Next Steps |
|------------|-------------------|------------------|------------|
| **COCO Layout Boxes** | 8 | 1 (omnidocbench) | Extract from benchmark metadata |
| **OCR Text (word-level)** | 12 | 4 (cocotext, docsynth, iam, mobile_receipts) | Parse parquet text fields |
| **Quality Scores** | 6 | 1 (ohr-bench converting) | Extract from parquet column |
| **Script/Language** | 12 | 3 (cocotext, docsynth, iam) | Multilingual field extraction |
| **Degradation Types** | 7 | 0 | ✅ Complete |
| **Handwriting Labels** | 6 (iam added) | 0 | ✅ All datasets have labels (IAM needs parser) |

### Extraction Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scripts/extract_coco_labels.py` | Extract COCO bounding boxes | JSON annotations | Layer 2 metadata |
| `scripts/extract_ocr_labels.py` | Extract OCR text + word boxes | Parquet/JSON | Layer 2 metadata |
| `scripts/extract_quality_scores.py` | Extract IQA scores | CSV/Parquet | Layer 2 metadata |
| `scripts/extract_script_labels.py` | Extract language/script labels | Parquet/JSON | Layer 2 metadata |
| `scripts/extract_degradation_labels.py` | Extract degradation types | JSON/text | Layer 2 metadata |

**Extraction Workflow**:

1. Convert source format (PDF/Parquet) → JPG/PNG
2. Run appropriate extraction script
3. Generate Layer 2 enrichment metadata
4. Validate extraction (spot-check)
5. Register in `DATASET_REGISTRY`

---

## Split Definition Status

### Official Splits (From Source)

**Complete**: 12 datasets have official train/val/test splits

| Dataset | Train | Val | Test | Source |
|---------|-------|-----|------|--------|
| doclaynet | 69,375 | 6,489 | 4,999 | Official DocLayNet |
| pubtabnet | 500,777 | 9,115 | 9,138 | Official PubTabNet |
| tablebank | 260,582 | 10,000 | 8,000 | Official TableBank |
| funsd | 199 | - | 199 | Official FUNSD |
| hasyv2 | 151,410 | - | 16,823 | Official HASYv2 |
| mlt19 | 10,000 | 2,000 | 8,000 | Official MLT-19 |
| cocotext | 43,686 | 10,000 | 10,000 | Official COCO-Text |
| mdiw13 | 232,170 | - | 58,043 | Competition test |

### Custom Splits (Generated)

**Complete**: 3 datasets with custom 80/10/10 splits

| Dataset | Train (80%) | Val (10%) | Test (10%) | Split File |
|---------|-------------|-----------|------------|------------|
| diqa-5000 | 4,400 | 550 | 550 | `splits/diqa_5000_splits.json` |
| smartdoc-qa | 3,424 | 428 | 428 | `splits/smartdoc_qa_splits.json` |
| ohr-bench | 6,849 | 856 | 856 | `splits/ohr_bench_splits.json` |

### No Splits (Full Dataset for Training)

**32 datasets** use entire dataset for training (no reserved test sets)

Examples: tobacco800, rvl_cdip, fintabnet, etc.

**Note**: These datasets do NOT have competition test sets. Safe to use full dataset with cross-validation.

---

## Processing Priorities

### Week 1 (Current)

- [ ] Convert ohr-bench parquet→PNG (8,561 images)
- [ ] Extract ohr-bench quality scores (already have labels)
- [ ] Verify ohr-bench train/val/test splits
- [ ] Update DATASET_REGISTRY with ohr-bench

### Week 2

- [ ] Convert cocotext parquet→JPG (63,686 images)
- [ ] Extract cocotext word boxes + scene text labels
- [ ] Convert financebench PDF→PNG (54,121 pages)
- [ ] Extract financebench table labels

### Week 3

- [ ] Implement IAM parser (XML + TXT formats)
- [ ] Generate/locate IAM split files (train/val/test)
- [ ] Assess mobile_receipts parquet size/structure
- [ ] Convert mobile_receipts if feasible

### Week 4+

- [ ] Convert docsynth300k parquet→PNG (chunked, 318K images)
- [ ] Extract docsynth synthetic labels
- [ ] Analyze omnidocbench benchmark structure
- [ ] Decide on omnidocbench extraction strategy

---

## Blockers & Resolutions

### Current Blockers

| Dataset | Issue | Priority | Owner | ETA |
|---------|-------|----------|-------|-----|
| **lrde-dbd** | Not downloaded | P2 | TBD | TBD |
| **sleukrith-ocr** | Not downloaded | P2 | TBD | TBD |

**lrde-dbd** (LRDE Document Binarization Dataset):

- **Source**: <https://www.lrde.epita.fr/wiki/Olena/DatasetDBD>
- **Count**: 375 images (official)
- **Purpose**: Document binarization benchmark, historical degradation
- **Action Required**: Download from LRDE official source
- **Target Location**: `01_base_data/02_benchmark_only/lrde-dbd/`
- **License**: Academic use (verify on download)

**sleukrith-ocr** (Khmer Manuscripts):

- **Source**: <https://huggingface.co/datasets/SEACrowd/sleukrith_ocr>
- **Count**: 657 pages
- **Purpose**: Khmer script OCR, degraded manuscript training
- **Action Required**: Download from HuggingFace
- **Target Location**: `01_base_data/multilingual/sleukrith-ocr/`
- **License**: CC-BY-SA 4.0 (verify on HuggingFace)
- **Note**: May require HuggingFace datasets library

### Previous Blockers

| Dataset | Blocker | Impact | Resolution | Owner |
|---------|---------|--------|------------|-------|
| docsynth300k | Parquet size (15GB+) | Slow conversion | Use chunked processing | Data team |
| omnidocbench | Complex metadata framework | Unclear extraction | Needs architecture review | Data team |
| mobile_receipts | Unknown size/structure | Unknown priority | Assess parquet first | Data team |

### Resolved

| Dataset | Previous Blocker | Resolution Date | How Resolved |
|---------|------------------|-----------------|--------------|
| yarmouk_ocr | Original in PDF | 2025-01-20 | Converted images found in separate directory |
| mdiw13 | Label format unclear | 2025-01-18 | Used competition annotation format |
| bhutan-afs | Missing metadata | 2025-01-15 | Manual label extraction from PDFs |

---

## Quality Validation Checklist

Before marking a dataset as ✅ Training-Ready, complete:

- [ ] **Format Conversion**
  - [ ] All images converted to JPG/PNG
  - [ ] Image quality preserved (spot-check 50 samples)
  - [ ] No data loss (image count matches source)
  - [ ] Storage location: `01_base_data/{dataset_name}/` or `02_benchmark_only/{dataset_name}/`

- [ ] **Label Extraction**
  - [ ] Labels extracted and validated (spot-check 50 samples)
  - [ ] Labels align with images (no mismatch)
  - [ ] Layer 2 metadata generated
  - [ ] Metadata location: `metadata_registry/json/{dataset_name}_layer2.json`

- [ ] **Split Definition**
  - [ ] Train/val/test splits defined (if applicable)
  - [ ] Split file created: `splits/{dataset_name}_splits.json`
  - [ ] Reserved test sets documented (if benchmark)

- [ ] **Metadata Registration**
  - [ ] Added to `DATASET_REGISTRY` in `schema_utils/dataset_source.py`
  - [ ] Canonical name + aliases defined
  - [ ] License documented
  - [ ] Special handling notes added (if applicable)

- [ ] **Documentation**
  - [ ] DATASET_QUICK_REFERENCE.md updated
  - [ ] DATASET_PROCESSING_STATUS.md updated (this file)
  - [ ] Individual dataset file created in source/ (if new dataset)

---

## Conversion Scripts Reference

### Primary Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/convert_parquet_to_images.py` | Convert parquet datasets to JPG/PNG | See [Parquet Conversion](#parquet--jpgpng-conversion) |
| `scripts/convert_pdf_to_images.py` | Convert PDF pages to PNG | See [PDF Conversion](#pdf--png-conversion) |
| `scripts/extract_layer2_metadata.py` | Extract labels and generate Layer 2 metadata | Universal label extraction |
| `scripts/validate_dataset.py` | Validate format conversion and label extraction | Quality checks |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check_parquet_structure.py` | Analyze parquet schema and size |
| `scripts/count_dataset_images.py` | Count images in dataset directories |
| `scripts/verify_splits.py` | Validate train/val/test split integrity |
| `scripts/generate_split_file.py` | Create custom 80/10/10 splits |

---

## Storage Tracking

### Current Storage Usage

| Location | Current Size | Projected Size | Notes |
|----------|--------------|----------------|-------|
| `01_base_data/` | ~420 GB | ~520 GB | After all conversions |
| `02_benchmark_only/` | ~80 GB | ~85 GB | Benchmark datasets |
| `03_training_datasets/` | ~165 GB | ~165 GB | Augmented datasets (Phase 7) |
| `metadata_registry/json/` | 2.2 GB | 2.5 GB | Layer 2 JSON metadata |
| **Total** | **~667 GB** | **~772 GB** | **+105 GB needed** |

### Storage Requirements for Pending Conversions

| Dataset | Format | Estimated Size |
|---------|--------|----------------|
| ohr-bench | PNG | ~4 GB |
| cocotext | JPG | ~6 GB |
| financebench | PNG | ~50 GB |
| iam | PNG (already extracted) | 6.4 GB ✅ |
| docsynth300k | PNG | ~30 GB |
| mobile_receipts | JPG | ~5 GB |
| **Total** | - | **~105 GB** |

**Action Required**: Ensure sufficient storage available before starting large conversions (docsynth300k, financebench)

---

## Related Documentation

- **Quick Reference**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) - Training-focused lookup
- **Individual Datasets**: [source/](source/) - 51 individual dataset files
- **Task Indices**: [indices/](indices/) - 7 task-based training recipes
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) - Canonical names and aliases
- **Label Mapping**: [../schema/LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) - Schema mappings
- **Project Plan**: [../planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) - Phased implementation

---

**Last Updated**: 2026-02-09
**Next Review**: 2026-02-14 (weekly updates)
**Contact**: Data team for processing questions
