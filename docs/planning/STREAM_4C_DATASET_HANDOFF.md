# Stream 4C Dataset Preparation — Handoff Document

**Date**: 2026-02-21
**Branch**: `feat/phase-10-remaining`
**Prepared by**: Phase 10 Implementation Team
**Recipient**: Dataset Preparation Team
**Status**: Ready for handoff — training infrastructure complete, datasets not yet uploaded

---

## 1. What Is This Work?

**Stream 4C** is the dataset preparation phase for the SigLIP 2 Multi-Task Teacher model. The
training script and model architecture are already written and tested. Your job is to prepare the
five training datasets and upload them to GCS in the format the training script expects.

Once the datasets are in place, training can be launched with a single Modal command
(that is **not** your responsibility — it is handled by the team running 4D).

### Context (read-only, no action needed)

The project is a document image preprocessing pipeline. The SigLIP 2 multi-task teacher model
(`modal/train_siglip2_multitask.py`) is a ViT-B/16 backbone extended with eight task heads. Three
IQA heads already exist from a previously trained checkpoint. Your datasets feed the **five new
detection heads**:

| Head | Task Type | Classes/Output |
|---|---|---|
| Script | Classification | 19 classes (see §4.1) |
| Document Source | Classification | 3 classes: `scanned`, `camera`, `born_digital` |
| Orientation | Classification | 4 classes: `0`, `90`, `180`, `270` (degrees) |
| Shadow | Regression | Float 0–1 (severity score) |
| Warping | Regression | Float 0–1 (severity score) |

---

## 2. Codebase Orientation

### Key Files

| File | Purpose | Your interaction |
|---|---|---|
| `modal/train_siglip2_multitask.py` | Training script (2,652 LOC) | Read for manifest format; **do not modify** |
| `config/siglip2_multitask.yaml` | Training configuration | Read for GCS paths and targets |
| `config/script_ml_classes.yaml` | ISO 15924 → ML class mapping | Read; authoritative script class source |
| `scripts/prepare_multitask_datasets.py` | **Your deliverable** (does not exist yet) | Write this |
| `docs/planning/STREAM_4_IMPLEMENTATION_PLAN.md` | Full implementation plan | Reference |

### Repository Setup

```bash
git clone <repo>
git checkout feat/phase-10-remaining
uv sync --extra dev
```

### GCS Access

- **Bucket**: `image_detection_b`
- **Auth**: `GCP_SA_KEY` secret (base64-encoded service account JSON)

```bash
# Decode and activate GCS credentials locally
echo "$GCP_SA_KEY" | base64 -d > /tmp/gcs_sa.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_sa.json
gcloud auth activate-service-account --key-file=/tmp/gcs_sa.json

# Verify access
gsutil ls gs://image_detection_b/
```

---

## 3. What You Deliver

### Deliverable: `scripts/prepare_multitask_datasets.py`

A single script with **five sub-commands**, one per head. Each sub-command:

1. Discovers source images (local or GCS)
2. Computes labels
3. Splits by document ID (80 / 10 / 10)
4. Uploads images to GCS (if not already there)
5. Writes a `manifest.json` to GCS

```
uv run python scripts/prepare_multitask_datasets.py script     [options]
uv run python scripts/prepare_multitask_datasets.py source     [options]
uv run python scripts/prepare_multitask_datasets.py orientation [options]
uv run python scripts/prepare_multitask_datasets.py shadow     [options]
uv run python scripts/prepare_multitask_datasets.py warping    [options]
```

### Definition of Done

Training can be launched without error when all five of these GCS paths have valid manifests:

| GCS Path | Head | Required Files |
|---|---|---|
| `gs://image_detection_b/datasets/script_training/` | Script | `manifest_train.json`, `manifest_val.json`, `manifest_test.json` |
| `gs://image_detection_b/datasets/source_training/` | Document Source | same |
| `gs://image_detection_b/datasets/orientation_training/` | Orientation | same |
| `gs://image_detection_b/datasets/shadow_training/` | Shadow | same |
| `gs://image_detection_b/datasets/warping_training/` | Warping | same |

All manifests must pass a smoke test (see §8).

---

## 4. Dataset Specifications

### 4.1 Script Dataset

#### Source Datasets (all on GCS or locally available)

| Dataset | GCS Path / Local | Images | Scripts | Status |
|---|---|---|---|---|
| synth-multiscript-250k | `gs://image_detection_b/synth-multiscript/` | 250,000 | 27 | ✅ On GCS |
| MDIW13 | `gs://image_detection_b/mdiw13/` | 290,000 | 13 | ✅ On GCS |
| SIW13 | Verify GCS or local | 16,000 | 13 | Verify |
| CVSI | Verify GCS or local | 10,000 | 10 | Verify |
| tibhcr | Verify GCS or local | 142,000 | 1 (Tibetan) | Verify — critical for TIBT class |
| hindi-synth | Verify GCS or local | 80,000 | 1 (Devanagari) | Verify — critical for DEVA class |

> **Note**: If the 108-script OpenLID v2 generation dataset is available, include it. If not, the
> six datasets above are sufficient for all 19 classes.

#### Class Mapping (authoritative source)

**Use `config/script_ml_classes.yaml`**. Do NOT use the class list in the implementation plan
— it describes a 12-class option that was considered but not adopted. The training script
uses the 19-class list below (hardcoded in `modal/train_siglip2_multitask.py` lines 101–121).

| Index | Class | ISO 15924 codes that map to it |
|---|---|---|
| 0 | LATN | Latn, Latf, Latg |
| 1 | CYRL | Cyrl, Cyrs |
| 2 | GREK | Grek |
| 3 | ARAB | Arab, Aran |
| 4 | HEBR | Hebr |
| 5 | DEVA | Deva |
| 6 | BENG | Beng |
| 7 | TAML | Taml |
| 8 | TELU | Telu |
| 9 | HANS | Hans, Hani |
| 10 | HANT | Hant |
| 11 | JPAN | Jpan, Hrkt, Hira, Kana |
| 12 | KORE | Kore, Hang |
| 13 | THAI | Thai |
| 14 | TIBT | Tibt |
| 15 | INDIC_OTHER | Gujr, Knda, Mlym, Orya, Sinh, Guru |
| 16 | SE_ASIAN_OTHER | Khmr, Laoo, Mymr |
| 17 | OTHER | Armn, Geor, Ethi, Zyyy, Zinh |
| 18 | UNKNOWN | Zzzz, undetermined |

> The full ISO → ML mapping is in `config/script_ml_classes.yaml` under `iso15924_to_ml_class`.
> Any script code not listed maps to `OTHER` (see `unmapped_default` field).

#### Source Label Format

Each source dataset stores script information differently. You will need to check each:

- **synth-multiscript-250k**: JSON metadata per image or sidecar file with `script` field
  (ISO 15924 code). Look in GCS metadata or accompanying `labels.json`.
- **MDIW13**: Folder-based — each subfolder is named by script (e.g., `Arabic/`, `Chinese/`).
  Map folder names to ISO 15924 codes, then to ML class.
- **tibhcr**: All images are Tibetan → class `TIBT`.
- **hindi-synth**: All images are Devanagari → class `DEVA`.
- **SIW13 / CVSI**: Check dataset documentation for label format.

#### Manifest Format (per-split JSON array)

```json
[
  {
    "image_path": "images/img_001.jpg",
    "script_class": "LATN",
    "source_dataset": "synth-multiscript-250k",
    "document_id": "doc_00123"
  },
  ...
]
```

> `image_path` is **relative to the GCS prefix** for that split. The training script resolves
> it as `{gcs_prefix}/{split}/images/img_001.jpg`.

#### Split Strategy

- Split by `document_id` (not image ID) — images from the same source document must stay
  in the same split to prevent train/test leakage.
- Target: **200K train / 25K val / 25K test**
- Minimum 1,000 samples per class per split
- Script classes with fewer than 1,000 samples available should be excluded from that split
  and logged in the preparation report
- UNKNOWN samples (class index 18) should be sampled at lower rate; set target to max 5% of
  total or zero if not needed for balance

#### Class Imbalance

Latin and CJK scripts will dominate raw counts. Downsample them to a ceiling after all rare
classes (TIBT, HEBR, GREK) meet the 1,000-per-split minimum.

The `config/script_ml_classes.yaml` provides initial `class_weights` (higher weight = more
emphasis). Your prepare script should:
1. Compute actual per-class counts in the final train split
2. Write computed class weights to the manifest alongside the sample list:
   ```json
   {
     "samples": [...],
     "class_weights": [1.0, 1.2, 1.5, ...]
   }
   ```
   (The training script reads this from the manifest to initialize the cross-entropy loss.)

---

### 4.2 Orientation Dataset

#### Source

Assembled orientation dataset: **50,000 images, 4-class balanced**.
- Local path (Windows): `E:\03_training_datasets\orientation\`
- WSL path: `/mnt/e/03_training_datasets/orientation/`
- GCS target: `gs://image_detection_b/datasets/orientation_training/`

Check if this dataset is already on GCS before uploading.

#### Label Format

Images are pre-rotated at 0°/90°/180°/270°. Labels are in either:
- **Filename encoding**: `doc_001_rot090.jpg` → `orientation: 90`
- **Sidecar JSON**: `labels.json` with `{"filename": "...", "orientation": 90}`

Check which format is present and handle both.

#### Manifest Format

```json
[
  {
    "image_path": "images/img_001.jpg",
    "orientation": 90,
    "document_id": "doc_00001"
  },
  ...
]
```

> `orientation` must be an integer: `0`, `90`, `180`, or `270`. The training script
> (`ORIENTATION_TO_IDX`) maps these exact integers to class indices.

#### Split

| Split | Count |
|---|---|
| Train | 40,000 |
| Val | 5,000 |
| Test | 5,000 |

Split by document ID — the same physical document, shown at different rotations, must not
span splits.

---

### 4.3 Document Source Dataset

#### Source Datasets and Class Assignments

| Dataset | Class | Images Available | Notes |
|---|---|---|---|
| SmartDoc-QA | `camera` | ~4,300 | Layer 2 metadata has `capture_method` |
| realdae | `camera` | ~1,200 | Layer 2 metadata |
| midv500 | `camera` | ~3,600 | MIT license |
| RVL-CDIP | `scanned` | ~400,000 total | Use subset of 10,000 |
| tobacco800 | `scanned` | ~1,300 | Layer 2 metadata |
| DocLayNet (born-digital subset only) | `born_digital` | ~81,000 | Use subset of 10,000 |

> **Critical naming**: The training script uses `born_digital` (with underscore), not `digital`.
> `SOURCE_CLASSES = ("scanned", "camera", "born_digital")`. Wrong spelling → sample silently
> dropped.

#### Labels

Labels come from Layer 2 metadata aggregates. The `capture_method` field in each dataset's
Layer 2 JSON uses the `CaptureMethod` enum values. Map:
- `SCAN` / `SCANNER` / `scanned` → `scanned`
- `PHONE` / `CAMERA` / `camera` → `camera`
- `DIGITAL` / `born_digital` / `BORN_DIGITAL` → `born_digital`

Layer 2 metadata directory: `/mnt/e/image_detection/metadata_registry/json/`

#### Balancing

Cap each class at 10,000 samples:

| Class | Raw Available | Use |
|---|---|---|
| `camera` | ~9,100 | All (no downsampling) |
| `scanned` | ~400,000 | Downsample to 10,000 |
| `born_digital` | ~81,000 | Downsample to 10,000 |

#### Manifest Format

```json
[
  {
    "image_path": "images/img_001.jpg",
    "source_class": "scanned",
    "source_dataset": "rvl-cdip",
    "document_id": "doc_00001"
  },
  ...
]
```

#### Split

80/10/10 stratified by class and document ID.

---

### 4.4 Shadow Dataset

#### Source Datasets

| Dataset | Type | Images | Notes |
|---|---|---|---|
| sd7k | Paired GT (shadow / clean) | 7,239 pairs | Best severity signal |
| wsrd | Paired GT (shadow / clean) | 4,500 pairs | Audit grade A (95) |
| DocLayNet / TableBank (negatives) | Clean (no shadow) | Sample 3,500 | Score = 0.0 |

> doc3d is available (102K images) but extraction of shadow severity from 3D illumination data
> is complex. **Do not use doc3d** unless sd7k + wsrd + negatives fall short of the 15K target.

#### Severity Label Computation

For each (shadow_image, clean_image) pair:

```python
from skimage.metrics import structural_similarity as ssim
import cv2

shadow_gray = cv2.cvtColor(shadow_img, cv2.COLOR_BGR2GRAY)
clean_gray  = cv2.cvtColor(clean_img,  cv2.COLOR_BGR2GRAY)

score = float(ssim(shadow_gray, clean_gray, data_range=255))
severity = round(1.0 - score, 4)  # 0 = no shadow, 1 = total shadow
severity = max(0.0, min(1.0, severity))  # clamp
```

Spot-check 50 pairs manually before processing all 11K to verify scores align with visual
severity.

#### Negative Examples

Sample 3,500 clean pages from DocLayNet or TableBank (born-digital, no visible shadows).
Assign `shadow_score = 0.0` exactly.

#### Manifest Format

```json
[
  {
    "image_path": "images/shadow_img_001.jpg",
    "severity": 0.43,
    "source_dataset": "sd7k",
    "document_id": "sd7k_0001"
  },
  ...
]
```

> The field name is `severity` (not `shadow_score`). The training script reads `entry["severity"]`
> for both shadow and warping datasets (see `_create_shadow_warp_dataset` in the training script).

#### Split

| Split | Count |
|---|---|
| Train | ~12,200 |
| Val | ~1,520 |
| Test | ~1,520 |

Split by document ID.

---

### 4.5 Warping Dataset

#### Source Datasets

| Dataset | Type | Images | Notes |
|---|---|---|---|
| warpdoc | Paired GT (distorted / flat) | 1,020 pairs | 6 warping types; best type diversity |
| anyphotodoc6300 | Paired GT (distorted / corrected) | 6,306 pairs | Audit grade A (92) |
| docalign12k | Aligned pairs | ~12,000 | Use subset of 4,000 |
| docreal | Paired GT | 200 pairs | MIT license |
| DocLayNet / TableBank (negatives) | Flat clean docs | Sample 5,000 | Score = 0.0 |

> **Do not use SmartDoc-QA** for warping labels unless the metadata clearly indicates distortion
> magnitude; its "perspective" metadata is not directly comparable to the SSIM severity scale.

#### Severity Label Computation

Same formula as shadow — SSIM difference between distorted and flat reference:

```python
severity = round(1.0 - ssim(distorted_gray, flat_gray, data_range=255), 4)
severity = max(0.0, min(1.0, severity))
```

For warpdoc specifically, the dataset provides 6 warping type labels (book spine, fold,
crumple, etc.). Store these as auxiliary metadata in the manifest (`warping_type` field)
but they are **not used during training** — only the scalar severity score is used. They are
for Phase E (evaluation) analysis only.

#### Manifest Format

```json
[
  {
    "image_path": "images/warp_img_001.jpg",
    "severity": 0.31,
    "source_dataset": "warpdoc",
    "document_id": "warpdoc_0001",
    "warping_type": "book_spine"
  },
  ...
]
```

> The `warping_type` field is optional and ignored by the training script. Include it for
> evaluation use.

#### Split

| Split | Count |
|---|---|
| Train | ~15,620 |
| Val | ~1,950 |
| Test | ~1,950 |

---

## 5. Training Script Contract (Read Carefully)

The training script expects datasets in one of two modes:

### Mode A — Per-Task Directories (default for Phase 1 training)

Each dataset lives in its own GCS prefix. The training script downloads each to a separate
local directory and instantiates a task-specific `Dataset` class:

```
gs://image_detection_b/datasets/script_training/
    manifest_train.json   ← array of {image_path, script_class, ...}
    manifest_val.json
    manifest_test.json
    images/
        img_001.jpg
        img_002.jpg
        ...
```

The `manifest_*.json` files must contain **relative** image paths (`images/img_001.jpg`),
not absolute paths. The training script resolves them against the dataset root directory.

### Mode B — Unified Manifest (for MultiTaskDataset)

A merged manifest where each entry can have labels for multiple tasks simultaneously.
Used when Phase 2 needs to co-train on samples that have both, e.g., IQA + script labels.

```json
[
  {
    "image_path": "images/img_001.jpg",
    "script": "LATN",
    "source": "scanned",
    "overall": 3.5,
    "sharpness": 4.0,
    "color": 3.8
  },
  {
    "image_path": "images/img_002.jpg",
    "orientation": 90,
    "shadow": 0.35
  }
]
```

**4C deliverable is Mode A only.** Mode B (unified manifest) is a Phase D/training-time
concern, not a 4C deliverable.

### Classification Label Values (exact strings — case-sensitive)

| Head | Valid label values |
|---|---|
| script | `"LATN"`, `"CYRL"`, `"GREK"`, `"ARAB"`, `"HEBR"`, `"DEVA"`, `"BENG"`, `"TAML"`, `"TELU"`, `"HANS"`, `"HANT"`, `"JPAN"`, `"KORE"`, `"THAI"`, `"TIBT"`, `"INDIC_OTHER"`, `"SE_ASIAN_OTHER"`, `"OTHER"`, `"UNKNOWN"` |
| source_class | `"scanned"`, `"camera"`, `"born_digital"` |
| orientation | `0`, `90`, `180`, `270` (integers, not strings) |

**Samples with invalid or unrecognized label values are silently dropped by the training
script.** Log and report any dropped samples.

### Regression Label Range

- `severity` field for both shadow and warping: float in `[0.0, 1.0]`
- The training script reads `entry["severity"]` directly with no transformation

---

## 6. Prepare Script Design Guidance

### Recommended Structure

```python
# scripts/prepare_multitask_datasets.py

import click

@click.group()
def cli(): ...

@cli.command()
@click.option("--output-gcs", required=True)
@click.option("--dry-run", is_flag=True)
def script(output_gcs, dry_run):
    """Prepare script detection dataset."""
    ...

@cli.command()
@click.option("--source-dir", required=True)
@click.option("--output-gcs", required=True)
def orientation(source_dir, output_gcs):
    """Prepare orientation dataset."""
    ...

# ... source, shadow, warping sub-commands

if __name__ == "__main__":
    cli()
```

### Required per Sub-Command

1. **Discovery**: List all source images and their raw labels
2. **Mapping**: Convert raw labels to the exact strings/ints the training script expects
3. **Splitting**: Deterministic 80/10/10 split by document ID
   - Use `hashlib.sha256(document_id.encode()).hexdigest()` to assign splits deterministically
   - Any document ID with hash prefix `00`–`cc` → train; `cd`–`e5` → val; `e6`–`ff` → test
   - This ensures reproducibility without storing a split registry
4. **Upload**: `gsutil -m cp` or `google.cloud.storage` for image files
5. **Manifest write**: Upload JSON manifest to GCS
6. **Report**: Print per-class counts, any dropped samples, class weight recommendations

### GCS Upload Pattern

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("image_detection_b")

def upload_manifest(manifest: list[dict], gcs_path: str) -> None:
    blob = bucket.blob(gcs_path)
    blob.upload_from_string(json.dumps(manifest, indent=2), content_type="application/json")
```

---

## 7. Open Questions — Decisions Needed Before Starting

These three questions must be resolved before work begins on 4C. Reach out to the project
lead for answers.

| # | Question | Impact |
|---|---|---|
| Q1 | Is the synth-multiscript-250k dataset at `gs://image_detection_b/synth-multiscript/`? What is the exact GCS path and label file location? | Script dataset — cannot start without this |
| Q2 | Are sd7k and wsrd datasets on GCS, or must they be uploaded from a local Windows path? What are the folder structures for paired shadow/clean images? | Shadow dataset — need to verify before SSIM computation |
| Q3 | Is the orientation dataset already on GCS (`gs://image_detection_b/datasets/orientation_training/`)? | Orientation — avoids redundant 3GB upload |

---

## 8. Smoke Test

Before declaring a dataset ready, run this verification against each GCS manifest:

```bash
# Verify script dataset
uv run python - <<'EOF'
import json, random
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("image_detection_b")

for split in ("train", "val", "test"):
    blob = bucket.blob(f"datasets/script_training/manifest_{split}.json")
    samples = json.loads(blob.download_as_text())
    print(f"{split}: {len(samples)} samples")

    # Check class distribution
    from collections import Counter
    counts = Counter(s["script_class"] for s in samples)
    for cls, count in sorted(counts.items()):
        print(f"  {cls}: {count}")

    # Spot-check 5 random images exist
    for s in random.sample(samples, min(5, len(samples))):
        b = bucket.blob(f"datasets/script_training/{split}/{s['image_path']}")
        assert b.exists(), f"Missing: {s['image_path']}"
    print("  Image spot-check: PASSED")
EOF
```

Repeat substituting `script_training` and field names for the other four datasets.

The full smoke test is also verifiable by running the training script in test mode:

```bash
uv run modal run modal/train_siglip2_multitask.py --test
```

This runs 2 training epochs with minimal data and will fail fast if any manifest or GCS path
is misconfigured.

---

## 9. Summary of Dataset Size Targets

| Dataset | Train | Val | Test | Total | GCS Prefix |
|---|---|---|---|---|---|
| Script | 200,000 | 25,000 | 25,000 | 250,000 | `datasets/script_training/` |
| Orientation | 40,000 | 5,000 | 5,000 | 50,000 | `datasets/orientation_training/` |
| Document Source | ~23,000 | ~2,900 | ~2,900 | ~29,000 | `datasets/source_training/` |
| Shadow | ~12,200 | ~1,520 | ~1,520 | ~15,240 | `datasets/shadow_training/` |
| Warping | ~15,620 | ~1,950 | ~1,950 | ~19,520 | `datasets/warping_training/` |

---

## 10. Success Criteria

4C is complete when **all five** of the following are true:

- [ ] `gs://image_detection_b/datasets/script_training/manifest_{train,val,test}.json` exist,
  total ≥ 250K samples, all 19 classes represented in train split with ≥ 1K samples each
- [ ] `gs://image_detection_b/datasets/orientation_training/manifest_{train,val,test}.json`
  exist, 50K total, balanced across 4 classes
- [ ] `gs://image_detection_b/datasets/source_training/manifest_{train,val,test}.json` exist,
  ~29K total, all 3 classes represented, `born_digital` spelling confirmed
- [ ] `gs://image_detection_b/datasets/shadow_training/manifest_{train,val,test}.json` exist,
  ≥ 15K total, `severity` field is a float in [0.0, 1.0]
- [ ] `gs://image_detection_b/datasets/warping_training/manifest_{train,val,test}.json` exist,
  ≥ 19K total, `severity` field is a float in [0.0, 1.0]
- [ ] `uv run modal run modal/train_siglip2_multitask.py --test` exits 0

When done, notify the 4D team. They will launch the Modal training run.

---

**End of handoff document.**
