---
l4_category: training-dataset
l4_dataset: shadow
l4_workstream: WS3
l4_source_datasets:
  - sd7k
  - wsrd
  - doc3d
  - synth-multiscript-v3
l4_generation_script: scripts/prepare_multitask_datasets.py
l4_image_count: 15000
l4_status: blocked
---

# shadow

> ❌ **P0 BLOCKED — label_shadow_severity.py script not yet created** | HAR Score: 28/100 (Blocked) | Status: 0/15,000 assembled. All L2 shadow_severity fields are null. Training BLOCKED until labeling script is built and run.

> **Quick Stats**: 15,000 images (target) | Shadow severity regression 0–1 | float label per image
>
> **Status**: ❌ Blocked | **HAR Score**: 28/100 | **P0 Gaps**: 3

---

## Label Sentinel Convention

| Value | Meaning |
|-------|---------|
| 0.0 | NO shadow (valid measurement — document is shadow-free) |
| 0.0–0.25 | Mild shadow |
| 0.25–0.60 | Moderate shadow |
| >0.60 | Severe shadow |
| shadow_unmeasurable=true | Cannot measure severity (e.g., entire document is binarized 1-bit; gradient destroyed) |

⚠️ CRITICAL: 0.0 is a VALID reading meaning "no shadow". Do NOT use 0.0 as a
catch-all for failed measurements or absent data. Unmeasurable cases must use
the `shadow_unmeasurable=true` flag in the metadata.

---

## Book Gutter Shadow Gap (P1)

The sd7k dataset contains only flat-document shadows (cast shadows on horizontal surfaces).
It does NOT contain book gutter shadows — the curved shadow created by page binding
at the inner margin of open books.

- Book gutter shadows are one of the most common scan artifacts in real-world document processing
- Current source datasets have 0 labeled book gutter examples
- Required: ≥1,000 gutter shadow examples with paired clean scans
- Acquisition path: scan physical books (double-page spreads) or synthetic 3D rendering

---

## Prerequisite Chain (Before Any Training)

```text
label_shadow_severity.py     (Step 1: CREATE this script — does not exist)
      ↓
Run labeling on sd7k/wsrd    (Step 2: Execute on GPU; ~2-3 hours on A100)
      ↓
Integrate into L2 metadata   (Step 3: Run integrate_sd7k_enrichments.py with shadow field)
      ↓
prepare_multitask_datasets.py shadow subcommand  (Step 4: Assemble 15K training set)
      ↓
Modal volume upload          (Step 5: Upload to multitask-datasets volume at /data/shadow/)
      ↓
Training                     (Step 6: SIG-G5-2 head training)
```

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `shadow` |
| **Head(s) Fed** | SIG-G5-2 `shadow_reg` (also written as `shadow_score`) |
| **Model(s)** | SigLIP 2 NAFlex |
| **Task Type** | Regression 0–1 continuous severity score |
| **Primary L2 Field(s)** | `physical_degradation.shadow_severity` (float 0–1) |
| **Training Phase** | Phase 5 — Page Attributes |
| **Target Size** | 15,000 images |
| **Image Size** | Variable (source-native; 384px target for training crops) |
| **Storage Location** | `E:\image_detection\03_training_datasets\shadow\` |
| **GCS Path** | `gs://image_detection_b/shadow_training/` |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py shadow` |
| **HAR File(s)** | [har/sig-g5-shadow-reg.md](../../planning/har/sig-g5-shadow-reg.md) |
| **DDR File** | [diversity_reports/shadow_ddr.md](../diversity_reports/shadow_ddr.md) |

### Shared-Data Heads

SIG-G5-3 (`warping_reg`) shares the `doc3d` source dataset with this head. Both shadow and
warping co-occur in bound-book images (gutter shadow + page curl), requiring independent labels
at `physical_degradation.shadow_severity` and `physical_degradation.warping_severity`. The global
split registry (SHA256-keyed) prevents a `doc3d` image from appearing in both shadow_reg training
and warping_reg test split.

### Severity Scale Definition

| Range | Bucket | Meaning |
|-------|--------|---------|
| 0.0 | NONE | No shadow present (not "measurement failed") |
| 0.0–0.25 | mild | Faint gradient, minimal OCR impact |
| 0.25–0.60 | moderate | Visible shadow, text partially obscured |
| > 0.60 | severe | Strong shadow, significant text degradation |

**Convention**: `shadow_severity = 0.0` means NO shadow is present. This is a statement about
the image, not a measurement failure. Images where shadow is physically present but unmeasurable
(e.g., binarized 1-bit documents where gradient information is lost in thresholding) MUST use a
dedicated sentinel value or boolean flag (`shadow_unmeasurable=true`), NOT 0.0. Overloading 0.0
with both meanings would corrupt the regression target for binarized inputs.

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | ❌ Blocked — `label_shadow_severity.py` does not exist; L2 field unpopulated for all source datasets |
| **Current Count** | 0 / 15,000 assembled |
| **HAR Adequacy Score** | 28/100 — ❌ Blocked |
| **P0 Gap Count** | 3 |
| **Primary Blocker** | `label_shadow_severity.py` not created — no L2 `physical_degradation.shadow_severity` values exist for any source dataset; `prepare_multitask_datasets.py shadow` returns 0 real records |
| **Estimated Unblock Effort** | 5–7 days for all three P0 blockers combined |
| **Last HAR Updated** | 2026-02-23 |

The Stream 4C dry-run shadow subcommand returned 0 real records and triggered a mixing cap
warning, confirming the complete L2 field gap. Assembly cannot begin until `label_shadow_severity.py`
is created and executed across all source datasets. The source pool is numerically sufficient
post-P0 (~21K available vs. 15K target); the block is entirely due to the missing labeling
infrastructure.

---

## Section 3 — Source Pool Analysis

> *Derived from HAR § Section 2. Identifies which source datasets contribute to this assembled
> training dataset and how much of each is usable given the required L2 field coverage.*

**Required L2 Field**: `physical_degradation.shadow_severity` (float 0–1)
**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)
**Label Provenance**: tier_0_exact preferred for paired GT datasets (sd7k, wsrd, v3 synthetic);
tier_1_annotation for realdae (VLM or classical measurement with confidence filter)

### Candidate Source Datasets

| Source Dataset | Total Images | Paired GT | Field Populated | Usable Now | Block Reason |
|----------------|-------------|-----------|-----------------|------------|--------------|
| sd7k | 7,239 | YES (shadow/clean + per-pixel mask) | ❌ Not in L2 | 0 | `label_shadow_severity.py` missing |
| wsrd | 4,500 | YES (shadow/clean pairs) | ❌ Not in L2 | 0 | `label_shadow_severity.py` missing |
| realdae | ~1,200 | PARTIAL | ❌ Not in L2 | 0 | `label_shadow_severity.py` missing |
| synth-multiscript-v3 shadow views | 8,000 | YES (Augraphy severity param = label) | ❌ Not in L2 | 0 | Severity not written to L2 sidecars |
| SmartDoc-QA clean frames | ~2,000 | N/A (NONE class, shadow_severity=0.0) | ❌ Not in L2 | 0 | shadow_severity=0.0 not written to L2 |
| MIDV500 flat captures | ~1,000 | N/A (NONE class, shadow_severity=0.0) | ❌ Not in L2 | 0 | shadow_severity=0.0 not written to L2 |
| doc3d | 102,000 | YES (3D geometry → shadow maps) | ❌ Not in L2 | 0 | DEFERRED P3 (209 GB extraction effort) |

### NONE-Class Construction

**Critical structural constraint**: sd7k and wsrd are shadow REMOVAL datasets. They contain
ONLY shadowed images paired with clean reference images. The 40% NONE-class target (6,000 images)
cannot be sourced from the shadowed side of sd7k/wsrd. The paired clean reference images FROM
these datasets must serve as the primary NONE-class source — this is the most domain-correct
approach because they share the same camera, lighting, and document type as the positive examples,
eliminating the domain-identity confound risk.

Constructing the NONE class from unrelated born-digital sources (e.g., DocLayNet) while using
camera-captured shadowed images as positives risks "domain shift cheating": the model may learn
to classify camera noise fingerprint vs. PDF rendering artifacts rather than shadow presence.

| NONE-Class Source | Estimated Count | Domain Match | Rationale |
|-------------------|----------------|--------------|-----------|
| sd7k/wsrd clean reference images | ~3,500–5,000 | BEST — same camera/document domain | Eliminates dataset-identity confound |
| SmartDoc-QA clean frames | ~2,000 | HIGH — smartphone capture, flat-lit | Extends camera diversity |
| MIDV500 flat captures | ~1,000 | MEDIUM — camera captures, no shadow | Additional camera diversity |
| v3 clean (zero Augraphy shadow) | ~500 | LOW — synthetic domain | Script diversity only |
| **Total NONE estimate** | **~7,000–8,500** | | Exceeds 6,000 target |

### Pool Summary

| Metric | Value |
|--------|-------|
| **Total usable (current)** | 0 images |
| **Total usable (post-P0)** | ~21,000–22,500 images (projected) |
| **Training target** | 15,000 images |
| **Pool surplus/deficit** | +6,000–7,500 images (+40–50% surplus) |
| **Real vs. synthetic ratio** | ~65% real (sd7k + wsrd + camera NONE sources) / ~35% synthetic (v3 shadow views) |

**Distribution risk**: sd7k and wsrd are shadow removal datasets — they were curated for visible,
challenging shadows. They likely over-represent moderate-to-severe cases and under-represent mild
shadows. After labeling, verify the mild bucket meets the 3,000 target. If deficient, increase
the v3 synthetic mild component via lower Augraphy severity parameters.

### Post-P0 Pool by Severity Bucket

| Severity Bucket | Target | Available After Labeling | Gap |
|-----------------|--------|--------------------------|-----|
| NONE (0.0) | 6,000 | ~7,000–8,500 | 0 |
| mild (0.0–0.25) | 3,000 | ~4,000 (sd7k/wsrd mild subset + v3 mild) | 0 (verify post-labeling) |
| moderate (0.25–0.60) | 3,000 | ~7,000 (sd7k/wsrd moderate + v3 moderate) | 0 |
| severe (> 0.60) | 3,000 | ~3,000 (sd7k/wsrd severe; may be skewed) | 0–1,000 (verify post-labeling) |
| **Total** | **15,000** | **~21,000–22,500** | **0 (numerically sufficient)** |

---

## Section 4 — Label Schema

> *The exact fields, types, and value conventions that training records must carry.*

**Primary L2 Field**: `physical_degradation.shadow_severity`
**Type**: float
**Range**: 0.0–1.0 (0.0 = no shadow present; 1.0 = maximum shadow severity)
**Provenance Tier**: tier_0_exact for paired GT datasets; tier_1_annotation for realdae

### Derivation Formula

**For sd7k and wsrd (paired GT with per-pixel shadow mask)**:

```
severity = mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0
```

where `shadow_mask` is the per-pixel shadow presence mask included in the sd7k/wsrd dataset.

**SSIM is explicitly banned** for shadow labeling (per DATASET_DIVERSITY_REQUIREMENTS §8.2):
SSIM measures blur, noise, and compression equally and does not isolate shadow severity. The
mean opacity formula above uses only pixels where shadow is confirmed present (inside the mask),
avoiding contamination from other degradation types.

**For synth-multiscript-v3 shadow views**: The Augraphy severity parameter IS the label. The
`generate_v3_shadow_view.py` script must be updated to write this value to L2 sidecars.

**For NONE-class sources** (SmartDoc-QA clean frames, MIDV500 flat captures, sd7k/wsrd clean
references, v3 clean views): Write `shadow_severity = 0.0` explicitly. Do NOT leave the field
absent — missing field is not the same as NONE.

**For binarized inputs**: Write `shadow_unmeasurable = true` and omit shadow_severity (or set to
a reserved sentinel). Do NOT write 0.0 for binarized images where shadow is visually present but
the gradient has been destroyed by thresholding.

### Shadow Type Sub-Label

| Type | Description | Primary Source |
|------|-------------|---------------|
| `cast_hard` | Sharp-edged shadow from nearby object or hand | sd7k/wsrd |
| `cast_soft` | Diffuse shadow with gradient edges | sd7k/wsrd |
| `book_gutter` | Hard gradient at page crease from physical binding | OOD only (not in training pool) |
| `spotlight` | Circular central shadow from overhead light | v3 synthetic |
| `scanner_lid` | Gradual edge darkening from partially closed scanner lid | v3 synthetic |
| `edge` | Shadow at document edge from lateral light source | v3 synthetic |

### Training Manifest Record Schema

```json
{
  "image_path": "shadow/images/{filename}.jpg",
  "source_dataset": "sd7k",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "shadow_severity": 0.42,
  "shadow_type": "cast_hard",
  "capture_method": "camera_smartphone"
}
```

### Label Statistics (target / post-assembly)

| Metric | Value |
|--------|-------|
| **Range** | [0.0, 1.0] |
| **Target mean** | ~0.35 (reflecting 40% NONE at 0.0, remainder distributed across mild/moderate/severe) |
| **Class/bucket distribution** | 40% NONE (0.0) / 20% mild (0.0–0.25) / 20% moderate (0.25–0.60) / 20% severe (>0.60) |

---

## Section 5 — Composition & Splits

> *Target count, severity distribution, split ratios, and leakage prevention strategy.*

### Target Distribution

| Severity Bucket | Range | Target % | Target Count | Primary Sources |
|-----------------|-------|----------|--------------|--------------  |
| NONE | 0.0 (exact) | 40% | 6,000 | sd7k/wsrd clean references, SmartDoc-QA, MIDV500, v3 clean |
| mild | 0.0–0.25 | 20% | 3,000 | sd7k/wsrd mild subset, v3 mild synthetic |
| moderate | 0.25–0.60 | 20% | 3,000 | sd7k/wsrd moderate subset, v3 moderate synthetic |
| severe | > 0.60 | 20% | 3,000 | sd7k/wsrd severe subset |
| **Total** | | **100%** | **15,000** | |

**Real vs. synthetic requirement**: ≥ 50% real (sd7k + wsrd + camera NONE sources) per
DATASET_DIVERSITY_REQUIREMENTS §8. Synthetic cap: ≤ 50% (v3 shadow views).

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 10,500 | 70% |
| Val | 2,250 | 15% |
| Test | 2,250 | 15% |
| **Total** | **15,000** | **100%** |

**Split Method**: Stratified by severity bucket (NONE / mild / moderate / severe) and by source
dataset, to ensure all four buckets are proportionally represented in each split.

**Random Seed**: 42

**Leakage Prevention**: Source dataset test splits are reserved for OOD evaluation and must not
appear in train/val/test manifests. The global split registry (SHA256-keyed) prevents any image
from a source dataset appearing in both shadow_reg training and warping_reg test split. sd7k and
wsrd clean reference images used as NONE-class training examples must not appear in the test
split of any other dataset that drew from these sources. dedup required: SHA256 + pHash (Hamming
≤ 5) against training manifests before registration.

### Post-Labeling Distribution Validation Gate

After `label_shadow_severity.py` runs and BEFORE assembly proceeds, verify:

1. NONE bucket ≥ 6,000 samples from domain-matched sources (sd7k/wsrd clean references primary)
2. mild bucket ≥ 3,000 samples; if deficient (sd7k/wsrd skewed toward moderate/severe), increase
   v3 synthetic mild component via lower Augraphy severity parameters
3. severe bucket ≥ 3,000 samples; if deficient, increase v3 synthetic severe component
4. Total real-image fraction ≥ 50% before any synthetic supplement is applied

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [shadow_ddr.md](../diversity_reports/shadow_ddr.md)
> **HAR Section 4 Reference**: [sig-g5-shadow-reg.md § Section 4](../../planning/har/sig-g5-shadow-reg.md)
> **Overall Diversity Score**: 20/100 (post-P0 estimate; automated DDR measured 46.1/100 overall
> but 3.6/100 on the 14-dimension diversity component with only 1 of 14 dimensions measurable)

*Sorted by relevance to shadow_reg. Dimensions not listed have LOW relevance and are not
separately targeted for this dataset.*

| Dimension | L2 Field | Relevance | Target | Current | Status |
|-----------|----------|-----------|--------|---------|--------|
| degradation (shadow severity) | `physical_degradation.shadow_severity` | CRITICAL — this IS the label; distribution must hit 40/20/20/20 buckets | All 4 buckets at minimum 20% | sd7k/wsrd skewed toward moderate/severe; mild may be deficient post-labeling | ⚠️ Estimated 50/100 |
| capture_method | `capture_method.method` | CRITICAL — shadow appearance differs fundamentally between camera (directional gradient) vs. scanner (lid-open, edge shadow) vs. born-digital (impossible) | ≥ 3 methods; camera dominant ≥ 55% | sd7k/wsrd + SmartDoc-QA are `camera_smartphone`; v3 is synthetic; scanner_lid type from v3 only | ⚠️ Estimated 55/100 |
| color_mode | `image_properties.color_mode` | HIGH — binarized documents lose shadow gradient entirely; model must correctly output 0.0 or use sentinel rather than hallucinating a moderate score from 1-bit text edges | ≥ 2 modes; binarized edge case defined and represented | No binarized shadow or binarized NONE examples; edge case handling not yet defined | ❌ Estimated 10/100 |
| document_age | `image_properties.document_age` | MEDIUM — aged documents develop yellowing and foxing that produce gradients mimicking mild shadow (false positive risk) | ≥ 2 age classes | SmartDoc-QA/MIDV500 are modern; aged documents absent from all source pools | ❌ Estimated 25/100 |
| domain | `domain.level1` | MEDIUM — glossy paper (photography books) reflects differently from matte; office vs. book shadows differ in gradient profile | ≥ 5 domains | sd7k/wsrd are camera-captured mixed domains; domain distribution unverified post-labeling | ⚠️ Estimated 30/100 |
| layout_type | `structure.layout_type` | MEDIUM — shadow over dense text vs. margins has different OCR impact; model may spuriously correlate shadow with text density | ≥ 3 layout types | sd7k/wsrd layout distribution unknown until L2 is populated | ⚠️ Estimated 25/100 |
| script_code | `language.script_code` | LOW — shadow detection is script-independent | ≥ 2 script families | v3 covers 27 scripts; sd7k/wsrd predominantly Latin | ⚠️ Estimated 40/100 |
| resolution | `resolution.category` | LOW — shadow severity detection not resolution-dependent at typical document DPIs | ≥ 2 resolution tiers | sd7k/wsrd have known DPI; distribution not yet verified | ⚠️ Estimated 30/100 |

### Key Diversity Gaps

- **born_digital shadow examples absent**: The pool is exclusively camera-captured and synthetic.
  Born-digital documents cannot physically have shadows, but scanner-lid-open produces a structural
  analog. This is a correct domain boundary, not a coverage gap — but it means the model has no
  in-distribution examples for the scanner domain.
- **Binarized color_mode undefined**: No binarized shadow examples and no binarized NONE examples
  exist. The model will encounter binarized documents in production and risks hallucinating shadow
  scores from high-contrast 1-bit text edges.
- **Only 2 domains verified in pool**: sd7k and wsrd document type coverage is unverified; no
  domain distribution audit has been run. Financial, scientific, legal, and other domain examples
  may be severely underrepresented.
- **Modern documents only**: All source datasets contain modern documents. Aged-document false
  positives (yellowing misclassified as shadow) have no training coverage.

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 Reference**: [sig-g5-shadow-reg.md § Section 5](../../planning/har/sig-g5-shadow-reg.md)
> **Overall Wild Condition Score**: 15/100 (1 condition partially covered via OOD; training
> coverage near zero for all conditions)

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| Book gutter shadow (hard gradient at page crease from physical binding) | `shadow_type = book_gutter` | ❌ Missing from training | sd7k and wsrd cover only flat-document shadows — documents photographed lying flat on a surface. Gutter shadows have a distinct parabolic gradient curve absent from training data. The model will systematically underestimate gutter severity as "moderate edge shadow." Covered by OOD-Degradation 4c only (100 images, internal photography). |
| Binarized document with shadow gradient present | `image_properties.color_mode = binarized` | ❌ Not covered | Shadow gradient information is destroyed in 1-bit thresholding. The model must be trained to output 0.0 (or sentinel) for binarized inputs, not moderate scores from text edges. No binarized shadow or binarized NONE examples exist in any source. Covered by OOD-Degradation 4d (100 binarized images) only. |
| Compound shadow + warping (bound book page with both gutter shadow and page curl) | `physical_degradation.shadow_severity` + `physical_degradation.warping_severity` | ❌ Not covered | Camera-captured bound books naturally produce both gutter shadow and page curl simultaneously. Training on single-degradation examples produces overconfident predictions on compound inputs. Some coverage in OOD-Mixed 4a (compound distortion sub-source) but not in training. |
| Scanner lid open shadow (gradual edge darkening) | `shadow_type = scanner_lid` | ⚠️ Partial | v3 generates scanner_lid type (8K synthetic) but severity is not yet labeled. Real scanner-lid examples absent from sd7k/wsrd (camera datasets). Coverage depends on v3 synthetic component post-P0. |
| Spotlight / circular shadow (camera flash off-center or overhead light) | `shadow_type = spotlight` | ⚠️ Partial | v3 Augraphy spotlight type provides partial synthetic coverage. Presence in sd7k/wsrd unverified. No dedicated OOD entry. |
| Cast shadow from hand or object held over document | `shadow_type = cast_hard` | ⚠️ Partial | sd7k and wsrd likely include hand-cast shadows from smartphone photography (these datasets specifically target smartphone shadow removal). Verification needed after labeling. |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: [sig-g5-shadow-reg.md § Section 6](../../planning/har/sig-g5-shadow-reg.md)

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Degradation (Phase 4, P0, 800 total images — shared with IQA heads) |
| **OOD Target Images (this head)** | 600 total: 500 compound (4a) + 100 book gutter (4c) |
| **OOD Acquisition Status** | ⏳ Not started |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 4a. Multiply-distorted (≥ 5 distortion types, shadow as one) | 500 | ✅ Direct | Augraphy compound augmentation on training-excluded documents; distortion stack: gutter-shadow + page_curl + defocus blur + noise + JPEG compression. Source docs drawn from doc3d test split + internal photography ONLY (sd7k/wsrd are training sources). All SigLIP heads are stressed simultaneously; shadow must be scored independently of the co-occurring distortions. IQA labels require human annotation — classical detectors insufficient for compound distortion. |
| 4c. Book gutter shadow (hard gradient at page crease) | 100 | ✅ Direct | Internal photography of bound books photographed open-flat. Tests the primary known failure mode — parabolic gutter gradient absent from sd7k/wsrd flat-document training data. Paired with page_curl warping: both SIG-G5-2 and SIG-G5-3 are stressed simultaneously. This is the ONLY shadow-specific OOD sub-source. |

**OOD Leakage Risk**: LOW. sd7k and wsrd are training sources and must not appear in OOD. OOD
must use doc3d test split images (not used in shadow_reg training) plus internally acquired
documents only. Book gutter shadow (4c) uses internal photography of bound books — no training
analog exists in the pool. SHA256 + pHash (Hamming ≤ 5) dedup required against training manifests.

### OOD Adequacy Assessment

Two concerns apply to the current OOD design:

1. **Statistical power**: 100 images (4c book gutter shadow) is insufficient for a stable MAE
   estimate on a regression head. At n=100, MAE confidence intervals are wide. Recommendation:
   expand 4c to ≥ 250 images by photographing at least 10 additional bound books from diverse
   domains (scientific manuals, financial reports, literary books, legal texts) to provide
   statistically meaningful regression evaluation.

2. **Coverage breadth**: The OOD set tests exactly one known failure mode (book gutter shadow).
   It does not test binarized-document false positives, scanner-lid shadow, or spotlight shadow.
   These failure modes would require additional OOD sub-sources to evaluate rigorously.

---

## Section 9 — Assembly Pipeline

**Status**: ❌ Blocked — three P0 prerequisites must be completed before assembly can run

### Prerequisites (required in order)

1. **Create `label_shadow_severity.py`** (SHADOW-G01): Define severity formula; extract labels
   from sd7k/wsrd paired GT using shadow mask files; derive v3 synthetic labels from Augraphy
   parameter; write shadow_severity=0.0 for NONE-class sources; document binarized sentinel
   convention.

2. **Run `label_shadow_severity.py`** (SHADOW-G02): Execute against all source datasets
   (sd7k, wsrd, v3 shadow views, SmartDoc-QA clean frames, MIDV500 flat captures); validate
   output distribution per dataset; confirm labels pass confidence threshold ≥ 0.7.

3. **Define NONE-class construction in assembly script** (SHADOW-G03): Update
   `prepare_multitask_datasets.py shadow` subcommand to explicitly source NONE-class images
   from sd7k/wsrd clean references (primary) + SmartDoc-QA + MIDV500 + v3 clean views.

### Assembly Commands

```bash
# Step 1: Create and run labeling script (P0 prerequisite — does not exist yet)
# uv run python scripts/label_shadow_severity.py --datasets sd7k wsrd synth-multiscript-v3 smartdoc-qa midv500

# Step 2: Validate label distribution per source dataset
# uv run python scripts/label_shadow_severity.py --validate-only

# Step 3: Dry run assembly (validates without writing files)
uv run python scripts/prepare_multitask_datasets.py shadow --dry-run

# Step 4: Full assembly
uv run python scripts/prepare_multitask_datasets.py shadow

# Step 5: Upload to GCS
# gsutil -m cp -r E:\image_detection\03_training_datasets\shadow\ gs://image_detection_b/shadow_training/
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|--------------|
| `label_shadow_severity.py` | ❌ Not created | Populating `physical_degradation.shadow_severity` in L2 metadata for all source datasets |
| `sd7k_metadata.json` | ❌ shadow_severity not in L2 | Shadowed training images (mild/moderate/severe buckets) |
| `wsrd_metadata.json` | ❌ shadow_severity not in L2 | Shadowed training images (mild/moderate/severe buckets) |
| `synth-multiscript-v3` L2 sidecars | ❌ shadow_severity not written | v3 shadow view synthetic labels |
| SmartDoc-QA L2 metadata | ❌ shadow_severity=0.0 not written | NONE-class camera-capture diversity |
| MIDV500 L2 metadata | ❌ shadow_severity=0.0 not written | NONE-class supplementary source |
| `generate_v3_shadow_view.py` | ✅ Exists (4 shadow types: edge/cast/spotlight/scanner_lid) | 8K synthetic shadow images |
| `prepare_multitask_datasets.py shadow` subcommand | ⚠️ Exists but NONE-class path undefined | Assembly orchestration |

### Augmentation Notes

`generate_v3_shadow_view.py` already generates 8K images with 4 shadow types. This script exists
and produces the synthetic shadowed component. The missing piece is that it does not currently
write the Augraphy severity parameter to L2 sidecars — this write must be added as part of
SHADOW-G01.

Book gutter shadow augmentation (`--pre-warp page_curl` applied before shadow overlay) does not
yet exist in the script. Adding this is a P1 gap (SHADOW-G04).

### Generated Outputs

| File | Description |
|------|-------------|
| `train_manifest.json` | Flat JSON list of 10,500 training records |
| `val_manifest.json` | Flat JSON list of 2,250 validation records |
| `test_manifest.json` | Flat JSON list of 2,250 test records |
| `shadow/images/` | Dataset images (or GCS path) |

---

## Section 10 — Gap Registry

> **Source**: [sig-g5-shadow-reg.md § Section 8](../../planning/har/sig-g5-shadow-reg.md)
> **HAR Adequacy Score**: 28/100 — ❌ Blocked

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
|--------|-------------|------------|-------------|--------|
| SHADOW-G01 | `label_shadow_severity.py` does not exist — sd7k and wsrd paired GT labels cannot be extracted to L2; v3 shadow views cannot be labeled; NONE class cannot be written | Script not yet created | Create script: (1) define severity formula `mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0` for paired datasets; (2) extract sd7k/wsrd labels using shadow mask files; (3) derive v3 synthetic labels from Augraphy severity parameter; (4) write shadow_severity=0.0 for NONE-class sources; (5) write all values to L2 sidecars; document convention for binarized sentinel | 3–4 days |
| SHADOW-G02 | L2 `physical_degradation.shadow_severity` field unpopulated for all 6 source datasets | SHADOW-G01 not yet executed | Execute `label_shadow_severity.py` after SHADOW-G01 is complete; validate output distribution per dataset; confirm sd7k audit grade B/87 and wsrd audit grade A/95 labels pass confidence threshold ≥ 0.7 | 1–2 days (dependent on SHADOW-G01) |
| SHADOW-G03 | NONE-class construction path not defined in assembly script; `prepare_multitask_datasets.py shadow` subcommand does not have a documented NONE-class source | Shadow removal datasets (sd7k/wsrd) contain only shadowed images; no NONE-class source was planned when scripts were written | Update assembly script: (1) include sd7k/wsrd clean reference images as primary NONE source; (2) add SmartDoc-QA clean frames (~2,000) and MIDV500 flat captures (~1,000) as secondary; (3) add v3 clean views (~500) for script diversity; (4) document domain-match rationale to prevent dataset-identity confound | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Remediation | Effort |
|--------|-------------|-------------|--------|
| SHADOW-G04 | Book gutter shadow absent from training data — sd7k/wsrd cover flat-document shadows only; model will systematically underestimate gutter shadows, which are the most common shadow type in scanned bound books | Add Augraphy gutter-shadow augmentation to `generate_v3_shadow_view.py` via `--pre-warp page_curl` flag (per DATASET_DIVERSITY_REQUIREMENTS §8.2 "Stacked Degradation Sub-Split"); target ~1,000 compound examples; cap compound examples at ≤ 5% of total shadow dataset | 1 day |
| SHADOW-G05 | Binarized document handling not defined — shadow gradient information is lost in 1-bit images; shadow_severity = 0.0 convention would be incorrect for images where shadow is present but unmeasurable; model risks hallucinating moderate scores from high-contrast 1-bit text edges | (1) Define binarized sentinel handling in SHADOW-G01 script (`shadow_unmeasurable=true`); (2) add ~500 binarized clean images to NONE class (from archival 1-bit TIFF sources or Sauvola binarization of clean documents) to train the model that binarized inputs have zero detectable shadow | 0.5 days |
| SHADOW-G06 | Compound shadow + warping not in training data — camera-captured bound books naturally produce both conditions simultaneously; training on single-degradation examples produces overconfident predictions | Add 500–800 compound examples: warp v3 base image (page_curl type) THEN apply shadow overlay; set `shadow_severity` AND `warping_severity` labels; weight at 0.8× (slightly down-weighted synthetic compound); cap at ≤ 5% of total shadow dataset | 1 day |
| SHADOW-G07 | OOD-Degradation 4c (book gutter shadow) has only 100 images — statistically insufficient for stable MAE regression evaluation; confidence intervals at n=100 are wide | Expand OOD-4c from 100 to ≥ 250 images (photograph 10+ additional bound books from diverse domains: scientific manuals, financial reports, literary books, legal texts) | 0.5 days (additional photography) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
|--------|-------------|-------------|
| SHADOW-G08 | Shadow type sub-label (hard/cast/spotlight/scanner_lid) not verified for training distribution — severity may correlate with type, creating spurious predictions on underrepresented types | After labeling, verify shadow type distribution within each severity bucket; ensure no single type dominates a single severity tier |
| SHADOW-G09 | doc3d (102K images) DEFERRED to P3 — 3D geometry-based shadow maps would provide highest-quality labels for severe shadow cases and book gutter analog | After P0/P1 resolved, assess severity bucket shortfalls; if severe bucket remains deficient, implement doc3d extraction pipeline (209 GB, estimated 2–3 weeks effort) |
| SHADOW-G10 | Domain diversity within camera class not verified — sd7k/wsrd may be concentrated on specific document types (e.g., form-style documents) | Post-labeling, audit domain distribution within sd7k/wsrd via L2 domain field; if concentrated, supplement with domain-diverse camera-captured documents |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set |
|---------|-----------|------|--------------|-------------|----------|
| SIG-G5-2 | `shadow_reg` | Regression 0–1 shadow severity | MAE | < 0.08 | OOD-Degradation shadow sub-set |

### Achieved Results

| Head | Val MAE | Test MAE | Status |
|------|---------|----------|--------|
| `shadow_reg` | — | — | ❌ Not trained (assembly blocked) |

### Evaluation Notes

The performance target of MAE < 0.08 will be evaluated on OOD-Degradation, specifically the
book gutter shadow sub-source (4c). The current 100-image 4c sub-source is statistically
insufficient to yield a stable MAE estimate for a regression head — confidence intervals at
n=100 are wide. Evaluation should be deferred until OOD-4c is expanded to ≥ 250 images
(SHADOW-G07).

The compound distortion sub-source (4a) will also exercise this head as part of multi-head
simultaneous evaluation, where shadow_severity must be predicted independently of co-occurring
blur, noise, warping, and compression.

---

## Related Documents

- **HAR File**: [sig-g5-shadow-reg.md](../../planning/har/sig-g5-shadow-reg.md)
- **DDR**: [shadow_ddr.md](../diversity_reports/shadow_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)
- **Related Head**: [training/warping.md](warping.md) (SIG-G5-3, shares doc3d source)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-02-23 | Added P0 BLOCKED notice, Label Sentinel Convention section, Book Gutter Shadow Gap section, Prerequisite Chain section |
| 1.0.0 | 2026-02-23 | Initial creation from HAR sig-g5-shadow-reg.md v2.0 and shadow_ddr.md |
