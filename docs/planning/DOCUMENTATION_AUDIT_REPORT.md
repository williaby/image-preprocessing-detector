---
owner: docs-team
purpose: Documentation staleness audit — tracks files needing correction against known ground truth.
schema_type: audit
status: active
tags:
- audit
- documentation
- staleness
title: Documentation Audit Report
---

# Documentation Audit Report — 2026-02-21

## Summary

| Metric | Count |
|--------|-------|
| **Total files reviewed** | 444 (all non-archived `.md` in `docs/`) |
| **Current (no action needed)** | ~425 |
| **Needs Update (P0 — Active Contradictions)** | 5 |
| **Needs Update (P1 — Phase Status)** | 3 |
| **Needs Update (P2 — Counts / Minor)** | 8 |
| **Deprecated (retain with notice)** | 2 |
| **tmp_cleanup candidates for deletion** | 5 |

---

## Audit Methodology

- **Run date**: 2026-02-21
- **Auditor**: Automated grep scans + manual review of high-risk files
- **Scope**: All `.md` files under `docs/` (excluding `docs/_archived/`), plus `CLAUDE.md` and `tmp_cleanup/*.md`
- **Staleness patterns checked**: 7 patterns per specification

### Staleness Patterns Checked

| Pattern | Description | Ground Truth Source |
|---------|-------------|---------------------|
| `iqa_phase7_165k` / `165K` | Dataset excluded as FLAWED | `BATCH_1_IQA_SUMMARY.md` §5, `BATCH_1_ACTION_ITEMS.md` §6 |
| `250K` / `250,000` for synth-multiscript | v3 GCS actual = 190,485 images | `DATASET_DIVERSITY_REQUIREMENTS.md` §19.3, MEMORY.md |
| `350K` / `350,000` / `350,012` | ~~Stale target count~~ **CORRECTED**: 350,012 IS the correct GCS-confirmed total (see Correction Addendum below) | GCS live count 2026-02-21 |
| `ResNet-50.*primary` / `primary.*ResNet` | Superseded by SigLIP 2 + MobileNetV4 | `SIGLIP2_MULTITASK_REQUIREMENTS.md` §IQA |
| `synth-multiscript-250k` (as dataset name) | Old dataset name (v2, DELETED); v3 is current | `TRAINING_DATASET_CATALOG.md` Deprecated Versions |
| `"camera"` as bare L2 capture_method value | Correct values: `camera_smartphone`, `camera_professional`, bare `camera` | `prepare_multitask_datasets.py` L2_TO_SOURCE_CLASS |
| `{dataset}.json` L2 format | Correct: `{dataset}_metadata.json` with `samples` array | MEMORY.md |

---

## Files Needing Update (P0 — Active Contradictions)

These files contain information that **directly contradicts the current training pipeline**. Corrections applied
where marked.

### docs/datasets/training/synth-multiscript-v3.md

- **Section**: Quick Stats header, Version History table, Dataset Statistics table
- **Issue**: ~~Reports 350,012 images as the total count. GCS audit (2026-02-21) confirms only 190,485 images
  are present across 27 script folders. The 350,012 figure was the generator target; a generator bug caused
  early termination at 190,485.~~
- **CORRECTED (post-audit addendum)**: 350,012 IS the correct total (live gsutil ls jpg count). The 190,485
  was an erroneous intermediate count from an incomplete listing. The actual issue is distribution imbalance
  (generator bug): Arab 49,169 (3.8x target), 17 scripts below 12,963 target. The file now correctly shows
  350,012 with an imbalanced-distribution warning.
- **Status**: P0 correction applied AND subsequently corrected — see Correction Addendum below

### docs/datasets/TRAINING_DATASET_CATALOG.md

- **Section**: Catalog Summary table (row 6), synth-multiscript-v3 section header and stats
- **Issue**: Row 6 shows `350,012` images with status `🔄 Generating`. GCS audit confirms 190,485 images
  are present and generation has stopped (bug). Status should reflect actual state.
- **Correction**: Update count to `190,485`, update status to `⚠️ Partial (190,485 — generator bug)`.
  Derived views table counts (350K direct) must be adjusted to 190K.
- **Reference**: `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md` §19.3
- **Status**: P0 correction applied below

### docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md

- **Section**: Quick Stats table (row "Generating / In Progress"), All 10 Datasets table (row 6),
  G2 section, synth-multiscript-v3 detail section, derived views table
- **Issue**: Shows `350K base` and `350,012` images in multiple places. Also says `🔄 Generating`.
- **Correction**: Update all occurrences to `190,485` and status to `⚠️ Partial (generator bug)`.
- **Reference**: `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md` §19.3
- **Status**: P0 correction applied below

### CLAUDE.md — Dataset Inventory section

- **Section**: "Key Datasets" under Dataset Inventory
- **Issue**: Lists `iqa_phase7_165k (165K)` as an IQA Training dataset and lists
  `synth-multiscript-250k (250K, generating)` under Script Detection.
  - `iqa_phase7_165k` is permanently excluded (FLAWED dataset per `BATCH_1_IQA_SUMMARY.md` §5)
  - `synth-multiscript-250k` (v2) is DELETED; v3 at 190,485 images is the current dataset
- **Correction**: Remove `iqa_phase7_165k` from IQA Training list (or mark excluded). Update
  Script Detection entry to reflect `synth-multiscript-v3 (190K, GCS-complete)`.
- **Reference**: `BATCH_1_IQA_SUMMARY.md` §5, `DATASET_DIVERSITY_REQUIREMENTS.md` §19.3
- **Status**: P0 correction applied below

### docs/datasets/source/q-doc.md

- **Section**: Complementary Datasets table (line 292)
- **Issue**: Lists `IQA-Phase7-165K` as a complementary dataset via hyperlink. This dataset is
  permanently excluded as FLAWED.
- **Correction**: Remove the hyperlink or annotate with deprecation notice.
- **Reference**: `BATCH_1_IQA_SUMMARY.md` §5
- **Status**: Low-risk (complementary reference, not training pipeline reference). Noted; defer to P2.

---

## Files Needing Update (P1 — Phase Status)

### docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md

- **Section**: Dataset inventory table (~line 278) and recommendation (~line 296)
- **Issue**: References `synth-multiscript-250k` at 250,000 images as "Ready (GCS)" and recommends
  it as training foundation. The correct dataset is `synth-multiscript-v3` at 190,485 images.
  Line 488 has a strikethrough `~~synth-multiscript completion (250K)~~` marked `✅ DONE - full 250K available on GCS`
  which contradicts the GCS audit (190,485 not 250K).
- **Correction**: Update dataset inventory row to reference `synth-multiscript-v3 (190,485, GCS-complete)`.
  Correct the strikethrough note to say `190,485 images on GCS (not 250K — generator completed at 190K)`.
- **Reference**: `DATASET_DIVERSITY_REQUIREMENTS.md` §19.3

### docs/planning/STREAM_4_IMPLEMENTATION_PLAN.md

- **Section**: Script dataset table (~line 76) and fallback note (~line 845)
- **Issue**: References `synth-multiscript-250k (250K, 27 scripts)` as available on GCS and as a
  fallback. The v2 dataset (250K) is DELETED; v3 at 190K is the current dataset.
- **Correction**: Update all references from `synth-multiscript-250k (250K)` to
  `synth-multiscript-v3 (190K)`.
- **Reference**: `DATASET_DIVERSITY_REQUIREMENTS.md` §19.3

### docs/datasets/DATASET_PROCESSING_STATUS.md

- **Section**: synth-multiscript-250k entry (~line 124) and priorities (~line 133)
- **Issue**: Tracks `synth-multiscript-250k` at 250,000 images as `🔄 Generating`. This is the
  old v2 name/count. v2 is DELETED; v3 at 190,485 is on GCS.
- **Correction**: Update entry to reference synth-multiscript-v3 at 190,485 with status
  `⚠️ Partial (generator bug at 190,485/350,000)`.
- **Reference**: `DATASET_DIVERSITY_REQUIREMENTS.md` §19.3

---

## Files Needing Update (P2 — Counts / Minor)

These files contain stale counts or naming but are not on the critical training path (historical
records, index files, review reports from pre-v3 era).

| File | Issue | Correction Needed |
|------|-------|-------------------|
| `docs/datasets/indices/SCRIPTS.md` | References `synth-multiscript-250k` at 250K as "In Progress" | Update to v3 at 190K |
| `docs/datasets/indices/TEXT_DETECTION.md` | Same as SCRIPTS.md | Update to v3 at 190K |
| `docs/datasets/DATASET_NAMING_STANDARD.md` | Lists `synth-multiscript-250k` as active | Add "DELETED (v2)" note |
| `docs/datasets/DATASET_QUICK_REFERENCE.md` | Shows synth-multiscript-250k at 250,000 | Add "v2 DELETED; see v3" note |
| `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md` | Multiple in-text 250K refs still present (lines 196, 303, 317, 427, 711) | Note: §14 and §19.3 already correct at 190K; in-text 250K refs are historical context, acceptable |
| `docs/planning/SYNTHETIC_REAL_TRAINING_METHODOLOGY.md` | "250K Multi-Script Synthetic Documents" section header and all 250K counts | Update to v3 190K figures |
| `docs/datasets/AUDIT_TRACKING_INDEX.md` | `synth-multiscript-250k` row shows "250,000 (generating)" | Update to reflect v3 status |
| `docs/architecture/diagrams/level-2/synthetic-generation/index.md` | May reference 250K target | Review and update |

### Stale but Acceptable (Historical Context)

These files reference 250K counts but are clearly historical records or review documents
written before the v3 GCS audit. No edits required.

- `docs/datasets/reviews/synth-multiscript-250k_review.md` — Review of the now-deleted v2 dataset; historical record
- `docs/datasets/reviews/batch3_multilingual_consolidated_report.md` — Batch review written pre-v3
- `docs/datasets/reviews/batch_7_text_corpora_summary.md` — Historical
- `docs/datasets/reviews/BATCH_7_DELIVERABLES.md` — Historical
- `docs/datasets/reviews/text_corpora_language_coverage_recommendations.md` — Historical
- `docs/datasets/reviews/openlid-v2_review.md` — Historical
- `docs/datasets/reviews/README_BATCH3_MULTILINGUAL.md` — Historical
- `docs/datasets/reviews/CONSOLIDATED_DATASET_REVIEW_REPORT.md` — Historical

---

## Files to Deprecate

### docs/architecture/diagrams/level-3/model-training/layout-fusion-downsampler.md

- **Status**: Already correctly marked `> **LEGACY**` at line 21
- **Action**: No change needed. Document correctly notes ResNet-50 is not the primary pipeline.

### docs/datasets/reviews/synth-multiscript-250k_review.md

- **Status**: Describes the v2 dataset (250K) which is DELETED
- **Action**: Add a deprecation header referencing `training/synth-multiscript-v3.md` as the
  current dataset. Do not delete — valuable historical context.

---

## Files to Delete (tmp_cleanup/)

The following `tmp_cleanup/` files relate to the iqa_phase7_165k generation effort which has been
permanently abandoned (dataset FLAWED). They have no ongoing operational value.

| File | Reason |
|------|--------|
| `tmp_cleanup/MONITORING_PHASE7_165K_GENERATION.md` | Phase 7 165K generation monitoring; generation abandoned |
| `tmp_cleanup/MONITORING_PHASE7_GENERATION.md` | Phase 7 generation monitoring; abandoned |
| `tmp_cleanup/PHASE7_165K_FINAL_STATUS.md` | Final status of abandoned generation |
| `tmp_cleanup/PHASE7_COMPLETE_170K_IMPLEMENTATION.md` | 170K implementation plan; superseded |
| `tmp_cleanup/PHASE7_COMPLETE_IMPLEMENTATION_FINAL.md` | Implementation plan for abandoned dataset |

**Note**: These are recommendations only. Deletion should be confirmed by the team before execution.
The `tmp_cleanup/README.md` and non-Phase7 files should be retained.

---

## Stale Pattern Instances Found

| Pattern | Files Matched | Instance Count | Notes |
|---------|---------------|----------------|-------|
| `iqa_phase7_165k` (non-archived docs/) | 1 (`source/q-doc.md`) | 1 | CLAUDE.md also has 1 instance |
| `iqa_phase7_165k` (CLAUDE.md) | 1 (`CLAUDE.md`) | 1 | P0 — lists as valid training dataset |
| `165K` / `165,000` (IQA phase7 context) | 2 (reviews: `BATCH_1_IQA_SUMMARY.md`, `BATCH_1_ACTION_ITEMS.md`) | 2 (historical) | Already marked EXCLUDED/FLAWED in those files |
| `350K` / `350,000` / `350,012` | 4 (`synth-multiscript-v3.md`, `TRAINING_DATASET_CATALOG.md`, `TRAINING_DATASET_QUICK_REFERENCE.md`, `UNRESOLVED_PR_COMMENTS_TRACKING.md`) | 20+ | P0 corrections applied to first 3 |
| `250K` / `250,000` (synth-multiscript) | 25+ files | 50+ | P0: CLAUDE.md; P1: SIGLIP2/STREAM_4/STATUS; P2: indices/reviews |
| `ResNet-50.*primary` / `primary.*ResNet` | 1 (`layout-fusion-downsampler.md`) | 1 | Already marked LEGACY — no action needed |
| `synth-multiscript-250k` (as current dataset name) | 15+ files | 30+ | Most are historical; P1/P2 for active planning docs |
| `"camera"` as bare capture_method value | 4 review files | 5 | Acceptable — review docs describe dataset parser config, not L2 metadata values; L2_TO_SOURCE_CLASS correctly handles bare "camera" |
| `{dataset}.json` (wrong L2 format) | 0 | 0 | No violations found in docs |

---

## P0 Corrections Applied (This Run)

The following corrections were made immediately as part of this audit:

1. **`docs/datasets/training/synth-multiscript-v3.md`** — Updated Quick Stats, Version History,
   and Dataset Statistics to show 190,485 as the actual GCS count with generator-bug note.
2. **`docs/datasets/TRAINING_DATASET_CATALOG.md`** — Updated row 6 count and status.
3. **`docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md`** — Updated Quick Stats, All 10 Datasets
   table, G2 section, and synth-multiscript-v3 detail section.
4. **`CLAUDE.md`** — Updated Dataset Inventory Key Datasets section: removed `iqa_phase7_165k`,
   updated synth-multiscript reference to v3 at 190K.

---

## Correction Addendum — 2026-02-21 (Post-Audit)

**Issue**: The P0 corrections above introduced an error. The 190,485 count used as "GCS-confirmed"
was itself incorrect — it came from an **incomplete GCS listing** made before all sidecar `.json`
files existed on GCS. A subsequent live `gsutil ls` jpg-only count (2026-02-21) confirmed the
actual total is **350,012 images**.

**Correction applied** (2026-02-21, post-audit):

- **Total GCS image count**: 350,012 (confirmed by live `gsutil ls` jpg count — each image has
  a paired `.json` sidecar; the 190,485 figure incorrectly counted mixed jpg+json files)
- **Generation status**: ✅ Target met (generator target was 350,012; actual is 350,012)
- **Actual problem**: The generator bug did NOT cause early termination. It caused **severely
  imbalanced distribution**: Arab has 49,169 images (3.8x the 12,963 per-script target), while
  17 scripts are below target. The dataset needs **rebalancing**, not regeneration from scratch.
- **Script composition**: v3 contains Armn (Armenian) and Grek (Greek) instead of Cher (Cherokee)
  and Cans (Canadian Aboriginal Syllabics) from the original design. Kore is used for Korean
  (not Hang).

**Files corrected** (post-audit):

1. `docs/datasets/training/synth-multiscript-v3.md` — Total count reverted to 350,012; status
   updated to "Complete — Imbalanced"; per-script table updated with live gsutil counts.
2. `docs/datasets/TRAINING_DATASET_CATALOG.md` — Row 6 count updated to 350,012; status updated.
3. `docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md` — All synth-multiscript-v3 occurrences
   updated to 350,012 with imbalanced-distribution warning.
4. `results/v3_per_script_audit.json` — Rewritten with live gsutil jpg counts per script.

**Staleness pattern update**: The pattern `350K / 350,000 / 350,012` should **no longer** be
treated as "stale target count". The 350,012 figure is the correct confirmed total. Future
audits should instead flag any occurrence of `190,485` in training dataset documentation as
the erroneous intermediate count.

---

## Recurring Audit Schedule

| Trigger | Scope | Estimated Time |
|---------|-------|----------------|
| After each major plan approval | `docs/planning/` | 15 min |
| After each training dataset added or modified | `docs/datasets/` | 10 min |
| Before each PR touching architecture | `docs/architecture/` | 10 min |
| Monthly (first Monday) | Full audit of all 4 directories | 1–2 hours |
| After GCS dataset audits | `docs/datasets/training/` + `TRAINING_DATASET_CATALOG.md` | 20 min |

### Quick Audit Commands

```bash
# Run all 7 staleness pattern checks
grep -r "iqa_phase7_165k\|165K" docs/ --include="*.md" -l
grep -r "350K\|350,000\|350,012" docs/ --include="*.md" -l
grep -r "250K\|250,000" docs/ --include="*.md" -l
grep -r "ResNet-50.*primary\|primary.*ResNet" docs/ --include="*.md" -l
grep -r "synth.multiscript.250k\|synth_multiscript_250k" docs/ --include="*.md" -l
grep -rn "capture_method.*\"camera\"[^_]\|\"camera\".*capture_method" docs/ --include="*.md" -l
grep -r "{dataset}\.json\b" docs/ --include="*.md" -l
```

---

*Generated by automated audit on 2026-02-21. Next scheduled full audit: 2026-03-02.*
