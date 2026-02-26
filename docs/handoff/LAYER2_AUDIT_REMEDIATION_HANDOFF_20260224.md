# Layer 2 Audit Remediation Handoff

**Date**: 2026-02-24
**Prepared by**: Byron Williams / Layer 2 Audit Team
**Target team**: Dataset Engineering / Metadata Operations
**Branch**: `docs/har-systematic-head-review` (current; create `chore/layer2-audit-remediation` for changes)

---

## Background

On 2026-02-24, the `layer2-audit-agent` was run against **12 datasets** that had been added to the
project in the last two weeks but had not yet been through the Layer 2 metadata audit pipeline.
This document packages the findings and assigns them into actionable work streams.

**Audit summary**:

| Dataset | Outcome | Phases Completed | Artifacts |
|---------|---------|-----------------|-----------|
| `arabic-docs` | Full audit — Grade C | 0–7 | `audit_report.md`, `defect_catalog.json` + 5 others |
| `multilingual-scripts` | Full audit — Grade C (52/100) | 0–7 | `audit_report.md`, `defect_catalog.json` + 5 others |
| `midv2020` | Full audit — 0% schema compliance | 0–7 | `audit_report.md`, `defect_catalog.json` + 5 others |
| `doc3d` | Phase 0 blocker — no metadata JSON | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `docsynth` | Phase 0 blocker — parquet not extracted | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `kuzushiji` | Phase 0 blocker — CDN unreachable | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `iiit-hw-hindi` | Phase 0 blocker — parser not registered | 0, 1 partial | `blocker_report.md` |
| `khatt` | Phase 0 blocker — no metadata JSON | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `doc3d` | Phase 0 blocker — no metadata JSON | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `casia-hwdb2` | Phase 0 blocker — DGRL not extracted | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `casia-hwdb2-line` | Phase 0 blocker — parquet not extracted | 0, 1 partial | `blocker_report.md`, `paper_ground_truth.json` |
| `openlid-v2` | Phase 0 blocker — text corpus | 0 | `blocker_report.md` |
| `wili-2018` | Phase 0 blocker — text corpus | 0 | `blocker_report.md` |

All audit artifacts are at: `scripts/audit/results/{dataset}/`

---

## Work Stream Index

| WS | Priority | Title | Datasets Affected | Est. Effort |
|----|----------|-------|------------------|-------------|
| [WS-1](#ws-1-systemic-fix-automated_prescreeningpy-stale-checks) | **P0 CRITICAL** | Fix automated_prescreening.py stale checks | ALL 51 datasets | 1–2 hours |
| [WS-2](#ws-2-full-audit-remediation--integration-script-fixes) | **P1 HIGH** | Fix integration script enum defects | arabic-docs, multilingual-scripts, midv2020 | 2–4 hours |
| [WS-3](#ws-3-materialize-docsynth-and-kuzushiji) | **P1 HIGH** | Materialize docsynth and kuzushiji | docsynth, kuzushiji | 6–16 hours |
| [WS-4](#ws-4-re-audit-casia-hwdb2-datasets-after-extraction) | **P1 HIGH** | Re-audit CASIA after extraction | casia-hwdb2, casia-hwdb2-line | 2–4 hours (post-extraction) |
| [WS-5](#ws-5-quick-win-onboarding) | **P2 MEDIUM** | Quick-win onboarding | iiit-hw-hindi, khatt, doc3d | 3–6 hours |
| [WS-6](#ws-6-housekeeping-and-schema-extensions) | **P3 LOW** | Housekeeping | openlid-v2, wili-2018, audit_config.py | 1–2 hours |

---

## Key Paths Reference

```text
PROJECT_ROOT      /home/byron/dev/image_detection
METADATA_ROOT     /mnt/e/image_detection/metadata_registry/json/
IMAGE_ROOT        /mnt/e/image_detection/01_base_data/
AUDIT_RESULTS     /home/byron/dev/image_detection/scripts/audit/results/
SCHEMA            /home/byron/dev/image_detection/docs/schema/layer2_enrichment_v2.schema.json
AUDIT_CONFIG      /home/byron/dev/image_detection/scripts/audit/audit_config.py
PRESCREENING      /home/byron/dev/image_detection/scripts/audit/automated_prescreening.py
```

---

## WS-1: Systemic Fix — automated_prescreening.py Stale Checks

**Priority**: P0 CRITICAL — Fix first. This is blocking valid metadata from passing prescreening.

**Discovery**: During the `arabic-docs` full audit (defects D12–D14), three prescreening checks
were identified that use **v1 field-name paths** that no longer match the v2.4.0 schema structure.
These checks currently produce **100% false failures on every one of the 51 datasets** in the
registry, making automated prescreening results meaningless.

### Defects to Fix

| Defect ID | Check Name | Current (broken) v1 path | Correct v2.4.0 path |
|-----------|-----------|--------------------------|---------------------|
| D12 | `capture_method_populated` | `sample["capture_method"]` (flat string) | `sample["capture_info"]["method"]` |
| D13 | `domain_populated` | `sample["domain"]` (flat string) | `sample["domain_info"]["level1"]` |
| D14 | `text_scope_populated` | `sample["text_scope"]` (flat string) | `sample["text_scope_info"]["content_type"]` |

### File to Edit

`/home/byron/dev/image_detection/scripts/audit/automated_prescreening.py`

Search for the three failing check functions and update the field access paths from flat strings
to nested Info objects per the v2.4.0 schema. The schema JSON at
`docs/schema/layer2_enrichment_v2.schema.json` is the authoritative source for the correct
nested structure.

### Verification

After fixing, run against any dataset with known-good metadata (e.g., `diqa-5000` or `doclaynet`):

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python scripts/audit/automated_prescreening.py \
    --dataset diqa-5000 \
    --metadata /mnt/e/image_detection/metadata_registry/json/diqa_5000_metadata.json
```

The pass rate should be meaningfully above 0% once the field paths are corrected.

---

## WS-2: Full-Audit Remediation — Integration Script Fixes

The three datasets that completed full audits (Phases 0–7) each have specific defects in their
integration scripts producing wrong or missing field values. The fixes below address the highest-
priority defects from each `defect_catalog.json`.

### 2a: arabic-docs (15 defects — 4 HIGH, 7 MEDIUM, 4 LOW)

**Audit artifacts**: `scripts/audit/results/arabic-docs/`
**Integration script**: `scripts/integrate_arabic_docs_ocr_enrichments.py`
**Metadata file**: `/mnt/e/image_detection/metadata_registry/json/arabic_docs_ocr_metadata.json`
**Note**: Naming discrepancy — source doc uses `arabic-docs`, registry uses `arabic-docs-ocr`.
  The canonical name should be standardized; recommend `arabic-docs` to match source doc.
**Prior audit** (2026-02-14, Grade B, 87.29): see `scripts/audit/results/arabic-docs-ocr/`

#### HIGH Priority Defects

| ID | Type | Description | Fix |
|----|------|-------------|-----|
| D01 | `wrong_value` | `capture_method="scanner"` (8,203 samples) — wrong enum value | Change to `"scanner_flatbed"` in integration script |
| D02 | `schema_gap` | `domain_level1="NEWS"` not in v2.4.0 enum (1,473 samples, 18%) | Add `"NEWS"` to schema OR map to closest valid enum (see WS-6 for schema extension request) |
| D05 | `wrong_value` | `has_figure=False` for all samples despite 83,834 Picture layout detections in docling output | Fix integration script to set `has_figure=True` when `layout_detections` contains `class_name="Picture"` |

#### MEDIUM Priority Defects

| ID | Type | Description | Fix |
|----|------|-------------|-----|
| D03 | `schema_gap` | `text_scope_content_type="document"` — not a valid enum value | Change to `"full_document"` (valid enum) or derive from layout detections |
| D06 | `not_populated` | `schema_version` absent from enrichment version objects (1,842 samples, 22%) | Add `"schema_version": "2.4.0"` to all enrichment version objects in integration script |
| D15 | `missing_data` | 1,842 samples have no enrichment data (10,045 raw − 8,203 enriched = 1,842 gap) | Investigate why 1,842 samples were skipped; re-run enrichment for missing samples |

#### Rerun After Fixes

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python scripts/integrate_arabic_docs_ocr_enrichments.py \
    --input /mnt/e/image_detection/metadata_registry/json/arabic_docs_ocr_metadata.json \
    --output /mnt/e/image_detection/metadata_registry/json/arabic_docs_ocr_metadata.json
# Then re-run audit
```

---

### 2b: multilingual-scripts (10 defects — Grade C, 52/100)

**Audit artifacts**: `scripts/audit/results/multilingual-scripts/`
**Integration script**: `scripts/integrate_multilingual_scripts_enrichments.py`
**Metadata file**: `/mnt/e/image_detection/metadata_registry/json/multilingual_scripts_metadata.json`
**Dataset structure**: 4 subdatasets — jssoda (CJK, 2,000), nepal_devanagari (Deva, 717),
  arabic_ocr (Arab, 500), dzongkha_digits (Tibt, 62). Total: 3,279 samples.

#### Critical Defects

| ID | Type | Description | Fix |
|----|------|-------------|-----|
| D01 | `wrong_value` | `script_family="rtl"` for 500 arabic_ocr samples — `"rtl"` is not a valid enum | Change to `"arabic"` (valid enum value) |
| D02 | `wrong_value` | `script_family="indic"` for 62 dzongkha_digits samples — `"indic"` is not valid for Tibetan | Change to `"other"` or `"tibetan"` (check schema enum values) |
| D03 | `wrong_value` | `capture_method="unknown"` for all 3,279 samples — should be derived per subdataset | Set per-subdataset: jssoda→`"synthetic"`, nepal_devanagari→`"born_digital"`, arabic_ocr→`"scanner_flatbed"`, dzongkha_digits→`"camera_smartphone"` |
| D04 | `not_populated` | `content_flags` absent for all 3,279 samples | Add content flags per subdataset (jssoda: `has_text=True`, `has_handwriting=False`; arabic_ocr: `has_handwriting=True`; etc.) |
| D05 | `wrong_value` | `iso639="bo"` (Tibetan language code) for dzongkha_digits — should be `"dz"` (Dzongkha) | Fix language code in integration script |

#### Schema Drift (All 3,279 samples)

The metadata was generated at schema v2.1 and was never migrated to v2.4.0. New fields added
in v2.2–v2.4.0 are absent. Add `"schema_version": "2.4.0"` to enrichment version objects
and populate any required v2.2+ fields.

#### Rerun After Fixes

```bash
PYTHONPATH=. uv run python scripts/integrate_multilingual_scripts_enrichments.py \
    --input /mnt/e/image_detection/metadata_registry/json/multilingual_scripts_metadata.json \
    --output /mnt/e/image_detection/metadata_registry/json/multilingual_scripts_metadata.json
```

---

### 2c: midv2020 (14 defects — 3 CRITICAL — 0% schema compliance)

**Audit artifacts**: `scripts/audit/results/midv2020/`
**Integration script**: `scripts/integrate_midv2020_enrichments.py`
**Metadata file**: `/mnt/e/image_detection/metadata_registry/json/midv2020_metadata.json`
**Dataset**: 4,000 samples, identity documents (50 document types × 2 conditions × 40 samples)

#### The Root Cause: Flat-field vs Nested Info Objects (0% Compliance)

The integration script writes fields as **flat strings** (e.g., `capture_method: "scanner"`)
but the v2.4.0 schema expects **nested Info objects** (e.g., `capture_info: {method: "scanner_flatbed", ...}`).
This structural mismatch causes 0% schema compliance even when data values are otherwise correct.
This is a universal risk affecting all datasets enriched before v2.4.0 — see WS-6 for the
cross-dataset schema migration plan.

#### Critical Defects to Fix

| ID | Type | Description | Fix |
|----|------|-------------|-----|
| D01 | `wrong_value` | `capture_method="scanner"` (3,000 samples, 75%) — wrong enum | Change to `"scanner_flatbed"` |
| D02/D03 | `schema_gap` | `domain_level1="GOV"` — not in v2.4.0 enum (100% of samples) | Add `"GOV"` to schema (WS-6) OR map to `"GOVT"` if that exists |
| D04 | `wrong_value` | `text_has_content=False` for all 4,000 samples — all are identity documents with text | Set `text_has_content=True` universally for this dataset |
| D05 | `wrong_value` | `orientation_class=0` for all 1,333 `scan_rotated` condition samples — should reflect actual rotation | Parse rotation metadata from midv2020 condition labels to set correct orientation_class |

#### Structural Rewrite Required

The `integrate_midv2020_enrichments.py` script needs to be updated to write nested Info objects
instead of flat fields. Reference the current v2.4.0 schema:

```bash
cat docs/schema/layer2_enrichment_v2.schema.json | python3 -m json.tool | grep -A 10 "capture_info"
```

Use an existing integration script that was written for v2.4.0+ as a template (check
`scripts/integrate_realdae_enrichments.py` or `scripts/integrate_doclaynet_enrichments.py`
for v2.4.0-compliant examples).

#### Rerun After Fixes

```bash
PYTHONPATH=. uv run python scripts/integrate_midv2020_enrichments.py \
    --input /mnt/e/image_detection/metadata_registry/json/midv2020_metadata.json \
    --output /mnt/e/image_detection/metadata_registry/json/midv2020_metadata.json
# Then re-run audit: target Grade B+ (>75/100)
```

---

## WS-3: Materialize docsynth and kuzushiji

Both datasets have raw data on disk but require a format-conversion step before the annotation
pipeline can run. This work stream was specifically requested as part of this handoff.

### 3a: docsynth (300,000 images in Parquet — highest priority layout dataset)

**Blocker report**: `scripts/audit/results/docsynth/blocker_report.md`
**Source doc**: `docs/datasets/source/docsynth.md`
**Raw data**: `/mnt/e/image_detection/01_base_data/layout/docsynth300k/`

- 30 parquet files (`part0.parquet` … `part29.parquet`) confirmed on disk
- `images/` directory is empty or sparsely populated — images not yet extracted
- `extract_images.py` script is present in the dataset directory

#### Step 1: Extract Images from Parquet

```bash
cd /mnt/e/image_detection/01_base_data/layout/docsynth300k
python extract_images.py
# Expected output: ~300,000 JPEG files in ./images/
#                  ~300,000 TXT files in ./labels/
# Estimated time: 60–120 minutes
# Disk space required: ~35 GB (images) + ~500 MB (labels)
```

Verify extraction completed successfully:

```bash
find /mnt/e/image_detection/01_base_data/layout/docsynth300k/images -name "*.jpg" | wc -l
# Should be close to 300,000
```

#### Step 2: Run Base Metadata Annotation

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python3 scripts/annotate_base_metadata.py \
    --dataset docsynth \
    --image-dir /mnt/e/image_detection/01_base_data/layout/docsynth300k/images \
    --output /mnt/e/image_detection/metadata_registry/json/docsynth_metadata.json
# Estimated time: 4–12 hours for 300K images (schedule as overnight batch)
```

#### Step 3: Register in audit_config.py

Add to `_KNOWN_CONFIGS` in `scripts/audit/audit_config.py`:

```python
"docsynth": {
    "image_base_path": (_BASE_DATA_DIR / "layout" / "docsynth300k" / "images"),
    "metadata_json_path": (DEFAULT_METADATA_ROOT / "docsynth_metadata.json"),
    "stratification_axes": (
        "capture_method",
        "domain_level1",
        "layout_type",
    ),
},
```

#### Step 4: Create Integration Script

`scripts/integrate_docsynth_enrichments.py` does not exist. Create it following the pattern of
`scripts/integrate_doclaynet_enrichments.py` (closest analogous layout dataset).

Key docsynth-specific notes:

- `capture_method` must be `"synthetic"` (born-digital renderer, NOT `"born_digital"`)
- 74-class taxonomy must be mapped to DocLayNet 11 classes in `layout_detections.class_name`
- No IQA degradation fields expected (synthetic = clean by construction)

#### Step 5: Re-run Full Audit

```text
Run Layer 2 audit on docsynth (source_doc: docs/datasets/source/docsynth.md, audit_scope: full)
```

---

### 3b: kuzushiji (481,336 images across 3 sub-datasets — CDN unreachable)

**Blocker report**: `scripts/audit/results/kuzushiji/blocker_report.md`
**Source doc**: `docs/datasets/source/kuzushiji.md`
**All subdataset directories are empty** — raw data was never downloaded due to CDN block.

#### Step 1: Download Raw Data (Choose One Option)

**Option A — Verify GCS first (fastest if available)**:

```bash
gsutil ls gs://image_detection_b/image-preprocessing-detector/datasets/kuzushiji/
# If data exists, copy it:
gsutil -m cp -r \
    gs://image_detection_b/image-preprocessing-detector/datasets/kuzushiji/ \
    /mnt/e/image_detection/01_base_data/handwriting/kuzushiji/
```

**Option B — torchvision (K-MNIST only, easiest)**:

```python
import torchvision
# Downloads ~20 MB IDX files, automatically decompresses
torchvision.datasets.KMNIST(
    root='/mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kmnist/',
    download=True
)
```

**Option C — Direct CDN** (try if CDN is reachable from another network):

```bash
# K-MNIST (IDX binary format, 60K train + 10K test = 70K images)
wget -P /mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kmnist/data/ \
    http://codh.rois.ac.jp/kmnist/dataset/kmnist/train-images-idx3-ubyte.gz \
    http://codh.rois.ac.jp/kmnist/dataset/kmnist/train-labels-idx1-ubyte.gz \
    http://codh.rois.ac.jp/kmnist/dataset/kmnist/test-images-idx3-ubyte.gz \
    http://codh.rois.ac.jp/kmnist/dataset/kmnist/test-labels-idx1-ubyte.gz \
    http://codh.rois.ac.jp/kmnist/dataset/kmnist/kmnist_classmap.csv

# K-49 (NumPy format, 232K train + 38K test = 270K images)
wget -P /mnt/e/image_detection/01_base_data/handwriting/kuzushiji/k49/data/ \
    http://codh.rois.ac.jp/kmnist/dataset/k49/k49-train-imgs.npz \
    http://codh.rois.ac.jp/kmnist/dataset/k49/k49-train-labels.npy \
    http://codh.rois.ac.jp/kmnist/dataset/k49/k49-test-imgs.npz \
    http://codh.rois.ac.jp/kmnist/dataset/k49/k49-test-labels.npy \
    http://codh.rois.ac.jp/kmnist/dataset/k49/k49_classmap.csv

# K-Kanji TAR (~310 MB, 140K images — already PNG in TAR)
wget -P /mnt/e/image_detection/01_base_data/handwriting/kuzushiji/kkanji/ \
    http://codh.rois.ac.jp/kmnist/dataset/kkanji/kkanji2.tar
```

#### Step 2: Create Materialization Script

Create `scripts/materialize_kuzushiji.py`. This script must:

1. Convert IDX binary files (K-MNIST) to individual PNG files
2. Convert NPZ arrays (K-49) to individual PNG files
3. Extract K-Kanji TAR to per-class PNG directories
4. Write JSONL sidecar index files (`train_index.jsonl`, `test_index.jsonl`) for the parser

Expected output structure:

```text
kuzushiji/kmnist/images/train/00000001.png  (60,000 files, 28×28 px)
kuzushiji/kmnist/images/test/00060001.png   (10,000 files, 28×28 px)
kuzushiji/kmnist/train_index.jsonl
kuzushiji/kmnist/test_index.jsonl
kuzushiji/k49/images/train/...              (232,365 files, 64×64 px)
kuzushiji/k49/images/test/...              (38,547 files, 64×64 px)
kuzushiji/k49/train_index.jsonl / test_index.jsonl
kuzushiji/kkanji/images/{class_name}/...   (per-class PNGs from TAR)
kuzushiji/kkanji/train_index.jsonl
```

Note: Total disk space ~4–6 GB when saved as PNG.

Note on 28×28 images: These are very low-resolution character crops. The resolution quality
labeling pipeline will score them all as `needs_major_upscale` — this is expected and correct.

#### Step 3: Run Base Metadata Annotation

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python3 scripts/annotate_base_metadata.py \
    --dataset kuzushiji \
    --output /mnt/e/image_detection/metadata_registry/json/kuzushiji_metadata.json
# Estimated time: 30–90 minutes for 481K images
```

#### Step 4: Verify audit_config.py Registration

The audit agent auto-registered kuzushiji during the 2026-02-24 audit run. Verify the entry
exists in `scripts/audit/audit_config.py` under `_KNOWN_CONFIGS`:

```python
"kuzushiji": {
    "image_base_path": Path("/mnt/e/image_detection/01_base_data/handwriting/kuzushiji"),
    "metadata_json_path": Path("/mnt/e/image_detection/metadata_registry/json/kuzushiji_metadata.json"),
    "stratification_axes": (
        "capture_method",
        "has_handwriting",
        "resolution_category",
    ),
}
```

If missing (the auto-registration was in-session only and may not have persisted), add it manually.

#### Step 5: Re-run Full Audit

```text
Run Layer 2 audit on kuzushiji (source_doc: docs/datasets/source/kuzushiji.md, audit_scope: full)
```

**Anticipated defects**: All samples will show `resolution_category="very_low"` (28px images).
`capture_method` should be `"scanned"` for K-MNIST/K-49 (scanned historical manuscripts) and
`"scanned"` for K-Kanji as well. Character-crop universal risk D08 applies (share with hasy, nist-sd19).

---

## WS-4: Re-audit casia-hwdb2 Datasets After Extraction

The CASIA HWDB2 datasets are currently being extracted from their native DGRL binary format.
Once extraction completes, the following steps are needed to run the full audits.

### Context: What Is Being Extracted

| Dataset | Raw Format | Images Dir | Extraction Script |
|---------|-----------|-----------|------------------|
| casia-hwdb2 | DGRL binary (5,091 files, 6 splits) | `/mnt/e/.../handwriting/casia-hwdb2/HWDB/` | `scripts/extract_casia_hwdb2_images.py` (being written) |
| casia-hwdb2-line | Parquet (HuggingFace) | `/mnt/e/.../handwriting/casia-hwdb2-line/` | `scripts/extract_casia_hwdb2_line.py` (being written) |

**Expected image counts** (from source docs):

- casia-hwdb2: 5,091 page-level PNGs (1,019 writers × ~5 pages each)
- casia-hwdb2-line: 52,160 line-crop images

### 4a: casia-hwdb2

**Blocker report**: `scripts/audit/results/casia-hwdb2/blocker_report.md`

Once extraction completes:

**Step 1: Verify extraction**

```bash
find /mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2/HWDB -name "*.png" | wc -l
# Expected: ~5,091 (one per DGRL source file)
```

**Step 2: Run base annotation**

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python3 scripts/annotate_base_metadata.py \
    --dataset casia-hwdb2 \
    --image-dir /mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2/HWDB \
    --output /mnt/e/image_detection/metadata_registry/json/casia_hwdb2_metadata.json
```

**Step 3: Create integration script**

`scripts/integrate_casia_hwdb2_enrichments.py` does not exist. Create following the
`scripts/integrate_iam_enrichments.py` pattern (scanner/handwriting dataset with page-level granularity).

Key casia-hwdb2-specific values:

- `capture_method`: `"scanner_flatbed"` (300 DPI scanner)
- `has_handwriting`: `True` (100% handwriting)
- `script_family`: `"han"` (Simplified Chinese)
- `iso639_language`: `"zh"` (Chinese)
- `resolution_category`: `"standard"` (300 DPI)

**Step 4: Register in audit_config.py** (if not already present from auto-registration)

```python
"casia-hwdb2": {
    "image_base_path": (_BASE_DATA_DIR / "handwriting" / "casia-hwdb2" / "HWDB"),
    "metadata_json_path": (DEFAULT_METADATA_ROOT / "casia_hwdb2_metadata.json"),
    "stratification_axes": (
        "has_handwriting",
        "resolution_category",
        "capture_method",
    ),
},
```

**Step 5: Re-run full audit**

```text
Run Layer 2 audit on casia-hwdb2 (source_doc: docs/datasets/source/casia-hwdb2.md, audit_scope: full)
```

---

### 4b: casia-hwdb2-line

**Blocker report**: `scripts/audit/results/casia-hwdb2-line/blocker_report.md`
**Note**: Universal risk D06 — line-crop granularity issue — shared with khatt, iiit-hw-hindi, pucit-ohul.
  Line-crop datasets have different resolution norms (wider aspect ratio, shorter height).

Once extraction completes:

**Step 1: Verify extraction**

```bash
find /mnt/e/image_detection/01_base_data/handwriting/casia-hwdb2-line -name "*.png" | wc -l
# Expected: 52,160
```

**Step 2–5**: Follow the same pattern as casia-hwdb2 (Steps 2–5 above), but:

- Use `--dataset casia-hwdb2-line`
- `metadata_json_path`: `casia_hwdb2_line_metadata.json`
- `capture_method`: `"scanner_flatbed"` (same scanner, line-crop view)
- Note that char_height for line crops will be ~30–50px, resolution quality scores may differ

---

## WS-5: Quick-Win Onboarding

These three datasets have their parser implemented and data available but are blocked by
simple configuration/registration issues. Each can be onboarded in < 1 hour of active work.

### 5a: iiit-hw-hindi — HIGHEST PRIORITY QUICK WIN

**Status**: 95,430 images downloaded, parser implemented, parser NOT registered in `__init__.py`
**Blocker report**: `scripts/audit/results/iiit-hw-hindi/blocker_report.md`
**Role**: Primary Devanagari handwriting dataset; earmarked for `script_cls` head training

#### Fix 1: Register parser (5 minutes)

Edit `src/image_preprocessing_detector/annotation/parsers/handwriting/__init__.py`:

```python
# Add this import
from .iiit_hw_hindi import IIITHWHindiParser

# Add to register_handwriting_parsers():
registry.register(IIITHWHindiParser())

# Add to __all__:
"IIITHWHindiParser",
```

Current registered parsers (for context): `HASYv2Parser, IAMParser, MathsHandwritingParser,
MuharafParser, NistDb2Parser, NistSd6Parser, NistSd19Parser, PucitOhulParser, SignaTRParser`

#### Fix 2: Add to audit_config.py (5 minutes)

```python
"iiit-hw-hindi": {
    "image_base_path": (_BASE_DATA_DIR / "handwriting" / "iiit-hw-hindi"),
    "metadata_json_path": (DEFAULT_METADATA_ROOT / "iiit_hw_hindi_metadata.json"),
    "stratification_axes": (
        "capture_method",
        "has_handwriting",
        "resolution_category",
    ),
},
```

#### Fix 3: Run base annotation (15–30 min runtime)

```bash
cd /home/byron/dev/image_detection
PYTHONPATH=. uv run python3 scripts/annotate_base_metadata.py \
    --dataset iiit-hw-hindi \
    --image-dir /mnt/e/image_detection/01_base_data/handwriting/iiit-hw-hindi \
    --output /mnt/e/image_detection/metadata_registry/json/iiit_hw_hindi_metadata.json
```

#### Fix 4: Create integration script (30–60 min)

Create `scripts/integrate_iiit_hw_hindi_enrichments.py` following
`scripts/integrate_nepali_handwritten_enrichments.py` (closest analogue: Devanagari word-level HW).

Parser-emitted fields to carry through:

- `language_code: "hi"`, `script_name: "Devanagari"`, `iso15924_script_code: "Deva"`
- `transcription`: Devanagari Unicode word text
- `raw_labels["split"]`: train / validation / test
- `raw_labels["granularity"]`: `"word-level"`

#### Fix 5: Re-run full audit

```text
Run Layer 2 audit on iiit-hw-hindi (source_doc: docs/datasets/source/iiit-hw-hindi.md, audit_scope: full)
```

**Also update source doc** (`docs/datasets/source/iiit-hw-hindi.md`) — several sections show
stale counts from when only 400 images were available. Full counts are now: Train 69,853 /
Val 12,708 / Test 12,869 / Total ~95,430 (100% coverage). See blocker report for exact table rows.

---

### 5b: khatt — OOD eval only (Academic license)

**Status**: 1,633 images present, parser implemented, no metadata JSON
**Blocker report**: `scripts/audit/results/khatt/blocker_report.md`
**License constraint**: Academic/research use only — OOD evaluation only, NOT for training

**Known issue in auto-registration**: The audit agent auto-registered khatt with wrong image path
(`01_base_datasets/khatt` instead of `01_base_data/handwriting/khatt`). Verify the `_KNOWN_CONFIGS`
entry uses the correct path:

```python
# Correct:
"image_base_path": (_BASE_DATA_DIR / "handwriting" / "khatt"),
# Wrong (fix if present):
# "image_base_path": Path("/mnt/e/image_detection/01_base_datasets/khatt"),
```

Steps to onboard (same pattern as iiit-hw-hindi):

1. Fix image path in `audit_config.py` (2 min)
2. Run `annotate_base_metadata.py` (5–15 min runtime, 1,633 images)
3. Create `scripts/integrate_khatt_enrichments.py` (follow `integrate_muharaf_enrichments.py`)
4. Re-run full audit

---

### 5c: doc3d — Synthetic 3D dewarping dataset

**Status**: 102,064 PNG images present, no parser, no metadata JSON
**Blocker report**: `scripts/audit/results/doc3d/blocker_report.md`
**Note**: doc3d is **FULLY SYNTHETIC** but stored under `camera_captured/` on disk. Any capture_method
  inference from the directory path would be WRONG. Must hard-code `capture_method="synthetic"`.

**Steps to onboard**:

1. Create a `Doc3DParser` (no existing parser) following `scripts/annotate_base_metadata.py` extension patterns
2. Hard-code `capture_method="synthetic"` — do NOT infer from path
3. Run `annotate_base_metadata.py` with the new parser
4. Create `scripts/integrate_doc3d_enrichments.py`
   - Primary enrichment opportunity: backward mapping NPY files (warp severity stats from `bm_*.zip` once extracted)
5. Re-run full audit

**audit_config.py** entry was auto-registered correctly (agent set path to `camera_captured/doc3d/data/doc3d/img/`).
The path is correct for images, but the `capture_method` semantic error must be handled in the parser/integration script.

---

## WS-6: Housekeeping and Schema Extensions

### 6a: Add Text Corpus Exclusions to audit_config.py

Two datasets audited are text corpora with no images — they should be excluded from future
audit runs to prevent false "dataset not found" failures.

Edit `scripts/audit/audit_config.py` — add to `_TEXT_CORPUS_EXCLUSIONS` list (or equivalent):

```python
_TEXT_CORPUS_EXCLUSIONS = [
    ...,  # existing entries
    "openlid-v2",   # Language identification text corpus — no images
    "wili-2018",    # Language identification text corpus — superseded by openlid-v2
]
```

Details:

- **openlid-v2**: 1.7M text sentences across 1,667 languages. No document images. OOD only.
  Blocker report: `scripts/audit/results/openlid-v2/blocker_report.md`
- **wili-2018**: 235K sentences across 235 languages. Superseded by openlid-v2 for all
  practical purposes. No document images. Blocker report: `scripts/audit/results/wili-2018/blocker_report.md`

---

### 6b: Schema Extension Requests

The following enum values were found missing from `docs/schema/layer2_enrichment_v2.schema.json`
and are needed to represent real data in our datasets:

| Field | Missing Value | Datasets Affected | Justification |
|-------|-------------|------------------|--------------|
| `domain_level1` | `"GOV"` (Government) | midv2020 (100%), potentially others | Identity documents are government-issued; no appropriate mapping exists in current enum |
| `domain_level1` | `"NEWS"` (News/Journalism) | arabic-docs (18%) | Arabic news documents need a domain bucket |
| `capture_method` | _(verify)_ `"scanner_flatbed"` | arabic-docs, midv2020, khatt, casia-hwdb2 | Confirm this value IS in the current schema (integration scripts may be using bare `"scanner"`) |

These should be submitted as a schema PR before the integration script fixes in WS-2 are finalized,
to avoid another round of enum corrections.

---

### 6c: audit_config.py Cleanups from Auto-Registrations

The 2026-02-24 audit wave auto-registered several datasets. Review each for correctness:

| Dataset | Auto-registered? | Known issue | Action |
|---------|-----------------|------------|--------|
| `midv2020` | Yes | None identified | Verify paths correct |
| `doc3d` | Yes | None identified | Parser needs creating |
| `kuzushiji` | Yes (in-session) | May not be persisted | Check file; add if missing |
| `khatt` | Yes | Wrong image path (`01_base_datasets` vs `01_base_data/handwriting`) | Fix path |
| `iiit-hw-hindi` | In-session only | Not persisted | Add to file |
| `docsynth` | No | Not yet registered | Add after WS-3 |
| `casia-hwdb2` | Yes | None identified | Verify after extraction |
| `casia-hwdb2-line` | Yes | None identified | Verify after extraction |

---

## Cross-Dataset Universal Risks

The audits identified several **universal risks** that affect multiple datasets across the registry.
These are systemic issues not tied to any single integration script.

| Risk ID | Description | Datasets Confirmed | All Others |
|---------|-------------|-------------------|------------|
| U01 | `"scanner"` used instead of `"scanner_flatbed"` as capture_method enum | arabic-docs, midv2020, khatt (expected) | Review all scanner datasets |
| U02 | Flat-field writes instead of nested Info objects (schema v2.1 vs v2.4.0 structural mismatch) | midv2020 (0% compliance), multilingual-scripts | All datasets enriched before v2.4.0 |
| U03 | `schema_version` absent from enrichment version objects | arabic-docs (22%), multilingual-scripts | All v2.1-era datasets |
| U04 | Line-crop datasets have resolution anomalies (wide aspect ratio, short height) | casia-hwdb2-line, khatt, iiit-hw-hindi, pucit-ohul | — |
| U05 | Character-crop datasets will all show `resolution_category="very_low"` (correct, but expected) | kuzushiji (28px), hasy, nist-sd19 | — |
| U06 | Synthetic datasets stored under `camera_captured/` path (capture_method path inference failure) | doc3d | Verify others in camera_captured/ |

---

## Completion Checklist

When each work stream is complete, the following gate checks confirm readiness:

**WS-1 done** when:

- [ ] `automated_prescreening.py` updated with v2.4.0 field paths
- [ ] Prescreening pass rate > 0% on at least 3 known-good datasets

**WS-2 done** when:

- [ ] arabic-docs re-audit Grade ≥ B (>75/100), D01/D02/D05 closed
- [ ] multilingual-scripts re-audit Grade ≥ B (>75/100), D01–D05 closed
- [ ] midv2020 re-audit schema compliance > 50%, critical defects D01–D05 closed

**WS-3 done** when:

- [ ] docsynth: `docsynth_metadata.json` exists, full audit complete
- [ ] kuzushiji: `kuzushiji_metadata.json` exists, full audit complete

**WS-4 done** when (after extraction pipeline provides images):

- [ ] casia-hwdb2: `casia_hwdb2_metadata.json` exists, full audit complete
- [ ] casia-hwdb2-line: `casia_hwdb2_line_metadata.json` exists, full audit complete

**WS-5 done** when:

- [ ] iiit-hw-hindi: parser registered, `iiit_hw_hindi_metadata.json` exists, full audit complete
- [ ] khatt: image path fixed, `khatt_metadata.json` exists, full audit complete
- [ ] doc3d: parser created, `doc3d_metadata.json` exists, full audit complete

**WS-6 done** when:

- [ ] Text corpus exclusions added to `audit_config.py`
- [ ] Schema extension PR raised (or inline notes added to pending fixes)
- [ ] Auto-registration entries in `audit_config.py` verified/corrected

---

## Questions / Escalation Points

These items require decisions before the assigned team can proceed:

1. **GOV vs GOVT domain enum**: Does `domain_level1` currently have `"GOVT"` or is `"GOV"` a
   completely new value? Check the schema JSON before fixing midv2020 integration script.

2. **docsynth 74-class taxonomy**: The 74 layout classes in docsynth are only partially
   documented. Without a complete mapping to DocLayNet 11 classes, `layout_detections.class_name`
   cannot be populated correctly. Escalate to the annotation team if taxonomy docs are unavailable.

3. **kuzushiji GCS availability**: Before attempting CDN download (which was blocked), check
   `gs://image_detection_b/image-preprocessing-detector/datasets/kuzushiji/` for existing data.
   This could save hours of download time.

4. **CASIA extraction pipeline**: This handoff assumes the extraction scripts
   (`extract_casia_hwdb2_images.py` and `extract_casia_hwdb2_line.py`) are already in progress.
   If they are not, create them following the blocker reports' detailed DGRL format descriptions
   before starting WS-4.

---

_Handoff prepared: 2026-02-24_
_Audit artifacts location: `scripts/audit/results/`_
_Schema reference: `docs/schema/layer2_enrichment_v2.schema.json` (v2.4.0)_
_Agent definition: `.claude/agents/layer2-audit-agent.md`_
