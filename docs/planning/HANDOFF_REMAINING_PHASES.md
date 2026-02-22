# Handoff: Remaining Phases (5–7) — Stream 4C Dataset Preparation

> **Date**: 2026-02-21
> **Branch**: `feat/ood-dataset-diversity-framework`
> **Author**: Claude Sonnet 4.6 (session continuation)
> **Recipient**: Team executing Phases 5–7 of Stream 4C

This document covers the three phases deferred from the current session due to unresolved
multitask dataset issues. Read Phase status summaries in order; each phase gates the next.

---

## 1. Phase Status Summary (as of 2026-02-21)

| Phase | Name | Status | Blocker |
|---|---|---|---|
| Phase 1 | Create scripts | ✅ Complete | — |
| Phase 2 | Spot-check severity | ✅ Complete | — |
| Phase 3 | Full severity labeling | ✅ **Complete** | sd7k 7,238/7,239 ✅; wsrd 2,200 shadow pairs ✅; warpdoc 1,020/1,020 ✅ |
| Phase 4 | Re-run DDRs | ✅ **Complete** | warping: 46.1/100 ✅; shadow: 46.1/100 ✅ (100% labeled, 9,438 pairs) |
| **Phase 5** | View generation | ❌ Deferred | Requires Phase 3 + resolved synth-multiscript-v3 |
| **Phase 6** | prepare_multitask_datasets | ❌ Deferred | Requires Phase 5 + warping real pairs resolved |
| **Phase 7** | Merge + GCS upload | ❌ Deferred | Requires Phase 6 completion |

### Phase 3 Verification (Do This First)

After the labeling jobs complete, verify all three datasets have severity fields:

```python
import json
for ds, field in [('sd7k', 'shadow_severity'), ('wsrd', 'shadow_severity'), ('warpdoc', 'warping_severity')]:
    with open(f'/mnt/e/image_detection/metadata_registry/json/{ds}_metadata.json') as f:
        data = json.load(f)
    n = sum(1 for s in data['samples']
            if s.get('enrichments', {}).get('versions', [{}])[-1].get('data', {}).get(field) is not None)
    print(f'{ds}: {n:,} / {len(data["samples"]):,} have {field}')
```

Final status (2026-02-21 — Phase 3 complete):
```
sd7k:    7,238 / 7,239 have shadow_severity  ✅ (1 skipped — no clean/gt pair found)
wsrd:    2,200 / 4,500 have shadow_severity  ✅ (2,300 skipped — warping-only samples)
warpdoc: 1,020 / 1,020 have warping_severity ✅
Total shadow labeled: 9,438 pairs
```

Shadow DDR re-run result: **46.1/100** (100% label quality, 100% stat tests)

---

## 2. Phase 5: View Generation

**Purpose**: Generate synthetic shadow/warping/orientation images from v3 GCS pool,
creating the synthetic component of each task's training manifest.

**Prerequisites**:
- Phase 3 complete (severity labels in L2)
- GCS credentials active (`GOOGLE_APPLICATION_CREDENTIALS`)
- E: drive mounted at `/mnt/e/`

### 5A. Shadow Views (8,000 images)

```bash
# Dry-run first — verify expected 8K output count
uv run python scripts/generate_v3_shadow_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/shadow_synthetic \
    --count 8000 \
    --dry-run

# Full run
uv run python scripts/generate_v3_shadow_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/shadow_synthetic \
    --count 8000
```

Expected output: `shadow_synthetic/shadow_metadata.json` (8,000 entries)
Shadow types: edge_shadow, cast_shadow, spotlight_shadow, scanner_lid_shadow

### 5B. Warping Views (5,000 images)

```bash
uv run python scripts/generate_v3_warping_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/warping_synthetic \
    --count 5000 \
    --dry-run  # Verify first

uv run python scripts/generate_v3_warping_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/warping_synthetic \
    --count 5000
```

Expected output: `warping_synthetic/warping_metadata.json` (5,000 entries)
Warp types: perspective, page_curl, fold

### 5C. Orientation Synthetic Component (~20,000 images)

```bash
uv run python scripts/derive_v3_orientation_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/synthetic \
    --target-per-class 5000 \
    --dry-run  # Verify ~20K total (4 classes × 5K)

uv run python scripts/derive_v3_orientation_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/synthetic \
    --target-per-class 5000
```

### 5D. Orientation Real Component (~11,000 images)

```bash
uv run python scripts/build_orientation_real_component.py \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/real \
    --sources doclaynet:8000 rvlcdip:3000 \
    --dry-run  # Verify ~11K total

uv run python scripts/build_orientation_real_component.py \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/real \
    --sources doclaynet:8000 rvlcdip:3000
```

### Phase 5 Verification Gate

```bash
# All four outputs must exist and have expected counts
python3 -c "
import json, pathlib
for path in [
    '/mnt/e/image_detection/03_training_datasets/shadow_synthetic/shadow_metadata.json',
    '/mnt/e/image_detection/03_training_datasets/warping_synthetic/warping_metadata.json',
]:
    data = json.loads(pathlib.Path(path).read_text())
    count = len(data) if isinstance(data, list) else len(data.get('samples', []))
    print(f'{pathlib.Path(path).name}: {count:,} records')
"
```

---

## 3. Phase 6: prepare_multitask_datasets.py Sub-Commands

**Run each sub-command with `--dry-run` first, then without.**

### Previous Dry-Run Results (2026-02-21)

These results are from the last dry-run session (before severity labels existed):

| Sub-command | Result | Issue |
|---|---|---|
| `script` | ✅ 753 MDIW13 images, 9 classes | v3 GCS skipped in dry-run |
| `source` | ✅ 39,893 records (camera:19K/born_digital:10K/scanned:10K) | None |
| `orientation` | ✅ 50K stub | 60% real/40% synth, balanced |
| `shadow` | ⚠️ 0 real records | Severity not in L2 yet (fixed after Phase 3) |
| `warping` | ⚠️ 0 real records | Severity not in L2 yet (fixed after Phase 3) |

### Synthetic Caps (Hard Limits)

```python
SYNTHETIC_CAPS = {
    "script":      0.60,   # ≤60% synthetic
    "orientation": 0.40,   # ≤40% synthetic
    "source":      0.05,   # ≤5% synthetic
    "shadow":      0.50,   # ≤50% synthetic
    "warping":     0.30,   # ≤30% synthetic (CRITICAL: see §3A)
}
```

### 3A. Known Issue: Warping Real Pair Shortfall

**Problem**: The warping cap is 30% synthetic, meaning:
`max_synth / total ≤ 0.30` → `total = real / 0.70`

With only warpdoc (1,020 real pairs after Phase 3):
- max synth = `1,020 × 0.30 / 0.70 = 437`
- total = `1,020 + 437 = 1,457` → **FAR below 19,520 target**

With warpdoc + anyphotodoc6300 (6,306) + docalign12k (~4,000 subset):
- Real total: ~11,326 pairs (after labeling — see `HANDOFF_GPU_WORK.md §2C`)
- Max synth: `11,326 × 0.30 / 0.70 = 4,854`
- Total: `~16,180` — closer but still below 19,520

**Resolution options** (choose one before Phase 6):
1. Label anyphotodoc6300 + docalign12k warping severity (2–3 hours CPU) — preferred
2. Relax `SYNTHETIC_CAPS["warping"]` from 0.30 to 0.40–0.50 (architecture decision)
3. Accept lower total for warping dataset (reduce target from 19,520)

### 6A. Script Sub-Command

```bash
uv run python scripts/prepare_multitask_datasets.py script \
    --mdiw13-dir /mnt/e/image_detection/01_base_data/language/mdiw13/SIW_Database/SIW_MultiscriptDatabase/MultiscriptPrintedDocuments/ \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/script_training \
    --dry-run

# Remove --dry-run after verifying ~200K expected records
```

Expected: ~753 real (MDIW13) + ≤60% synthetic from v3 = ~188K total (after v3 completion)

### 6B. Source Sub-Command

```bash
uv run python scripts/prepare_multitask_datasets.py source \
    --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \
    --output-dir /mnt/e/image_detection/03_training_datasets/source_training \
    --dry-run

# Expected: ~39,893 records (camera/born_digital/scanned)
```

### 6C. Orientation Sub-Command

```bash
uv run python scripts/prepare_multitask_datasets.py orientation \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_training \
    --dry-run

# Expected: ~50K records from existing orientation dataset
```

### 6D. Shadow Sub-Command (Requires Phase 5A first)

```bash
uv run python scripts/prepare_multitask_datasets.py shadow \
    --synthetic-metadata /mnt/e/image_detection/03_training_datasets/shadow_synthetic/shadow_metadata.json \
    --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \
    --output-dir /mnt/e/image_detection/03_training_datasets/shadow_training \
    --dry-run

# GATE: "0 real records" → Phase 3 did not complete. Debug before proceeding.
# Expected after Phase 3: ~9,439 real (sd7k+wsrd) + ≤50% synthetic (max 9,439) = ~17,439 total
```

### 6E. Warping Sub-Command (Requires Phase 5B + §3A resolved first)

```bash
uv run python scripts/prepare_multitask_datasets.py warping \
    --synthetic-metadata /mnt/e/image_detection/03_training_datasets/warping_synthetic/warping_metadata.json \
    --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \
    --output-dir /mnt/e/image_detection/03_training_datasets/warping_training \
    --dry-run

# Expected after §3A resolved: ~11,326 real + ≤30% synthetic = ~16,180 total
```

### Phase 6 Verification Gate

Each output dir must contain `{task}_manifest.json`:

```bash
for task in script source orientation shadow warping; do
    f="/mnt/e/image_detection/03_training_datasets/${task}_training/${task}_manifest.json"
    [ -f "$f" ] && echo "$task: ✅ $(python3 -c "import json; d=json.load(open('$f')); print(len(d.get('samples', d)) if isinstance(d, (dict, list)) else 'err')" ) records" || echo "$task: ❌ MISSING"
done
```

---

## 4. Phase 7: Merge + GCS Upload

**Prerequisite**: All 5 task manifests verified in Phase 6.

```bash
uv run python scripts/prepare_multitask_datasets.py merge \
    --script-dir /mnt/e/image_detection/03_training_datasets/script_training \
    --orientation-dir /mnt/e/image_detection/03_training_datasets/orientation_training \
    --source-dir /mnt/e/image_detection/03_training_datasets/source_training \
    --shadow-dir /mnt/e/image_detection/03_training_datasets/shadow_training \
    --warping-dir /mnt/e/image_detection/03_training_datasets/warping_training \
    --gcs-output-prefix gs://image_detection_b/datasets/multitask_training
```

### Smoke Test After Upload

```bash
# Verify manifests exist on GCS
gsutil ls gs://image_detection_b/datasets/multitask_training/
# Expected: train_manifest.json, val_manifest.json

# Check manifest format (flat JSON list per training script contract)
gsutil cat gs://image_detection_b/datasets/multitask_training/train_manifest.json | \
    python3 -c "import json, sys; d=json.load(sys.stdin); print(type(d), len(d), 'records')"
# Must be: <class 'list'> N records

# Validate required fields in first 5 samples
gsutil cat gs://image_detection_b/datasets/multitask_training/train_manifest.json | \
    python3 -c "
import json, sys
d = json.load(sys.stdin)
required = ['image_path', 'split_type']
for i, s in enumerate(d[:5]):
    missing = [f for f in required if f not in s]
    print(f'[{i}] split_type={s.get(\"split_type\")!r} missing={missing}')
"
```

---

## 5. Known Gotchas

| Issue | Details |
|---|---|
| Warping shortfall | See §3A — needs anyphotodoc6300/docalign12k labeling before Phase 6 |
| No anyphotodoc6300 resolver | `label_warping_severity.py` supports only `warpdoc` and `wsrd`; add resolver for `anyphotodoc6300` before running |
| Phase 1 scripts not yet run | `generate_v3_shadow_view.py` etc. have not been executed; shadow/warping Phase 6 will fail without their output |
| OOD leakage check is active | `prepare_multitask_datasets.py` checks all images against `metadata_registry/ood_registry.jsonl`; registry is currently empty so check is vacuous but active |
| `split_type` required | All manifest records must have `split_type: "train"`, `"val"`, or `"test"` — training script rejects `"ood"` entries |
| GCS auth per session | `GOOGLE_APPLICATION_CREDENTIALS` must be set before any GCS operation |
| WSL cross-filesystem IO | Image loading from `/mnt/e/` is ~2–3s/img; severity labeling for 9K+ pairs takes 3+ hours on WSL |

---

## 6. Definition of Done

### Phase 5
- [ ] `shadow_synthetic/shadow_metadata.json` exists with 8,000 entries
- [ ] `warping_synthetic/warping_metadata.json` exists with 5,000 entries
- [ ] `orientation_v2/synthetic/` and `orientation_v2/real/` populated

### Phase 6
- [ ] `shadow` dry-run shows `>0 real records`
- [ ] `warping` dry-run shows `>0 real records`
- [ ] All 5 task manifests exist in output dirs
- [ ] Shadow total ≥ 12,000 records; warping total ≥ 10,000 records (or agreed lower target)

### Phase 7
- [ ] `gs://image_detection_b/datasets/multitask_training/train_manifest.json` exists
- [ ] `gs://image_detection_b/datasets/multitask_training/val_manifest.json` exists
- [ ] Both are flat JSON lists (not `{"samples": [...]}`)
- [ ] All records have `image_path` (relative to `/data/`), `split_type`, and at least one task field
- [ ] Modal training run starts without manifest validation errors

### Final Gate: Training Launch

```bash
# On Modal (4D team responsibility)
uv run modal run modal/train_siglip2_multitask.py \
    --manifest-gcs-path gs://image_detection_b/datasets/multitask_training/train_manifest.json \
    --epochs 1 \
    --batch-size 8  # Smoke test: 1 epoch, small batch
```
