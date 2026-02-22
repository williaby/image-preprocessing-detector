# Handoff: synth-multiscript-v3 Completion

> **Date**: 2026-02-21
> **Branch**: `feat/ood-dataset-diversity-framework`
> **Author**: Claude Sonnet 4.6 (session continuation)
> **Recipient**: Team responsible for synth-multiscript-v3 completion run

This document covers everything needed to bring synth-multiscript-v3 from 190,485 images
to the 350,000-image target. The generator bug is already fixed. Three label decisions
must be resolved before the generation run begins.

---

## 1. Current State

| Metric | Value |
|---|---|
| Images on GCS (`gs://image_detection_b/synth_multiscript_v3/`) | **190,485** |
| Target | 350,000 |
| Deficit | **~159,515 images** |
| splits.jsonl entries | 345,638 (pre-planned, includes planned images not yet generated) |
| Target per script (27 scripts) | 12,962–12,963 images |

**Key fact**: splits.jsonl line count (345,638) does NOT equal image count (190,485).
splits.jsonl was planned for 350K but images were only generated to 190K before the
generator bug was discovered. Always use GCS listing or `audit_v3_per_script_counts.py`
for accurate counts.

---

## 2. Generator Bug — Already Fixed

### What Was Wrong

`scripts/generate_base_dataset_v3.py` line ~811 previously passed
`chunk_distribution[scripts[0]]` (the allocation for the first script only) to all worker
processes instead of per-script allocations. This caused all scripts after the first to
be assigned the first script's quota, producing uneven per-script generation.

### What Was Fixed

A new function `_samples_per_script_for_worker()` was introduced (lines 600–627):

```python
def _samples_per_script_for_worker(
    worker_scripts: list[str],
    distribution: dict[str, int],
) -> int:
    """Return the max samples any worker script needs (drives chunk size)."""
    return max(distribution.get(script, 0) for script in worker_scripts)
```

Workers receive their actual target from the `distribution` dict, and
`src/image_preprocessing_detector/synthetic/generator.py` was updated (lines 1208–1225)
to prune each script's corpus when the per-script target is reached.

**The bug fix is committed and requires no further changes.**

---

## 3. Three Pending Label Decisions

**These must be decided before the generation run.** The generator will fail or produce
incorrect output if the script list or class assignments are ambiguous.

### Decision 1: Cher + Cans (Cherokee, Canadian Aboriginal Syllabics)

`Cher` (Cherokee) and `Cans` (Unified Canadian Aboriginal Syllabics) appear in the V3
script list but fonts for these scripts are not confirmed in `fonts/synthetic-gen/`.

**Options**:
- **Include**: Acquire font files (SIL Noto Cherokee, Noto Sans Canadian Aboriginal) and
  add to `fonts/synthetic-gen/`. This expands the model to 27+2=29 classes.
- **Exclude**: Remove from `V3_SCRIPTS` in `audit_v3_per_script_counts.py` and from the
  generator script list. Model stays at 27 classes.

**Recommendation**: Run `scripts/audit_font_coverage.py --min-families 5 --fail-below` first.
If Cher/Cans have 0 font families, exclude or acquire fonts before the run.

### Decision 2: Armn + Grek (Armenian, Greek) — Unexpected Scripts

Armenian (`Armn`) and Greek (`Grek`) were found in the v3 bucket but were not in the
original design. They exist because the generator corpus included multilingual documents.

**Options**:
- **Keep**: Expand to 29-class model (27 planned + Armn + Grek). Requires updating
  `config/script_ml_classes.yaml` and the training config.
- **Remove**: Delete Armn/Grek images from GCS (`gsutil -m rm gs://image_detection_b/synth_multiscript_v3/Armn/**`).
  Model stays at 27 classes.

**Recommendation**: Check actual counts first. If < 1,000 images each, removing is simpler.

### Decision 3: Kore → Hang (Korean Script Code Fix) — Trivial

The current generator uses `Kore` (Korean — composite) for Korean text. The correct
ISO 15924 code is `Hang` (Hangul). This is a cosmetic rename with no functional impact,
but should be done now to avoid confusion.

**Fix**: In all scripts that reference the Korean script code, replace `Kore` → `Hang`:
- `scripts/audit_v3_per_script_counts.py` (line 47)
- `scripts/generate_base_dataset_v3.py` (wherever Korean script code is used)

---

## 4. Audit Commands

Run these before the generation fill to establish baseline and verify font coverage:

```bash
# Baseline: count current images per script from GCS
uv run python scripts/audit_v3_per_script_counts.py \
    --no-use-splits-jsonl \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --output results/v3_per_script_audit.json \
    --expected-per-script 12962

# Verify font coverage (need ≥5 families per script)
uv run python scripts/audit_font_coverage.py \
    --font-dir fonts/synthetic-gen/ \
    --min-families 5 \
    --fail-below

# Review audit output to inform Decisions 1-2
cat results/v3_per_script_audit.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total found: {data[\"audit_total\"]:,}')
print(f'Scripts needing generation: {data[\"scripts_needing_generation\"]}')
for s, info in data['per_script'].items():
    if not info['done']:
        print(f'  {s}: found={info[\"found\"]:,} remaining={info[\"remaining\"]:,}')
"
```

---

## 5. Generation Fill Command

After resolving Decisions 1–3 and verifying fonts:

```bash
# Full targeted fill (skips scripts already at target)
uv run python scripts/generate_base_dataset_v3.py \
    --total 350000 \
    --resume-from-audit results/v3_per_script_audit.json \
    --output-gcs gs://image_detection_b/synth_multiscript_v3/ \
    --font-min-families 5 \
    --fail-on-corpus-error \
    --chunk-size 5000

# Monitor progress (new terminal)
watch -n 60 "gsutil du -s gs://image_detection_b/synth_multiscript_v3/"
```

**Timing estimate**:
- A100 GPU: ~5–8 hours (image rendering is CPU-bound; A100 helps with JPEG encoding)
- CPU-only: ~15–25 hours (feasible with nohup or tmux)

**Resume support**: The generator reads `--resume-from-audit` at startup and skips scripts
with `done: true`. If the run is interrupted, re-run the audit step, then re-run the
generator with the updated audit JSON.

---

## 6. Verification After Generation

```bash
# Verify all 27 scripts within ±5% of 12,962 target
uv run python scripts/audit_v3_per_script_counts.py \
    --no-use-splits-jsonl \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --expected-per-script 12962 \
    --tolerance 0.05 \
    --verify

# Expected: exit 0 with "VERIFICATION PASSED: All 27 scripts at target."
# If any script fails, re-run the generator with updated audit JSON.
```

Also update `docs/datasets/training/synth-multiscript-v3.md` to record the new count.

---

## 7. Key Files

| File | Role |
|---|---|
| `scripts/generate_base_dataset_v3.py` | Generator (bug already fixed) |
| `scripts/audit_v3_per_script_counts.py` | Per-script count audit + deficit JSON |
| `scripts/audit_font_coverage.py` | Font family count per script |
| `config/script_ml_classes.yaml` | Authoritative ISO 15924 → ML class mapping |
| `results/v3_per_script_audit.json` | Output of audit step (consumed by generator) |
| `docs/datasets/training/synth-multiscript-v3.md` | Dataset documentation (update after completion) |

---

## 8. Completion Criteria

| Criterion | Status |
|---|---|
| All 3 label decisions resolved | ❌ Pending |
| Cher/Cans font families ≥ 5 (or excluded) | ❌ Pending audit |
| Armn/Grek kept or removed with GCS cleanup | ❌ Pending decision |
| Kore → Hang rename applied | ❌ Trivial, do immediately |
| GCS image count ≥ 345,000 (±5%) | ❌ ~190K currently |
| All scripts within ±5% of 12,962 | ❌ Pending generation |
| `synth-multiscript-v3.md` updated | ❌ Pending |
