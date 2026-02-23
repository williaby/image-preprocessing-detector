# Head Adequacy Review: orientation_cls (SIG-G3-1)

> **Status**: ✅ Complete
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: A — Geometry
> **Adequacy**: ⚠️ Needs Work (52/100)

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G3-1 |
| Model | SigLIP 2 NAFlex |
| Group | G3 — Orientation + Skew |
| Head Name | orientation_cls |
| Task Type | Classification — 4 classes (0 / 90 / 180 / 270) |
| Output Format | Softmax over 4 orientations |
| Priority | P1 |
| Performance Target | Accuracy ≥ 98% |
| Primary L2 Field | `geometric.orientation_class` |
| Shared-Data Heads | MNV4-H1 (shares training dataset); SIG-G3-2 (same dataset group) |
| Training Phase | Phase 4 — Orientation + Skew Group (trained jointly with SIG-G3-2) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `geometric.orientation_class` _string enum: 0, 90, 180, 270_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact — orientation labels are the applied rotation value (deterministic ground truth)

**Audit-Derived Defects**: ORIENT-DEF-01 (symmetric doc absent), ORIENT-DEF-02 (Stream 4C rebuild unconfirmed), ORIENT-DEF-03 (source imbalance)

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DocLayNet (via build_orientation_real_component.py) | ~15,000 | 15,000 | 100% | 100% (applied GT) | — | ✅ ~15,000 |
| RVL-CDIP (via build_orientation_real_component.py) | ~15,000 | 15,000 | 100% | 100% (applied GT) | — | ✅ ~15,000 |
| synth-multiscript-v3 (via derive_v3_orientation_view.py) | ~20,000 | 20,000 | 100% | 100% (applied GT) | — | ✅ ~20,000 |
| **Total assembled** | **50,000** | **50,000** | **100%** | **100%** | — | **✅ 50,000** |

### Usable Pool Summary

- **Total usable before enrichment**: 50,000 images (training target met)
- **Training target**: 50,000 images (same dataset as MNV4-H1)
- **Gap**: ✅ No volume gap — however, a **strategic correction-layer gap** exists: SIG-G3-1's role is to correct MNV4-H1 failures, yet training on identical balanced data means SIG-G3-1 will fail on precisely the same ambiguous documents as MNV4-H1

### VLM Validation Sampling Tier

**Tier 1 (Standard)**: max(10, 3% of dataset) per class — labels are deterministic applied rotations, not annotation-derived. VLM sampling needed only to verify no rotation application errors in image I/O pipeline.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| ORIENT-DEF-01 | orientation (assembled) | orientation_class | Symmetric documents (0°/180° visually indistinguishable) absent from training — confounds correction layer as severely as primary model | OPEN |
| ORIENT-DEF-02 | orientation (assembled) | all | Stream 4C rebuild status unconfirmed; current manifest path uncertain | OPEN |
| ORIENT-DEF-03 | RVL-CDIP / DocLayNet | source | Source chi-square FAIL on uniformity test — source imbalance persists even with class balance | OPEN |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-001 | Identical training dataset as MNV4-H1 means SIG-G3-1 cannot function as an effective correction layer for MNV4-H1 failure modes — cascade architecture anti-pattern | HIGH: Defeats the purpose of the two-model cascade for ambiguous orientation cases |
| KI-002 | Standard balanced test set evaluation gives inflated accuracy metrics for SIG-G3-1's correction-layer role — the interesting cases are precisely those MNV4-H1 fails on, which are underrepresented in the balanced test set | MEDIUM: Reported accuracy will overstate production correction effectiveness |

### Remediation Path

1. **Hard negative mining** (P1): After training MNV4-H1, extract low-confidence / incorrect predictions from the test set + unlabeled pool → curate hard negative set (~2–5K images) → add to SIG-G3-1 training mixture
2. **Cascade-aware evaluation** (P1): Create SIG-G3-1-specific test set composed of MNV4-H1 failure cases from OOD-Geometry + the hard negative pool → report correction rate, not just raw accuracy
3. **Symmetric doc augmentation** (P1): Same as MNV4-H1 ORIENT-MNV4-G01 — add 500–1,000 symmetric document examples with both 0° and 180° labels to the shared training set

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 50,000 images (same dataset as MNV4-H1) |
| Assembly Status | ✅ Complete (dataset ready at E:\image_detection\03_training_datasets\orientation\\) |
| Distribution | Same as MNV4-H1 — balanced 4-class (12,500 docs × 4 rotations). Japanese vertical text labeled at 0°. |
| Real Data Ratio | ≥ 50% required |
| Accuracy Note | SIG-G3-1 targets higher accuracy (≥ 98%) than MNV4-H1 (≥ 95%) due to larger model capacity. MNV4-H1 achieved 99.5% orient_acc on balanced test — SIG-G3-1 target is achievable on the easy distribution. |
| Assembly Script | `scripts/prepare_multitask_datasets.py orientation` |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 14.3/100 (from orientation DDR; same dataset as MNV4-H1)

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| orientation | `geometric.orientation_class` | CRITICAL — primary label | Balanced 4-class | ✅ 25% each | ✅ 100 |
| source | `capture_method.method` | HIGH — correction layer needs source diversity | ≥ 4 sources | ⚠️ 10 sources, chi-sq FAIL (imbalanced) | ⚠️ 50 |
| document_type | `domain.level1` | HIGH | ≥ 6 types | ⚠️ 12 types but imbalanced (3.1% min) | ⚠️ 50 |
| script_code | `language.script_code` | HIGH — SigLIP 2 processes diverse scripts | ≥ 5 scripts | ❌ Not measured in DDR | TBD |
| capture_method | `capture_method.method` | HIGH | ≥ 3 methods | ❌ Not measured in DDR | TBD |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes | ❌ Not measured in DDR | TBD |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages | ❌ Not measured in DDR | TBD |
| resolution | `resolution.category` | MEDIUM | Standard OK | ❌ Not measured in DDR | TBD |
| layout_type | `structure.layout_type` | LOW | ≥ 3 types | ❌ Not measured in DDR | TBD |
| degradation | `quality.degradations` | LOW | ≥ 2 types | ❌ Not measured in DDR | TBD |

**Note**: 9 of 14 dimensions not measured in DDR. DDR 14-dim score (14.3/100) reflects data sparsity in aggregated metadata, not true coverage. The orientation dataset likely has good coverage on measured dimensions once metadata is fully populated.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 20/100 (DDR baseline 25/100, reduced by additional correction-layer condition)

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Symmetric documents (0°/180° visually indistinguishable) | `domain.level1=text_heavy` + symmetric layout | ❌ Missing | CRITICAL for correction layer — if MNV4-H1 fails here, SIG-G3-1 trained on same data also fails. Must be added to shared training set. |
| Non-Latin RTL documents (Arabic/Hebrew) | `language.script_code` = Arab, Hebr | ⚠️ Partial | v3 synthetic has some; coverage unquantified |
| Camera perspective vs pure rotation (> 30° tilt) | `capture_method.method = camera_smartphone` | ⚠️ Partial | MIDV500 has some; SigLIP 2 needs these as hard negatives for correction layer |
| Partial/cropped page | `structure.layout_type = partial` | ❌ Missing | Not present in DocLayNet or RVL-CDIP training samples |
| MNV4-H1 failure cases not curated for SIG-G3-1 | `ml_predictions.mnv4_h1_confidence < 0.5` | ❌ Missing | Correction-layer-specific gap — SIG-G3-1 must see cases where MNV4-H1 is uncertain or wrong |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Geometry (Phase 2, P0, 500 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 2a. Symmetric documents | 300 | Wikipedia / gov-form screenshots NOT from DocLayNet | orientation_class | mobilenetv4 + siglip2 | Tests 0°/180° disambiguation on visually symmetric pages. Must dedup against DocLayNet. |
| 2b. Extreme perspective | 100 | Internal photography at > 30° tilt | skew_angle_degrees (measured), warping_type=perspective, capture_method=camera_smartphone | mobilenetv4 + siglip2 | — |
| 2c. Japanese vertical text | 100 | NDL Digital Collection | script=Jpan, orientation=0, text_direction=ttb | mobilenetv4 + siglip2 | Must dedup against synth-multiscript-v3 Jpan samples. |

### Additional Coverage

OOD-Mixed sub-sources that include orientation cascade failures (Mongolian TTB + aged + perspective) test whether SigLIP 2 can correct MNV4 failures on ambiguous documents.

### OOD Leakage Risk

Same as MNV4-H1 — training set is closed, OOD uses different sources. OOD-Mixed cross-category may re-use OOD-Geometry images combined with other distortions; this is intentional and does not constitute leakage.

### OOD Design Assessment

The OOD-Geometry design adequately stresses orientation failure modes in general. However, OOD-Geometry symmetric docs (300 images) serve double duty: they stress both MNV4-H1 and SIG-G3-1. Since these docs are OOD-only for SIG-G3-1 (not in training), the correction rate metric will measure interpolation ability on unseen symmetric patterns — which is weak. These documents should additionally be in SIG-G3-1's training set as hard negatives.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| MNV4-H1 (orientation) | Shares exact same 50K training dataset | Must use global split registry (SHA256-keyed) to avoid test contamination. SigLIP 2 serves as correction/validation layer over MNV4-H1 predictions. |
| SIG-G3-2 (skew_reg) | Trained jointly in Phase 4 | Skew and orientation interact — misoriented docs appear skewed. Labels must be computed after canonical orientation is established. |

### Split Leakage Risk

**Level**: LOW

Same reasoning as MNV4-H1 — training set is closed (12,500 unique docs × 4 rotations). OOD uses different sources. The correction-layer evaluation concern (KI-002) is a measurement gap, not a leakage issue.

### Label Convention

`orientation=0` for Japanese TTB text — same convention must be enforced in both MNV4-H1 and SIG-G3-1 training datasets. Any future dataset additions must apply this convention before assembly to maintain consistency across the two heads sharing this dataset.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| _(none)_ | — | No P0 blockers — dataset assembled and training-ready | — | — | — |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| ORIENT-SIG-G01 | Hard negative mining absent — SIG-G3-1 trains on identical distribution as MNV4-H1 | Cascade architecture: correction layer needs to see primary model failure cases | After MNV4-H1 training: extract low-confidence predictions → curate 2–5K hard negatives → add to SIG-G3-1 training mix | 2–3 days |
| ORIENT-SIG-G02 | Cascade-aware evaluation lacking — balanced test set gives inflated metrics | Standard accuracy metric doesn't measure correction-layer effectiveness | Build correction-specific test set from OOD-Geometry + MNV4-H1 failure pool; report correction rate (cases MNV4-H1 was wrong, SIG-G3-1 was right) | 1–2 days |
| ORIENT-SIG-G03 | Symmetric document examples absent from training | Same gap as MNV4-H1 ORIENT-MNV4-G01 | Shared remediation: add 500–1,000 symmetric doc examples (Wikipedia/gov screenshots) to the orientation training set | 2 days (shared with MNV4-H1) |
| ORIENT-SIG-G04 | Stream 4C rebuild status unconfirmed — manifest path uncertain | Stream 4C pipeline in active development | Verify `prepare_multitask_datasets.py orientation` produces valid manifest; confirm 50K target images are accessible at Modal volume path | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| ORIENT-SIG-G05 | Partial/cropped page coverage absent | Add cropped-page examples from v3 synthetic generator or RVL-CDIP subset |
| ORIENT-SIG-G06 | 9 of 14 diversity dimensions unmeasured in DDR | Populate L2 metadata aggregates with capture_method, color_mode, document_age, resolution fields for orientation dataset |
| ORIENT-SIG-G07 | Correction rate baseline not established | Establish MNV4-H1 failure rate on production-representative corpus before SIG-G3-1 training; set correction rate target (e.g., ≥ 60% of MNV4-H1 failures corrected) |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete

**Adequacy Rating (pre-consensus)**: ⚠️ Needs Work — No P0 blockers; P1 gaps are methodological (correction-layer design), not data volume gaps.

**Analyst Summary**:
SIG-G3-1 has no data volume gap — the 50K orientation dataset is assembled and training-ready. However, a fundamental cascade architecture concern makes this head methodologically inadequate in its current design: SIG-G3-1 is intended to correct MNV4-H1 errors, yet it trains on the exact same balanced dataset. Both models will learn the same decision boundaries and fail on the same ambiguous cases — primarily symmetric documents and extreme perspective. The OOD-Geometry design is sound for general stress testing but insufficient as a correction mechanism because SIG-G3-1 has never seen these hard cases during training. Hard negative mining (post-MNV4-H1 training), a cascade-aware evaluation metric, and shared inclusion of symmetric docs in training are the three critical P1 items. The 14-dimension diversity score (14.3/100) reflects DDR metadata sparsity rather than true coverage failure.

**Consensus Prompt**:

Evaluate the training dataset design and cascade architecture for the SigLIP 2 NAFlex `orientation_cls` head (SIG-G3-1). This head is a 4-class orientation classifier (0/90/180/270°) targeting ≥ 98% accuracy, and crucially, it is intended as a correction layer over MobileNetV4-Conv-S MNV4-H1 in a two-stage cascade. Primary L2 field: `geometric.orientation_class`. Training dataset: 50K images, balanced 4-class (identical to MNV4-H1). MNV4-H1 training results: 99.5% orient_acc on the same balanced test set. Key concern: SIG-G3-1 trains on the same balanced data as MNV4-H1 — symmetric documents and extreme perspective documents are absent from training. Wild condition score: 20/100. DDR 14-dim score: 14.3/100. No P0 blockers. P1 gaps: (1) hard negative mining — SIG-G3-1 needs MNV4-H1 failure cases in its training set; (2) cascade-aware evaluation — need correction rate metric, not just raw accuracy; (3) symmetric docs must be added to shared training (currently OOD-only). Evaluate: (1) Is the correction-layer design adequate given identical training data? (2) Is hard negative mining a P0 or P1 issue? (3) Does OOD-Geometry adequately test correction-layer failure modes? (4) What risks are missing from the gap registry? (5) Overall rating: Ready / Needs Work / Blocked — with 1-paragraph justification.

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview (both neutral)

**Consensus Summary**:

Both models independently confirmed the cascade architecture anti-pattern as the central risk.

**Gemini 2.5 Pro**: _Needs Work (9/10 confidence)._ "Using an identical dataset for SIG-G3-1 and MNV4-H1 is a structural design flaw for a correction layer. The model will learn the same decision boundaries and fail on the same ambiguous documents — defeating the cascade purpose. Hard negative mining is effectively P0 for the correction-layer role (even if training-ready for standalone classification). The cascade-aware evaluation metric is essential before any useful training data decisions can be made. Symmetric documents must be in SIG-G3-1's training set, not only in OOD. Until corrected, reported ≥ 98% accuracy is meaningless for production correction performance."

**Gemini 3 Pro Preview**: _Needs Work (9/10 confidence)._ "The cascade architecture anti-pattern is confirmed. Training SIG-G3-1 on the same balanced distribution as MNV4-H1 guarantees it will fail on the same hard examples: symmetric docs, extreme perspective, partial pages, and low-confidence near-90° cases. Hard examples must be explicitly and sufficiently represented in SIG-G3-1's training data. The evaluation mismatch is equally critical: reporting 99%+ accuracy on a balanced test set tells you nothing about whether SIG-G3-1 corrects MNV4-H1's ~0.5% error cases in production. Gap registry is missing: (a) near-90° low-confidence cases (not the same as extreme perspective), (b) documents with faint or no text making orientation inference rely on layout alone."

**Final Rating**: ⚠️ **Needs Work**

**Top Recommendations**:

1. **Hard negative mining is a P0 for the correction-layer role** — reclassify ORIENT-SIG-G01 from P1 to P0 for cascade architecture intent
2. Define and implement a correction rate metric before beginning SIG-G3-1 training evaluation
3. Symmetric documents must be added to the shared orientation training set (not OOD-only for SIG-G3-1)
4. Add near-90° low-confidence cases and layout-only orientation examples to gap registry as P1 items
5. Consider whether SIG-G3-1 even needs to share MNV4-H1's full 50K dataset, or should focus on a harder 20–30K subset with enriched ambiguous cases

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 85/100 (pool fully assembled, no P0 blockers; hard-negative strategic gap is P1) | 29.75 |
| 14-Dimension Coverage | 25% | 14.3/100 (DDR score; 9/14 dimensions unmeasured in aggregates) | 3.58 |
| Wild Condition Coverage | 20% | 20/100 (0 covered, 2 partial, 3 missing across 5 conditions) | 4.00 |
| OOD Design Quality | 20% | 75/100 (3 OOD sub-sources, 500 images; not correction-layer-specific) | 15.00 |
| **Overall** | 100% | — | **52.33** |

**Grade**: ⚠️ **Needs Work** (52/100) — No P0 blockers, but correction-layer design is a fundamental strategic issue that must be addressed before training evaluation can be meaningful.
