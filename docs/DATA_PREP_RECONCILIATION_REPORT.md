# Data Preparation Reconciliation Report

> **Generated**: 2025-01-31
> **Purpose**: Identify and resolve discrepancies in data preparation pipeline
> **Action Required**: Work through each section to align documentation with reality

---

## Executive Summary

| Category | Expected | Actual | Gap | Priority |
|----------|----------|--------|-----|----------|
| GCS Datasets | ~46 | 53 | +7 extras | P2 - Audit |
| E: Drive Base Datasets | ~46 | ~50+ | Needs alignment | P2 - Audit |
| Metadata JSON Files | 46 | 42 | -4 missing | P1 - Create |
| Parquet Conversions Needed | 1 (thought) | 3-4 actual | P1 - Convert |
| Synthetic 250k | 250,000 | 27,004 | -223K | P0 - Continue |
| Docling Processed | All | 7 | -46 datasets | P1 - Process |

---

## Section 1: GCS vs E: Drive Alignment

### 1.1 Datasets in GCS but NOT on E: Drive

These need to be either downloaded or confirmed as GCS-only:

| Dataset | In GCS | On E: | Action |
|---------|--------|-------|--------|
| `docsynth300k` | ✅ | ❌ | Download or mark GCS-only |
| `invoices_kaggle` | ✅ | ❌ | Download to `01_base_data/forms/` |
| `iqa_phase2` | ✅ | ❌ | Training dataset - check `03_training_datasets/` |
| `iqa_phase2_100k` | ✅ | ❌ | Training dataset - check `03_training_datasets/` |
| `mobile_receipts_voxel51` | ✅ | ❌ | Download to `01_base_data/forms/` |
| `receipts_hitl` | ✅ | ❌ | Download to `01_base_data/forms/` |
| `synthetic_iqa` | ✅ | ❌ | Small test dataset - download |

**Action Items**:

```bash
# Check if training datasets exist elsewhere
ls -la /mnt/e/image_detection/03_training_datasets/

# Download missing datasets from GCS
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/invoices_kaggle /mnt/e/image_detection/01_base_data/forms/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/mobile_receipts_voxel51 /mnt/e/image_detection/01_base_data/forms/
```

### 1.2 Datasets on E: Drive but NOT in GCS

These may be working directories or need upload:

| Dataset | On E: | In GCS | Action |
|---------|-------|--------|--------|
| `doc3d` | ✅ | ❌ | Research dataset - evaluate if needed |
| `doc3d_repo` | ✅ | ❌ | Source repo - don't upload |
| `github_downloads` | ✅ | ❌ | Temp directory - don't upload |
| `huggingface_downloads` | ✅ | ❌ | Cache directory - don't upload |
| `kaggle_downloads` | ✅ | ❌ | Cache directory - don't upload |
| `sample_100_images` | ✅ | ❌ | Test subset - don't upload |
| `pics` | ✅ | ❌ | Part of OCR-Quality - already covered |

### 1.3 Naming Inconsistencies

| E: Drive Name | GCS Name | Metadata Name | Resolution |
|---------------|----------|---------------|------------|
| `cc_ocr_extracted` | `cc_ocr` | `cc_ocr` | Rename E: to `cc_ocr` |
| `hasyv2_original` | `hasyv2` | `hasyv2` | Rename E: to `hasyv2` |
| `nist_sd19_pages` | `nist_sd19` | `nist_sd19` | Rename E: to `nist_sd19` |
| `ohr-bench` | `ohr_bench` | `ohr-bench` | Standardize to `ohr_bench` |
| `yarmouk_ocr_images` | `yarmouk_ocr_images` | `yarmouk_ocr` | Keep both (images vs source) |
| `pucit_ohul_urdu` | `pucit_ohul_urdu` | `pucit_ohul` | Update metadata name |

---

## Section 2: Image Format Conversion Status

### 2.1 Datasets Needing Parquet → Image Conversion

| Dataset | Parquet Location | Expected Images | Current Images | Status |
|---------|------------------|-----------------|----------------|--------|
| `cocotext` | HuggingFace | 63,686 | 800 | ⚠️ INCOMPLETE (1.3%) |
| `ocr_quality` | `01_base_data/ocr_quality/OCR-Quality.parquet` | 1,000 | 1,000 | ✅ COMPLETE |
| `docsynth300k` | GCS only | 318,000 | 0 local | ❌ NOT STARTED |
| `omnidocbench` | Complex format | Unknown | 1,358 | ⚠️ VERIFY |

### 2.2 Conversion Priority Actions

**P0 - COCOTEXT (Critical - 63K images)**:

```bash
# Current: 800 images in /mnt/e/image_detection/01_base_data/language/cocotext/
# Expected: 63,686 images
# Gap: 62,886 images (98.7% missing)

# Check if there's a parquet source
find /mnt/e/image_detection/ -name "*cocotext*" -type f 2>/dev/null

# If parquet exists, run conversion
python scripts/convert_parquet_to_images.py \
  --input /path/to/cocotext.parquet \
  --output /mnt/e/image_detection/01_base_data/language/cocotext/ \
  --format jpg
```

**P1 - DOCSYNTH300K (Large - 318K images)**:

```bash
# Decide: Download from GCS or convert from parquet?
# Storage requirement: ~30GB

# Option A: Download from GCS (if already converted)
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/docsynth300k \
  /mnt/e/image_detection/01_base_data/documents/

# Option B: Convert locally (requires parquet source)
```

### 2.3 Datasets Already Converted (Verified)

| Dataset | Image Count | Format | Location |
|---------|-------------|--------|----------|
| arabic_docs_ocr | 10,045 | JPG | `01_base_data/language/` |
| bhutan_financial | 135 | PNG | `01_base_data/documents/` |
| cc_ocr | 6,510 | PNG | `01_base_data/language/cc_ocr_extracted/` |
| cvsi | 10,715 | PNG | `01_base_data/language/` |
| dibco | 46 | PNG | `02_benchmark_only/` |
| diqa-5000 | 5,500 | JPG | `02_benchmark_only/` |
| doclaynet | 81,471 | PNG | `01_base_data/documents/` |
| financebench | 54,489 | PDF→PNG | `02_benchmark_only/` |
| fintabnet | 97,475 | PNG | `01_base_data/tables/` |
| funsd | 149 | PNG | `01_base_data/forms/` |
| funsd_plus | 1,139 | PNG | `01_base_data/forms/` |
| hasyv2 | 168,233 | PNG | `01_base_data/handwriting/hasyv2_original/` |
| hindi_ocr_synthetic | 80,009 | PNG | `01_base_data/language/` |
| historical_degraded | 1,356 | PNG | `01_base_data/degraded/` |
| iam_handwriting | 10,373 | PNG | `01_base_data/handwriting/` |
| im2latex | 10,000 | PNG | `01_base_data/formulas/` |
| maths_handwriting | 15,000 | PNG | `01_base_data/handwriting/` |
| mathverse | 6,940 | PNG | `01_base_data/formulas/` |
| mdiw13 | 290,213 | PNG | `01_base_data/language/` |
| midv500 | TBD | PNG | `01_base_data/documents/` |
| mle2e | 1,816 | PNG | `01_base_data/language/` |
| mlt19 | 19,742 | JPG | `01_base_data/language/` |
| multilingual_scripts | 3,279 | PNG | `01_base_data/language/` |
| multimodal_textbook | 1,113 | PNG | `01_base_data/educational/` |
| nepali_handwritten | 958 | PNG | `01_base_data/language/` |
| nist_db2 | 5,590 | PNG | `01_base_data/forms/` |
| nist_sd6 | 5,595 | PNG | `01_base_data/forms/` |
| nist_sd19 | 3,669 | PNG | `01_base_data/handwriting/nist_sd19_pages/` |
| ohr-bench | 9,564 | PNG/PDF | `02_benchmark_only/` |
| omnidocbench | 1,358 | PNG | `02_benchmark_only/` |
| pubtabnet | 519,030 | PNG | `01_base_data/tables/` |
| pucit_ohul_urdu | 7,401 | PNG | `01_base_data/language/` |
| realdae | 1,200 | PNG | `01_base_data/camera_captured/` |
| rvl_cdip | 16,000 | PNG | `01_base_data/documents/` |
| signatr6k | 12,514 | PNG | `01_base_data/handwriting/` |
| siw13 | 16,291 | PNG | `01_base_data/language/` |
| smartdoc-qa | 4,281 | JPG | `02_benchmark_only/` |
| sroie | 2,043 | JPG | `01_base_data/forms/` |
| tablebank | 260,025 | JPG | `01_base_data/tables/` |
| tobacco800 | 1,290 | PNG | `01_base_data/degraded/` |
| yarmouk_ocr | 15,062 | PNG | `01_base_data/language/yarmouk_ocr_images/` |

**Total Verified Images**: ~1.8M+ images across ~42 datasets

---

## Section 3: Metadata Registry Gaps

### 3.1 Datasets in GCS Missing Metadata JSON

These 14 datasets exist in GCS but have no Layer 2 metadata file:

| Dataset | Expected Action |
|---------|-----------------|
| `cocotext` | Create after completing image conversion |
| `docsynth300k` | Create after downloading/converting |
| `iam_handwriting` | ⚠️ Images exist - CREATE METADATA |
| `invoices_kaggle` | Download first, then create metadata |
| `iqa_phase2` | Training dataset - may not need Layer 2 |
| `iqa_phase2_100k` | Training dataset - may not need Layer 2 |
| `midv500_data` | Check if separate from midv500 |
| `mobile_receipts_voxel51` | Download first, then create metadata |
| `ohr_bench` | Naming issue - metadata exists as `ohr-bench` |
| `pucit_ohul_urdu` | Naming issue - metadata exists as `pucit_ohul` |
| `receipts_hitl` | Download first, then create metadata |
| `synthetic_iqa` | Small test set - may not need Layer 2 |
| `wili_2018` | Text-only corpus - no images |
| `yarmouk_ocr_images` | Duplicate of yarmouk_ocr - consolidate |

### 3.2 Priority Metadata Creation

```bash
# Run base metadata annotation for missing datasets
python scripts/annotate_base_metadata.py --dataset iam_handwriting
python scripts/annotate_base_metadata.py --dataset midv500_data

# After fixing naming:
# Rename pucit_ohul_metadata.json → pucit_ohul_urdu_metadata.json
# Rename ohr-bench_metadata.json → ohr_bench_metadata.json (if needed)
```

---

## Section 4: Synthetic 250k Generation Status

### 4.1 Current Progress

| Metric | Value |
|--------|-------|
| **Target** | 250,000 images |
| **Generated** | 27,004 images |
| **Progress** | 10.8% |
| **Scripts Covered** | 27/27 |
| **Images per Script** | ~1,000 each |
| **Target per Script** | ~9,259 each |

### 4.2 Per-Script Breakdown

| Script | Current | Target | Gap |
|--------|---------|--------|-----|
| Arab | 1,000 | 9,259 | -8,259 |
| Armn | 1,000 | 9,259 | -8,259 |
| Beng | 1,000 | 9,259 | -8,259 |
| Cyrl | 1,000 | 9,259 | -8,259 |
| Deva | 1,000 | 9,259 | -8,259 |
| Ethi | 1,000 | 9,259 | -8,259 |
| Geor | 1,000 | 9,259 | -8,259 |
| Grek | 1,000 | 9,259 | -8,259 |
| Gujr | 1,000 | 9,259 | -8,259 |
| Guru | 1,000 | 9,259 | -8,259 |
| Hans | 1,000 | 9,259 | -8,259 |
| Hant | 1,000 | 9,259 | -8,259 |
| Hebr | 1,000 | 9,259 | -8,259 |
| Jpan | 1,000 | 9,259 | -8,259 |
| Khmr | 1,000 | 9,259 | -8,259 |
| Knda | 1,000 | 9,259 | -8,259 |
| Kore | 1,000 | 9,259 | -8,259 |
| Laoo | 1,000 | 9,259 | -8,259 |
| Latn | 1,004 | 9,259 | -8,255 |
| Mlym | 1,000 | 9,259 | -8,259 |
| Mymr | 1,000 | 9,259 | -8,259 |
| Orya | 1,000 | 9,259 | -8,259 |
| Sinh | 1,000 | 9,259 | -8,259 |
| Taml | 1,000 | 9,259 | -8,259 |
| Telu | 1,000 | 9,259 | -8,259 |
| Thai | 1,000 | 9,259 | -8,259 |
| Tibt | 1,000 | 9,259 | -8,259 |

### 4.3 Generation Locations

- **Primary**: `/mnt/e/image_detection/03_training_datasets/synthetic_multiscript/`
- **Augmented**: `/mnt/e/image_detection/03_training_datasets/synthetic_multiscript_augmented/`
- **Local working**: `data/synthetic_250k/` (4 workers)

### 4.4 Resume Generation

```bash
# Check current generation status
cat data/synthetic_250k/generation.log | tail -20

# Resume generation (if stopped)
python scripts/generate_dataset_parallel.py \
  --dataset synth-multiscript-250k \
  --output /mnt/e/image_detection/03_training_datasets/synthetic_multiscript/ \
  --resume \
  --workers 4
```

---

## Section 5: Docling Processing Status

### 5.1 Current Progress

| Metric | Value |
|--------|-------|
| **Total Datasets** | 53 in GCS |
| **Docling Processed** | 7 datasets |
| **Progress** | 13.2% |

### 5.2 Completed Docling Processing

| Dataset | Output Location | Status |
|---------|-----------------|--------|
| diqa-5000 | `extracted/diqa-5000/` | ✅ Complete |
| funsd | `extracted/funsd/` + `extracted_text/funsd/` | ✅ Complete |
| nist-sd2 | `extracted/nist-sd2/` | ✅ Complete |
| nist-sd6 | `extracted/nist-sd6/` | ✅ Complete |
| rvl-cdip | `extracted/rvl-cdip/` | ✅ Complete |
| smartdoc-qa | `extracted/smartdoc-qa/` | ✅ Complete (NEW!) |
| sroie | `extracted/sroie/` | ✅ Complete |

### 5.3 Docling Processing Priority Queue

**P0 - High Value (Large datasets with text)**:

| Dataset | Images | Docling Value | Notes |
|---------|--------|---------------|-------|
| doclaynet | 81,471 | HIGH | Layout + text |
| pubtabnet | 519,030 | HIGH | Tables + text |
| tablebank | 260,025 | MEDIUM | Tables only |
| mdiw13 | 290,213 | HIGH | Multilingual text |
| mlt19 | 19,742 | HIGH | Multilingual text |

**P1 - Medium Value**:

| Dataset | Images | Docling Value | Notes |
|---------|--------|---------------|-------|
| fintabnet | 97,475 | MEDIUM | Financial tables |
| cc_ocr | 6,510 | HIGH | CJK text |
| arabic_docs_ocr | 10,045 | HIGH | Arabic text |
| hindi_ocr_synthetic | 80,009 | MEDIUM | Synthetic Hindi |

**P2 - Lower Priority**:

| Dataset | Images | Docling Value | Notes |
|---------|--------|---------------|-------|
| hasyv2 | 168,233 | LOW | Math symbols (no text) |
| im2latex | 10,000 | LOW | Formulas (no prose) |
| handwriting datasets | Various | LOW | Handwriting (OCR poor) |

### 5.4 Run Docling Processing

```bash
# Deploy Docling (if not running)
./deployment/deploy-docling.sh

# Process high-priority dataset
python deployment/scripts/gcs_processor.py doclaynet --batch-size 5000 --workers 8

# Process medium-priority datasets
python deployment/scripts/gcs_processor.py pubtabnet --batch-size 10000 --workers 16
python deployment/scripts/gcs_processor.py mdiw13 --batch-size 5000 --workers 8
```

---

## Section 6: Action Checklist

### Immediate Actions (This Week)

- [ ] **Fix COCOTEXT**: Complete conversion from 800 → 63,686 images
- [ ] **Standardize Names**: Rename E: drive folders to match GCS/metadata
  - [ ] `cc_ocr_extracted` → `cc_ocr`
  - [ ] `hasyv2_original` → `hasyv2`
  - [ ] `nist_sd19_pages` → `nist_sd19`
- [ ] **Create Missing Metadata**: Run annotation script for `iam_handwriting`, `midv500_data`
- [ ] **Continue Synthetic Generation**: Resume 250k generation (~223K remaining)

### Short-term Actions (Next 2 Weeks)

- [ ] **Docling Processing**: Process top 5 high-value datasets
  - [ ] doclaynet
  - [ ] pubtabnet
  - [ ] mdiw13
  - [ ] mlt19
  - [ ] fintabnet
- [ ] **Download Missing**: Get `invoices_kaggle`, `mobile_receipts_voxel51`, `receipts_hitl` from GCS
- [ ] **Evaluate docsynth300k**: Decide if needed locally or GCS-only

### Documentation Updates

- [ ] Update `DATASET_PROCESSING_STATUS.md` with actual conversion status
- [ ] Update `DATASET_QUICK_REFERENCE.md` with correct image counts
- [ ] Add Docling processing status section to documentation
- [ ] Fix naming inconsistencies in `DATASET_NAMING_STANDARD.md`

---

## Appendix: Quick Commands

```bash
# Check E: drive storage
du -sh /mnt/e/image_detection/01_base_data/*/

# Check GCS storage
gsutil du -sh gs://image_detection_b/image-preprocessing-detector/

# Count images in a dataset
find /mnt/e/image_detection/01_base_data/tables/pubtabnet -name "*.png" | wc -l

# Check docling deployment
curl http://192.168.1.209:5001/health

# Run metadata annotation
python scripts/annotate_base_metadata.py --dataset <dataset_name> --verbose
```

---

**Report Generated By**: Claude Code Audit
**Next Review**: After immediate actions complete
