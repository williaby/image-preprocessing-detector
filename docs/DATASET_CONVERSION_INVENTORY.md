# Dataset Conversion Inventory & Plan

> **Created**: 2025-01-30
> **Purpose**: Operational plan for converting PDF and Parquet datasets to image format (JPG/PNG)
> **Scope**: 7 datasets totaling ~510K images requiring conversion
> **Audience**: Data team executing conversion pipeline

---

## Executive Summary

**Total Datasets Requiring Conversion**: 7 datasets (6 Parquet, 1 PDF)
**Total Images**: ~510,000 images
**Total Storage Required**: ~105 GB
**Priority Distribution**:

- P0 (Critical): 2 datasets (258,561 images)
- P1 (High): 2 datasets (179,006 images)
- P2 (Medium): 1 dataset (54,121 images)
- P3 (Low): 2 datasets (318,000+ images)

**Timeline**: 4 weeks (staggered execution)

---

## Datasets Requiring Conversion

### Priority 0 - Critical (Week 1)

#### 1. ohr-bench (IQA Training Dataset)

**Status**: 🔄 In Progress
**Source Format**: Parquet (2.1 GB)
**Target Format**: PNG
**Image Count**: 8,561 images
**Estimated Storage**: ~4 GB

**Why Critical**:

- Primary IQA training dataset for Phase 2/3
- Quality score labels already extracted
- Blocking ML IQA model training

**Conversion Command**:

```bash
python scripts/convert_parquet_to_images.py \
  --input /path/to/ohr-bench.parquet \
  --output 01_base_data/ohr_bench/ \
  --format png \
  --workers 4
```

**Next Steps**:

1. Convert parquet→PNG (8,561 images)
2. Verify quality score labels (already extracted)
3. Generate train/val/test splits (80/10/10)
4. Update DATASET_REGISTRY
5. Register in DATASET_QUICK_REFERENCE.md

**ETA**: Week 1 (2-3 hours)

---

#### 2. synth-multiscript-250k (Script Detection Dataset)

**Status**: 🔄 Generating
**Source Format**: Synthetic generation from OpenLID v2 text corpus
**Target Format**: PNG
**Image Count**: 250,000 images (currently 40/250K generated)
**Estimated Storage**: ~25 GB

**Why Critical**:

- SigLIP script detection training (27 scripts)
- Critical for multilingual document routing
- Synthetic generation in progress

**Generation Command**:

```bash
python scripts/generate_dataset_parallel.py \
  --dataset synth-multiscript-250k \
  --text_corpus openlid-v2 \
  --output 03_training_datasets/synth_multiscript_250k/ \
  --format png \
  --workers 16 \
  --scripts 27 \
  --iqa_dimensions 8
```

**Next Steps**:

1. Complete synthetic generation (210K remaining)
2. Auto-generate Layer 2 metadata (labels included in generation)
3. Generate train/val/test splits
4. Update DATASET_REGISTRY

**ETA**: Week 2-3 (GPU-dependent generation time)

---

### Priority 1 - High (Week 2)

#### 3. cocotext (Scene Text Detection)

**Status**: 🔄 Queued
**Source Format**: Parquet (3.2 GB)
**Target Format**: JPG
**Image Count**: 63,686 images
**Estimated Storage**: ~6 GB

**Why High Priority**:

- COCO-Text official benchmark dataset
- Scene text detection critical for hybrid documents
- Word boxes + multilingual labels available

**Conversion Command**:

```bash
python scripts/convert_parquet_to_images.py \
  --input /path/to/cocotext.parquet \
  --output 01_base_data/cocotext/ \
  --format jpg \
  --quality 95 \
  --workers 8
```

**Next Steps**:

1. Convert parquet→JPG (63,686 images)
2. Extract word boxes + scene text labels from parquet
3. Use official train/val/test splits (43,686/10,000/10,000)
4. Generate Layer 2 metadata
5. Update DATASET_REGISTRY

**ETA**: Week 2 (6-8 hours conversion)

---

#### 4. iam_handwriting (Handwriting Corpus)

**Status**: 🔄 Queued
**Source Format**: Parquet (5 GB)
**Target Format**: PNG
**Image Count**: 115,320 images
**Estimated Storage**: ~10 GB

**Why High Priority**:

- Largest handwriting corpus in dataset collection
- Character-level handwriting labels
- Critical for handwriting detection training

**Conversion Command**:

```bash
python scripts/convert_parquet_to_images.py \
  --input /path/to/iam_handwriting.parquet \
  --output 01_base_data/iam_handwriting/ \
  --format png \
  --workers 8
```

**Next Steps**:

1. Convert parquet→PNG (115,320 images)
2. Extract character-level handwriting labels from parquet
3. Generate custom 80/10/10 splits (no official splits)
4. Generate Layer 2 metadata
5. Update DATASET_REGISTRY

**ETA**: Week 2-3 (12-16 hours conversion)

---

### Priority 2 - Medium (Week 2-3)

#### 5. financebench (Financial Documents)

**Status**: 🔄 Queued
**Source Format**: PDF (8 GB)
**Target Format**: PNG
**Image Count**: 54,121 pages
**Estimated Storage**: ~50 GB (300 DPI)

**Why Medium Priority**:

- Financial domain coverage (tables, charts, reports)
- Large storage footprint (50 GB)
- Useful but not blocking critical training

**Conversion Command**:

```bash
python scripts/convert_pdf_to_images.py \
  --input 06_staging/financebench_pdfs/ \
  --output 01_base_data/financebench/ \
  --dpi 300 \
  --format png \
  --workers 8 \
  --page_range 0:-1
```

**Next Steps**:

1. Convert PDF→PNG (54,121 pages at 300 DPI)
2. Extract financial table labels from source metadata
3. Generate custom 80/10/10 splits
4. Generate Layer 2 metadata
5. Update DATASET_REGISTRY

**ETA**: Week 2-3 (20-24 hours conversion)

**Storage Warning**: Requires 50 GB storage - verify availability before starting

---

### Priority 3 - Low (Week 3-4+)

#### 6. mobile_receipts (Receipt Images)

**Status**: 🔄 Assess First
**Source Format**: Parquet (size unknown)
**Target Format**: JPG
**Image Count**: Unknown
**Estimated Storage**: ~5 GB (estimated)

**Why Low Priority**:

- Unknown size/structure
- Receipt domain overlap with SROIE (already complete)
- Need assessment before committing resources

**Assessment Command**:

```bash
python scripts/check_parquet_structure.py \
  --input /path/to/mobile_receipts.parquet \
  --sample_size 100 \
  --output mobile_receipts_assessment.json
```

**Next Steps**:

1. **Assess parquet size and structure first**
2. Review sample images (quality, usefulness)
3. Decide if conversion is worth storage cost
4. If yes: Convert parquet→JPG
5. Extract receipt labels
6. Generate Layer 2 metadata

**ETA**: Week 3 (assess), Week 4+ (convert if approved)

---

#### 7. docsynth300k (Synthetic Documents)

**Status**: 🔄 Queued (Large - Chunked Processing)
**Source Format**: Parquet (15+ GB)
**Target Format**: PNG
**Image Count**: 318,000 images
**Estimated Storage**: ~30 GB

**Why Low Priority**:

- Synthetic dataset (lower priority than real data)
- Extremely large (15 GB parquet → 30 GB images)
- Requires chunked processing to avoid memory issues

**Conversion Command** (Chunked):

```bash
python scripts/convert_parquet_to_images.py \
  --input /path/to/docsynth300k.parquet \
  --output 01_base_data/docsynth300k/ \
  --format png \
  --chunked \
  --chunk_size 50000 \
  --workers 8
```

**Next Steps**:

1. **Verify storage availability (30 GB required)**
2. Convert parquet→PNG in chunks (6 chunks × 50K images)
3. Extract synthetic labels from parquet
4. Generate custom 80/10/10 splits
5. Generate Layer 2 metadata

**ETA**: Week 3-4 (30-40 hours chunked processing)

**Storage Warning**: Requires 30 GB storage - defer if storage constrained

---

### Excluded from Conversion

#### 8. omnidocbench (Benchmark Framework)

**Status**: ⚠️ Needs Architecture Review
**Source Format**: Parquet (metadata framework)
**Complexity**: High - benchmark framework, not simple dataset

**Why Excluded**:

- Complex metadata framework (not simple image dataset)
- Requires architectural analysis before extraction
- Unclear if extraction fits our schema
- Deferred to Week 4+ after simpler datasets complete

**Action**: Defer until Weeks 1-3 datasets complete

---

#### 9. yarmouk_source (Source PDFs)

**Status**: ❌ Deprioritized
**Source Format**: PDF (size unknown)
**Reason**: yarmouk_ocr already complete with 15,062 PNG images

**Action**: Skip conversion - use existing yarmouk_ocr dataset

---

## Conversion Plan Timeline

### Week 1 (Current) - P0 Critical

**Goal**: Complete IQA training dataset preparation

- [ ] **Day 1-2**: Convert ohr-bench parquet→PNG (8,561 images)
  - Verify quality score labels
  - Generate train/val/test splits
  - Update DATASET_REGISTRY
  - **Deliverable**: ohr-bench ready for Phase 2/3 IQA training

- [ ] **Day 3-7**: Monitor synth-multiscript-250k generation
  - Track progress (40/250K → 250K)
  - Prepare for Layer 2 metadata generation
  - **Deliverable**: Generation progress report

**Week 1 Metrics**:

- Datasets completed: 1 (ohr-bench)
- Images converted: 8,561
- Storage used: ~4 GB

---

### Week 2 - P1 High Priority

**Goal**: Complete scene text and handwriting datasets

- [ ] **Day 1-3**: Convert cocotext parquet→JPG (63,686 images)
  - Extract word boxes + scene text labels
  - Use official train/val/test splits
  - Generate Layer 2 metadata
  - **Deliverable**: COCO-Text ready for text detection training

- [ ] **Day 4-7**: Convert iam_handwriting parquet→PNG (115,320 images)
  - Extract character-level handwriting labels
  - Generate custom 80/10/10 splits
  - Generate Layer 2 metadata
  - **Deliverable**: IAM Handwriting ready for handwriting detection

**Week 2 Metrics**:

- Datasets completed: 2 (cocotext, iam_handwriting)
- Images converted: 179,006
- Storage used: ~16 GB

---

### Week 3 - P2 Medium + P3 Assessment

**Goal**: Complete financial dataset and assess receipts

- [ ] **Day 1-5**: Convert financebench PDF→PNG (54,121 pages)
  - Extract financial table labels
  - Generate custom 80/10/10 splits
  - Generate Layer 2 metadata
  - **Deliverable**: FinanceBench ready for financial document training

- [ ] **Day 6-7**: Assess mobile_receipts parquet
  - Analyze parquet structure and size
  - Review sample images (quality check)
  - Make conversion decision
  - **Deliverable**: mobile_receipts assessment report

**Week 3 Metrics**:

- Datasets completed: 1 (financebench)
- Images converted: 54,121
- Storage used: ~50 GB

---

### Week 4+ - P3 Low Priority (Optional)

**Goal**: Complete large synthetic datasets if storage permits

- [ ] **Week 4**: Complete synth-multiscript-250k generation
  - Finalize 250K synthetic images
  - Generate Layer 2 metadata
  - Create train/val/test splits
  - **Deliverable**: Synth-multiscript-250k ready for SigLIP training

- [ ] **Week 4+**: Convert docsynth300k (chunked processing)
  - Only if storage available (30 GB required)
  - Chunked conversion in 6 batches (50K each)
  - Extract synthetic labels
  - **Deliverable**: DocSynth300k ready (if storage permits)

- [ ] **Week 4+**: Analyze omnidocbench benchmark framework
  - Architectural review of benchmark structure
  - Decide extraction strategy
  - **Deliverable**: Extraction plan or defer decision

**Week 4+ Metrics** (if completed):

- Datasets completed: 2-3 (synth-multiscript, docsynth300k, omnidocbench)
- Images converted: 568,000+
- Storage used: ~55 GB

---

## Storage Requirements Summary

### Pre-Conversion Storage Check

**Current Storage**: ~667 GB
**Projected Storage**: ~772 GB
**Available Storage Required**: **105 GB**

| Week | Datasets | Images | Storage | Cumulative |
|------|----------|--------|---------|------------|
| Week 1 | ohr-bench | 8,561 | ~4 GB | 4 GB |
| Week 2 | cocotext, iam_handwriting | 179,006 | ~16 GB | 20 GB |
| Week 3 | financebench | 54,121 | ~50 GB | 70 GB |
| Week 4+ | synth-multiscript, docsynth300k | 568,000 | ~55 GB | 125 GB |

**Critical Actions**:

1. Verify 105 GB storage available before Week 1
2. Monitor storage after Week 3 (70 GB used)
3. Defer Week 4+ datasets if storage <55 GB available

---

## Prerequisites & Dependencies

### Required Scripts

**Conversion Scripts**:

- [x] `scripts/convert_parquet_to_images.py` - Parquet→JPG/PNG conversion
- [x] `scripts/convert_pdf_to_images.py` - PDF→PNG conversion
- [x] `scripts/check_parquet_structure.py` - Parquet analysis utility

**Extraction Scripts**:

- [x] `scripts/extract_layer2_metadata.py` - Layer 2 metadata generation
- [x] `scripts/extract_coco_labels.py` - COCO bounding box extraction
- [x] `scripts/extract_ocr_labels.py` - OCR text + word box extraction
- [x] `scripts/extract_quality_scores.py` - IQA score extraction

**Validation Scripts**:

- [x] `scripts/validate_dataset.py` - Dataset validation
- [x] `scripts/verify_splits.py` - Split integrity checks
- [x] `scripts/count_dataset_images.py` - Image counting utility

**Generation Scripts**:

- [x] `scripts/generate_dataset_parallel.py` - Synthetic dataset generation
- [x] `scripts/generate_split_file.py` - Custom split generation

### Python Dependencies

**Core Libraries**:

```bash
# Image processing
uv add pillow opencv-python-headless pymupdf

# Data processing
uv add pandas pyarrow polars

# Parallel processing
uv add joblib tqdm

# Optional: GPU acceleration
uv add pillow-simd  # If available
```

### System Requirements

**Compute**:

- CPU: 8+ cores recommended for parallel processing
- RAM: 16 GB minimum (32 GB for large datasets)
- GPU: Optional (not required for conversion)

**Storage**:

- Fast SSD recommended (30-40 hours → 15-20 hours on SSD)
- 105 GB available for all conversions
- 70 GB minimum for P0-P2 datasets

**Network** (for synth-multiscript generation):

- Access to OpenLID v2 text corpus
- GCS credentials for font downloads

---

## Quality Validation Checklist

After each conversion, verify:

### Format Conversion Validation

- [ ] **Image Count Match**: Converted count == source count
- [ ] **Format Correct**: All images in target format (JPG/PNG)
- [ ] **Quality Preserved**: Spot-check 50 random images
- [ ] **No Data Loss**: No corrupted or missing images
- [ ] **Storage Location**: Images in correct directory structure

### Label Extraction Validation

- [ ] **Labels Extracted**: All labels extracted from source
- [ ] **Label Alignment**: Labels match images (no mismatch)
- [ ] **Layer 2 Generated**: Metadata in `metadata_registry/json/`
- [ ] **Spot Check**: Manually verify 50 random labels

### Split Definition Validation

- [ ] **Splits Defined**: train/val/test splits created (if applicable)
- [ ] **Split File Created**: JSON file in `splits/` directory
- [ ] **No Leakage**: Test sets reserved for competition data
- [ ] **Split Integrity**: Verify with `scripts/verify_splits.py`

### Registration Validation

- [ ] **DATASET_REGISTRY Updated**: Entry in `schema_utils/dataset_source.py`
- [ ] **Canonical Name Defined**: Consistent naming convention
- [ ] **Aliases Documented**: All known dataset aliases listed
- [ ] **License Documented**: License and citation info included

### Documentation Validation

- [ ] **DATASET_QUICK_REFERENCE.md Updated**: Training-focused entry
- [ ] **DATASET_PROCESSING_STATUS.md Updated**: Status changed to ✅
- [ ] **DATASET_CATALOG.md Updated**: Full catalog entry (if new)

---

## Monitoring & Reporting

### Weekly Progress Reports

**Format**:

```markdown
## Week N Progress Report

**Datasets Completed**: X/Y
**Images Converted**: X,XXX
**Storage Used**: XX GB

**Completed This Week**:
- Dataset 1: [Status] [Images] [Storage]
- Dataset 2: [Status] [Images] [Storage]

**Blockers**:
- [Blocker description] - [Resolution plan]

**Next Week Plan**:
- [Dataset to convert]
- [Expected completion date]
```

### Conversion Metrics to Track

| Metric | Target | Actual | Notes |
|--------|--------|--------|-------|
| Conversion Speed | 1000 img/hour | TBD | Hardware-dependent |
| Error Rate | <0.1% | TBD | Corrupted images |
| Storage Efficiency | PNG: 1-10 MB/img | TBD | Format-dependent |
| Label Accuracy | >99% alignment | TBD | Spot-check validation |

---

## Troubleshooting Guide

### Common Issues

**Issue**: Parquet conversion fails with memory error
**Solution**: Use `--chunked --chunk_size 10000` flag

**Issue**: PDF conversion extremely slow
**Solution**: Reduce `--dpi` from 300 to 200, or increase `--workers`

**Issue**: Images corrupted after conversion
**Solution**: Check source parquet schema with `check_parquet_structure.py`

**Issue**: Label extraction mismatch
**Solution**: Verify image-label alignment with spot-check script

**Issue**: Insufficient storage during conversion
**Solution**: Defer P3 datasets, focus on P0-P2 only

---

## Related Documentation

- **Processing Status**: [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) - Current state
- **Quick Reference**: [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) - Training lookup
- **Full Catalog**: [DATASET_CATALOG.md](DATASET_CATALOG.md) - Comprehensive details
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) - Canonical names
- **Project Plan**: [planning/PROJECT_PLAN.md](planning/PROJECT_PLAN.md) - Phase timeline

---

**Document Owner**: Data team
**Last Updated**: 2025-01-30
**Next Review**: Weekly (every Monday)
