# Head Adequacy Review: orientation (MNV4-H1)

> **Status**: ✅ Analysis Complete
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: A — Geometry
> **Adequacy**: ⚠️ Needs Work

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | MNV4-H1 |
| Model | MobileNetV4-Conv-S |
| Group | Pre-Correction Stage Gate |
| Head Name | orientation |
| Task Type | Classification — 4 classes (0 / 90 / 180 / 270) |
| Output Format | Softmax over 4 orientations |
| Priority | P0 |
| Performance Target | Accuracy ≥ 95% (≥ 98% with SigLIP distillation) |
| Primary L2 Field | `geometric.orientation_class` |
| Shared-Data Heads | SIG-G3-1 (orientation_cls uses same training dataset) |
| Training Phase | Phase 4 — Pre-Correction Gate (trained before SigLIP 2) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `geometric.orientation_class` _string enum: 0, 90, 180, 270_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (labels are ground truth by construction — rotation IS the label)

**Audit-Derived Defects**: DDR score 41.8/100 (Insufficient). Wild condition score 25/100. 14-dimension score 14.3/100 (most dimensions not measured in the assembled manifest). Label quality 100/100. Source chi-square FAIL (10 sources, highly imbalanced distribution despite perfect class balance).

### Candidate Source Datasets

The orientation training dataset is assembled; this head does not draw from a free pool. The dataset was REBUILT under Stream 4C to add multi-script diversity.

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DocLayNet (PDFs, rotated) | ~32K | `orientation_class` tier_0_exact | 100% | Yes (exact) | N/A — synthetic rotation | Yes |
| RVL-CDIP (scans, rotated) | ~12K | `orientation_class` tier_0_exact | 100% | Yes (exact) | N/A — synthetic rotation | Yes |
| synth-multiscript-v3 (non-LATN) | ~20K | `orientation_class` tier_0_exact | 100% | Yes (exact) | N/A — synthetic orientation | Yes |
| **Total assembled** | **~50K** | | 100% | | | |

### Usable Pool Summary

- **Total usable before enrichment**: 50,000 images (dataset assembled at E:\03_training_datasets\orientation\)
- **Training target**: 50,000 images
- **Gap**: No count gap. Dataset is assembled. Critical gaps are diversity and missing sub-categories (see Section 8), not size.

### VLM Validation Sampling Tier

**Tier 1 — Not required.** Labels are tier_0_exact (orientation is established by construction via controlled rotation). No annotation error to validate. However, a spot-check of ~50 images is recommended to verify the Japanese TTB convention (`orientation=0` for vertical Japanese text) is correctly applied in the assembled dataset.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| ORIENT-DEF-01 | Orientation manifest (50K) | 12 of 14 L2 dimensions | L2 diversity enrichment not applied to orientation manifest — capture_method, domain, color_mode, document_age, degradation, resolution, layout_type all show "Not measured" in DDR | Open — requires L2 enrichment pass |
| ORIENT-DEF-02 | Orientation manifest (50K) | `orientation_ambiguous` sub-category | ~2,500 orientation_ambiguous samples (§1.2.1 of DATASET_DIVERSITY_REQUIREMENTS.md) are specified but absent from the assembled dataset. Symmetric docs appear only in OOD. | Open — structural gap |
| ORIENT-DEF-03 | DocLayNet (primary source) | `capture_method.method` | DocLayNet is ~100% born-digital; RVL-CDIP adds scanner. Camera-captured documents are minimal in the training set. Source chi-square FAIL reflects this imbalance. | Open — source rebalancing needed |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-ORIENT-01 | Symmetric documents (visually identical at 0° and 180°) are absent from training. These are placed only in OOD-Geometry 2a. Without training examples, the model learns overconfident heuristics for ambiguous inputs — it will assign 0° or 180° with high confidence on symmetric pages. This is a silent failure mode: the model never abstains, it guesses confidently wrong. | HIGH — §1.2.1 of DATASET_DIVERSITY_REQUIREMENTS.md mandates ~2,500 `orientation_ambiguous` sub-category samples in training |
| KI-ORIENT-02 | Source distribution chi-square FAIL (10 sources, imbalanced). The model will overfit to DocLayNet born-digital feature space (dominant source) and generalize poorly to under-represented sources (RVL-CDIP scanned documents, v3 synthetic non-Latin). | MEDIUM — class balance is perfect but feature bias is a risk |
| KI-ORIENT-03 | Partial/cropped pages (e.g., scanned page fragments, header-only crops) are absent from training. These images lack the structural cues the model relies on for orientation. | MEDIUM — DDR reports this as "Missing" wild condition |
| KI-ORIENT-04 | Dataset rebuild (Stream 4C) was in-progress at time of analysis. The old 50K dataset lacked multi-script diversity; the rebuilt version (DocLayNet + RVL-CDIP real + v3 synthetic) is the correct training dataset. Confirm rebuild execution is complete before training. | MEDIUM — if old dataset used, non-Latin accuracy is unknown |
| KI-ORIENT-05 | Japanese TTB convention: vertical Japanese text is labeled `orientation=0`. This convention must be consistently applied and must match the convention used in SIG-G3-1 (same dataset). | LOW — convention is defined; operational risk is consistency enforcement |

### Remediation Path

1. **Before training (P1)**: Add ~2,500 `orientation_ambiguous` samples to the training set per §1.2.1 of DATASET_DIVERSITY_REQUIREMENTS.md. Sources: DocLayNet blank separator pages, figure-dominant pages, symmetric numeric/title pages. Train with confidence-suppression target (low-confidence output for ambiguous inputs), not as a 5th class.
2. **Before training (P1)**: Confirm Stream 4C rebuild is complete. Verify the assembled orientation dataset contains v3 non-Latin scripts as documented.
3. **Before evaluation (P1)**: Acquire OOD-Geometry dataset (0/500 images collected). Sub-source 2a (symmetric docs) is specifically needed to measure MNV4-H1's ambiguity handling.
4. **Before evaluation (P1)**: Apply L2 enrichment to orientation manifest (resolve ORIENT-DEF-01). Re-run DDR to get accurate diversity scores.
5. **Nice-to-have (P2)**: Rebalance source distribution across DocLayNet / RVL-CDIP / v3 to reduce the chi-square FAIL. Currently DocLayNet likely dominates.

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 50,000 images |
| Assembly Status | ✅ Complete (dataset at E:\image_detection\03_training_datasets\orientation\) — confirm Stream 4C rebuild version |
| Distribution | Balanced 4-class (12,500 docs × 4 rotations). Vertical Japanese labeled as 0°. |
| Real Data Ratio | ≥ 50% required. Rebuild target: ≥ 60% real (DocLayNet + RVL-CDIP) + ≤ 40% v3 synthetic (non-Latin scripts). |
| Assembly Script | `scripts/prepare_multitask_datasets.py orientation` |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 14.3/100 (DDR automated score — most dimensions not measured due to missing L2 enrichment on orientation manifest)

**Note**: The 14.3/100 automated score reflects the absence of L2 enrichment on the manifest, not necessarily poor actual diversity. The assembled dataset draws from diverse sources (DocLayNet born-digital FIN/SCI/TEC, RVL-CDIP scanner variety, v3 non-Latin synthetic). However, without L2 metadata on the assembled manifest, the DDR tool cannot measure most dimensions. Three genuine diversity problems are confirmed: (1) symmetric doc absence, (2) source distribution imbalance (chi-square FAIL), (3) camera capture under-representation.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | HIGH — born-digital docs have crisp edges and clear orientation cues; scanner and camera docs have noise, perspective, shadows that make orientation harder. The model must handle all capture methods in production. | ≥ 20% camera, ≥ 25% scanner, ≥ 40% born-digital | Estimated: ~64% born-digital (DocLayNet), ~24% scanner (RVL-CDIP), ~2% camera. Camera severely under-represented. Source chi-square FAIL confirms imbalance. | ⚠️ 35/100 — camera under-represented |
| domain | `domain.level1` | MEDIUM — document layout conventions (one-column academic vs. multi-column newspaper vs. form-based) affect which visual features encode orientation. | ≥ 5 domains with ≥ 5% each | Estimated adequate: DocLayNet covers FIN/TEC/SCI; RVL-CDIP covers letter/memo/form; v3 synthetic covers varied scripts. Domain breadth is likely sufficient. | ✅ 70/100 — adequate domain breadth |
| color_mode | `image_properties.color_mode` | MEDIUM — binarized documents lack color and texture cues. Orientation detection on binarized text (common in fax, legacy scans) relies purely on stroke direction and layout geometry. The model must generalize across color modes. | ≥ 15% binarized, ≥ 25% grayscale | Not measured. v3 synthetic profile (60% color, 30% grayscale, 10% binarized) applies to the synthetic component; RVL-CDIP scans are predominantly grayscale. | ⚠️ 45/100 — estimated partially adequate but unmeasured |
| document_age | `image_properties.document_age` | LOW-MEDIUM — aged documents have degraded contrast and paper texture. Orientation cues may be weakened but the task is generally robust to age. | ≥ 5% aged/historical | Estimated minimal in the assembled dataset — DocLayNet born-digital is modern; RVL-CDIP scans are legacy but not historically aged. | ⚠️ 30/100 — likely under-represented |
| script_code | `language.script_code` | IMPORTANT — orientation cues differ by script. RTL scripts (Arabic, Hebrew) have different paragraph-level orientation signatures. CJK vertical text requires special label convention. Script imbalance was addressed by the Stream 4C rebuild (adding v3 non-Latin). | ≥ 50% Latin, ≥ 8% CJK, ≥ 8% Arabic | DDR reports 24 scripts present but chi-square FAIL on script distribution indicates severe imbalance. v3 synthetic adds 19 non-Latin script classes. Latin-dominant synthetic rotation component still makes up ~60-70% of the dataset. | ⚠️ 50/100 — present but imbalanced |
| resolution | `resolution.category` | LOW-MEDIUM — orientation detection is generally robust to resolution; coarse orientation cues (aspect ratio, paragraph layout) are resolution-independent. | ≥ 20% standard_300, ≥ 20% medium | Not measured. Estimated adequate: DocLayNet renders at 300 DPI; RVL-CDIP varies; v3 synthetic rendered at multiple DPI tiers. | ⚠️ 45/100 — unmeasured but likely adequate |
| layout_type | `structure.layout_type` | IMPORTANT — symmetric document layouts (centered title, palindromic tables) are the primary failure mode for orientation. Single-column is easy; multi-column and complex layouts provide conflicting symmetry signals. | ≥ 30% single-col, ≥ 20% multi-col, ≥ 10% form-tabular | Not measured. DocLayNet covers multi-column (SCI/TEC), form-based, tabular. Layout diversity is estimated adequate. | ⚠️ 40/100 — unmeasured |
| degradation | `quality.degradations` | IMPORTANT — degradation reduces orientation signal quality. Blur/noise reduce edge sharpness; contrast degradation weakens paragraph structure signals. The dataset notes 50% clean / 35% light / 15% moderate. | ≥ 50% clean, ≥ 35% light, ≥ 15% moderate | Assembly spec: 50% clean, 35% light, 15% moderate degradation applied during generation. This target is adequate if implemented correctly. | ✅ 70/100 — target adequately specified |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 25/100 (DDR automated score)

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Symmetric documents — visually identical at 0° and 180° | `structure.layout_type = symmetric`, `content_flags.orientation_ambiguous` | ❌ Missing | No symmetric document training examples. OOD-Geometry 2a (300 images) tests this but without training exposure, the model assigns arbitrary high-confidence predictions. §1.2.1 requires ~2,500 `orientation_ambiguous` training samples with confidence-suppression target. |
| Partial / cropped pages (header-only, fragment, corner scan) | `structure.completeness = partial` | ❌ Missing | Pages where only a fragment is visible lack global layout cues. The model relies on full-page paragraph flow for orientation; partial pages may be systematically misclassified. |
| RTL script documents (Arabic, Hebrew, Urdu) | `language.script_code` in [ARAB, HEBR, URDU] | ⚠️ Partial | Stream 4C rebuild adds Arabic (MDIW13, Arabic-docs-ocr). RTL orientation cues differ from LTR. Coverage is present but imbalanced (chi-square FAIL on script distribution). |
| Camera perspective distortion vs. pure rotation | `capture_method = camera_smartphone` + `geometric.perspective_tilt_degrees` | ⚠️ Partial | Camera documents have perspective tilt that can appear as off-axis orientation. Under-represented in training (camera ≈ 2% estimated). OOD-Geometry 2b (100 images) tests extreme perspective but training coverage is thin. |
| Japanese TTB vertical text labeled as 0° | `language.script_code = Jpan` + `text_direction = ttb` | ✅ Present | Convention is defined and applied. v3 synthetic includes Jpan 30% TTB. JSSODa provides real Japanese vertical text sources. Convention consistency with SIG-G3-1 is required. |
| Blank pages (no text, no orientation cue) | `text_density = none` | ❌ Not assessed | Included under `orientation_ambiguous` sub-category (§1.2.1: ~750 blank pages). Currently absent from assembled dataset. |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Geometry (Phase 2, P0, 500 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 2a. Symmetric documents | 300 | Wikipedia / gov-form screenshots NOT from DocLayNet | orientation_class | mobilenetv4 + siglip2 | Tests 0°/180° disambiguation on visually symmetric pages. Must dedup against DocLayNet. |
| 2b. Extreme perspective | 100 | Internal photography at > 30° tilt | skew_angle_degrees (measured), warping_type=perspective, capture_method=camera_smartphone | mobilenetv4 + siglip2 | — |
| 2c. Japanese vertical text | 100 | NDL Digital Collection | script=Jpan, orientation=0, text_direction=ttb | mobilenetv4 + siglip2 | Must dedup against synth-multiscript-v3 Jpan samples. |

### Cross-Categorization

OOD-Script sub-sources 1a and 1b also cross-categorize (TTB vertical Mongolian scripts relevant to this head).

### OOD Leakage Risk

Orientation dataset is distinct (rotations applied to DocLayNet/RVL-CDIP); OOD-Geometry uses different sources. Must verify OOD-Geometry 2a subset does NOT overlap with any training rotation set.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G3-1 (orientation_cls) | Shares exact same 50K training dataset | Must use global split registry (SHA256-keyed). SigLIP corrects MNV4 errors on ambiguous orientations. |
| MNV4-H2 (skew_reg) | Same model, different task | Source documents may overlap (both use RVL-CDIP/DocLayNet base docs). |

### Split Leakage Risk

**Level**: LOW

Training set is closed (12,500 unique docs × 4 rotations). OOD uses different sources. No cross-contamination path identified.

### Label Convention

Vertical Japanese text is labeled as `orientation=0` (non-standard convention). This convention must be consistent between MNV4-H1 and SIG-G3-1 training datasets. Any future dataset additions must apply the same convention before assembly.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before training)

No P0 blockers — the assembled dataset is usable for an initial training run. However, the gaps below represent serious quality concerns that will likely prevent the ≥ 95% accuracy target from being met on ambiguous document types.

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| — | — | No hard P0 blockers found | — | — | — |

### P1 Improvements (resolve before training)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| ORIENT-MNV4-G01 | **Symmetric/ambiguous documents absent from training.** §1.2.1 mandates ~2,500 `orientation_ambiguous` sub-category samples. Without them, the model learns high-confidence arbitrary heuristics on symmetric inputs — a silent production failure mode. | Symmetric docs were placed only in OOD (2a) instead of being split: ~2,500 in training + 300 in OOD. This is a design error in dataset assembly. | Curate ~2,500 symmetric-layout documents from DocLayNet figure-dominant pages, DocLayNet blank separator pages, and symmetric RVL-CDIP forms. Apply confidence-suppression training target (label = `orientation_ambiguous` with output target of uniform 25%/25%/25%/25% or low-max-logit constraint). Add to training manifest. | Medium — 1–2 engineer-days for curation + assembly script update |
| ORIENT-MNV4-G02 | **Stream 4C rebuild not confirmed complete.** DATASET_DIVERSITY_REQUIREMENTS.md lists orientation dataset status as REBUILDING. The old 50K dataset lacks multi-script diversity. Training on the old dataset would mean SIG-G3-1 and MNV4-H1 both lack non-Latin coverage. | Assembly scripts were written but execution (data transfer + generation) was in-progress at time of analysis. | Confirm `build_orientation_real_component.py` and `derive_v3_orientation_view.py` have completed successfully. Verify output contains v3 non-Latin scripts in expected proportions. Run DDR against the confirmed-complete dataset before training. | Low — verify-only; 1–2 hours |
| ORIENT-MNV4-G03 | **OOD-Geometry acquisition not started.** 0/500 images acquired. Without OOD evaluation, it is impossible to verify MNV4-H1's behavior on the most critical failure modes (symmetric docs, extreme perspective, Japanese TTB). | OOD acquisition planning is complete but no images have been collected. | Acquire OOD-Geometry dataset: 2a (300 symmetric doc screenshots from Wikipedia/gov-forms), 2b (100 extreme perspective photos), 2c (100 NDL Japanese TTB scans). Prioritize 2a as it directly measures the symmetric doc gap. | High — requires manual collection or scripted scraping; estimate 1–2 engineer-days |
| ORIENT-MNV4-G04 | **Source distribution chi-square FAIL.** Despite perfect class balance, the distribution across 10 source datasets is highly imbalanced (DocLayNet dominates). The model will overfit to DocLayNet born-digital feature space and generalize poorly to scanner and camera document types. | DocLayNet (born-digital, clean, Latin-dominant) provides ~64% of the training pool by default. No explicit source-count balancing cap was applied. | Apply a per-source cap at 40% of total when assembling the manifest. Specifically ensure RVL-CDIP contributes ≥ 20% (scanner variety) and v3 synthetic contributes ≥ 20% (non-Latin scripts). | Low — sampling script change, 0.5 engineer-days |
| ORIENT-MNV4-G05 | **Partial/cropped pages absent.** Pages with only a fragment visible lack global layout orientation cues. These appear in production (OCR on page regions, header crops). | Dataset design does not include partial pages. DocLayNet has some partial-page entries but they were not specifically targeted. | Add ~500 partial-page samples: (a) region crops from DocLayNet images (header-only, footer-only, half-page), (b) OCR partial-scan simulation (RVL-CDIP with edge masking). Label: keep original 4-class orientation. | Low — 0.5 engineer-days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| ORIENT-MNV4-G06 | **Training manifest does not track color_mode, document_age, capture_device.** 12 of 14 L2 diversity dimensions are unmeasured, blocking future DDR audits. | Run `aggregate_layer2_metadata.py` against the orientation manifest. Add L2 enrichment fields. Re-run DDR to get accurate diversity scores. |
| ORIENT-MNV4-G07 | **Camera-captured orientation examples under-represented.** Estimated ~2% camera vs. target 20%. Camera docs have perspective tilt that confuses orientation detection. | Include SmartDoc-QA and MIDV500 rotated samples (camera capture, varied documents). Add ~1,000 camera-captured images to the orientation training manifest. |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete (2026-02-23)

**Adequacy Rating (pre-consensus)**: ⚠️ Needs Work

**Analyst Summary**: The MNV4-H1 orientation head has a solid foundation: 50K images, perfect 4-class balance, tier_0_exact labels (rotation is the label), and a clear architecture target (95% accuracy on a 4-class softmax with ~4M parameter backbone). However, the dataset has three material design flaws that will prevent reliable production performance. First, symmetric/ambiguous documents are absent from training despite being mandated by §1.2.1 — the model will learn to make overconfident arbitrary choices on these inputs, causing systematic silent failures. Second, source distribution is highly imbalanced (chi-square FAIL: DocLayNet born-digital dominates), creating feature bias toward clean born-digital documents while scanner and camera inputs are under-represented. Third, partial/cropped pages are absent. The DDR score (41.8/100) quantitatively confirms these issues. The dataset rebuild (Stream 4C) addresses the multi-script gap but still requires the ambiguous document fix.

**Consensus Prompt**: "Evaluate the MNV4-H1 orientation head training dataset. 50K balanced 4-class, tier_0_exact labels, DDR=41.8/100. Critical gap: ~2,500 `orientation_ambiguous` samples are required by §1.2.1 but absent — symmetric docs are only in OOD. Source chi-square FAIL (DocLayNet dominant). Questions: (1) Is 50K sufficient? (2) Should symmetric docs be in training? (3) Does source imbalance matter with perfect class balance? (4) Binarized/grayscale gap? (5) Script diversity risk? (6) Overall rating."

**Models consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

---

### Consensus Summary

**Unanimous rating: NEEDS WORK** (both models, confidence 9/10).

**Key consensus findings:**

**Q1 — Is 50,000 balanced samples sufficient?**
Both models agree: sample count is more than sufficient for a 4-class softmax head. The primary problem is diversity, not quantity. The low DDR score (41.8/100) confirms that 12,500 unique source documents are too homogenous — the model will excel on the dominant distribution but fail on underrepresented scenarios.

**Q2 — Should symmetric documents be in training?**
Unanimous: placing symmetric documents only in OOD is a **critical design flaw**. OOD sets exist to evaluate generalization on out-of-distribution scenarios, not to withhold known failure modes from training. Omitting symmetric documents from training guarantees the model will learn overconfident and incorrect heuristics. The model must be explicitly trained to output low-confidence, split probabilities (e.g., ~50% for 0°, ~50% for 180°) on symmetric inputs. This requires moving ~2,500 orientation_ambiguous samples INTO the training set as mandated by §1.2.1.

**Q3 — Does source distribution imbalance matter with perfect class balance?**
Yes — the source chi-square FAIL is a major risk. Perfect class balance masks feature bias toward the dominant source (DocLayNet born-digital). The model overfits to clean, born-digital, Latin-script document features. Scanner documents (RVL-CDIP) and camera documents will generalize poorly if the dominant source is ≥ 64% of training. Rebalancing is needed even though class counts are equal.

**Q4 — Does excluding binarized/grayscale documents create a wild condition gap?**
Gemini 2.5 Pro: Yes, binarized images (common in fax, legacy scans) have fundamentally different orientation cues — textural cues used by CNNs/ViTs are absent. This creates an untested production scenario. Gemini 3 Pro: Agrees; the model must see binarized documents during training to develop binarization-invariant orientation features.

**Q5 — Domain/script diversity risks?**
Strong bias risk: dominance of Latin-script born-digital business documents means the model will be weak on RTL scripts, underperform on Japanese TTB (despite correct labeling), and have blind spots for handwritten and form-based documents. The Stream 4C rebuild adds v3 non-Latin scripts but the source imbalance issue still applies.

**Additional concern (Gemini 3 Pro)**: The SIG-G3-1 correction layer shares the same training dataset as MNV4-H1. Training SIG-G3-1 on identical data means it will fail on the same ambiguous cases as MNV4-H1 — defeating the cascade's purpose. For SIG-G3-1 to function as an effective correction layer, it needs hard negative mining from MNV4-H1's failure distribution. This is an architectural concern flagged as a P1 issue in the SIG-G3-1 HAR.

**Final Rating**: ⚠️ NEEDS WORK

**Top Recommendations** (priority order):

1. Add ~2,500 `orientation_ambiguous` training samples (blank/symmetric/figure-only pages) with confidence-suppression training target — moves the critical flaw from OOD-only to properly addressed
2. Apply per-source sampling cap (≤ 40%) to rebalance DocLayNet dominance; ensure RVL-CDIP ≥ 20% and v3 non-Latin ≥ 20%
3. Acquire OOD-Geometry 2a (300 symmetric doc screenshots) to measure orientation ambiguity handling
4. Confirm Stream 4C rebuild is complete before training
5. Apply L2 enrichment to manifest to enable DDR re-scoring

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 88 | 30.80 |
| 14-Dimension Coverage | 25% | 42 | 10.50 |
| Wild Condition Coverage | 20% | 35 | 7.00 |
| OOD Design Quality | 20% | 72 | 14.40 |
| **Overall** | 100% | — | **62.70** |

**Grade**: ⚠️ Needs Work (63/100)

**Score rationale**:

- Source Pool Adequacy (88): Dataset assembled, perfectly balanced, tier_0_exact labels — strong foundation. Score capped by rebuild-in-progress status and missing orientation_ambiguous sub-category (confirmed structural gap per §1.2.1).
- 14-Dimension Coverage (42): Class balance is excellent (4-way perfect). Score depressed by missing L2 enrichment (12/14 dimensions unmeasured) and confirmed source imbalance (chi-square FAIL). Estimated actual diversity is moderate but untested.
- Wild Condition Coverage (35): DDR automated score 25/100. Two conditions Missing (symmetric docs, partial pages), two Partial (RTL, camera perspective). Symmetric docs gap is most critical given head's operational role.
- OOD Design Quality (72): OOD design is well-specified with three appropriate stress-test scenarios. Score capped by 0/500 images acquired and the structural issue that OOD 2a duplicates what should be training data.
