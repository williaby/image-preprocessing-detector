# Head Adequacy Review: resolution_quality_reg (SIG-G5-5)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: D — Resolution
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G5-5 |
| Model | SigLIP 2 NAFlex |
| Group | G5 — Page Attributes |
| Head Name | resolution_quality_reg |
| Task Type | Regression 0-1 (char-height-aware quality score) |
| Output Format | Linear output [0-1] |
| Priority | P2 (validation head — redundant with MNV4-H3 for cross-checking) |
| Performance Target | MAE < 0.1; serves as validation of MNV4-H3 predictions |
| Primary L2 Field | `resolution.resolution_quality_score` (shared with MNV4-H3) |
| Shared-Data Heads | MNV4-H3 (shares exact training dataset) |
| Training Phase | Phase 5 — Page Attributes |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `resolution.resolution_quality_score` _(float 0-1, char-height-aware; identical field to MNV4-H3)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (PaddleOCR DBNet + CC analysis pipeline — same source as MNV4-H3)

**Audit-Derived Defects**: _(analysis required — same defects as MNV4-H3; see mnv4-h3-resolution-quality.md Section 2 for known issues)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | ✅ Complete | 99.9% (5,499 labeled, 1 error) | _(analysis required)_ | _(check audit)_ | ~5,499 |
| OHR-Bench | 8,500 | _(analysis required)_ | — | — | — | — |
| RealDAE | 1,200 | _(analysis required)_ | — | — | — | — |
| DocLayNet (multi-DPI renders) | _(analysis required)_ | _(not populated)_ | 0% | — | — | 0 (needs rendering pipeline) |
| RVL-CDIP (multi-DPI renders) | _(analysis required)_ | _(not populated)_ | 0% | — | — | 0 (needs rendering pipeline) |

### Usable Pool Summary

- **Total usable before enrichment**: ~5,499 (DIQA-5000 only — same as MNV4-H3)
- **Training target**: 30,000 images (same dataset as MNV4-H3)
- **Gap**: ~24,500 images (identical gap to MNV4-H3; resolving MNV4-H3 blockers resolves this head's blockers simultaneously)

### VLM Validation Sampling Tier

_(analysis required — automated labeling pipeline only; same sampling tier logic as MNV4-H3 applies)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required — same defects as MNV4-H3; cross-reference mnv4-h3-resolution-quality.md)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-RQ-01 | PaddleOCR v2 ONLY (paddleocr>=2.7,<3.0) — v3 API incompatible; shared with MNV4-H3 | HIGH — inherited from MNV4-H3 |
| KI-RQ-02 | SIGILL on Intel Broadwell CPUs; labeling must run on GPU VM | MEDIUM — inherited from MNV4-H3 |
| KI-RQ-03 | V1 precision: median IQR 9.0px; coarse buckets validated | MEDIUM — inherited from MNV4-H3 |
| KI-G5-5-01 | This head is P2 priority — if MNV4-H3 training is delayed, SIG-G5-5 training is further deprioritized; dependency ordering must be tracked | LOW — scheduling risk only |

### Remediation Path

_(analysis required — all blockers are shared with MNV4-H3; remediation follows the same path. See mnv4-h3-resolution-quality.md Section 2 Remediation Path.)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 30,000 images (same dataset as MNV4-H3) |
| Assembly Status | ⏳ Not started (0/30,000) |
| Role | SIG-G5-5 is a validation head — its predictions cross-check MNV4-H3 to detect model drift or labeling inconsistency |
| Labels | Same character-height-aware pipeline as MNV4-H3 (PaddleOCR DBNet + CC analysis) |
| Distribution Target | Same as MNV4-H3: ~49% needs_light_upscale / ~37% optimal / ~11% good / ~3% needs_major_upscale |
| Real Data Ratio | 100% real documents (no synthetic generation) |
| Split Convention | Global split registry (SHA256-keyed) — same train/val/test splits as MNV4-H3 mandatory |
| Assembly Script | Same resolution pipeline as MNV4-H3; `scripts/prepare_multitask_datasets.py` (resolution subcommand not yet implemented) |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly; same dataset as MNV4-H3 so diversity scores will be identical)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| resolution | `resolution.category` | CRITICAL — core signal; same analysis as MNV4-H3 | All 8 DPI tiers represented | DIQA-5000 only (natural distribution) | TBD |
| capture_method | `capture_method.method` | HIGH — same analysis as MNV4-H3 | ≥ 3 methods (born_digital, scanner, camera_smartphone) | unknown | TBD |
| script_code | `language.script_code` | HIGH — CJK char_height differences; same analysis as MNV4-H3 | ≥ 3 script families | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs affect pipeline behavior; same as MNV4-H3 | ≥ 2 modes | unknown | TBD |
| domain | `domain.level1` | MEDIUM — same analysis as MNV4-H3 | ≥ 5 domains | unknown | TBD |
| layout_type | `structure.layout_type` | MEDIUM — same analysis as MNV4-H3 | ≥ 3 types | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — same analysis as MNV4-H3 | ≥ 2 age classes | unknown | TBD |
| degradation | `quality.degradations` | MEDIUM — same analysis as MNV4-H3 | ≥ 3 degradation types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis; same dataset as MNV4-H3, same wild condition analysis applies)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Born-digital PDF at low DPI (large fonts → high char_height paradox) | `capture_method.method` = born_digital + `resolution.dpi` < 150 | ⚠️ | Same gap as MNV4-H3 — OOD-Resolution 6a shared |
| Bicubic-upscaled raster (no real resolution gain) | `resolution.upscale_factor` | ⚠️ | Same gap as MNV4-H3 — OOD-Resolution 6b shared |
| SigLIP vs MobileNetV4 divergence on ambiguous images | _(inter-model comparison metric)_ | ⏳ | Key stress test unique to this head: cases where SIG-G5-5 and MNV4-H3 predictions diverge by > 0.2 signal potential labeling errors or model-specific overfitting |
| CJK documents (larger char_height baseline) | `language.script_code` in {HANS, HANT, JPAN, KORE} | ⏳ | Same gap as MNV4-H3 |
| Documents with no text (image-only pages) | `structure.has_text` = false | ⏳ | Same gap as MNV4-H3 |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Resolution (Phase 6, P0, 500 total images — shared with MNV4-H3)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 6a. Vector PDF at 3 DPIs | 300 | DocLayNet born-digital PDFs rendered at 72/150/300 DPI (100 images each) | resolution_quality_score (measured on rendered image) | mobilenetv4 + siglip2 | Shared with MNV4-H3. SIG-G5-5 evaluated on same OOD set — divergence between the two heads flags review. |
| 6b. Upscaled rasters | 200 | OHR-Bench test set OR RealDAE subset (NOT DIQA-5000). 2× and 4× bicubic upscaling. | resolution_quality_score (measured on ORIGINAL before upscaling) + upscale_factor | mobilenetv4 + siglip2 | Shared with MNV4-H3. Key diagnostic: if SIG-G5-5 and MNV4-H3 agree on upscaled images, model is not detecting upscaling artifacts; disagreement triggers investigation. |

### OOD Evaluation Role

SIG-G5-5 is evaluated on OOD-Resolution to identify cases where SigLIP 2 and MobileNetV4 disagree. A divergence threshold (e.g., |SIG-G5-5 − MNV4-H3| > 0.2) triggers a review workflow to determine which head has drifted or encountered a novel distribution.

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 6, P0 — shared with MNV4-H3)

### OOD Leakage Risk

Same as MNV4-H3: DIQA-5000 in training; OHR-Bench test split withheld; DocLayNet OOD renders must use pages not in any training split. Global split registry required.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| MNV4-H3 (resolution_quality) | Shares exact training dataset; identical L2 field | Label convention must be bit-for-bit identical — both heads read the same `resolution.resolution_quality_score` field from the same L2 sidecar. If the two heads diverge significantly on OOD, it signals one or both has overfit. Divergence metric must be computed and monitored during evaluation. |
| SIG-G5-1 (capture_cls) | Different head, different dataset; born-digital capture interacts with resolution | Born-digital low-DPI paradox creates interaction: capture_method=born_digital + low DPI → high char_height → potentially misleading resolution_quality score. Both heads must handle this scenario consistently and not contradict each other in downstream routing. |
| Other G5 heads | Co-trained in Phase 5 | SIG-G5-5 is the lowest-priority G5 head (P2). If training compute is constrained, it may be dropped from Phase 5 and trained separately. Must not create label dependency on other G5 heads. |

### Split Leakage Risk

**Level**: MEDIUM

Same analysis as MNV4-H3. The critical requirement is that train/val/test splits are byte-identical between MNV4-H3 and SIG-G5-5 — this is achieved by using the same global split registry entries for the shared 30K dataset.

### Label Convention

Identical to MNV4-H3: `resolution_quality_score` from L2 field `resolution.resolution_quality_score`, log-normalized [0,1], where 0.0 = needs_major_upscale and ~0.65 = optimal (32-48px char_height range). Any convention change applied to MNV4-H3 must be applied simultaneously to SIG-G5-5. The two heads must never be trained on different versions of the label schema.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G5-5-G01 | — | All MNV4-H3 P0 blockers (H3-G01, H3-G02, H3-G03) are inherited — dataset shared | Same root cause as MNV4-H3 | Resolve MNV4-H3 blockers first; SIG-G5-5 assembly is unblocked automatically | 0 additional days (piggybacks on MNV4-H3 work) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G5-5-G02 | Inter-model divergence metric not yet defined (|SIG-G5-5 − MNV4-H3| threshold for triggering review) | Divergence monitoring not yet designed | Define divergence threshold; implement divergence logging in inference pipeline | 0.5 days |
| G5-5-G03 | P2 priority creates scheduling risk — SIG-G5-5 may be skipped in Phase 5 if compute is constrained | Training compute allocation not finalized | Confirm Phase 5 training budget includes SIG-G5-5; document explicit go/no-go decision | 0 days (decision only) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G5-5-G04 | SIG-G5-5 calibration vs MNV4-H3 not yet studied (do the two heads agree on the full DIQA-5000 validation set?) | Run inference comparison after both heads are trained; plot prediction scatter to identify systematic bias |
| G5-5-G05 | Uncertainty output not planned (linear vs Gaussian NLL head) | Consider switching to Gaussian NLL head (mu, sigma_sq) for richer uncertainty signal — currently P2 since head is primarily used for drift detection |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution

**Adequacy Rating (pre-consensus)**: ⏳ TBD (analysis required)

**Analyst Summary**: _(To be written after Sections 2–8 analysis is complete)_

**Consensus Prompt**: _(To be written after Section 8 gap registry is complete)_

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _(Pending)_

**Final Rating**: _(Pending)_

**Top Recommendations**: _(Pending)_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | TBD | TBD |
| 14-Dimension Coverage | 25% | TBD | TBD |
| Wild Condition Coverage | 20% | TBD | TBD |
| OOD Design Quality | 20% | TBD | TBD |
| **Overall** | 100% | — | TBD |

**Grade**: ⏳ TBD
