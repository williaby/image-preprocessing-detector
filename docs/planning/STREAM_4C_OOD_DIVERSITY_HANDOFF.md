# Stream 4C — OOD & Diversity Framework: Team Handoff

> **Date**: 2026-02-21
> **Branch**: `feat/ood-dataset-diversity-framework` (from `feat/phase-10-remaining`)
> **Plan source**: `~/.claude/plans/jiggly-finding-lighthouse.md`
> **Author**: Claude Sonnet 4.6 (session d548b0f3)

This document transfers full context to the next team. Read the plan source and the files listed
below before making any changes.

---

## 1. What This Work Is

A 9-part framework to address three critical problems in the 503K-image training pipeline:

1. **No formal OOD holdout** — models can't be evaluated on truly unseen conditions
2. **No repeatable diversity standard** — no process to detect gaps before training
3. **Non-Latin handwriting completely absent** — all 5 wild handwriting conditions missing

The framework establishes:
- Per-head wild condition catalogs (what real-world documents look like)
- A formal OOD holdout dataset design (~4K images, 7 categories)
- Schema extensions to permanently mark OOD samples and prevent training leakage
- A repeatable Dataset Diversity Report (DDR) script with multi-model consensus review
- Execution of that framework against 8 of 10 training datasets

---

## 2. Completed Deliverables

### New Files Created

| File | Purpose |
| --- | --- |
| `docs/planning/WILD_CONDITIONS_ANALYSIS.md` | Per-head wild condition catalog (all model heads) |
| `docs/planning/OOD_DATASET_DESIGN.md` | OOD holdout specification (~4K images, 7 categories) |
| `docs/datasets/OOD_DATASET_CATALOG.md` | Per-OOD-image documentation template |
| `scripts/evaluate_dataset_diversity.py` | DDR generator — runs against any training dataset |
| `metadata_registry/ood_registry.jsonl` | OOD image SHA256+pHash registry (initially empty) |
| `docs/datasets/diversity_reports/` | 8 DDR markdown files + README |
| `docs/planning/DIVERSITY_REMEDIATION_PLAN.md` | Consolidated P0/P1/P2 remediation actions |
| `docs/planning/DOCUMENTATION_AUDIT_REPORT.md` | Documentation staleness audit results |

### DDR Status (8 of 10 Complete)

| Dataset | DDR File | Section 7 Consensus | Score |
| --- | --- | --- | --- |
| orientation | `orientation_ddr.md` | ✅ Gemini 2.5 Pro | 27.5/100 |
| skew | `skew_ddr.md` | ✅ Gemini 2.5 Pro | 27.5/100 |
| resolution-quality | `resolution_quality_ddr.md` | ✅ Gemini 2.5 Pro | 20.0/100 |
| iqa-curated | `iqa_curated_ddr.md` | ✅ Gemini 2.5 Pro | 22.5/100 |
| iqa-synthetic | `iqa_synthetic_ddr.md` | ✅ Gemini 2.5 Pro | 20.0/100 |
| handwriting | `handwriting_ddr.md` | ✅ Gemini 2.5 Pro | 20.0/100 |
| capture-method | `capture_method_ddr.md` | ✅ Gemini 2.5 Pro | 20.0/100 |
| synth-multiscript-v3 | `synth_multiscript_v3_ddr.md` | ✅ Gemini 2.5 Pro | 20.0/100 |
| shadow | ❌ Not generated | — | BLOCKED |
| warping | ❌ Not generated | — | BLOCKED |

**Note on low scores**: Section 2 (14-dimension diversity) scores 0.0/100 for all datasets
because the E: drive is not mounted in the current WSL session. The `evaluate_dataset_diversity.py`
script now correctly converts `E:/` → `/mnt/e/` and streams `gs://` via `gsutil cat` — the
infrastructure is fixed, but the drive must be mounted to populate real scores.

### Modified Files

| File | Change |
| --- | --- |
| `scripts/prepare_multitask_datasets.py` | OOD leakage check (SHA256) added to all 6 sub-commands; `split_type` and `ood_categories` fields added to manifest schema |
| `modal/train_siglip2_multitask.py` | Validation: rejects manifest items with `split_type == "ood"` |
| `docs/datasets/training/synth-multiscript-v3.md` | Count corrected: 350,012 → 190,485 (generator bug) |
| `docs/datasets/TRAINING_DATASET_CATALOG.md` | Same count correction |
| `docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md` | Same count correction |
| `CLAUDE.md` | Removed `iqa_phase7_165k` from active datasets; updated synth-multiscript-v3 count |

---

## 3. Key Design Decisions (Do Not Change Without Review)

### `handwriting_density` Annotation Taxonomy

Five-tier categorical scheme. Annotators assign a tier; model trains on the float midpoint.
Boundaries are area-based (% of page covered by handwriting) — script-agnostic.

| Tier | Float Range | Regression Target | Canonical Example |
| --- | --- | --- | --- |
| `none` | 0.0 | 0.0 | Fully printed/born-digital page; zero handwriting |
| `low` | 0.01–0.05 | 0.03 | Single signature, stamp, or one handwritten date |
| `medium` | 0.05–0.40 | 0.22 | Margin notes, corrections, partial field fill-in |
| `high` | 0.40–0.75 | 0.575 | Substantially annotated; handwriting dominates |
| `all` | 0.75–1.0 | 0.875 | Predominantly or fully handwritten page |

**Source**: User decision 2026-02-21. Documented in `handwriting_ddr.md` Section 7.4 and
`DIVERSITY_REMEDIATION_PLAN.md` P0-4.

### `handwriting_script` Fine-Grained Classes

9 classes (not the original 5-family model):
`Latin-Print`, `Latin-Cursive`, `CJK-Simplified`, `CJK-Traditional`,
`Arabic-Naskh`, `Arabic-Ruqah`, `Arabic-Nastaliq`, `Devanagari`, `Cyrillic-Print`

Minimum 2,000 images per class. Do NOT use IAM as the foundation — start with CASIA-HWDB (CJK).

### OOD Categories (7 types, ~4K images total)

`ood_script` (600) | `ood_capture` (600) | `ood_degradation` (800) | `ood_handwriting` (500) |
`ood_geometry` (500) | `ood_resolution` (500) | `ood_domain` (500)

OOD images are NEVER in training or validation manifests. They are only for final hold-out
evaluation. The `ood_registry.jsonl` registry enforces this via SHA256 matching in
`prepare_multitask_datasets.py`.

### Capture-Method: 4-Class v1 (collapsed from 7)

`scanned_flatbed` | `scanned_adf` | `camera_capture` | `born_digital`

The 7-class head cannot be learned from current data (RVL-CDIP is 100% 1990s CCD). Expand back
to 7 classes only after ≥2K examples per fine-grained class are collected.

### synth-multiscript-v3 Script Decisions Pending (Sprint)

Three decisions must be made before the next generation run (see P0-7):

1. **Cher + Cans** (Cherokee, Canadian Aboriginal): Include? If yes, font acquisition needed first.
2. **Armn + Grek** (Armenian, Greek): Keep unexpected scripts → 29-class model, or remove?
3. **Kore → Hang**: Rename Korean label to correct ISO 15924 code (trivial, do now).

---

## 4. Remaining Work

### Immediately Executable (No GPU Required)

#### 4A: Re-run DDRs With Real Manifest Data (P0-8)

Once E: drive is mounted (`/mnt/e/` accessible), re-run to populate Section 2 scores:

```bash
python scripts/evaluate_dataset_diversity.py --dataset orientation \
    --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset skew \
    --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset resolution-quality \
    --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset synth-multiscript-v3 \
    --output docs/datasets/diversity_reports/
```

iqa-curated, iqa-synthetic, handwriting, and capture-method have 0 samples loaded currently
(no manifests on GCS or E: for those planned datasets).

#### 4B: Part 9 Code Fixes — synth-multiscript-v3 Generator

These files need editing before the 350K completion run:

**Fix 1** — `scripts/generate_base_dataset_v3.py` line ~811:

```python
# BEFORE (bug): uses scripts[0] count for all workers
chunk_per_script = chunk_distribution[scripts[0]]

# AFTER: pass full dict; each worker reads its own script's allocation
# (exact refactor depends on how _run_workers consumes this value)
```

**Fix 2** — `src/image_preprocessing_detector/synthetic/generator.py` (~lines 992–1180):
- Add per-script counters; skip generation for scripts already at target
- Fail hard (raise RuntimeError) if corpus is empty or no fonts for script
  (currently falls back silently, producing low-diversity output)

**New script 1** — `scripts/audit_font_coverage.py`:
- Lists all font files in `fonts/synthetic-gen/` + system paths
- Reports per-script font family count
- Exits non-zero if any script is below `--min-families` threshold

**New script 2** — `scripts/audit_v3_per_script_counts.py`:
- Lists GCS `gs://image_detection_b/synth_multiscript_v3/` per-script counts
- Outputs deficit JSON for `--resume-from-audit` flag
- Verifies final distribution within ±10% of 12,963 target

After fixes, execution sequence:
```bash
# 1. Audit current state
python scripts/audit_v3_per_script_counts.py \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --output results/v3_per_script_audit.json

# 2. Verify fonts (target ≥5 per script)
python scripts/audit_font_coverage.py --min-families 5 --fail-below

# 3. Targeted fill (GPU VM or local P40)
python scripts/generate_base_dataset_v3.py \
    --total 350000 \
    --resume-from-audit results/v3_per_script_audit.json \
    --output-gcs gs://image_detection_b/synth_multiscript_v3/ \
    --font-min-families 5 --fail-on-corpus-error --chunk-size 5000

# 4. Verify final counts
python scripts/audit_v3_per_script_counts.py \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --expected-per-script 12963 --tolerance 0.05
```

### Requires GPU VM (Vultr A100) or Local P40

#### 4C: Shadow + Warping Severity Labeling (BLOCKS DDRs #9 + #10)

```bash
# Run on GPU VM
python scripts/label_shadow_severity.py \
    --datasets sd7k wsrd anyphotodoc6300 \
    --output /mnt/e/image_detection/metadata_registry/json/

python scripts/label_warping_severity.py \
    --datasets wsrd warpdoc anyphotodoc6300 \
    --output /mnt/e/image_detection/metadata_registry/json/
```

#### 4D: Phase 1 Synthetic View Generation

```bash
python scripts/generate_v3_shadow_view.py     # 8K shadow images from v3
python scripts/generate_v3_warping_view.py    # 5K warped images from v3
python scripts/derive_v3_orientation_view.py  # non-Latin orientation synthetic
python scripts/build_orientation_real_component.py  # DocLayNet/RVL-CDIP
```

After 4C and 4D, re-run prepare_multitask_datasets.py dry-run:
```bash
python scripts/prepare_multitask_datasets.py shadow --dry-run   # must show >0 real
python scripts/prepare_multitask_datasets.py warping --dry-run  # must show >0 real
```

Then generate shadow + warping DDRs (same command as 4A with `--dataset shadow` / `--dataset warping`).

### Requires Data Acquisition (Multi-Week)

See `DIVERSITY_REMEDIATION_PLAN.md` for full detail. Critical path:

1. **P0-4** (3–5 days): Taxonomy finalized ✅ — annotate handbook from the density table above
2. **P0-5** (4–6 weeks): CASIA-HWDB → KHATT → FUNSD+ → IIIT-INDIC → HKR → IAM
3. **P1-6** (2–3 weeks): Modern CIS scanner (2K images), screen recapture rig (300 images)

---

## 5. File Map for Key Concepts

| Concept | Where to Read |
| --- | --- |
| Wild conditions per head | `docs/planning/WILD_CONDITIONS_ANALYSIS.md` |
| OOD holdout specification | `docs/planning/OOD_DATASET_DESIGN.md` |
| OOD registry format | `metadata_registry/ood_registry.jsonl` (schema in plan Part 3) |
| All P0/P1/P2 remediation actions | `docs/planning/DIVERSITY_REMEDIATION_PLAN.md` |
| DDR per dataset | `docs/datasets/diversity_reports/{dataset}_ddr.md` |
| DDR generator | `scripts/evaluate_dataset_diversity.py` |
| Documentation staleness audit | `docs/planning/DOCUMENTATION_AUDIT_REPORT.md` |
| Training manifest contract | `MEMORY.md` + `modal/train_siglip2_multitask.py` |
| Handwriting taxonomy | `docs/datasets/diversity_reports/handwriting_ddr.md` §7.4 |
| Capture-method 4-class decision | `docs/datasets/diversity_reports/capture_method_ddr.md` §7.4 |
| synth-multiscript-v3 generator bug | `docs/datasets/training/synth-multiscript-v3.md` |

---

## 6. Known Gotchas

- **`mcp__pal__tiered_consensus` Level 2** returns configuration metadata only for all datasets
  (no model consultations). Fall back to `mcp__pal__chat` with `google/gemini-2.5-pro`
  (`thinking_mode: high`) for all consensus reviews.

- **`/mnt/e/` not mounted** in this WSL session — `path.exists()` raises `OSError`. The script
  handles this gracefully (returns `[]`) but Section 2 will show 0.0/100 until mounted.

- **splits.jsonl is 345K lines** — the GCS loader caps at 10K lines by default. This is
  sufficient for statistical sampling. Do not raise the cap without a timeout increase.

- **synth-multiscript-v3 actual count is 190,485** (not 350,012). The splits.jsonl has 345,638
  entries (pre-planned). Do not use splits.jsonl line count as the image count.

- **shadow + warping P0 in DIVERSITY_REMEDIATION_PLAN.md** — these datasets were not evaluated.
  There are no DDRs for them. Shadow/warping P0 actions cannot be prioritized until DDRs exist.

- **iqa_phase7_165k is excluded** — removed from CLAUDE.md and docs. Do not reference it as
  a valid training source. See `docs/planning/DOCUMENTATION_AUDIT_REPORT.md` for the record.

- **OOD registry is empty** — `metadata_registry/ood_registry.jsonl` exists but has no entries.
  The leakage check in `prepare_multitask_datasets.py` is active but vacuous until populated.
  First population target: 600 Mongolian OOD-Script samples (MTHv2 + v3 extract).

---

## 7. Completion Criteria (from Original Plan)

| Criterion | Status |
| --- | --- |
| All 10 DDRs generated | 8/10 ✅ (shadow + warping blocked) |
| All 10 datasets consensus-reviewed | 8/10 ✅ |
| Zero OOD leakage in training manifests | ✅ (enforcement active; registry empty) |
| `DIVERSITY_REMEDIATION_PLAN.md` with P0/P1/P2 | ✅ |
| `ood_registry.jsonl` ≥600 OOD-Script entries | ❌ Registry empty |
| `DOCUMENTATION_AUDIT_REPORT.md` + P0 corrections | ✅ (4 files corrected) |
| shadow + warping DDRs show >0 real records | ❌ Blocked (GPU labeling scripts needed) |
| synth-multiscript-v3 GCS count ≥345,000 | ❌ Currently 190,485 (Part 9 fix needed) |
| All 27 scripts ≥5 font families | ❌ Not verified (audit script not yet created) |

---

*Handoff prepared 2026-02-21 — session d548b0f3*
