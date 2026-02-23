---
l4_category: training-dataset
l4_dataset: warping
l4_workstream: WS3
l4_source_datasets:
  - doc3d
  - smartdoc-qa
  - anyphotodoc6300
  - warpdoc
  - synth-multiscript-v3
  - doclaynet
  - rvl-cdip
l4_generation_script: scripts/prepare_multitask_datasets.py
l4_image_count: 20000
l4_status: blocked
---

# warping

> **Quick Stats**: 20,000 images (target) | Warping severity regression 0–1 | SigLIP 2 NAFlex
>
> **Status**: ❌ Blocked | **HAR Score**: 17/100 | **P0 Gaps**: 4

> **Note on HAR consensus**: During the multi-model consensus run for this head, 3 of 4 models
> experienced context contamination from prior consensus sessions and answered about the
> `code_reg` head rather than `warping_reg`. Only the Gemini 2.5 Pro response is treated as
> valid for this HAR. The ratings, formula recommendations, and gap analysis below reflect
> exclusively the Gemini 2.5 Pro review (9/10 confidence), crosschecked against the analyst's
> independent assessment in the HAR.

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `warping` |
| **Head(s) Fed** | SIG-G5-3 `warping_reg` (also written as `warping_score`) |
| **Model(s)** | SigLIP 2 NAFlex |
| **Task Type** | Regression 0–1 continuous severity score |
| **Primary L2 Field(s)** | `physical_degradation.warping_severity` (float 0–1) |
| **Training Phase** | Phase 5 — Page Attributes |
| **Target Size** | 20,000 images |
| **Image Size** | Variable (NaFlex aspect-ratio-preserving; 384px effective) |
| **Storage Location** | `E:\image_detection\03_training_datasets\warping\` |
| **GCS Path** | `gs://image_detection_b/warping_training/` |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py warping` |
| **HAR File(s)** | [sig-g5-warping-reg.md](../../planning/har/sig-g5-warping-reg.md) |
| **DDR File** | [warping_ddr.md](../diversity_reports/warping_ddr.md) |

`warping_reg` is the sole head consuming this dataset. It is the lowest-scoring head in the
entire SigLIP 2 multi-task review at 17/100 — lower than any other of the 22 heads — because
the primary source dataset (doc3d, 102K images) contains the right raw data but requires a
3D-mesh-to-scalar derivation pipeline that does not yet exist. Unlike most blocked heads where
data is simply absent, warping_reg has the data volume necessary (post-remediation pool of
~111K warped + ~86K NONE candidates) but lacks the extraction formula that would make that
data usable.

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | ❌ Blocked — 4 P0 gaps, none resolved |
| **Current Count** | 0 / 20,000 assembled |
| **HAR Adequacy Score** | 17/100 — ❌ Blocked |
| **P0 Gap Count** | 4 |
| **Primary Blocker** | `label_warping_severity.py` does not exist; derivation formula (WARP-G02) is prerequisite for the labeling script (WARP-G01), which is prerequisite for field population (WARP-G04). WARP-G03 (NONE class construction) is an equally critical parallel blocker. |
| **Estimated Unblock Effort** | 9–11 days (WARP-G02: 2d → WARP-G01: 4–5d → WARP-G04: 2–3d; WARP-G03: 1d in parallel) |
| **Last HAR Updated** | 2026-02-23 |

### Prerequisite Chain

The four P0 gaps are not independent. They form a strict dependency ordering unique among all
22 SigLIP 2 heads:

```text
WARP-G02 (define formula)          WARP-G03 (NONE class path)
    |                                    |
    v                                    v
WARP-G01 (create labeling script)   [run in parallel with G01/G04]
    |
    v
WARP-G04 (run extraction on doc3d, populate L2)
    |
    v
prepare_multitask_datasets.py warping
```

WARP-G02 must be the first engineering task initiated. No other step can begin until the
derivation formula is defined and calibrated. This sequencing is the core reason the HAR score
is 17/100 rather than simply "data not assembled" — the path to assembly requires a data-science
design decision (formula calibration) that cannot be automated or delegated to a labeling script.

### Stream 4C Dry-Run Result

The `prepare_multitask_datasets.py warping --dry-run` command returned **0 real records** and
triggered a mixing cap warning. This confirms the total L2 field gap across all source datasets.

---

## Section 3 — Source Pool Analysis

> Derived from HAR § Section 2.

**Required L2 Field**: `physical_degradation.warping_severity` (float, 0.0–1.0)
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)
**Label Provenance**: tier_0_exact preferred (doc3d 3D mesh geometry derivable once formula
exists); tier_1_annotation for SmartDoc-QA (perspective angle from camera calibration);
tier_0_exact for v3 warping views (generation parameters); tier_0_exact for NONE class
(born-digital documents cannot be physically warped)

### Candidate Source Datasets

| Source Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Usable |
|----------------|-------------|-----------------|------------|-------------|--------|
| doc3d | 102,000 | ❌ Not in L2 | 0% | — | ❌ 0 (blocked on WARP-G02 formula + WARP-G01 script) |
| SmartDoc-QA | 4,357 | ❌ Not in L2 | 0% | — | ❌ 0 (blocked on WARP-G01; camera-calibration angle conversion not implemented) |
| anyphotodoc6300 | 6,306 | ❌ Not in L2 | 0% | — | ❌ 0 (blocked on WARP-G01; perspective+dewarped GT pairs not yet extracted) |
| warpdoc | 1,020 | ❌ Not in L2 | 0% | — | ❌ 0 (blocked; 6 warp types: curl/fold/perspective/wave/crumple/mixed) |
| synth-multiscript-v3 warping view | 5,000 | ❌ Not in L2 | 0% | — | ❌ 0 (generate_v3_warping_view.py produces images but does NOT write warping_severity to L2 sidecars) |
| realdae | ~1,200 | ❌ Not in L2 | 0% | — | ❌ 0 (partial warped documents, proportion unknown) |
| DocLayNet (NONE class) | ~80,000 | ❌ Not labeled for warping | 0% | — | ❌ 0 (NONE class construction path undefined — WARP-G03) |
| RVL-CDIP flatbed (NONE class) | ~400,000 | ❌ Not labeled for warping | 0% | — | ❌ 0 (NONE class construction path undefined — WARP-G03; flatbed-only subset required) |

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current)** | 0 images (fully blocked) |
| **Total usable (post-P0)** | ~111K warped candidates (doc3d 102K + SmartDoc-QA 4.3K + v3 5K) + ~86K NONE candidates (DocLayNet 80K pool + RVL-CDIP 6K flatbed subset) |
| **Training target** | 20,000 images |
| **Pool surplus (post-remediation)** | +177K vs. 20K target — volume is not the constraint |
| **Real vs. synthetic ratio** | ≥ 60% real required; v3 warping views (5K synthetic) must remain ≤ 40% |

The post-remediation pool is vastly larger than the 20,000-image target. Once the derivation
formula exists and the labeling script is built, the assembly step itself is a stratified
sampling exercise, not a data-acquisition problem.

---

## Section 4 — Label Schema

**Primary L2 Field**: `physical_degradation.warping_severity`
**Type**: float
**Range**: 0.0–1.0 (0.0 = flat document with no deformation; 1.0 = extreme curl, fold, or
perspective distortion where text lines are severely non-linear)
**Provenance Tier**: tier_0_exact (doc3d 3D mesh derivation, v3 generation params, DocLayNet
NONE class by construction); tier_1_annotation (SmartDoc-QA camera calibration conversion)
**Derivation Formula**: `warping_severity = clip(k * std(Z_grid_normalized), 0.0, 1.0)`

### Derivation Formula Details

The recommended primary formula for doc3d 3D mesh data:

```text
warping_severity = clip(k * std(Z_grid_normalized), 0.0, 1.0)
```

Where:

- `Z_grid_normalized`: depth values of mesh vertices, normalized to [0,1] range within each
  document (zero-mean normalization across the mesh grid)
- `std(Z_grid_normalized)`: standard deviation across all mesh vertex depths — captures
  overall deviation from flatness; a perfectly flat mesh produces std = 0.0
- `k`: empirical calibration constant, tuned so that a visually "moderate" warp (page_curl
  visible but text readable) maps to ~0.4–0.5 and extreme distortion maps to ~0.9+

**Secondary validation formula** (must be computed during calibration; used to flag
disagreements): `severity = clip(max_displacement / document_diagonal, 0, 1)` where
max_displacement is the maximum vertex displacement from the best-fit plane and
document_diagonal is the document's bounding-box diagonal. If the two formulas disagree by
> 0.2 for the same sample, that sample must be flagged for human review.

**Calibration requirement**: The constant `k` must be tuned by visual inspection of 50 doc3d
samples before any label extraction. The calibration is accepted if a 2-person spot-check
achieves SRCC ≥ 0.70 between computed scalar and visual severity perception. This calibration
step is part of WARP-G02 and is prerequisite for WARP-G01.

**Label convention** (must not be violated):

- `0.0` = flat document (NONE class; never use 0.0 to mean "unable to measure")
- `~0.15` = light curl visible at page edge only
- `~0.3` = moderate page curl (text distorted at margins)
- `~0.5` = significant perspective or curl (multi-line curvature visible)
- `~0.7` = strong deformation (text at page center is distorted)
- `1.0` = extreme distortion (text lines severely non-linear)
- If measurement fails: set `warping_measurement_failed = true`; do NOT use 0.0 as a fallback

### Training Manifest Record Schema

```json
{
  "image_path": "warping/images/{filename}.jpg",
  "source_dataset": "doc3d",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "warping_severity": 0.42,
  "capture_method": "camera_smartphone"
}
```

For NONE class records (DocLayNet born-digital):

```json
{
  "image_path": "warping/images/{filename}.jpg",
  "source_dataset": "doclaynet",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "warping_severity": 0.0,
  "capture_method": "born_digital"
}
```

### Label Statistics (target / post-assembly)

| Metric | Value |
|--------|-------|
| **Range** | [0.0, 1.0] |
| **Target mean** | ~0.35 (reflecting 35% NONE class at 0.0 + severity distribution above) |
| **Class distribution** | NONE 35% / mild 25% / moderate 25% / severe 15% — see Section 5 |

---

## Section 5 — Composition & Splits

> Derived from HAR § Section 3.

### Target Distribution

| Severity Bucket | Range | Target % | Target Count | Primary Source | Label Type |
|----------------|-------|----------|--------------|--------------|-----------:|
| NONE | 0.0 (exact) | 35% | 7,000 | DocLayNet born-digital (5,000) + RVL-CDIP flatbed (2,000) | tier_0_exact |
| Mild | 0.0–0.3 | 25% | 5,000 | doc3d low-Z-std subset | tier_0_exact (3D mesh) |
| Moderate | 0.3–0.7 | 25% | 5,000 | doc3d medium-Z-std + SmartDoc-QA + v3 views | tier_0_exact / tier_1_annotation |
| Severe | > 0.7 | 15% | 3,000 | doc3d high-Z-std + warpdoc extreme types | tier_0_exact |

**Composition rationale**: The 35% NONE class is higher than the shadow dataset's NONE
allocation because flat documents are very common in production. Scanners and born-digital
PDFs produce no warping; the model must learn that most documents it will encounter in practice
are flat. The severe bucket is smaller (15%) because extremely warped documents are rare in
typical document capture pipelines but must be represented to avoid systematic underestimation
near the boundary.

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 14,000 | 70% |
| Val | 3,000 | 15% |
| Test | 3,000 | 15% |
| **Total** | **20,000** | **100%** |

**Split Method**: Stratified by severity bucket; doc3d images are split at the document level
(not image level) to prevent train/val leakage from multiple pages of the same document.
**Random Seed**: 42
**Leakage Prevention**: doc3d test split images must NOT appear in the training split; SHA256-
keyed global split registry is mandatory. DocLayNet images used here for NONE class must
not overlap with DocLayNet images used in other training datasets (orientation, script,
capture-method). v3 warping view base images must not appear in script detection training splits.
The global split registry enforces all constraints by SHA256 keying per image.

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [warping_ddr.md](../diversity_reports/warping_ddr.md) — DDR pilot score
> 46.1/100 on 1,020 warpdoc images (proxy dataset only; warpdoc is not in the current source pool)
>
> **HAR Section 4 Reference**: [sig-g5-warping-reg.md § Section 4](../../planning/har/sig-g5-warping-reg.md)
>
> **Overall Diversity Score**: ~22/100 (HAR estimate — pre-assembly, computed from DDR pilot and known gaps)

*Sorted by relevance to this head. The DDR pilot (warping_ddr.md) scored 3.6/100 on 14-dimension
diversity due to warpdoc having only 1 source value and many dimensions unmeasured. The score
below reflects the assembled dataset design, not the proxy pilot.*

| Dimension | L2 Field | Relevance | Target | Current | Status |
|-----------|----------|-----------|--------|---------|--------|
| degradation | `quality.degradations` | CRITICAL — warping is the core signal; must span all four severity tiers (NONE/mild/moderate/severe) with no underrepresentation of any bucket | All 4 buckets, minimum 15% each (see Section 5) | 0 (dataset not assembled) | ❌ Blocked |
| capture_method | `capture_method.method` | CRITICAL — spurious shortcut risk: camera-captured docs ≈ warped, scanner/born-digital ≈ flat. Model must NOT learn capture_method as a proxy for warping. Requires camera-captured FLAT documents in training to break correlation. | ≥ 3 methods; camera_smartphone + born_digital + scanner_flatbed all required; critically: camera-captured FLAT examples must be present | Unknown (0 assembled) | ❌ Blocked — structural path exists but NONE class requires born_digital/scanner |
| color_mode | `image_properties.color_mode` | HIGH — warping in binarized documents loses gradient and depth-cue information; perspective cues depend on texture gradients lost in binarization; model trained only on color/grayscale warped docs will underperform on binarized warped scans | ≥ 2 modes; at least 15% binarized warping examples | Unknown; doc3d is color/grayscale; binarized warped docs absent | ❌ Binarized warped docs absent from all source pools |
| document_age | `image_properties.document_age` | MEDIUM — aged documents (humidity exposure, paper degradation) warp differently from modern documents; humidity-induced cockling creates high-frequency deformation distinct from smooth perspective warp | ≥ 2 age classes (modern + aged) | Unknown; doc3d likely modern-only | ⚠️ Aged/historical warped documents absent |
| domain | `domain.level1` | MEDIUM — textbooks (bound-spine curvature) warp differently from loose forms (perspective only); ID cards have plastic rigidity (no warp); receipt paper has characteristic thermal-paper curl | ≥ 5 domains | Unknown; doc3d is multi-domain camera captures | ⚠️ Estimated partial coverage via doc3d |
| layout_type | `structure.layout_type` | MEDIUM — warping distorts text-line geometry; dense-text pages provide more structural cues for severity estimation than image-heavy or sparse pages | ≥ 3 layout types | Unknown; doc3d multi-layout by construction | ⚠️ Estimated partial coverage |
| script_code | `language.script_code` | LOW — warping detection is a geometric signal independent of script; script does not drive warping severity | ≥ 2 script families | Unknown; doc3d likely Latin-dominant | ⚠️ Acceptable gap; NONE class via DocLayNet will add diversity |
| resolution | `resolution.category` | LOW — geometric distortion is visible across typical document DPI range (200–600); resolution does not meaningfully affect warping severity detection | ≥ 2 resolution tiers | Unknown; doc3d captured at various distances/DPIs | ⚠️ Acceptable; doc3d provides inherent variation |

### Key Diversity Gaps

**Critical (affects training correctness)**:

- **Spurious capture_method shortcut**: Camera-captured documents appear warped; scanner and
  born-digital documents appear flat. Without deliberate counter-examples (flat camera captures
  from SmartDoc-QA flat-surface condition, ADF curl scanner captures), the model will learn
  capture method as a proxy for warping presence and fail on flat camera images or curled ADF
  scans. This is the most dangerous systematic bias risk for this head.

- **Binarized warped documents absent**: All warped source datasets (doc3d, SmartDoc-QA) are
  color or grayscale. Binarized warping (common in scanned documents processed through older
  workflows) loses depth cues and creates a distributional gap.

**Moderate (affects robustness)**:

- **ADF scanner curl absent from training**: ADF curl is mechanically distinct from camera
  perspective curl — rollers force a transverse cylindrical bend not present in doc3d. This is
  the most common warping type in enterprise document scanning and is currently present only
  in OOD, not in training (see Section 7 and WARP-G05).

- **Crumple/cockling type absent**: Humidity-induced high-frequency deformation is not in any
  source dataset. This physically differs from smooth warp types in spatial frequency by an
  order of magnitude (see WARP-G06).

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [sig-g5-warping-reg.md § Section 5](../../planning/har/sig-g5-warping-reg.md)
> **Overall Wild Condition Score**: ~15/100 (HAR estimate; DDR pilot scored 16.7/100 on proxy warpdoc data)

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| ADF scanner curl (transverse cylindrical curl from document-feeder rollers; mechanically distinct from perspective or page_curl) | `physical_degradation.warping_type` = page_curl + `capture_method` = scanner_adf | ❌ Absent from training | OOD-3b (150 images) stresses this directly. ADF curl must be added to training, not kept in OOD only — this is the most common warping type in enterprise scanning and having it only in OOD creates a systematic training-to-deployment mismatch. See WARP-G05. |
| Book spine cylindrical distortion (smooth curvature at inner margin from bound-book binding) | `physical_degradation.warping_type` = page_curl | ⚠️ Partial | doc3d may include bound-book captures; extent unknown. Book-spine warping is the most common real-world warping type in document scanning (libraries, research labs). Coverage must be verified during WARP-G04 distribution validation. |
| Wet/humidity warping — crinkle/cockling (high-frequency sharp deformation from paper absorbing moisture) | `physical_degradation.warping_type` = crumple | ❌ Absent | None of the source datasets include humidity-induced cockling. This is a fundamentally different deformation type from smooth page_curl or perspective: spatial frequency is an order of magnitude higher. A model trained only on smooth warp types will assign near-zero severity to heavily cockled paper. See WARP-G06. |
| Extreme perspective (> 45° camera tilt angle) | `physical_degradation.warping_type` = perspective | ⚠️ Partial | SmartDoc-QA covers moderate perspective; doc3d perspective range is uncertain. Extreme angles may be OOD relative to training distribution. OOD-Geometry 2b stresses this with 100 images. |
| Fold warping (sharp crease with step-function depth discontinuity across page) | `physical_degradation.warping_type` = fold | ⚠️ Partial | v3 warping views include fold type (5K images, generation parameters). doc3d fold coverage uncertain. Fold creates a depth discontinuity that is geometrically different from smooth page_curl. |
| Compound warping + shadow (book gutter scenario: spine curl + shadow co-occur) | `shadow_severity` + `warping_severity` both elevated | ⚠️ Partial | OOD-Degradation 4c (book gutter shadow, 100 images) stresses this directly. Training must include co-occurring warping+shadow examples so the model learns to score each independently. Risk: if all high-warping images also have high shadow in training, the model cannot separate the two signals. See cross-head note in Section 8. |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: [sig-g5-warping-reg.md § Section 6](../../planning/har/sig-g5-warping-reg.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Capture (Phase 3, P0 — shared with SIG-G5-1 `capture_cls`) |
| **OOD Target Images (this head)** | 150 (OOD-3b dedicated) + contributions from OOD-4a and OOD-4c |
| **OOD Acquisition Status** | ⏳ Not started |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 3b. ADF scanner with curl artifacts | 150 | ✅ Direct | Internal ADF scanning (Fujitsu ScanSnap or equivalent) with deliberate page-curl loading and edge-feed artifacts. `capture_method=scanner_adf`, `warping_type=page_curl`, `warping_severity` human-labeled 0–1, `skew_angle_degrees` measured. Labels must be coordinated with SIG-G5-1 annotation (single acquisition + annotation pass populates both L2 fields simultaneously). ADF curl is the primary production case that is NOT in doc3d training. |
| OOD-Degradation 4a: Multiply-distorted (≥ 5 types) | 500 | ✅ Direct | `warping_severity` is one of ≥ 5 simultaneous distortions (blur + noise + compression + shadow + warping). Tests whether warping_reg assigns an independent, correctly-calibrated score amid compound degradation. |
| OOD-Degradation 4c: Book gutter shadow | 100 | ✅ Direct | `warping_type=page_curl` AND `shadow_type=hard` co-occur (bound book scanned open-flat). Both `warping_reg` and `shadow_reg` are stressed simultaneously. Tests independence of the two regression heads. |
| OOD-Geometry 2b: Extreme perspective (> 30°) | 100 | ⚠️ Indirect | `warping_type=perspective` at angles beyond the training distribution. Tests whether `warping_reg` correctly assigns high severity to extreme perspective cases not seen in training. |

**OOD Leakage Risk**: doc3d (102K images) is the primary training source. OOD evaluation must
use only images NOT in the doc3d training split. Sub-source 3b (ADF scanner curl) is a novel
internal acquisition with no training analog — confirmed zero leakage risk. Compound distortion
OOD (4a and 4c) must draw exclusively from the doc3d test split only (images withheld from
training) combined with Augraphy augmentations. SmartDoc-QA OOD images must use only the
SmartDoc-QA test split. SHA256-keyed global split registry is mandatory to enforce all
cross-dataset constraints.

---

## Section 9 — Assembly Pipeline

**Status**: ❌ Blocked — WARP-G02 must be completed before any other step can begin.

### Prerequisite Chain (must be executed in this order)

```bash
# Step 1: Define and calibrate the derivation formula (WARP-G02)
# --- Manual engineering task, not automated ---
# Review 50 doc3d samples at various computed Z_grid std values
# Calibrate constant k; document what 0.0/0.25/0.5/0.75/1.0 map to
# Validate with 2-person spot-check; require SRCC >= 0.70
# Estimated: 2 days
# Output: documented formula + calibrated k constant

# Step 2: Create the labeling script (WARP-G01, after WARP-G02 complete)
# scripts/label_warping_severity.py
# Modules: doc3d (3D mesh parsing + Z_grid formula), SmartDoc-QA
#          (camera calibration to severity scalar), v3 (generation-param mapping)
# Estimated: 4-5 days

# Step 3: Define NONE class construction (WARP-G03, run in parallel with Steps 2-4)
# Register DocLayNet born-digital sample (5,000 images, warping_severity=0.0)
# Register RVL-CDIP flatbed-only subset (2,000 images, warping_severity=0.0 +/- 0.05)
# Estimated: 1 day

# Step 4: Run label extraction on doc3d corpus (WARP-G04, after WARP-G01 complete)
uv run python scripts/label_warping_severity.py \
    --dataset doc3d \
    --input-dir /mnt/e/image_detection/01_base_data/warping/doc3d \
    --output-dir metadata_registry/json \
    --gpu

uv run python scripts/label_warping_severity.py \
    --dataset smartdoc-qa \
    --input-dir /mnt/e/image_detection/01_base_data/perspective/smartdoc-qa \
    --output-dir metadata_registry/json

# Step 5: Validate severity distribution
# Confirm stratified sampling can achieve target NONE/mild/moderate/severe distribution
# Verify v3 warping views (5K) do not exceed 40% synthetic cap

# Step 6: Dry run (validates without writing manifests)
uv run python scripts/prepare_multitask_datasets.py warping --dry-run

# Step 7: Full assembly
uv run python scripts/prepare_multitask_datasets.py warping
```

Note: `generate_v3_warping_view.py` already exists and has produced 5,000 images
(perspective/page_curl/fold types) but does NOT yet write `warping_severity` to L2 sidecars.
Step 2 (`label_warping_severity.py`) must add a v3 module that reads generation parameters
and maps warp type + intensity to a severity scalar.

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| WARP-G02 derivation formula (documented) | ❌ Not defined | WARP-G01 cannot begin without this |
| `scripts/label_warping_severity.py` | ❌ Not created | doc3d / SmartDoc-QA / v3 L2 population |
| `doc3d_metadata.json` with `warping_severity` | ❌ Not populated | Assembly warped-class records |
| `smartdoc-qa_metadata.json` with `warping_severity` | ❌ Not populated | Assembly moderate-class records |
| NONE class sampling strategy registered | ❌ Not defined | Assembly NONE-class records (35% of target) |
| v3 warping views L2 sidecars updated | ❌ Not done | Assembly severe-class synthetic records |
| OOD leakage registry populated | ❌ Not done | Prevents train/OOD contamination |

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of 14,000 training records |
| `val_manifest.json` | Flat JSON list of 3,000 validation records |
| `test_manifest.json` | Flat JSON list of 3,000 test records |
| `warping/images/` | Assembled dataset images (or GCS path) |

---

## Section 10 — Gap Registry

> **Source**: [sig-g5-warping-reg.md § Section 8](../../planning/har/sig-g5-warping-reg.md)
> **HAR Adequacy Score**: 17/100 — ❌ Blocked

### P0 Blockers (must resolve before assembly can run)

The four P0 blockers are sequential and parallel dependencies, not independent tasks.
WARP-G02 is the critical prerequisite for WARP-G01, which is prerequisite for WARP-G04.
WARP-G03 is a parallel blocker of equal priority.

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| WARP-G02 | 3D mesh → scalar warping_severity derivation formula not defined. **This is prerequisite for WARP-G01 and all downstream steps.** The formula must be specified, calibrated against visual perception (50 doc3d samples, 2-person spot-check, SRCC ≥ 0.70), and documented before any code is written. | No warping_severity scoring methodology exists; the mapping from 3D surface geometry to a 1D perceptual score is a data-science problem with no prior art in this codebase | Define scoring methodology: implement `severity = clip(k * std(Z_grid_normalized), 0, 1)` as primary formula. Calibrate k constant on 50 doc3d samples across the severity range. Document thresholds: what Z_grid std value maps to 0.25, 0.5, 0.75? Validate with 2-person spot-check (SRCC ≥ 0.70 required). Use `severity = clip(max_displacement / document_diagonal, 0, 1)` as secondary validation; flag samples where both formulas disagree by > 0.2 for human review. | 2 days |
| WARP-G01 | `label_warping_severity.py` does not exist. **Requires WARP-G02 to be complete first.** doc3d 3D mesh labels, SmartDoc-QA perspective angles, and v3 warping view generation parameters have not been extracted to L2 metadata. | Script not created; this is more complex than shadow labeling because it requires 3D mesh geometry parsing rather than paired-GT extraction | Create `label_warping_severity.py` with three modules: (a) doc3d module — parse 3D mesh geometry (.mat or .npz depth maps), apply Z_grid std formula from WARP-G02, normalize to [0,1]; (b) SmartDoc-QA module — read camera calibration data, convert perspective tilt angle to severity scalar; (c) v3 module — map warping type (perspective/page_curl/fold) + generation intensity parameters to severity scalar. | 4–5 days (after WARP-G02) |
| WARP-G03 | NONE class construction path undefined. doc3d and SmartDoc-QA contain ONLY warped images. 35% of training target (7,000 flat-document images) has no identified source. | Current warping source pool was designed around warped documents; the NONE class was not considered when building the source pool | Define NONE class sourcing: sample 5,000 flat images from DocLayNet born-digital set (warping_severity = 0.0 by construction — no physical document exists) + 2,000 from RVL-CDIP flatbed-only scanner subset (warping_severity = 0.0 ± 0.05, limited to documents confirmed as flatbed-scanned, not ADF). Include camera-captured FLAT documents from SmartDoc-QA flat-surface condition if available — this is critical for breaking the spurious camera≈warped shortcut (see diversity Section 6). Register sampling strategy in assembly script. | 1 day |
| WARP-G04 | doc3d L2 field unpopulated. 102,000 images have no `warping_severity` value in metadata_registry. | `label_warping_severity.py` not yet run on doc3d | After WARP-G01 complete: run extraction on full doc3d corpus (102K images, GPU-accelerated mesh parsing). Validate severity distribution — doc3d should span the full range 0.0–1.0 given its warp-type diversity. Confirm stratified sampling can achieve the 25%/25%/15% target for mild/moderate/severe. Expected: 2–3 days of GPU compute. | 2–3 days (after WARP-G01) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| WARP-G05 | ADF scanner curl absent from training data. ADF curl is mechanically distinct from camera perspective curl (rollers force a transverse cylindrical bend at fixed radius). It is the most common warping type in enterprise document capture. Keeping it only in OOD while excluding it from training creates a systematic training-to-deployment mismatch. | Source or acquire ADF-specific warping training examples: (a) scan 200–500 documents through ADF scanner with varying curl severity and label warping_severity manually; OR (b) apply Augraphy `scanner_adf` augmentation to flat training documents to generate synthetic ADF curl examples at known severity levels. Add as a 4th warping-type sub-class in the training set. | 2 days |
| WARP-G06 | Wet/humidity warping (paper cockling/crumpling) absent from all source datasets. Crinkle deformation is high-frequency and creates a fundamentally different visual texture from smooth perspective warp or fold — spatial frequency is an order of magnitude higher. A model trained only on smooth warp types will assign near-zero severity to heavily cockled paper. | Add Augraphy `paper_factory` augmentation (crumple simulation) to v3 warping views pipeline to generate 1,000–2,000 crumpled examples. These are synthetic but represent the correct visual pattern. Assign severity ~0.3–0.7 (visible but not preventing OCR). Gemini 2.5 Pro consensus ranked this as the most critical missing warp type after ADF curl. | 1–2 days |
| WARP-G07 | doc3d severity scale validation: std(Z) is a global statistic that does not distinguish between a large-area gentle slope (visually mild) and a sharp narrow fold (visually severe) that have the same std value. This may produce perceptually miscalibrated labels for edge cases. | Compute both std(Z_grid) and 90th-percentile gradient magnitude across the mesh surface during WARP-G04 extraction. For calibration samples where the two metrics disagree by > 0.2 normalized, flag for human review. Incorporate this validation as part of the WARP-G02 calibration step. | 0.5 days (absorbed into WARP-G02) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| WARP-G08 | Extreme perspective coverage (> 45° camera angle) uncertain in doc3d. SmartDoc-QA covers moderate angles but extreme tilt may not be well-represented in training, leading to underestimation. | Audit doc3d perspective angle distribution after WARP-G04 extraction. If max tilt < 30°, add SmartDoc-QA test-split extreme-angle examples or OOD-Geometry 2b images for training-distribution coverage. |
| WARP-G09 | Compound warping+shadow training examples not explicitly planned. Training should include joint examples where both signals are high (book gutter shots) AND independence-ensuring examples where they are decorrelated. | Add 500–800 doc3d samples with warping_severity > 0.4 AND shadow_severity > 0.3 (coordinate with shadow_reg training assembly); add corresponding flat+shadow examples (shadow_severity > 0.3, warping_severity = 0.0). |
| WARP-G10 | `warping_type` sub-label (perspective/page_curl/fold/crumple) not planned in training manifest. Only severity scalar used. | Add `warping_type` field to L2 enrichment if downstream correction logic (DocRes dewarping strategy selection) requires warp type. Not needed for head training but operationally valuable for correction pipeline routing. |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set |
|---------|-----------|------|--------------|-------------|----------|
| SIG-G5-3 | `warping_reg` | Regression 0–1 warping severity | MAE | < 0.08 | OOD-Capture (warping sub-set) |

The MAE < 0.08 target is achievable in principle given the doc3d source quality (3D mesh
geometry provides precise ground truth once the formula is defined). However, achieving this
target depends on the calibration quality of the derivation formula — if `k` is poorly tuned
or the formula does not map to human perception (SRCC < 0.70 on calibration spot-check), the
labels will be systematically miscalibrated and the MAE target will not reflect real performance.

The OOD evaluation sub-set is the ADF scanner curl sub-source (OOD-3b, 150 images). This is
the most demanding OOD scenario for this head because ADF curl is mechanically distinct from
all training warp types. Achieving MAE < 0.08 on the full OOD-Capture set while ADF curl is
absent from training is unlikely; WARP-G05 (adding ADF curl to training) is classified as P1
precisely because the performance target depends on it.

### Achieved Results

| Head | Val MAE | Test MAE | OOD-Capture MAE | Status |
|------|---------|----------|----------------|--------|
| `warping_reg` | — | — | — | ❌ Not trained (blocked) |

---

## Related Documents

- **HAR File**: [sig-g5-warping-reg.md](../../planning/har/sig-g5-warping-reg.md)
- **DDR**: [warping_ddr.md](../diversity_reports/warping_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Related Dataset**: [shadow.md](shadow.md) — shares doc3d source dataset; cross-head label independence required
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)
- **OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-23 | Initial creation from HAR sig-g5-warping-reg.md v1.1 and warping_ddr.md |
