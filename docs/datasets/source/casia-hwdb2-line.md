---
dataset_id: casia-hwdb2-line
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - scanner_artifacts
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### CASIA-HWDB2-line (Teklia HuggingFace Edition)

> **Quick Stats**: 52,160 images | 1,020 writers | Chinese handwriting line crops | Text transcriptions
>
> **License**: MIT | **Commercial Use**: Permitted

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | CASIA Offline Chinese Handwriting Database 2.x — Line Level (Teklia Edition) |
| **Version** | 1.0 (Teklia repack, 2024-03-14) |
| **Release Date** | 2024-03-14 (HuggingFace); original HWDB2 ~2011 |
| **Maintainer** | Teklia (HF repack); original: NLPR/CASIA (Cheng-Lin Liu, Fei Yin) |
| **HuggingFace** | [Teklia/CASIA-HWDB2-line](https://huggingface.co/datasets/Teklia/CASIA-HWDB2-line) |
| **Original Source** | [NLPR CASIA Databases](http://www.nlpr.ia.ac.cn/databases/handwriting/Download.html) |
| **Paper** | C.-L. Liu et al., "CASIA online and offline Chinese handwriting databases," ICDAR 2011 |
| **License** | MIT (Teklia repack) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/casia-hwdb2-line/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

###### Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPEG (RGB) | Chinese handwriting line crops, height=128px, variable width |
| **Labels** | Parquet (HuggingFace) | `image` (PIL) + `text` (Chinese transcription, 1-50 chars) |
| **Splits** | Official train/val/test | Writer-independent splits |

###### Dataset Split Locations

| Split | Images | Writers | Notes |
|-------|--------|---------|-------|
| **Train** | 33,400 | ~714 | Writer-independent |
| **Validation** | 8,320 | ~178 | Writer-independent |
| **Test** | 10,440 | ~128 | RESERVED — benchmark |
| **Total** | 52,160 | 1,020 | |

**Split Organization Pattern**: `huggingface_parquet` (auto-converted by HF)

**Split Status**: [VERIFIED] Official writer-independent splits from Teklia.

###### Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | Parquet `text` field | Line-level | Chinese character sequences (1-50 chars) |
| **Images** | Parquet `image` field (JPEG bytes) | Line-level | Pre-cropped, height-normalized to 128px |

###### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Extracted from NLPR HWDB2 DGRL annotations |
| **Provenance Tier** | Tier 1 (ground-truth labels from original NLPR dataset) |
| **Annotator Details** | NLPR staff; handwriting collected using Anoto digital pens |
| **Quality Assurance** | Writer-independent splits; official NLPR benchmark splits preserved |
| **GT Label Coverage** | 100% (all 52,160 line images have Chinese transcriptions) |

##### Dataset Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Images** | 52,160 | [Official — HuggingFace] |
| **Train Images** | 33,400 | [Official] |
| **Validation Images** | 8,320 | [Official] |
| **Test Images** | 10,440 | [Official] |
| **Writers** | 1,020 | [Official] |
| **Image Format** | JPEG (RGB) | [Official] |
| **Image Height** | 128px (fixed) | [Official — preprocessed] |
| **Image Width** | Variable (~200–2000px) | [Official] |
| **Label Length** | 1–50 Chinese characters | [Official] |
| **Download Size** | 1.36 GB (Parquet) | [Official — HuggingFace] |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Handwritten Chinese text (newsprint, general text) |
| **Document Types** | Line crops from full handwritten page scans (HWDB2.0-2.2) |
| **Language(s)** | Chinese Simplified (100%) |
| **Script** | Hans (Simplified Chinese) |
| **Capture Method** | Scanner (300 DPI original); images resized to 128px height for this edition |
| **Content Type** | Handwritten (100%) |
| **Writers** | 1,020 volunteers using Anoto digital pens on paper |

###### Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage |
|-----------------|----------|---------|----------|
| Chinese Simplified | Hans / zho | 52,160 | 100% |

**Script ML Class**: `HANS`

**Script Characteristics**:

- Simplified Chinese logographic characters
- Cursive and semi-cursive writing styles
- Horizontal text lines (left-to-right)
- 3,755–7,185 character class vocabulary (full GB2312 coverage in original HWDB)

##### IQA Profile

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Line crops from 300 DPI scanner pages, height-normalized |
| **Capture Device** | Flatbed scanner (original); JPEG-compressed in this edition |
| **Original Quality** | High (controlled lab collection) |
| **Compression** | JPEG (lossy, moderate quality) |
| **Known Artifacts** | None significant; height normalization may introduce resampling artifacts |
| **DPI** | 300 DPI original; pixel dimensions vary after normalization |

| Degradation Type | Severity | Notes |
|-----------------|----------|-------|
| **Blur** | LOW | Clean scanner capture |
| **Noise** | LOW | Controlled environment |
| **Contrast** | LOW | Good ink-on-white contrast |
| **Skew** | MINIMAL | Anoto pen; controlled writing conditions |
| **Compression** | MEDIUM | JPEG encoding in this edition |

##### Project Usage

**Training Heads**:

| SigLIP2 Head | Role | Notes |
|-------------|------|-------|
| Script detection (HANS) | ✅ Primary | 33K handwritten HANS line images — fills handwritten gap |
| Handwriting presence | ✅ Positive examples | All 33K images = 100% handwritten |
| Handwriting ratio (regression) | ✅ Positive | All lines are handwritten (ratio = 1.0) |
| Handwriting legibility | ⚠️ Proxy only | No explicit legibility labels; text transcription = readable |

**Addresses Known Gaps** (from `DATASET_DIVERSITY_REQUIREMENTS.md`):

- HANS target: 6,000 — gap was "Tight" with ~15K mostly printed. This adds 33K **handwritten** HANS.
- Script detection "30% handwritten" content type target — this is 100% handwritten.
- Handwriting training dataset Chinese coverage — currently **zero** real handwritten CJK.

**Parser Status**: ✅ Implemented (`src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2_line.py`)

**Phase(s)**: Script detection (Phase 10B), Handwriting presence/legibility (SigLIP2 Group 4)

##### Parser & Metadata Integration

**Parser Status**: ✅ Implemented

**Parser Location**: `src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2_line.py`

**Required Capabilities**:

1. Load HuggingFace Parquet `image` field → save to disk as JPEG
2. Extract `text` field → Chinese transcription
3. Assign script metadata: `Hans`, `zho`, `HANS`
4. Derive split assignment from HF dataset split

**Schema-Derived Comparison Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| Parquet `image` | `image_path` | ✅ Yes | High | Extracted on first parse |
| Parquet `text` | `text_content.full_text` | ✅ Yes | High | Chinese transcription |
| Script (derived) | `language.script_code` | ✅ Yes | High | Always `Hans` |
| Split (HF split name) | `provenance.split` | ✅ Yes | High | train/val/test |
| Writer ID | `provenance.writer_id` | ❌ No | Low | Not exposed in this edition |
| Line dimensions | `image_metadata.width/height` | ✅ Yes | Medium | From PIL image |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Parquet files** | `/mnt/e/.../casia-hwdb2-line/data/{train,validation,test}.parquet` | ✅ Downloaded | 1.3 GB total (train 836 MB, val 209 MB, test 255 MB) |
| **PNG images** | `/mnt/e/.../casia-hwdb2-line/images/{split}/*.png` | ❌ Not materialized | Run `scripts/materialize_casia_hwdb2_line.py` — lossless 8-bit grayscale PNG |
| **Sidecar index** | `/mnt/e/.../casia-hwdb2-line/{split}_index.jsonl` | ❌ Not generated | Written by materialize script — filename/text/char_count per image |
| **Layer 2 Metadata** | `metadata_registry/json/casia-hwdb2-line_metadata.json` | ❌ Not generated | Pending materialization + parser run |

**Materialize command**:

```bash
# Full materialization — all 52,160 images across 3 splits
uv run python scripts/materialize_casia_hwdb2_line.py

# Single split (smoke test)
uv run python scripts/materialize_casia_hwdb2_line.py --splits train
```

##### Related Datasets

| Dataset | Relationship | Notes |
|---------|-------------|-------|
| [casia-hwdb2.md](casia-hwdb2.md) | Parent dataset | Same data at page level (DGRL format) |
| [jssoda.md](jssoda.md) | Complementary CJK | Japanese handwriting |
| [mle2e.md](mle2e.md) | Complementary CJK | Mixed CJK scene text |
| [mdiw13.md](mdiw13.md) | Script complement | 13-script printed corpus |

##### Known Issues

- **No explicit legibility labels**: Transcription presence implies legibility, but no graded score.
- **Character class distribution**: HWDB2 uses GB2312 common characters (~3,755 classes); rare characters are underrepresented.
- **Height normalization artefacts**: 128px-height normalization may compress vertical-aspect characters.
- **Printed vs. handwritten only**: This edition contains only handwritten Chinese. No printed Chinese in this dataset.

##### Dataset-Specific Notes

**Relationship to CASIA-HWDB2 (Page Edition)**:

This dataset is a line-level extraction from CASIA-HWDB2 full pages. Teklia extracted individual text lines, normalized them to 128px height, and packaged as HuggingFace Parquet. The full-page DGRL version is cataloged separately at [casia-hwdb2.md](casia-hwdb2.md). Use line-level data for HTR training and script detection; use page-level for page-classification training.

**Teklia's Related Model**:

[Teklia/pylaia-casia-hwdb2](https://huggingface.co/Teklia/pylaia-casia-hwdb2) — PyLaia HTR model trained on this dataset, providing a reference accuracy baseline.

**Usage Note for Script Detection**:

For script detection training, use the train split (33,400) only. val/test splits should be reserved. Given HANS target is 6,000, a stratified 6,000-sample subset of the train split should be used to avoid class imbalance vs. other scripts.

##### 11. Layer 2 Audit Summary

###### 11.1 Quality Scorecard

> **Audit Date**: Pending | **Grade**: N/A | **Auditor**: N/A

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | - | - | Pending Layer 2 generation |
| Field Validity | - | - | Pending Layer 2 generation |
| Doc Completeness | - | - | Pending |
| **Overall** | **N/A** | | **Grade N/A** |

###### 11.2 Key Defects

> No audit performed yet. Run `scripts/integrate_casia_hwdb2_line_enrichments.py` after parser is operational.

###### 11.3 VLM Inspection Summary

> **Status**: Deferred — pending Layer 2 base metadata generation.

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ | 0 | N/A | Line crops at 128px height — not page-level; orientation concept not applicable to line strips |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | Line crops are pre-straightened during extraction; no meaningful skew angle to regress |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | N/A | 128px fixed-height crops lack DPI context; character height signal unreliable after normalization |
| SIG-G1-1 | blur_score | 🟡 | 33,400 train | IQA labeling required | Clean scanner source; expected high blur score; contributes high-quality cluster after labeling |
| SIG-G1-2 | noise_score | 🟡 | 33,400 train | IQA labeling required | Low noise (controlled scan); contributes high-score end of noise distribution after labeling |
| SIG-G1-3 | contrast_score | 🟡 | 33,400 train | IQA labeling required | Good ink-on-white contrast; contributes high-score examples after labeling |
| SIG-G1-4 | skew_score | 🟡 | 33,400 train | IQA labeling required | Minimal skew in line crops; contributes low-degradation end of skew_score range |
| SIG-G1-5 | compression_score | 🟡 | 33,400 train | IQA labeling required | JPEG encoding in this edition; contributes moderate compression-score examples after labeling |
| SIG-G1-6 | overall_quality | 🟡 | 33,400 train | IQA labeling required | High-quality controlled source; expected high overall_quality cluster after VLM labeling |
| SIG-G2-1 | script_cls | ✅ | 33,400 train | GT (HANS) | 100% handwritten Simplified Chinese; large-scale HANS — use ≤6,000 stratified subset for class balance |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | N/A | Line-level crops; post-correction orientation not applicable |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | N/A | Pre-straightened crops; post-correction residual skew not applicable |
| SIG-G4-1 | handwriting_presence_cls | ✅ | 33,400 train | GT (derived: DOMINANT) | Every image is 100% handwritten — presence class = DOMINANT |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | 33,400 train | Proxy (text transcription) | Transcription present implies legibility; proxy class = HIGH (no explicit legibility grade) |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | 33,400 train | GT (derived: PRINTED) | Chinese logographic strokes are printed-style (individual characters, not cursive joins); content_type = PRINTED |
| SIG-G4-4 | presence_reg | ✅ | 33,400 train | GT (derived: 1.0) | All images 100% handwritten; presence_reg = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 | 33,400 train | Proxy (high-end) | Controlled collection with transcription GT; proxy legibility_reg ≈ 0.8–0.9 |
| SIG-G5-1 | capture_method_cls | ✅ | 33,400 train | GT (derived: scanner) | Derived from 300 DPI flatbed scans; scanner class representative despite JPEG repackaging |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | Controlled lab collection; no shadow present |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | Flatbed scan source; no page warping |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | No programming or mathematical code content |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | N/A | 128px fixed-height crops lack reliable DPI/char-height signal; exclude from RQ head training |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ✅ | HANS only — 100% handwritten Simplified Chinese; largest handwritten CJK source in corpus |
| 2 | Capture method | ✅ | Scanner (300 DPI original; JPEG-repackaged by Teklia in this edition) |
| 3 | Document domain | 🟡 | Handwritten Chinese text lines (newsprint/given text); no structured document types |
| 4 | Layout type | ✅ | Line-level strips — uniform single-text-line layout per image |
| 5 | Text density | 🟡 | Single line per image (1–50 chars); no multi-line or paragraph density variation |
| 6 | Degradation types | 🟡 | Minimal — JPEG compression from repackaging; no blur, noise, or skew artifacts |
| 7 | Resolution/DPI range | ❌ | Fixed 128px height after normalization; no DPI diversity; character height unreliable |
| 8 | Document age | ✅ | Modern (collected 2011); no aged or historical documents |
| 9 | Text scope | ✅ | Line-level images with full Chinese character transcriptions (1–50 chars) |
| 10 | Content flags | ✅ | has_handwriting=true (100%); no tables, formulas, or figures |
| 11 | Binarization status | 🟡 | JPEG RGB (converted from 8-bit grayscale original; effectively near-grayscale) |
| 12 | Artifact types | ❌ | No shadow, warping, or watermark artifacts |
| 13 | Color mode | 🟡 | JPEG RGB (nominally color; content is grayscale ink-on-white) |
| 14 | Font variety | ❌ | Handwriting only — no printed fonts present |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

Line-level Chinese handwriting corpus providing 33,400 training images of 100% handwritten Simplified Chinese (HANS); primary contributions are script_cls (cap use at ≤6,000 stratified samples to maintain class balance), handwriting_presence_cls (DOMINANT), handwriting_content_type_cls (PRINTED), presence_reg (1.0), and capture_method_cls (scanner). MIT license permits commercial use. Test split (10,440 images) is RESERVED for benchmark evaluation; MNV4 heads and resolution_quality_reg are excluded because the 128px fixed-height crops lack page-level orientation and reliable DPI context.

---
