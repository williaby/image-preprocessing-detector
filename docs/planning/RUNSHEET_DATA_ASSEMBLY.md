---
title: Data Assembly Run-Sheet
schema_type: common
status: active
owner: core-maintainer
purpose: "Ordered, copy-pasteable steps for the first dataset-assembly session on the machine with the data drive and GPU VM."
tags:
- planning
- datasets
- training_data
---

# Data Assembly Run-Sheet

> **Prepared**: 2026-10-02 from a cloud session with no access to the data drive, GCS or a GPU.
> Everything here was written and unit-tested against synthetic data only. Steps marked
> **VERIFY** depend on assumptions about real data that have not been confirmed.
>
> **Goal**: five validated task manifests (`script`, `orientation`, `source`, `shadow`,
> `warping`) so GCS upload and the SigLIP 2 Phase-1 smoke run can start next.
> Decisions this run-sheet implements: see `MASTER_PROJECT_PLAN.md` Tier 0 (2026-10-01).

Paths below assume `DATA=/mnt/e/image_detection` and `TRAIN=/mnt/e/03_training_datasets`.
Run each command with `--dry-run` first where the script supports it. Stop at any
**STOP IF** line.

---

## 0. Policy gates (read before running anything)

Defaults in the scripts predate the licensing decisions. Pass the overrides shown.

| Script | Default includes | Problem | Use instead |
| --- | --- | --- | --- |
| `prepare … shadow` | `sd7k, wsrd` | wsrd is CC-BY-NC-SA (excluded from production training) | `--l2-datasets sd7k` |
| `prepare … warping` | `warpdoc, anyphotodoc6300, docalign12k, docreal` | warpdoc unspecified; anyphotodoc6300 GPL-3.0; docalign12k unspecified | `--l2-datasets docreal` + `--extra-real-labels` (doc3d) |
| `prepare … source` | `doclaynet, rvlcdip, smartdoc-qa, realdae, midv500` | rvlcdip / smartdoc-qa / realdae are research-terms-only | see **OPEN DECISION** below |
| `prepare … script` | MDIW13 | MDIW13 is academic-terms-only | see **OPEN DECISION** below |

**OPEN DECISION (not yet made): research-terms datasets.** The 2026-10-01 decision covers
CC-BY-SA and NC/GPL data. It does not cover ~22 datasets under "research use" terms
(rvl-cdip, mdiw13, smartdoc-qa, realdae, …). `LICENSE_IMPACT_REPORT.md` rates these *high
TOU risk for a public release*, which is what CC-BY-SA weights are. Options: (a) accept the
risk and disclose in the model card, (b) exclude them from the production run and use them
for evaluation/smoke runs only, (c) run smoke now, decide before the production run.
**Recommendation: (c).** Nothing in the smoke run is irreversible; the manifests carry
dataset provenance so they can be filtered. Whichever you choose, record it in the plan.

**License fields (added 2026-10-02)**: every manifest record now carries `license` and
`license_class` (`permissive`, `public_domain`, `share_alike`, `generated`, `research_only`,
`mixed`, `non_commercial`, `copyleft_gpl`, `unspecified`), resolved from the `license:`
frontmatter of `docs/datasets/source/*.md`. Each manifest build logs counts per class and
warns on excluded/open classes. At merge, drop classes without rebuilding, e.g.
`--exclude-license-class non_commercial --exclude-license-class copyleft_gpl
--exclude-license-class unspecified` (add `--exclude-license-class research_only` if the open
decision goes that way). Records from a dataset with no source doc are `unspecified`, so they
fail closed. The `--l2-datasets` overrides above remain the first line of defence.

---

## 1. Pre-flight (15 min)

```bash
git pull origin claude/project-plan-sprint-review-0ijvx5
uv sync --extra dev
uv run pytest tests/unit/test_warping_severity.py tests/unit/test_label_doc3d_warping_severity.py \
  tests/unit/test_convert_tiff_to_png.py tests/unit/test_multitask_label_parsing.py \
  tests/unit/test_prepare_warping_extra_labels.py --no-cov -q        # expect 64 passed
gsutil ls gs://image_detection_b/ | head -30
gsutil ls gs://image_detection_b/synth_multiscript_v3/ | head -3
gsutil ls gs://image_detection_b/synth-multiscript-v3/ | head -3
```

**VERIFY**: the scripts default to `synth_multiscript_v3` (underscore); the plan says
`synth-multiscript-v3` (hyphen). Whichever `ls` succeeds is the real prefix. If it is the
hyphen form, pass `--v3-gcs-prefix gs://image_detection_b/synth-multiscript-v3` to every
command that takes it. **STOP IF** neither exists.

Free disk check: warping/shadow/orientation outputs are ~10s of GB; `df -h $TRAIN`.

---

## 2. khatt JPEG → PNG (CPU, ~minutes) — safe to run first

```bash
uv run python scripts/convert_tiff_to_png.py convert \
  --src $DATA/data/train.zip --src $DATA/data/validation.zip --dest $TRAIN/_remediation/khatt_png
uv run python scripts/convert_tiff_to_png.py verify \
  --png-dir $TRAIN/_remediation/khatt_png --jpeg-dir $DATA/01_base_data/<khatt-dir> \
  --report $TRAIN/_remediation/khatt_report.json
```

**Expect**: `converted=~1633 failed=0`; verify prints `missing=0 bad=0 ok=True`.
**VERIFY**: TIFF stems equal the existing JPEG stems (`missing` > 0 means they do not;
then a `--mapping` CSV is needed). **Do not** run `retire-jpeg --yes` yet — first move the
PNGs into place and update L2 metadata/docs (plan "Dataset format remediation" steps 3–6).
`retire-jpeg --png-dir <png> --jpeg-dir <jpeg>` without `--yes` is a safe dry run; it re-verifies
the directories itself and never reads paths from the report file.

**rvl-cdip**: blocked on the TIFF re-download and a `jpeg_stem,tiff_relative_path` CSV. Skip
for this session unless the source mapping is already known.

---

## 3. doc3d warping severity (CPU; bm zips are ~105 GB — read in place)

```bash
D3=$DATA/01_base_data/camera_captured/doc3d/data/doc3d
mkdir -p results/doc3d_warping
uv run python scripts/label_doc3d_warping_severity.py score \
  --bm-dir $D3 --out results/doc3d_warping/spot.jsonl --spot-check 200
```

**Expect**: `scored≈200 skipped≈0`, a percentile line, and `example shape: [448, 448, 2]`.
**VERIFY / STOP IF**:

- error "No usable backward maps found" → open one `bm_*.zip`; the member format or key is
  not `.npy`/`.mat` with key `bm`. Fix `load_backward_map` before continuing.
- raw percentiles all ~0 or all identical → map units/orientation differ from assumption.
- `mat` files that fail to load → they are probably HDF5 (v7.3); `scipy.io.loadmat` cannot
  read those; add `h5py`.

If the spot check is sane, run the full scoring (all maps; allow hours for 102K), then
calibrate and apply:

```bash
uv run python scripts/label_doc3d_warping_severity.py score --bm-dir $D3 --out results/doc3d_warping/raw.jsonl
uv run python scripts/label_doc3d_warping_severity.py calibrate \
  --raw results/doc3d_warping/raw.jsonl --bm-dir $D3 --image-dir $D3/img \
  --out results/doc3d_warping/calibration.json --sample 2000
uv run python scripts/label_doc3d_warping_severity.py apply \
  --raw results/doc3d_warping/raw.jsonl --calibration results/doc3d_warping/calibration.json \
  --image-dir $D3/img --out results/doc3d_warping/doc3d_severity.jsonl
```

**Expect** (calibrate): `Pearson r(raw, ssim_severity) ≥ 0.5` and no WARNING. **STOP IF**
there is a WARNING: do not use these labels. Fall back to downloading doc3d depth maps and
`std(Z)` (plan, Tier 0). Check also that `apply` severity std is not ~0 (a collapsed
distribution gives the head nothing to learn) and spans 0–1 reasonably.

---

## 4. Synthetic views (need GCS read; GPU not required; generation is CPU)

All four are idempotent only if `--seed` is unchanged. Dry-run each first.

```bash
V3=gs://image_detection_b/synth_multiscript_v3     # or the hyphen form per section 1

uv run python scripts/generate_v3_shadow_view.py --v3-gcs-prefix $V3 \
  --output-dir $TRAIN/shadow_synthetic --count 8000 --dry-run
uv run python scripts/generate_v3_warping_view.py --v3-gcs-prefix $V3 \
  --output-dir $TRAIN/warping_synthetic --count 5000 --dry-run
uv run python scripts/derive_v3_orientation_view.py --v3-gcs-prefix $V3 \
  --output-dir $TRAIN/orientation_v2/synthetic --target-per-class 5000 --dry-run
uv run python scripts/build_orientation_real_component.py \
  --output-dir $TRAIN/orientation_v2/real --sources doclaynet:8000 rvlcdip:3000 --dry-run --verbose
```

Then rerun each without `--dry-run`.

**Expect**: shadow → `shadow_metadata.json` (8,000 rows); warping → `warping_metadata.json`
(5,000); orientation synthetic → `orientation_synthetic_metadata.json` (~20,000, balanced 4
classes); orientation real → `orientation_real_metadata.json` (~4 rotated copies per base
doc: 11K base ≈ 44K images, which is more than the plan's "11K real" — that figure counts
base documents).

**Known caveat (decision needed, low urgency)**: shadow/warping views are written as JPEG
(`JPEG_QUALITY = 92`) from v3 sources that are themselves JPEG q95 — a second compression
generation, in data feeding quality-adjacent heads. Acceptable for the smoke run; for
production regenerate from v4 (PNG) and switch the encoder to PNG.

**Known caveat**: `build_orientation_real_component.py` includes `rvlcdip` — see policy gate.

---

## 5. Manifests (CPU)

```bash
uv run python scripts/prepare_multitask_datasets.py orientation \
  --real-metadata $TRAIN/orientation_v2/real/orientation_real_metadata.json \
  --synthetic-metadata $TRAIN/orientation_v2/synthetic/orientation_synthetic_metadata.json \
  --output-dir $TRAIN/orientation_training --dry-run

uv run python scripts/prepare_multitask_datasets.py shadow \
  --synthetic-metadata $TRAIN/shadow_synthetic/shadow_metadata.json \
  --l2-datasets sd7k --output-dir $TRAIN/shadow_training --dry-run

uv run python scripts/prepare_multitask_datasets.py warping \
  --synthetic-metadata $TRAIN/warping_synthetic/warping_metadata.json \
  --l2-datasets docreal \
  --extra-real-labels results/doc3d_warping/doc3d_severity.jsonl --max-extra-real 15000 \
  --output-dir $TRAIN/warping_training --dry-run

uv run python scripts/prepare_multitask_datasets.py source --output-dir $TRAIN/source_training --dry-run
uv run python scripts/prepare_multitask_datasets.py script --mdiw13-dir $DATA/mdiw13 \
  --v3-gcs-prefix $V3 --output-dir $TRAIN/script_training --dry-run
```

Rerun without `--dry-run`, then:

```bash
uv run python scripts/prepare_multitask_datasets.py merge \
  --script-dir $TRAIN/script_training --orientation-dir $TRAIN/orientation_training \
  --source-dir $TRAIN/source_training --shadow-dir $TRAIN/shadow_training \
  --warping-dir $TRAIN/warping_training \
  --gcs-output-prefix gs://image_detection_b/datasets/multitask_training --dry-run
```

**Checks (each manifest)**:

- Flat JSON list (merged: `train_manifest.json`, `val_manifest.json`), not `{"samples": …}`
  (the `script` manifest is a dict with `samples`; `merge` unwraps it).
- **Mixing caps are warnings, not enforcement.** Grep the output for `MIXING CAP EXCEEDED`.
  Caps: script ≤60% synthetic, orientation ≤40%, shadow ≤50%, warping ≤30%. If it appears,
  reduce synthetic count or add real data; do not proceed to training.
- Warping real share: with doc3d capped at 15,000 + docreal 200 vs 5,000 synthetic, real ≈
  75% (cap needs ≥70%). doc3d is a *rendered* dataset; the cap check only counts
  `provenance == "synthetic_v3"` as synthetic, so doc3d is counted as real. That matches the
  plan but is a judgment call.
- OOD leak check runs on non-dry-run and reads `metadata_registry/ood_registry.jsonl`
  relative to the current directory — **run from the repo root**. **STOP IF** it reports a
  leak. **VERIFY** it also covers the ~480 john11 entries added since the plan's 9,170 count.
- **Read the "hashed N of M samples" line.** All five sub-commands call the leak check
  without an `image_root`, so a relative `image_path` is resolved against the *current
  directory*. Run from the repo root, dataset images on the data drive are not found and are
  skipped, which previously made the check pass having hashed nothing. It now prints a
  `WARNING ... hashed 0 of M` when that happens. **STOP IF N is far below M**: the leak check
  did not actually run on those samples. Keep the repo root as the working directory (the
  OOD registry path is also relative to it) and do not proceed with a low count; the proper fix
  is an `--image-root` option on the sub-commands, which does not exist yet. Paths containing
  `..` (either slash style) are rejected rather than hashed.
- doc3d split is by mesh ID; confirm no mesh appears in both train and val.
- Shadow and warping `severity` distributions: check for 0–1 spread, not a spike at 0 or 1.

---

## 6. Do not run yet

- `merge` without `--dry-run` / GCS upload — wait for the research-terms decision (section 0), then merge with the matching `--exclude-license-class` flags.
- `retire-jpeg --yes` — wait until PNGs are in place and L2 metadata/docs are updated.
- DeQA-Doc pseudo-labeling — first verify mPLUG-Owl2 / DeQA-Doc output terms are compatible
  with CC-BY-SA weights (plan, Decision 1 follow-ups).

## 7. Report back

For each step record: command, wall time, counts, and any **STOP IF** hit. The three
highest-value facts to bring back: (1) the real prefix of v3 on GCS, (2) the real bm file
format/units from the spot check, (3) the calibration Pearson r.
