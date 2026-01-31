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

> **Last Updated**: 2025-01-30
> **Purpose**: Operational tracking of dataset processing pipeline
> **Usage**: Check current state, identify blockers, track conversion progress
> **Audience**: Development team working on dataset preparation

---

## Processing Pipeline Overview

```
Source Format              Format Conversion         Label Extraction          Training-Ready
─────────────              ─────────────────         ────────────────          ──────────────
PDF/Parquet/JPG/PNG   →   Standardize to JPG/PNG  → Parse source labels  →   ✅ Ready for training
                                                      + Layer 2 enrichment
```

**Current Status**: 35/46 datasets training-ready (76.1%)

| Status | Count | Percentage | Description |
|--------|-------|------------|-------------|
| ✅ **Training-Ready** | 35 | 76.1% | Format standardized + labels extracted |
| 🔄 **In Progress** | 9 | 19.6% | Format conversion, label extraction, or generating |
| 📚 **Non-Image Corpus** | 1 | 2.2% | Text-only corpus (openlid-v2, used for generation) |
| ❌ **Blocked** | 1 | 2.2% | Fundamental issue preventing use |

---

## Processing Status by Dataset

### ✅ Training-Ready (35 datasets)

Format standardized to JPG/PNG, labels extracted and mapped to Layer 2 schema.

| Dataset | Images | Format | Labels | Layer 2 Status | Notes |
|---------|--------|--------|--------|----------------|-------|
| arabic_docs_ocr | 10,045 | ✅ JPG | ✅ OCR text | ✅ Complete | Arabic word-level |
| bhutan_financial | 135 | ✅ PNG | ✅ Extracted | ✅ Complete | Annual reports |
| cc_ocr | 6,533 | ✅ PNG | ✅ OCR + boxes | ✅ Complete | CJK mixed |
| cvsi | 10,715 | ✅ PNG | ✅ Scene text boxes | ✅ Complete | Video scene text |
| dibco | 343 | ✅ PNG | ✅ Degradation labels | ✅ Complete | Competition data |
| diqa-5000 | 5,500 | ✅ JPG | ✅ MOS scores | ✅ Complete | IQA benchmark |
| doclaynet | 81,471 | ✅ PNG | ✅ COCO boxes | ✅ Complete | 11 DocLayNet classes |
| fintabnet | 97,475 | ✅ PNG | ✅ COCO + structure | ✅ Complete | Financial tables |
| funsd | 398 | ✅ PNG | ✅ COCO + OCR | ✅ Complete | Noisy forms |
| funsd_plus | 1,139 | ✅ PNG | ✅ COCO + OCR | ✅ Complete | Extended FUNSD |
| hasyv2 | 168,233 | ✅ PNG | ✅ Symbol labels | ✅ Complete | Math symbols |
| hindi_ocr_synthetic | 80,009 | ✅ PNG | ✅ OCR text | ✅ Complete | Synthetic Hindi |
| historical_degraded | 1,356 | ✅ PNG | ✅ Degradation labels | ✅ Complete | Real degradation |
| im2latex | 10,000 | ✅ PNG | ✅ Formula labels | ✅ Complete | Math formulas |
| invoices_kaggle | 1,414 | ✅ JPG | ✅ Extracted | ✅ Complete | Mixed formats |
| iqa_phase7_165k | 165,000 | ✅ PNG | ✅ Quality scores | ✅ Complete | Augmented dataset |
| mathverse | 6,940 | ✅ PNG | ✅ Math labels | ✅ Complete | Multi-modal math |
| mdiw13 | 290,213 | ✅ PNG | ✅ Script labels | ✅ Complete | 13 scripts |
| midv500 | 3,612 | ✅ PNG | ✅ Mobile capture | ✅ Complete | ID documents |
| midv500_data | 15,050 | ✅ PNG | ✅ Mobile capture | ✅ Complete | Extended MIDV-500 |
| mlt19 | 20,000 | ✅ JPG | ✅ Word boxes + script | ✅ Complete | 10 languages |
| multilingual_scripts | 3,279 | ✅ PNG | ✅ Script labels | ✅ Complete | 27 scripts synthetic |
| multimodal_textbook | 1,113 | ✅ PNG | ✅ Extracted | ✅ Complete | STEM content |
| nepali_handwritten | 958 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Devanagari handwriting |
| nist_sd2 | 5,590 | ✅ PNG | ✅ Form labels | ✅ Complete | Tax forms |
| nist_sd6 | 5,595 | ✅ PNG | ✅ Form + handwriting | ✅ Complete | Forms with handprint |
| nist_sd19 | 3,669 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Digits + letters |
| ocr-quality | 1,000 | ✅ JPG | ✅ Quality scores | ✅ Complete | Multilingual |
| pucit_ohul_urdu | 7,401 | ✅ PNG | ✅ Handwriting labels | ✅ Complete | Urdu handwriting |
| pubtabnet | 568,000 | ✅ PNG | ✅ COCO + structure | ✅ Complete | Research papers |
| realdae | 1,200 | ✅ PNG | ✅ Before/after + scores | ✅ Complete | Camera-captured GT |
| rvl_cdip | 16,000 | ✅ PNG | ✅ Document class | ✅ Complete | 16 document types |
| signatr6k | 12,514 | ✅ PNG | ✅ Segmentation | ✅ Complete | Text segmentation |
| siw13 | 16,291 | ✅ PNG | ✅ Script labels | ✅ Complete | 13 scripts |
| smartdoc-qa | 4,280 | ✅ JPG | ✅ Quality + mobile | ✅ Complete | Mobile capture QA |
| sroie | 2,043 | ✅ JPG | ✅ COCO + OCR | ✅ Complete | Receipts |
| synthetic_iqa | 9 | ✅ PNG | ✅ Quality scores | ✅ Complete | Prototype samples |
| tablebank | 278,582 | ✅ JPG | ✅ COCO boxes | ✅ Complete | Table regions |
| tobacco800 | 1,290 | ✅ PNG | ✅ Degradation labels | ✅ Complete | Archival scans |
| yarmouk_ocr | 15,062 | ✅ PNG | ✅ OCR text | ✅ Complete | Arabic documents |

---

### 🔄 In Progress (9 datasets)

Format conversion, label extraction, or generation currently underway.

| Dataset | Images | Format Status | Labels Status | Blocker | Next Steps | ETA |
|---------|--------|---------------|---------------|---------|------------|-----|
| **synth-multiscript-250k** | 250,000 | 🔄 Generating | ✅ Auto-generated | Generation in progress (40/250K) | 1. Complete synthetic generation<br>2. Generated from OpenLID v2 text corpus<br>3. 27 scripts + 8 IQA dimensions | Week 2-3 |
| **cocotext** | 63,686 | 🔄 Parquet→JPG | ⚠️ Needs extraction | Parquet large (3.2GB) | 1. Convert parquet to JPG<br>2. Extract word boxes + scene text labels | Week 2 |
| **docsynth300k** | 318,000 | 🔄 Parquet→PNG | ⚠️ Needs extraction | Parquet huge (15GB+) | 1. Batch parquet conversion (chunked)<br>2. Extract synthetic labels | Week 3-4 |
| **financebench** | 54,121 | 🔄 PDF→PNG | ⚠️ Needs extraction | PDF processing | 1. PyMuPDF batch conversion<br>2. Extract financial table labels | Week 2 |
| **iam_handwriting** | 115,320 | 🔄 Parquet→PNG | ⚠️ Needs extraction | Parquet large (5GB) | 1. Convert parquet to PNG<br>2. Extract handwriting labels | Week 2-3 |
| **mobile_receipts** | Unknown | 🔄 Parquet→JPG | ⚠️ Needs extraction | Parquet format | 1. Assess parquet size<br>2. Convert to JPG<br>3. Extract receipt labels | Week 3 |
| **ohr-bench** | 8,561 | 🔄 Parquet→PNG | ✅ Quality scores | Parquet (2.1GB) | 1. Convert parquet to PNG<br>2. Labels already extracted | Week 1 |
| **omnidocbench** | Metadata | 🔄 Parquet→PNG | ⚠️ Framework metadata | Complex benchmark | 1. Understand benchmark structure<br>2. Extract relevant images<br>3. Map to our schema | Week 4+ |
| **yarmouk_source** | Unknown | 🔄 PDF→PNG | ⚠️ Needs extraction | Original PDFs | 1. Convert source PDFs<br>2. Note: yarmouk_ocr already complete | Deprioritized |

**Priority Order**:

1. **P0 (SigLIP Training)**: synth-multiscript-250k (250,000 images) - script detection critical
2. **P0 (IQA Training)**: ohr-bench (8,561 images) - already have labels
3. **P1 (Text Detection)**: cocotext (63,686 images) - scene text critical
4. **P1 (Handwriting)**: iam_handwriting (115,320 images) - large handwriting corpus
5. **P2 (Financial)**: financebench (54,121 images) - financial domain coverage
6. **P3 (Synthetic)**: docsynth300k (318,000 images) - large but synthetic
7. **P3 (Receipts)**: mobile_receipts (size unknown) - assess priority
8. **P4 (Benchmark)**: omnidocbench (metadata framework) - complex, defer

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
| docsynth300k | 318,000 | ~15 GB | `scripts/convert_parquet_to_images.py --chunked` | `01_base_data/docsynth300k/` | 🔄 Queued |
| iam_handwriting | 115,320 | ~5 GB | `scripts/convert_parquet_to_images.py` | `01_base_data/iam_handwriting/` | 🔄 Queued |
| ohr-bench | 8,561 | ~2.1 GB | `scripts/convert_parquet_to_images.py` | `01_base_data/ohr_bench/` | 🔄 In Progress |
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
- iam_handwriting: ~10 GB (PNG)
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

## Label Extraction Pipeline

### Extraction Status by Label Type

| Label Type | Datasets Complete | Datasets Pending | Next Steps |
|------------|-------------------|------------------|------------|
| **COCO Layout Boxes** | 8 | 1 (omnidocbench) | Extract from benchmark metadata |
| **OCR Text (word-level)** | 12 | 4 (cocotext, docsynth, iam, mobile_receipts) | Parse parquet text fields |
| **Quality Scores** | 6 | 1 (ohr-bench converting) | Extract from parquet column |
| **Script/Language** | 12 | 3 (cocotext, docsynth, iam) | Multilingual field extraction |
| **Degradation Types** | 7 | 0 | ✅ Complete |
| **Handwriting Labels** | 5 | 1 (iam_handwriting) | Character-level labels from parquet |

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
| doclaynet | 75,466 | 6,005 | - | Official DocLayNet |
| pubtabnet | 500,777 | 33,611 | 33,612 | Official PubTabNet |
| tablebank | 260,582 | 10,000 | 8,000 | Official TableBank |
| funsd | 199 | - | 199 | Official FUNSD |
| hasyv2 | 151,410 | - | 16,823 | Official HASYv2 |
| mlt19 | 10,000 | 2,000 | 8,000 | Official MLT-19 |
| cocotext | 43,686 | 10,000 | 10,000 | Official COCO-Text |
| dibco | 212 | - | 131 | Competition test sets |
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

Examples: tobacco800, historical_degraded, rvl_cdip, fintabnet, etc.

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

- [ ] Convert iam_handwriting parquet→PNG (115,320 images)
- [ ] Extract iam handwriting character labels
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
| bhutan_financial | Missing metadata | 2025-01-15 | Manual label extraction from PDFs |

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
  - [ ] DATASET_CATALOG.md updated (if new dataset)

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
| iam_handwriting | PNG | ~10 GB |
| docsynth300k | PNG | ~30 GB |
| mobile_receipts | JPG | ~5 GB |
| **Total** | - | **~105 GB** |

**Action Required**: Ensure sufficient storage available before starting large conversions (docsynth300k, financebench)

---

## Related Documentation

- **Quick Reference**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) - Training-focused lookup
- **Full Catalog**: [DATASET_CATALOG.md](DATASET_CATALOG.md) - Comprehensive dataset details
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) - Canonical names and aliases
- **Label Mapping**: [schema/LABEL_MAPPING_SPECIFICATION.md](schema/LABEL_MAPPING_SPECIFICATION.md) - Schema mappings
- **Project Plan**: [planning/PROJECT_PLAN.md](planning/PROJECT_PLAN.md) - Phased implementation

---

**Last Updated**: 2025-01-30
**Next Review**: 2025-02-06 (weekly updates)
**Contact**: Data team for processing questions
