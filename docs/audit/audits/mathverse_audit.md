# Layer 2 Metadata Audit - mathverse

> **Version**: 1.3.0
> **Date**: 2026-02-15
> **Auditor**: claude-opus-4-6
> **Methodology**: 9-Phase Audit (v2.3.0)
> **Reference**: [docs/prompts/layer2_audit_prompt.md](../prompts/layer2_audit_prompt.md)
>
> **Audit Goal**: The purpose of this audit is not just to identify errors and gaps, but to
> **close them** so the dataset is ready for production training. Every defect should be
> resolved, deferred with justification, or documented as a known limitation.

---

## Dataset Overview

| Property | Value |
|----------|-------|
| Dataset Name | mathverse |
| Total Samples | 6940 |
| Image Base Path | /mnt/e/image_detection/01_base_datasets/mathverse |
| Audit Started | 2026-02-15 |
| Audit Completed | |
| Enrichment Version | |

---

## Pre-Flight Checklist

### Dataset Registration

- [ ] Dataset registered in `scripts/audit/audit_config.py`?
  - **Known datasets**: diqa-5000, doclaynet, funsd, pubtabnet, fintabnet, sroie, hiertext, cc-ocr, arabic-docs-ocr, ohr-bench, jssoda, mlt19
  - **Status**:

- [ ] Metadata JSON exists at `/mnt/e/image_detection/metadata_registry/json/mathverse_metadata.json`?
  - **Status**:

- [ ] Dataset source doc exists at `docs/datasets/source/mathverse.md`?
  - **Status**:

### Enrichment Source Inventory

Check existence of each enrichment source (✅ exists, ❌ missing, ⏭️ N/A):

| Source | Path | Exists? | Notes |
|--------|------|---------|-------|
| Base metadata | `json/mathverse_metadata.json` | [ ] | Layer 0+1 fields |
| LLM enrichment | `enrichments/mathverse_llm_enrichment.json` | [ ] | domain, content_flags, orientation |
| Language enrichment | `enrichments/mathverse_language_enrichment.json` | [ ] | iso639, iso15924, script_family |
| Docling layout | `enrichments/mathverse_docling_layout.json` | [ ] | layout_detections with bboxes |
| Docling OCR | `enrichments/mathverse_docling_ocr.json` | [ ] | text_content, text_statistics |
| Classical IQA | `enrichments/mathverse_classical_iqa.json` | [ ] | 8 detector scores |
| Resolution quality | `results/mathverse_resolution_labels.json` | [ ] | char_height, resolution_quality_score |
| Skew/orientation | `results/mathverse_skew_labels.json` | [ ] | skew_angle, orientation_class |
| Parser/manifest | Dataset-specific | [ ] | split, source annotations |
| VLM contact sheet | `scripts/audit/results/mathverse/vlm_test_enrichments.json` | [ ] | language, script (visual batch) |
| Train GT enrichment | `scripts/audit/results/mathverse/train_gt_enrichments.json` | [ ] | language, script from GT files |

**Total sources available**: ___/11

### Known Issues Applicability

Review [scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json) and check which issues apply:

| Issue | Title | Severity | Applies? | Notes |
|-------|-------|----------|----------|-------|
| KI-001 | Docling layout label casing | CRITICAL | [ ] | Applies if Docling layout exists |
| KI-002 | Table detection multi-column FP | HIGH | [ ] | Applies if synthetic/multi-column |
| KI-003 | Picture detection dense text FP | MEDIUM | [ ] | Applies if synthetic |
| KI-004 | LLM handwriting on synthetic | HIGH | [ ] | Applies if synthetic dataset |
| KI-005 | LLM cannot detect synthetic capture | HIGH | [ ] | Applies if synthetic dataset |
| KI-006 | LLM formula semantic confusion | MEDIUM | [ ] | Applies if LLM enrichment exists |
| KI-007 | LLM domain UNK on generic content | LOW | [ ] | Applies if LLM enrichment exists |
| KI-008 | Docling multi-column text extraction | HIGH | [ ] | Applies if multi-column docs |

**Applicable issues**: KI-___

### Dataset Characteristics

Fill in based on dataset documentation review:

| Property | Value | Source |
|----------|-------|--------|
| Is synthetic? | | Dataset documentation |
| Primary language(s) | | Dataset documentation |
| Primary script(s) | | Dataset documentation |
| Capture method | | Dataset documentation |
| Expected splits | | Dataset documentation / parser |
| Total samples | | Parser manifest |
| Has ground truth files? | | Dataset structure |
| Multi-column documents? | | Dataset documentation |

---

## Phase 0: Paper Review

### Documentation Review

- [ ] Read `docs/datasets/source/mathverse.md` thoroughly
- [ ] Read `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json`
- [ ] Review parser source code at `src/image_preprocessing_detector/annotation/parsers/mathverse_parser.py` (if exists)

### Expected Field Values

Document expected values based on documentation (ground truth for validation):

| Field | Expected Value | Source | Confidence |
|-------|---------------|--------|------------|
| `capture_method` | | Dataset documentation | |
| `iso639_language` | | Dataset documentation | |
| `iso15924_script` | | Dataset documentation | |
| `script_family` | | Derived from script | |
| `split` | | Parser manifest | |
| `is_synthetic` | | Dataset characteristics | |
| `domain_level1` | | Dataset content type | |

**Notes**:

---

## Phase 1: Automated Prescreening

### Command

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset mathverse
```

**Output**: `scripts/audit/results/mathverse/automated_screening.json`

### Results

15-field validation summary:

| # | Field | Pass Rate | Status | Notes |
|---|-------|-----------|--------|-------|
| 1 | `split` | % | ⬜ | Must not be "unknown" |
| 2 | `capture_method` | % | ⬜ | Must be in enum |
| 3 | `domain_level1` | % | ⬜ | Must not be "UNK" |
| 4 | `iso639_language` | % | ⬜ | Must not be "und" or null |
| 5 | `script_family` | % | ⬜ | Must be in enum |
| 6 | `layout_detections` | % | ⬜ | Must be list with >=1 element |
| 7 | `layout_bbox_valid` | % | ⬜ | All bboxes: [x,y,w,h], w>0, h>0 |
| 8 | `content_flags_boolean` | % | ⬜ | has_table/formula/handwriting/figure/code must be boolean |
| 9 | `text_has_content` | % | ⬜ | text_statistics.has_content must be true |
| 10 | `orientation_class` | % | ⬜ | Must be in enum (0, 90, 180, 270) |
| 11 | `image_properties_color_mode` | % | ⬜ | Must be non-empty string |
| 12 | `handwriting_present` | % | ⬜ | Must be boolean |
| 13 | `quality_overall_mos` | % | ⬜ | Must be numeric 1.0-5.0 (context-dependent) |
| 14 | `text_direction` | % | ⬜ | Must be in {ltr, rtl, ttb} (v2.3.0) |
| 15 | `text_directions_present` | % | ⬜ | All items must be in {ltr, rtl, ttb} (v2.3.0) |

**Overall Pass Rate**: _**%
**Fields at 100%**:**_/15
**Fields at 0%**: ___ (indicates missing enrichment sources)

### Decision Point

| Pass Rate Range | Action | Status |
|----------------|--------|--------|
| 90%+ | ✅ Proceed to Phase 2 | [ ] |
| 50-89% | ⚠️ Investigate missing sources, then proceed | [ ] |
| <50% | ❌ Fix enrichment gaps before proceeding | [ ] |

**Notes**:

---

## Phase 2: Schema Compliance

### Command

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/audit_schema_compliance.py \
    --dataset mathverse \
    --output scripts/audit/results/mathverse/compliance.json
```

**Output**: `scripts/audit/results/mathverse/compliance.json`

### Results Summary

| Field Group | Fields Checked | Valid % | Invalid % | Notes |
|-------------|---------------|---------|-----------|-------|
| capture_resolution | | | | DPI, resolution_category, color_mode |
| domain_language | | | | domain_level1, iso639, iso15924, script_family |
| content_flags | | | | has_table/formula/figure/code/handwriting |
| layout_detections | | | | class_name, bbox, confidence, structure |
| geometric_quality | | | | orientation, skew, quality scores |
| text_document | | | | text_scope, split, content_type |

**Overall Validity**: ___%

### Defect Types Found

| Type | Count | Description |
|------|-------|-------------|
| `wrong_value` | | Value exists but factually incorrect |
| `missing_value` | | Required field absent |
| `wrong_format` | | Wrong type or structure |
| `wrong_enum` | | Not in allowed enumeration |
| `inconsistent` | | Cross-field contradiction |
| `not_populated` | | Optional field not populated |

**Total Defects**: ___

**Notes**:

---

## Phase 3: Multi-Source Comparison

### Command

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/assemble_comparison.py \
    --dataset mathverse
```

**Output**: `scripts/audit/results/mathverse/comparison_report.json`

### Sources Discovered

| Source | Fields Contributed | Priority |
|--------|-------------------|----------|
| | | |
| | | |
| | | |

### Field Agreement Analysis

| Field | Sources | Agreement | Disagreement | Notes |
|-------|---------|-----------|--------------|-------|
| | | | | |
| | | | | |
| | | | | |

### Top Disagreements

| Field | Source A | Source B | Affected Samples | Root Cause |
|-------|----------|----------|-----------------|------------|
| | | | | |
| | | | | |
| | | | | |

**Notes**:

---

## Phase 4: Defect Cataloging

### Defect Catalog

Document all defects in `scripts/audit/results/mathverse/defect_catalog.json`

| ID | Field | Type | Severity | Affected | Status | Root Cause | Fix Location |
|----|-------|------|----------|----------|--------|------------|--------------|
| D01 | | | | | OPEN | | |
| D02 | | | | | OPEN | | |
| D03 | | | | | OPEN | | |
| D04 | | | | | OPEN | | |
| D05 | | | | | OPEN | | |

**Total Defects**: ___

- **Critical**: ___
- **High**: ___
- **Medium**: ___
- **Low**: ___

### Defect Status Breakdown

| Status | Count | Percentage |
|--------|-------|------------|
| OPEN | | % |
| PARTIALLY_RESOLVED | | % |
| RESOLVED | | % |
| DEFERRED | | % |

### Cross-Dataset Risk Assessment

Defects with `universal_risk=true` that may affect other datasets:

| Defect ID | Field | Pattern | Potentially Affected Datasets |
|-----------|-------|---------|------------------------------|
| | | | |

**Notes**:

---

## Phase 4.5: Scale Assessment & Strategy Selection

### Resolution Strategy Per Defect

| Defect ID | Affected Count | Strategy | Est. Turns | Est. Sessions | Notes |
|-----------|---------------|----------|------------|--------------|-------|
| | | | | | |
| | | | | | |
| | | | | | |

### Strategy Tier Reference

| Affected Samples | Strategy | Context Cost | Approach |
|------------------|----------|-------------|----------|
| **< 50** | Individual VLM inspection | Low (1-2 images/turn) | Read each image directly |
| **50 - 500** | Programmatic enrichment | Minimal (code execution) | Exploit GT files, parsers, heuristics |
| **500 - 2,000** | Stratified sampling + extrapolation | Medium (15-25 turns) | Inspect 30-50 samples, extrapolate |
| **> 2,000** | Contact sheet batch VLM | High but manageable (1 sheet/turn) | Generate thumbnail grids, classify in bulk |

### GT File Exploitation Opportunities

- [ ] Check for ground truth annotation files (`.txt`, `.xml`, `.json`)
- [ ] Review sample GT file format
- [ ] Identify fields extractable from GT (language, script, bboxes)

**GT files found**:

**Fields extractable**:

### Contact Sheet Plan (if applicable)

- **Defect ID requiring contact sheets**: ___
- **Total samples to classify**: ___
- **Estimated sheets** (50 thumbnails/sheet): ___
- **Estimated turns** (5 sheets/turn): ___
- **Estimated sessions**: ___
- **Incremental save path**: `scripts/audit/results/mathverse/vlm_test_enrichments.json`
- **Progress tracking file**: `scripts/audit/results/mathverse/audit_progress.json`

**Notes**:

---

## Phase 5: Integration Script

### Integration Script Development

- [ ] Create `scripts/integrate_mathverse_enrichments.py`
- [ ] Follow established integration script pattern
- [ ] Support `--dry-run` mode

### Pre-Integration Actions

- [ ] Run `standardize_layout_labels.py --dataset mathverse` (KI-001)
- [ ] Determine capture_method from documentation (KI-005)
- [ ] Plan synthetic overrides if applicable (KI-004, KI-005)

### Command

```bash
# Dry run first
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/integrate_mathverse_enrichments.py --dry-run

# Actual integration
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/integrate_mathverse_enrichments.py
```

### Field Population Priority

| Field | Priority Source | Fallback | Notes |
|-------|----------------|----------|-------|
| `capture_method` | Dataset documentation | LLM enrichment | Never trust LLM for synthetic (KI-005) |
| `domain_level1` | LLM enrichment | "UNK" acceptable | Accept UNK (KI-007) |
| `iso639_language` | Parser/documentation | Language enrichment | Use highest-confidence source |
| `iso15924_script` | Parser/documentation | Language enrichment | |
| `script_family` | Derived from iso15924_script | `_get_script_family()` | Automatic derivation |
| `layout_detections` | Docling/Egret layout | Parser annotations | Must standardize labels first (KI-001) |
| `content_flags.*` | `derive_content_flags()` from layout + LLM | LLM-only | VLM-verify all True flags |
| `split` | Parser/manifest | Dataset documentation | |
| `text_scope` | LLM content_type field | "printed" default | |
| `orientation_class` | LLM enrichment | 0 (upright) default | |
| `quality_overall` | VLM IQA / Classical IQA | Deferred if unavailable | |
| `resolution_quality_score` | PaddleOCR pipeline | Deferred if no GPU | |

### Known Issue Mitigations Applied

| Issue | Mitigation | Status |
|-------|-----------|--------|
| KI-001 | Ran standardize_layout_labels.py | [ ] |
| KI-002 | VLM verification for has_table=True | [ ] |
| KI-003 | VLM verification for has_figure=True | [ ] |
| KI-004 | Override has_handwriting=False (synthetic) | [ ] |
| KI-005 | Hardcode capture_method=synthetic | [ ] |
| KI-006 | VLM verification for has_formula=True | [ ] |
| KI-007 | Accept domain_level1=UNK | [ ] |

### Post-Integration Prescreening

Re-run prescreening to measure improvement:

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset mathverse
```

**Before/After Comparison**:

| Field | Before | After | Delta |
|-------|--------|-------|-------|
| `split` | % | % | +/- % |
| `capture_method` | % | % | +/- % |
| `domain_level1` | % | % | +/- % |
| `iso639_language` | % | % | +/- % |
| `script_family` | % | % | +/- % |
| `layout_detections` | % | % | +/- % |
| `layout_bbox_valid` | % | % | +/- % |
| `content_flags_boolean` | % | % | +/- % |
| `text_has_content` | % | % | +/- % |
| `orientation_class` | % | % | +/- % |
| `image_properties_color_mode` | % | % | +/- % |
| `handwriting_present` | % | % | +/- % |
| `quality_overall_mos` | % | % | +/- % |

**Overall improvement**: +/- _**%
**Fields improved to 100%**:**_

**Notes**:

---

## Phase 6: VLM Visual Inspection (MANDATORY)

> **This phase is MANDATORY.** Skipping VLM inspection caps the scorecard
> grade at **D** regardless of all other dimension scores. Content flags
> without visual verification are unverified soft labels unsuitable for
> training. At minimum, complete Track A (content flag checks) and
> Track C (passing sample validation).

### Sample Selection (Metadata-Driven)

**Default approach**: Use `select_audit_samples.py --phase6` to generate Track A/B/C
sample sets from prescreening results and metadata JSON. This avoids filesystem directory
scanning, which causes OOM on WSL network mounts with 500K+ files.

```bash
# Generate Phase 6 sample sets (requires Phase 1 prescreening to exist)
PYTHONPATH=. uv run python3 scripts/audit/select_audit_samples.py \
    --dataset mathverse --phase6 --verbose

# Output: scripts/audit/results/mathverse/phase6_track_{a,b,c}_samples.json
```

**Tier override** (if defect catalog or cross-source disagreement signals warrant):

```bash
PYTHONPATH=. uv run python3 scripts/audit/select_audit_samples.py \
    --dataset mathverse --phase6 --tier 3 --verbose
```

**Contact sheet generation** (for Track B, datasets > 2K):

```bash
python scripts/audit/create_contact_sheets.py \
    --sample-json scripts/audit/results/mathverse/phase6_track_b_samples.json \
    --output-dir tmp_cleanup/mathverse_contact_sheets/ \
    --cols 10 --rows 5 --thumb-width 150
```

### Adaptive Sampling Tier Selection

**Before starting VLM inspection**, determine the sampling tier based on signals from Phases 1-4.
Higher tiers require more samples to compensate for lower metadata confidence.

#### Tier Decision Table

| Signal | Tier 1 (Standard) | Tier 2 (Enhanced) | Tier 3 (Comprehensive) |
|--------|-------------------|-------------------|------------------------|
| Prescreening pass rate | >= 85% | 50-84% | < 50% |
| Critical/High defects | 0-2 | 3-5 | 6+ |
| Fields at 0% (missing enrichment) | 0-1 | 2-3 | 4+ |
| Cross-source disagreement on any field | < 10% | 10-30% | > 30% |
| KI-009 language mismatch detected | No | N/A | Yes (auto Tier 3) |

**Rule**: Use the **highest tier triggered by ANY signal**. For example, if prescreening is
92% (Tier 1) but there are 4 critical defects (Tier 2), use Tier 2.

#### Sampling Requirements Per Tier

Sample counts use `max(fixed_count, pct_of_dataset)` to ensure larger datasets receive
proportionally more inspection. The **percentage floor** guarantees coverage scales with
dataset size rather than being limited to a small fixed number.

| Component | Tier 1 (Standard) | Tier 2 (Enhanced) | Tier 3 (Comprehensive) |
|-----------|-------------------|-------------------|------------------------|
| **Track A per flag** | max(10, 3% of dataset) | max(15, 10% of dataset) | max(25, 15% of dataset) or all if < 50 |
| **Track C passing** | max(10, 2% of dataset) | max(15, 5% of dataset) | max(25, 10% of dataset) |
| **Total minimum** | max(15, 5% of dataset) | max(30, 15% of dataset) | max(60, 25% of dataset) |
| **Total target** | max(40, 5% of dataset) | max(75, 15% of dataset) | max(120, 25% of dataset) |
| **Adaptive expansion** | No | If any flag FP > 20%, inspect all TRUE | If any flag FP > 15%, inspect all TRUE |

**Percentage floor examples**: For a 1,200-image dataset at Tier 2, the minimum is
max(30, 180) = 180. For a 5,000-image dataset at Tier 3, max(60, 1250) = 1,250.
For datasets > 10K images, use Track B contact sheets for the percentage-based portion.

**Adaptive expansion**: After processing the initial Track A batch, check per-flag FP rates.
If a flag exceeds the threshold, expand inspection for that specific flag before concluding.

#### Tier Selection

- [ ] Prescreening pass rate: `___%` → Tier `___`
- [ ] Critical/High defects: `___` → Tier `___`
- [ ] Fields at 0%: `___` → Tier `___`
- [ ] Cross-source disagreement: `___%` → Tier `___`
- [ ] KI-009 language mismatch: Yes/No → Tier `___`

**Selected Tier**: `___` (highest triggered)

**Justification**:

### Track A: Small-Scale Inspection (< 50 failing samples)

#### Content Flag Verification

- [ ] Generate Track A sample set (auto-selected from prescreening failures):

```bash
# Already generated by --phase6 above; samples in:
# scripts/audit/results/mathverse/phase6_track_a_samples.json
```

- [ ] For each failing sample in Track A JSON, read image using Read tool
- [ ] Assess against field definitions

**Fields to inspect**:

| Field | Samples to Inspect | Status |
|-------|--------------------|--------|
| `has_table` | | [ ] |
| `has_formula` | | [ ] |
| `has_figure` | | [ ] |
| `has_handwriting` | | [ ] |
| `has_code` | | [ ] |
| `capture_method` | | [ ] |
| `orientation_class` | | [ ] |

#### Inspection Results

**Output**: `scripts/audit/results/mathverse/vlm_corrections.json`

| Field | Original True Count | Corrected True Count | FP Rate | Root Cause | Action |
|-------|-------------------|---------------------|---------|------------|--------|
| `has_table` | | | % | | |
| `has_formula` | | | % | | |
| `has_figure` | | | % | | |
| `has_handwriting` | | | % | | |
| `has_code` | | | % | | |

**Total images inspected (Track A)**: ___

### Track B: Large-Scale Contact Sheet Classification (> 2,000 samples)

#### Contact Sheet Generation

- [ ] Generate Track B sample set (metadata-driven, no filesystem scan):

```bash
PYTHONPATH=. uv run python3 scripts/audit/select_audit_samples.py \
    --dataset mathverse --phase6 --verbose
```

- [ ] Generate contact sheets from Track B samples:

```bash
python scripts/audit/create_contact_sheets.py \
    --sample-json scripts/audit/results/mathverse/phase6_track_b_samples.json \
    --output-dir tmp_cleanup/mathverse_contact_sheets/ \
    --cols 10 --rows 5 --thumb-width 150
```

- Grid: 10 columns x 5 rows = 50 thumbnails per sheet
- Thumbnail size: ~150x150px
- Sheet size: ~1500x750px, JPEG quality 90
- Each thumbnail labeled with filename
- Save to `tmp_cleanup/mathverse_contact_sheets/contact_sheet_NNN.jpg`

#### Batch Processing

- [ ] Process sheets in batches of 5 (250 images per turn)
- [ ] Use compact codes to minimize output tokens
  - Script ID: `la hi bn ko zh ja ar un` (latin, devanagari, bengali, hangul, chinese, japanese, arabic, unclear)
  - Orientation: `0 90 180 270`
  - Capture: `sc bd cm sy` (scanner, born-digital, camera, synthetic)
- [ ] Save incrementally after every 5 sheets

**Progress Tracking**:

| Batch | Sheets Processed | Samples Classified | Status | Notes |
|-------|-----------------|-------------------|--------|-------|
| 1 | 1-5 | 1-250 | [ ] | |
| 2 | 6-10 | 251-500 | [ ] | |
| 3 | 11-15 | 501-750 | [ ] | |
| ... | | | | |

**Output**: `scripts/audit/results/mathverse/vlm_test_enrichments.json`

**Total sheets**: ___
**Total images classified**:___
**Sessions required**: ___

#### Incremental Save Pattern

Save after every 5 sheets to `vlm_test_enrichments.json`:

```json
{
  "dataset": "mathverse",
  "method": "vlm_contact_sheet",
  "completed": 250,
  "sheets_processed": 5,
  "total_sheets": 195,
  "samples": { ... }
}
```

### Track C: Validate Passing Samples (tier-dependent)

- [ ] Track C sample set (auto-generated by `--phase6`):

```bash
# Already generated by --phase6 above; samples in:
# scripts/audit/results/mathverse/phase6_track_c_samples.json
```

- Tier 1: max(10, 2% of dataset) | Tier 2: max(15, 5%) | Tier 3: max(25, 10%)
- [ ] For each sample in Track C JSON, read image and verify ALL populated fields
- [ ] Compute accuracy rate per field

**Output**: `scripts/audit/results/mathverse/vlm_validation_passing.json`

#### Passing Sample Validation

| Sample | All Fields Match? | Incorrect Fields | Notes |
|--------|------------------|-----------------|-------|
| 1 | ✅/❌ | | |
| 2 | ✅/❌ | | |
| 3 | ✅/❌ | | |
| ... | | | |

**Per-Field Accuracy**:

| Field | Correct | Total | Accuracy | Status |
|-------|---------|-------|----------|--------|
| `capture_method` | | 15 | % | ⬜ |
| `domain_level1` | | 15 | % | ⬜ |
| `iso639_language` | | 15 | % | ⬜ |
| `has_table` | | 15 | % | ⬜ |
| `has_formula` | | 15 | % | ⬜ |
| `has_figure` | | 15 | % | ⬜ |
| `has_handwriting` | | 15 | % | ⬜ |
| `orientation_class` | | 15 | % | ⬜ |

**Overall Passing Accuracy**: ___%

**Target**: 95%+ accuracy (Minimum: 90%)

**Notes**:

### Context Budget Tracking

| Phase | Approach | Turns Used | Cumulative | Notes |
|-------|----------|-----------|-----------|-------|
| Track A | Individual images | | | |
| Track B | Contact sheets | | | |
| Track C | Passing validation | | | |
| **Total** | | | | |

**Session threshold**: ~40-60 turns before context pressure

---

## Phase 6.5: VLM Text Labeling (Conditional)

> **Trigger**: Run this phase if Phase 1 prescreening shows `text_has_content` pass rate < 50%.
> If >= 50%, skip to Phase 7.

### Trigger Check

- [ ] `text_has_content` pass rate from prescreening: ___%
- [ ] Trigger condition met (< 50%)? Yes / No

### Sample Count

**Formula**: `max(ceil(0.01 * 6940), 10)` = ___ samples

### Sample Selection

- [ ] Upright images only (orientation_class == 0)
- [ ] Confidence > 75% for VLM transcription
- [ ] Diverse document types across content categories
- [ ] Both splits represented (train + test if available)

### Transcription Results

| # | Image ID | Confidence | Document Type | Lines | Status |
|---|----------|-----------|---------------|-------|--------|
| 1 | | | | | [ ] |
| 2 | | | | | [ ] |
| 3 | | | | | [ ] |
| ... | | | | | |

**Output**: `results/mathverse_text_labels.json`

### Integration

```bash
# Re-run integration with VLM text labels
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/integrate_mathverse_enrichments.py \
    --vlm-text-labels results/mathverse_text_labels.json
```

- [ ] Integration script updated with `--vlm-text-labels` flag
- [ ] Enrichment version bumped
- [ ] Prescreening re-run to verify `text_has_content` improvement

**Fields set**: `text_has_content`, `text_content`, `text_content_confidence`, `text_content_source`, `text_statistics`

---

## Phase 7: Apply Corrections

### Integration Script Updates

- [ ] Update integration script with VLM corrections
- [ ] Add new enrichment sources from Phase 6
- [ ] Bump enrichment version tag
- [ ] Update field population priority logic

**Version progression**:

- v2 integration: ___
- v3 integration: ___
- v4 integration: ___

### Commands

```bash
# Dry run with updated script
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/integrate_mathverse_enrichments.py --dry-run

# Actual write
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/integrate_mathverse_enrichments.py

# Re-run prescreening
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/automated_prescreening.py --dataset mathverse
```

### Post-Correction Prescreening

| Field | Phase 5 (After v2) | Phase 7 (After v3) | Final Delta | Status |
|-------|-------------------|-------------------|-------------|--------|
| `split` | % | % | +/- % | ⬜ |
| `capture_method` | % | % | +/- % | ⬜ |
| `domain_level1` | % | % | +/- % | ⬜ |
| `iso639_language` | % | % | +/- % | ⬜ |
| `script_family` | % | % | +/- % | ⬜ |
| `layout_detections` | % | % | +/- % | ⬜ |
| `layout_bbox_valid` | % | % | +/- % | ⬜ |
| `content_flags_boolean` | % | % | +/- % | ⬜ |
| `text_has_content` | % | % | +/- % | ⬜ |
| `orientation_class` | % | % | +/- % | ⬜ |
| `image_properties_color_mode` | % | % | +/- % | ⬜ |
| `handwriting_present` | % | % | +/- % | ⬜ |
| `quality_overall_mos` | % | % | +/- % | ⬜ |

**Overall improvement**: +/- ___%

### Defect Catalog Update

- [ ] Update defect statuses (OPEN → RESOLVED/PARTIALLY_RESOLVED/DEFERRED)
- [ ] Document resolution notes
- [ ] Track remaining open defects

| Defect ID | Original Status | Updated Status | Resolution Notes |
|-----------|----------------|----------------|-----------------|
| D01 | OPEN | | |
| D02 | OPEN | | |
| D03 | OPEN | | |

**Resolved**: ___
**Partially Resolved**:___
**Deferred**: ___
**Still Open**:___

---

## Phase 8: Documentation

### Dataset Documentation Updates

- [ ] Update `docs/datasets/source/mathverse.md`
- [ ] Add **Layer 2 Annotation Summary** section
- [ ] Add **Reliability & Bottlenecks** section
- [ ] Update **Version History**

### Layer 2 Annotation Summary

Add to dataset documentation:

```markdown
## Layer 2 Annotation Summary

**Enrichment Version**: integrated_v3
**Audit Date**: 2026-02-15
**Auditor**: claude-opus-4-6

### Enrichment Sources

| Source | Fields Contributed | Confidence | Notes |
|--------|-------------------|-----------|-------|
| | | | |

### Field Coverage

| Field | Coverage % | Source | Reliability |
|-------|-----------|--------|------------|
| | | | |

### Known Issues & Mitigations

| Issue | Mitigation | Status |
|-------|-----------|--------|
| | | |

### VLM Validation

- **Passing sample accuracy**: ___%
- **Content flag FP rate**: ___%
- **Total images inspected**: ___
```

### Reliability & Bottlenecks Section

```markdown
## Reliability & Bottlenecks

### Prescreening Results

- **Pass rate**: ___% (before), ___% (after)
- **Fields at 100%**: ___/15
- **Remaining failures**: ___

### Deferred Items

| Field | Reason | Requirements |
|-------|--------|--------------|
| | | |

### Version History

| Version | Date | Changes |
|---------|------|---------|
| integrated_v2 | 2026-02-15 | Initial integration (parser GT, LLM, layout) |
| integrated_v3 | 2026-02-15 | Added VLM contact sheet, train GT enrichment |
```

### Cross-Dataset Pattern Documentation

- [ ] Review for new cross-dataset patterns
- [ ] Add to `docs/known_issues/KI-{NNN}-{slug}.md` (if new pattern)
- [ ] Update `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` (if new pattern)

**New patterns identified**: ___

**Known issues updated**: ___

---

## Phase 9: Dataset Catalog Update

> **Purpose**: Ensure `docs/datasets/source/mathverse.md` is the single source of truth
> by running aggregation scripts and updating all sections per template v1.4.0.

### Step 1: Regenerate Aggregate Statistics

```bash
uv run python3 scripts/aggregate_layer2_metadata.py \
    --dataset mathverse \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --verbose
```

- [ ] Script completed successfully
- [ ] Output: `metadata_registry/aggregates/mathverse_stats.json`

### Step 2: Materialize Reliability Summary

```bash
uv run python3 scripts/materialize_reliability_summary.py \
    --datasets mathverse \
    --update-docs \
    --force
```

- [ ] Script completed successfully
- [ ] `docs/datasets/source/mathverse.md` Section 12 updated
- [ ] Re-added contextual notes if needed (script overwrites entire section)

### Step 3: Update Source Doc Sections

Update `docs/datasets/source/mathverse.md` per template v1.4.0:

- [ ] **Section 5.3 (Language & Script)**: Reflects actual LLM-detected distribution, not just paper claims
- [ ] **Section 7 (Known Issues)**: Includes "Layer 2 Audit Findings" subsection with defect IDs
- [ ] **Section 8 (Layer 2 Annotation Summary)**: Enrichment sources and field coverage current
- [ ] **Section 11 (Layer 2 Audit Summary)**: Added/updated with:

| Subsection | Content Source |
|------------|---------------|
| Quality Scorecard | `scorecard.json` |
| Key Defects | `defect_catalog.json` |
| VLM Inspection Summary | `vlm_corrections.json` |
| Cross-Dataset Findings | `CROSS_DATASET_KNOWN_ISSUES.json` |

- [ ] **Section 12 (Reliability & Bottlenecks)**: Verified from Step 2 output

### Step 4: Recompute Final Scorecard

```bash
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/audit/compute_scorecard.py --dataset mathverse --verbose
```

- [ ] Scorecard recomputed (doc_completeness may change after doc updates)
- [ ] Final grade: ___
- [ ] Final score: ___/100

### Step 5: (Optional) Dataset Catalog Agent Gap Analysis

- [ ] Invoked `.claude/agents/dataset-catalog-agent.md` for full 12-section gap analysis
- [ ] Cross-file consistency verified (Quick Reference, Processing Status, Task Indices)
- [ ] All gaps resolved or documented as deferred

---

## Phase 10: Lessons Learned & Process Improvement

### Friction Points Identified

| Category | Description | Target File(s) | Status |
|----------|-------------|-----------------|--------|
| Script bug | | | [ ] |
| Template gap | | | [ ] |
| New known issue | | | [ ] |
| New enrichment type | | | [ ] |
| Documentation stale | | | [ ] |
| Process change | | | [ ] |

### Changes Applied

| Change | File Modified | Type | Notes |
|--------|--------------|------|-------|
| | | Quick fix / Script fix / Template / KI | |
| | | | |

### Phase 10 Checklist

- [ ] Reviewed audit execution for friction points and gaps
- [ ] Categorized improvements by type
- [ ] Applied quick fixes (README version, field counts, troubleshooting entries)
- [ ] Proposed or implemented script/template changes
- [ ] Added new known issues to `CROSS_DATASET_KNOWN_ISSUES.json` (if applicable)
- [ ] Updated `docs/audit/README.md` version number and Last Updated date
- [ ] Added these lessons learned to this audit checklist

### What Worked Well

-

### What Caused Friction

-

### Recommendations for Next Audit

-

---

## Sign-Off

### Acceptance Criteria

| Criterion | Target | Minimum | Actual | Pass? | Notes |
|-----------|--------|---------|--------|-------|-------|
| Prescreening pass rate | 95%+ | 85% | % | ⬜ | |
| Fields at 100% | 12+/15 | 10/15 | /15 | ⬜ | |
| VLM passing accuracy | 95%+ | 90% | % | ⬜ | **REQUIRED** - grade capped at D without |
| VLM images inspected (Tier 1) | max(40, 5%) | max(15, 5%) | | ⬜ | **REQUIRED** - Track A + Track C |
| VLM images inspected (Tier 2) | max(75, 15%) | max(30, 15%) | | ⬜ | Enhanced: gaps or critical defects |
| VLM images inspected (Tier 3) | max(120, 25%) | max(60, 25%) | | ⬜ | Comprehensive: major gaps or KI-009 |
| Defects resolved | 90%+ | 75% | % | ⬜ | |
| Content flag FP rate | <5% | <15% | % | ⬜ | |
| Adaptive expansion triggered | N/A | N/A | | ⬜ | If any flag FP > threshold, expand |
| Cross-dataset findings documented | All | All critical/high | | ⬜ | |

### Quality Scorecard

Based on [config/audit_scorecard.yaml](../../config/audit_scorecard.yaml):

| Dimension | Weight | Score | Weighted | Notes |
|-----------|--------|-------|----------|-------|
| Field Coverage | 0.25 | | | Avg pass rate across 13 fields |
| Field Validity | 0.25 | | | Schema compliance validity rate |
| Doc Completeness | 0.15 | | | 11 expected sections |
| Defect Rate | 0.15 | | | Inverse defect density |
| Cross-Source Agreement | 0.10 | | | Pairwise agreement (if applicable) |
| VLM Accuracy | 0.10 | | | Passing sample accuracy |

**Total Score**: _**/100
**Grade**:**_

**Grade Thresholds**:

- A = 90+ (Excellent - ready for production training)
- B = 80+ (Good - minor gaps, usable with caveats)
- C = 70+ (Acceptable - significant gaps needing attention)
- D = 60+ (Below Standard - major remediation required)
- F = <60 (Failing - not suitable for use)

### Final Status

- [ ] **APPROVED** - All acceptance criteria met or exceeded
- [ ] **APPROVED WITH CAVEATS** - Minimum criteria met, documented caveats
- [ ] **REJECTED** - Below minimum standards, requires additional work

**Caveats** (if applicable):

**Auditor Sign-Off**: _______________________

**Date**: _______________________

---

## Output Artifacts Checklist

All standard audit artifacts:

| File | Purpose | Created | Verified |
|------|---------|---------|----------|
| `scripts/audit/results/mathverse/automated_screening.json` | Per-field pass/fail counts | [ ] | [ ] |
| `scripts/audit/results/mathverse/compliance.json` | Schema validation per field | [ ] | [ ] |
| `scripts/audit/results/mathverse/comparison_report.json` | Multi-source field comparison | [ ] | [ ] |
| `scripts/audit/results/mathverse/defect_catalog.json` | Categorized defects with status | [ ] | [ ] |
| `scripts/integrate_mathverse_enrichments.py` | Integration script | [ ] | [ ] |
| `scripts/audit/results/mathverse/vlm_corrections.json` | VLM visual inspection corrections | [ ] | [ ] |
| `scripts/audit/results/mathverse/vlm_validation_passing.json` | Passing sample accuracy check | [ ] | [ ] |
| `docs/datasets/source/mathverse.md` (UPDATED) | Documentation with L2 summary + audit summary | [ ] | [ ] |
| `metadata_registry/aggregates/mathverse_stats.json` | Regenerated aggregate statistics | [ ] | [ ] |
| `scripts/audit/results/mathverse/scorecard.json` | Final quality scorecard | [ ] | [ ] |

**Optional artifacts** (if applicable):

| File | Purpose | Created | Verified |
|------|---------|---------|----------|
| `tmp_cleanup/mathverse_contact_sheets/` | Contact sheet images | [ ] | [ ] |
| `scripts/generate_mathverse_contact_sheets.py` | Contact sheet generator | [ ] | [ ] |
| `scripts/audit/results/mathverse/vlm_test_enrichments.json` | VLM batch classification results | [ ] | [ ] |
| `scripts/audit/results/mathverse/train_gt_enrichments.json` | Train GT file extraction results | [ ] | [ ] |
| `scripts/audit/results/mathverse/audit_progress.json` | Multi-session progress tracking | [ ] | [ ] |
| `results/mathverse_text_labels.json` | VLM text transcription labels (Phase 6.5) | [ ] | [ ] |
| `docs/known_issues/KI-{NNN}-{slug}.md` | New cross-dataset pattern (if found) | [ ] | [ ] |

---

## Audit Trail

### Session Log

| Session | Date | Phase(s) | Turns Used | Progress | Notes |
|---------|------|----------|-----------|----------|-------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

### Key Decisions

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| | | | |

### Challenges Encountered

| Challenge | Resolution | Lessons Learned |
|-----------|-----------|----------------|
| | | |

---

## Notes

(Space for auditor notes, observations, and recommendations)
