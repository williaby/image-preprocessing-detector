---
dataset_id: casia-hwdb2
version: "1.0"
license: academic
commercial_use: false
iqa_profiles:
  - scanner_artifacts
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### CASIA-HWDB2 (Page-Level Offline Chinese Handwriting)

> **Quick Stats**: 5,091 pages (4,076 train / 1,015 test) | 1,019 writers | 300 DPI | DGRL format
>
> **License**: Academic Research Only | **Commercial Use**: ❌ Not Permitted

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | CASIA Offline Chinese Handwriting Database 2.0–2.2 (Page Level) |
| **Version** | HWDB2.0, HWDB2.1, HWDB2.2 |
| **Release Date** | ~2011 (freely downloadable since February 2020) |
| **Maintainer** | National Laboratory of Pattern Recognition (NLPR), CASIA |
| **Official Download** | [NLPR CASIA Databases](http://www.nlpr.ia.ac.cn/databases/handwriting/Download.html) |
| **Paper** | C.-L. Liu et al., "CASIA online and offline Chinese handwriting databases," ICDAR 2011 |
| **License** | Academic Research Only (no commercial use) |
| **Contact** | <liucl@nlpr.ia.ac.cn> (Cheng-Lin Liu), <fyin@nlpr.ia.ac.cn> (Fei Yin) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/casia-hwdb2/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

###### Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | DGRL (binary) | Full-page handwritten document scans; 300 DPI color |
| **Annotations** | DGRL (embedded) | Per-character bounding boxes + GB2312 labels; line-level structure |
| **Archives** | ZIP | 6 ZIP files (train+test per HWDB2.0/2.1/2.2) |

###### Dataset Split Locations

| Sub-dataset | Train Pages | Test Pages | Total Pages | Download Size |
|------------|-------------|------------|-------------|---------------|
| HWDB2.0 | 1,677 | 415 | 2,092 | — |
| HWDB2.1 | 1,200 | 300 | 1,500 | — |
| HWDB2.2 | 1,199 | 300 | 1,499 | — |
| **Total** | **4,076** | **1,015** | **5,091** | **5.3 GB (HWDB.zip from HF)** |

> **Note**: Counts verified from `HWDB.zip` (`luozhongze/HWDB2`, HuggingFace). Matches official NLPR figure of 5,091 pages from 1,019 writers. Earlier estimate of ~1,097 pages was incorrect.

**Split Organization Pattern**: `sub_dataset_train_test` (each sub-dataset has separate train/test ZIPs)

**Split Status**: [VERIFIED] Official NLPR splits. Writers are disjoint between train and test.

###### Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Character Labels** | DGRL binary | Line-level | GBK-encoded char codes per line (no per-char bboxes) |
| **Line Positions** | DGRL binary | Line-level | XYWH bounding box per text line (y, x, h, w) |
| **Line Bitmaps** | DGRL binary | Line-level | 8-bit grayscale pixel data for each line |
| **Page Dimensions** | DGRL binary | Page-level | Height, width, line count from image meta block |

###### DGRL Binary Format Specification

The DGRL (Document Ground-truth Representation Language) format is a CASIA-proprietary binary format.
One `.dgrl` file = one page. Format confirmed from `read_dgrl.py` (CASIA community reference script).

**File Header** (variable length):

```text
[4 bytes]             header_size  : uint32 LE — total header bytes including this field
[header_size-4 bytes] header_body  : variable content
  bytes [-4:-2] of header_body     : code_length (uint16 LE), typically 4
                                     (bytes per char code in label block)
```

**Image Meta** (12 bytes, immediately after header):

```text
[4 bytes]  height    : uint32 LE — page height in pixels
[4 bytes]  width     : uint32 LE — page width in pixels
[4 bytes]  line_num  : uint32 LE — number of text lines on page
```

**Line Record** (repeated `line_num` times):

```text
[4 bytes]                  char_num  : uint32 LE — characters in this line
[code_length × char_num]   labels    : each char = code_length LE bytes assembled to
                                       uint32, decoded via struct.pack('<I',code).decode('gbk')
[4 bytes]                  y         : uint32 LE — line top edge
[4 bytes]                  x         : uint32 LE — line left edge
[4 bytes]                  h         : uint32 LE — line height in pixels
[4 bytes]                  w         : uint32 LE — line width in pixels
[h × w bytes]              bitmap    : grayscale 8-bit, row-major
```

> **Note**: No per-character bounding boxes in DGRL. Only line-level positions are stored.
> Bitmap is always 8-bit grayscale regardless of original scan color depth.

###### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human (NLPR staff annotation + Anoto pen digital capture) |
| **Provenance Tier** | Tier 1 (ground-truth labels from original collection) |
| **Annotator Details** | NLPR staff; 1,019 writers each wrote 5 pages of given texts |
| **Quality Assurance** | Dual-mode capture (online + offline); cross-validated |
| **GT Label Coverage** | 100% (all characters have line-level positions + GBK labels; no per-char bboxes in DGRL format) |

##### Dataset Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Pages** | 5,091 (4,076 train / 1,015 test) | [Verified from HWDB.zip contents] |
| **Total Characters** | 1,349,414 | [Official — NLPR] |
| **Writers** | 1,019 | [Official] |
| **Pages per Writer** | 5 (given text) | [Official] |
| **Image Format** | DGRL binary, 8-bit grayscale | [Verified from read_dgrl.py] |
| **Resolution** | 300 DPI | [Official] |
| **Download Size** | 5.3 GB (HWDB.zip, HuggingFace) | [Verified] |
| **Character Classes** | ~3,755–7,185 (GB2312 + extensions) | [Official] |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Handwritten Chinese text pages (general/newsprint content) |
| **Document Types** | Full handwritten page scans |
| **Language(s)** | Chinese Simplified (100%) |
| **Script** | Hans (Simplified Chinese) |
| **Capture Method** | Flatbed scanner (300 DPI color); Anoto pen on paper |
| **Content Type** | Handwritten (100%) |
| **Text Layout** | Horizontal lines, left-to-right, free-form layout |

###### Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage |
|-----------------|----------|---------|----------|
| Chinese Simplified | Hans / zho | ~1,097 pages | 100% |

**Script ML Class**: `HANS`

##### IQA Profile

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Flatbed scanner (300 DPI color) — high quality |
| **Capture Device** | Professional flatbed scanner |
| **Original Quality** | High (controlled collection, clean paper) |
| **Compression** | Lossless in DGRL; varies if converted to JPEG |
| **Known Artifacts** | Minimal; some ink bleed-through on thin paper |

| Degradation Type | Severity | Notes |
|-----------------|----------|-------|
| **Blur** | MINIMAL | 300 DPI scanner capture |
| **Noise** | LOW | Controlled environment |
| **Contrast** | LOW | Good ink-on-white contrast |
| **Skew** | LOW | Pages placed on scanner flatbed |
| **Ink Bleed** | LIGHT | Some through-paper bleeding on thin pages |

##### Project Usage

**Training Heads**:

| SigLIP2 Head | Role | Notes |
|-------------|------|-------|
| Script detection (HANS) | ✅ Primary | Full pages of Chinese handwriting |
| Handwriting presence | ✅ Strong positives | Complete handwritten pages |
| Handwriting ratio (regression) | ✅ Positive | Pages = ~100% handwritten |
| Capture method (scanner) | ✅ Scanner diversity | 300 DPI flatbed scans |

**Unique Value vs. casia-hwdb2-line**:

The page-level edition provides full 300 DPI document images — directly compatible with SigLIP2 page-level classification. The line edition (52K crops at 128px) is better for handwriting recognition and script classification at fine granularity. Both are recommended; use page-level for page-level head training.

**Parser Status**: ✅ Implemented (`src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2.py`)

**Phase(s)**: Script detection (Phase 10B), Handwriting presence (SigLIP2 Group 4), Capture method diversity (scanner)

##### Parser & Metadata Integration

**Parser Status**: ✅ Implemented

**Parser Location**: `src/image_preprocessing_detector/annotation/parsers/handwriting/casia_hwdb2.py`

**Required Capabilities**:

1. Binary DGRL file parsing (custom CASIA format; see format spec above)
2. GBK character decoding (LE bytes → uint32 → struct.pack+GBK)
3. Extract line-level bounding boxes (XYWH) and transcription per line
4. Seek past line bitmaps without loading pixel data into memory
5. Assign script metadata: `Hans`, `zho`, `HANS`
6. Map sub-dataset (2.0/2.1/2.2) + train/test to split assignment

**Schema-Derived Comparison Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| DGRL char_code (GBK) | `text_content.full_text` | ✅ Yes | High | LE bytes → uint32 → struct.pack+GBK decode |
| DGRL line position (XYWH) | `layout_detections.bbox` | ✅ Yes | High | Line-level bbox only; no per-char bboxes in format |
| DGRL line bitmap | `image_path` (line crop) | ⚠️ Partial | Medium | Bitmap seeked past in parser; not saved to disk |
| Script (derived) | `language.script_code` | ✅ Yes | High | Always `Hans` |
| Sub-dataset + split | `provenance.split` | ✅ Yes | High | From directory/filename |
| Page dimensions | `image_metadata.width/height` | ✅ Yes | Medium | Derived from bitmaps |
| Writer ID | `provenance.writer_id` | ⚠️ Partial | Low | In filename for some sub-datasets |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **ZIPs (raw)** | `/mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2/*.zip` | ⚠️ CDN blocked | NLPR (nlpr.ia.ac.cn) TCP-unreachable from this host |
| **HF mirror** | `/mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2/HWDB.zip` | ✅ Downloaded | `luozhongze/HWDB2` on HuggingFace (5.3 GB) — all 5,091 DGRL pages |
| **DGRL files** | `/mnt/e/.../casia-hwdb2/HWDB/HWDB2.x{Train,Test}/*.dgrl` | ✅ Extracted | 5,091 `.dgrl` files across 6 sub-dataset directories |
| **PNG pages** | `/mnt/e/.../casia-hwdb2/HWDB/HWDB2.x{Train,Test}_images/*.png` | ⚠️ In progress | Run `scripts/render_casia_hwdb2_pages.py` — renders DGRL bitmaps to lossless 8-bit grayscale PNG |
| **Sidecar index** | `/mnt/e/.../casia-hwdb2/HWDB/HWDB2.x{Train,Test}_index.jsonl` | ⚠️ In progress | Written by render script — filename/writer_id/line_count per page |
| **Layer 2** | `metadata_registry/json/casia-hwdb2_metadata.json` | ❌ Not generated | Pending PNG render + parser run |

**Render command**:

```bash
# Full render — all 5,091 pages (estimate ~25 min with 4 workers)
uv run python scripts/render_casia_hwdb2_pages.py --workers 4

# Single sub-dataset (smoke test)
uv run python scripts/render_casia_hwdb2_pages.py --filter HWDB2.0Train --workers 1
```

##### Related Datasets

| Dataset | Relationship | Notes |
|---------|-------------|-------|
| [casia-hwdb2-line.md](casia-hwdb2-line.md) | Derived dataset | Teklia HF line extraction from this dataset |
| [jssoda.md](jssoda.md) | Complementary CJK | Japanese scene text |
| [muharaf.md](muharaf.md) | Analogous | Arabic cursive handwriting at page + line level |

##### Known Issues

- **DGRL format is proprietary**: No public library; parser must be custom (see format spec above).
- **GB2312 encoding**: Python `codecs` module handles this natively — `bytes.decode('gb2312')`.
- **Offline vs. online**: This catalog covers offline DGRL only. OLHWDB2.x (online POT format) not cataloged.
- **Page count uncertainty**: NLPR page combines offline+online stats; offline-only page count estimated from ZIP sizes.
- **Academic license**: No commercial use permitted. Must cite Liu et al. ICDAR 2011.

##### Dataset-Specific Notes

**Collection Methodology**:

Each of the 1,019 writers wrote 5 pages of given text using Anoto digital pens on special dotted paper. The Anoto system simultaneously captured both the online trajectory and the offline image. The offline DGRL files contain the scanned page images plus per-character bounding box annotations derived from the Anoto trajectory data, making the ground truth highly accurate.

**Relationship to CASIA-HWDB2-line (HF edition)**:

Teklia extracted individual text lines from these pages, height-normalized to 128px, and published as HuggingFace Parquet. If line-level granularity is needed without building a DGRL parser, use the HF edition. For page-level tasks or when the full 300 DPI page image is required, use this dataset directly.

##### 11. Layer 2 Audit Summary

###### 11.1 Quality Scorecard

> **Audit Date**: Pending | **Grade**: N/A | **Auditor**: N/A

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | - | - | Pending download + extraction |
| Field Validity | - | - | Pending |
| Doc Completeness | - | - | Pending |
| **Overall** | **N/A** | | **Grade N/A** |

###### 11.2 Key Defects

> No audit performed. DGRL extraction required before metadata generation.

###### 11.3 VLM Inspection Summary

> **Status**: Deferred — pending extraction and Layer 2 base metadata generation.

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ➖ | ~4,076 train pages | Derived (0° only) | All pages collected right-way-up on flatbed; useful as 0° negatives only |
| MNV4-H2 | skew_reg | ➖ | ~4,076 train pages | Derived (near-zero) | Flatbed placement produces very low skew; contributes near-zero ground truth |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~4,076 train pages | RQ labeling required | 300 DPI high-quality pages; contributes high-score examples after RQ labeling |
| SIG-G1-1 | blur_score | 🟡 | ~4,076 train pages | IQA labeling required | Minimal blur expected (flatbed scanner); contributes high-quality examples after VLM labeling |
| SIG-G1-2 | noise_score | 🟡 | ~4,076 train pages | IQA labeling required | Low noise (controlled scan); high-score examples after VLM labeling |
| SIG-G1-3 | contrast_score | 🟡 | ~4,076 train pages | IQA labeling required | Good ink contrast; high-score examples after VLM labeling |
| SIG-G1-4 | skew_score | 🟡 | ~4,076 train pages | IQA labeling required | Minimal skew degradation; contributes low-degradation end of skew_score range |
| SIG-G1-5 | compression_score | 🟡 | ~4,076 train pages | IQA labeling required | Lossless in DGRL; high compression score after conversion; label after extraction |
| SIG-G1-6 | overall_quality | 🟡 | ~4,076 train pages | IQA labeling required | High-quality cluster expected; contributes after VLM overall_quality labeling (SRCC ≥ 0.65 target) |
| SIG-G2-1 | script_cls | ✅ | ~4,076 train pages | GT (HANS) | 100% Simplified Chinese handwriting; HANS is an included class |
| SIG-G3-1 | orientation_cls (post) | ➖ | ~4,076 train pages | Derived (0° only) | Post-correction orientation — same as pre; 0° negatives only |
| SIG-G3-2 | skew_reg (post) | ➖ | ~4,076 train pages | Derived (near-zero) | Post-correction residual skew ≈ 0°; contributes low-residual examples |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~4,076 train pages | GT (derived: DOMINANT) | Every page is 100% handwritten Chinese — presence class = DOMINANT |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~4,076 train pages | Proxy (GT text transcription) | Controlled lab writing; no explicit legibility grade but clean collection implies HIGH/VERY_HIGH |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~4,076 train pages | GT (derived: PRINTED) | Chinese printed-style strokes (non-cursive individual logographs); content_type = PRINTED |
| SIG-G4-4 | presence_reg | ✅ | ~4,076 train pages | GT (derived: 1.0) | All pages entirely handwritten; presence_reg = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 | ~4,076 train pages | Proxy (high-end) | Controlled collection; proxy legibility_reg ≈ 0.8–0.9 (no graded score available) |
| SIG-G5-1 | capture_method_cls | ✅ | ~4,076 train pages | GT (derived: scanner) | 300 DPI professional flatbed — clean scanner class representative |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | Controlled lab collection; no shadow present |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | Flatbed scan; no page warping |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | No programming/mathematical code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~4,076 train pages | RQ labeling required | 300 DPI high-quality; expected high RQ score after labeling |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ✅ | HANS only — 100% Simplified Chinese; fills handwritten CJK gap |
| 2 | Capture method | ✅ | Scanner — 300 DPI professional flatbed; strong scanner class representative |
| 3 | Document domain | 🟡 | General handwritten text (newsprint/given text); no structured documents |
| 4 | Layout type | 🟡 | Full handwritten page with free-form line layout; no multi-column or table structure |
| 5 | Text density | ✅ | Dense continuous handwriting — 5 pages per writer, ~265 chars/page average |
| 6 | Degradation types | 🟡 | Minimal — ink bleed-through on thin paper only; no blur, noise, or compression artifacts |
| 7 | Resolution/DPI range | 🟡 | Uniform 300 DPI; no DPI diversity (all same resolution) |
| 8 | Document age | ✅ | Modern (collected 2011); no aged or historical documents |
| 9 | Text scope | ✅ | Line-level bounding boxes + page-level images; both granularities available |
| 10 | Content flags | ✅ | has_handwriting=true (100%); no tables, formulas, figures |
| 11 | Binarization status | 🟡 | Grayscale (8-bit DGRL storage); not binarized, not full color |
| 12 | Artifact types | ❌ | No shadow, warping, or watermark artifacts |
| 13 | Color mode | 🟡 | Grayscale (DGRL stores 8-bit grayscale bitmaps per line) |
| 14 | Font variety | ❌ | Handwriting only — no printed fonts present |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

Page-level Chinese handwriting corpus providing 4,076 training pages of controlled, high-quality HANS script from 1,019 writers; primary contributions are script_cls (HANS), handwriting_presence_cls (DOMINANT), handwriting_content_type_cls (PRINTED), presence_reg (1.0), and capture_method_cls (scanner). Academic Research Only license requires `license_restriction=academic` tagging on all derived samples; the test split (1,015 pages) is RESERVED for benchmark evaluation and must not be included in training manifests.

---
