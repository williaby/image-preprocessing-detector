# Head Adequacy Review: compression_score (SIG-G1-5)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-5 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | compression_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | VQualA ≥ 0.92 (SRCC with human MOS) |
| Primary L2 Field | `ml_image_quality.compression_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: Human MOS / VLM scores → L2 field; Phase 2: JPEG quality parameter (inverse: lower quality = higher compression severity) → L2 field |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.compression_score` (float 0-1; Phase 1) / JPEG quality factor parameter (Phase 2)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_0_exact (human MOS) or tier_1_annotation (VLM); Phase 2: tier_0_exact (JPEG quality factor recorded at generation time; score is inverted: compression_score = quality_factor / 100 so lower JPEG quality = lower score)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/diqa-5000_audit.md for compression_score-specific defect codes; note classical JPEG blockiness detector may have non-zero but low-SRCC performance)_

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | _(analysis required)_ | — | — | _(check audit)_ | — |
| OHR-Bench | 10,800 | _(analysis required)_ | — | — | — | — |

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The JPEG quality factor applied during Augraphy generation is the ground-truth label, converted to a 0-1 score.

- **Target**: 100,000 synthetic images via Augraphy/augmentation pipeline
- **Label provenance**: tier_0_exact (JPEG quality factor is recorded at generation time)
- **Normalization**: compression_score = jpeg_quality / 100.0 (quality=100 → score=1.0 = perfect, no compression; quality=10 → score=0.1 = severe compression)
- **Note**: This is the INVERSE of compression severity — higher score = better quality. Consistent with all other G1 score conventions.
- **Pipeline status**: _(analysis required — check if Phase 2 pipeline script exists)_

### Usable Pool Summary

- **Phase 1 usable**: _(analysis required)_
- **Phase 1 target**: 16,300 images
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 100,000 Phase 2 images

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — VLM pilot complete for 200 images (overall_quality focus; compression-specific validation not yet run)
- Phase 1 OHR-Bench: Tier 2 (max(15, 10%)) — VLM labeling not yet started
- Phase 2: No VLM sampling needed (JPEG quality factor is an exact ground-truth parameter)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required — review diqa-5000_audit.md; note classical JPEG blockiness detector may have known limitations)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch affects all G1 VLM labels | HIGH — compression-specific VLM SRCC not yet measured separately |
| IQA-KI-COMPRESS-BLUR | JPEG blockiness can appear as blur — risk of label confusion between compression_score and blur_score | MEDIUM — VLM prompt must explicitly distinguish DCT block artifacts from optical blur |
| _(check audit for additional KI codes)_ | — | — |

### Remediation Path

_(analysis required after reviewing DIQA-5000 audit and OHR-Bench L2 population status)_

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: 🔄 Phase 1 partial (16,300 images); Phase 2 not started (0/100,000)

**Target Count**: 16,300 (Phase 1) + 100,000 (Phase 2 synthetic) = 116,300 total

**Current Count**: 16,300 Phase 1 available; Phase 2 pipeline not yet created

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 16,300 | 16,300 | ✅ Met |
| Phase 2 total images | 100,000 | 0 | ❌ Not started |
| Phase 1 label tier | ≥80% tier_1 | Mixed: MOS (human) + VLM pilot | ⚠️ VLM SRCC below target |
| Phase 2 label source | Augmentation params (JPEG quality factor) | Not applicable (self-labeling) | ✅ No L2 dependency |
| DIQA-5000 coverage | 5,500 images | 5,500 (5,499 labeled) | ✅ Met |
| OHR-Bench coverage | 10,800 images | 10,800 (split TBD) | ⚠️ Labels not yet populated |
| JPEG quality range coverage | ≥5 quality tiers (10/20/50/75/95) | unknown in Phase 1 | ⚠️ Requires analysis |

**Blockers**:

- VLM labeling SRCC for compression_score not yet measured independently.
- OHR-Bench L2 `ml_image_quality.compression_score` field not yet populated.
- Phase 2 Augraphy synthetic pipeline not yet created.
- Phase 1 JPEG quality distribution in DIQA-5000/OHR-Bench is unknown — may be biased toward moderate compression.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` _(not yet implemented)_

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | HIGH — JPEG compression artifacts are the core degradation signal for this head | ≥5 compression severity levels (lossless/mild/moderate/heavy/severe) | unknown | TBD |
| capture_method | `capture_method.method` | HIGH — camera photos are re-compressed; scanned docs saved as JPEG; born-digital PDFs may embed JPEG streams | ≥3 capture methods represented | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — JPEG compression behaves differently on color, grayscale, and cannot be applied to 1-bit binarized | ≥2 modes (color + grayscale; binarized as special case with no JPEG artifacts) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — older digitized documents were often saved with aggressive compression; historical digitization practices | ≥2 age classes (modern + aged) | unknown | TBD |
| domain | `domain.level1` | MEDIUM — JPEG blockiness is more visible on text than on photographic content | ≥5 domains | unknown | TBD |
| resolution | `resolution.category` | MEDIUM — high-DPI JPEG compression artifacts are finer and harder to detect; must disentangle | ≥3 resolution tiers | unknown | TBD |
| script_code | `language.script_code` | MEDIUM — CJK ideograph stroke edges show JPEG ringing artifacts more visibly than Latin | ≥3 script families | unknown | TBD |
| layout_type | `structure.layout_type` | LOW — layout type not a primary driver of compression artifact signal | ≥3 types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Severe JPEG (quality ≤ 20) with visible blockiness | `quality.degradations` (compression subtype) | ⏳ | Phase 1 pool distribution at extreme low quality is unknown |
| Multi-round JPEG recompression (camera → scan → store) | `quality.degradations` | ⏳ | Chained compression degrades differently from single-pass; Phase 2 should model this |
| JPEG ringing on text edges (medium quality 40-60) | `quality.degradations` | ⏳ | Mid-range quality produces ringing without obvious blockiness; hardest perceptual case |
| PNG or lossless originals (compression_score = 1.0) | `capture_method.method` (born_digital) | ⚠️ | Born-digital PDFs often use lossless encoding; head must correctly assign 1.0 for these |
| Binarized documents (JPEG artifacts absent post-binarization) | `image_properties.color_mode` | ⚠️ | OOD-4d tests binarized; binarization removes JPEG block structure; model must score appropriately |
| Mixed compression (some embedded images JPEG, text vector) | `capture_method.method` (born_digital) | ⏳ | Hybrid PDFs have spatially non-uniform compression; global score may be misleading |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | JPEG compression combined with defocus blur, noise, and shadow — compression_score must be evaluated when blockiness is obscured by other degradations |
| 4b. Watermarked documents | 100 | ⚠️ Indirect | Watermark overlay may interact with JPEG blocking grid; secondary effect |
| 4c. Book gutter shadow | 100 | ⚠️ Indirect | Shadow regions may mask compression artifacts in low-gradient areas; secondary effect |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | Binarized docs have no JPEG artifacts; head must correctly predict high compression_score (or 1.0) for these |
| OOD-Mixed cascade | TBD | ⚠️ Indirect | Multi-distortion compounds including compression-degraded scans |

**OOD Acquisition Status**: ⏳ Not started (Phase 4)

**Missing OOD Sub-sources**: Compound distortion labeling for compression_score requires human annotation or the classical JPEG quality factor (DCT coefficient analysis) if it has sufficient SRCC — must be validated before use as OOD ground truth.

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench (16,300 images); Phase 2: synthetic augmentation

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| All other G1 heads (G1-1 to G1-4, G1-6) | DIQA-5000 + OHR-Bench | Multi-label independence required; labels must not be derived from each other | ✅ Each head's label is independently computed from MOS/VLM/augmentation params |
| SIG-G1-1 (blur_score) | Same dataset | JPEG blockiness can appear as blur — risk of label correlation at medium quality levels (40-60) | ⚠️ VLM prompt must explicitly score compression and blur independently; separate scoring dimensions |
| SIG-G1-4 (skew_score) vs SIG-G3-2 (skew_reg) | Different datasets | Naming confusion risk: skew_score ≠ skew angle | ✅ Different L2 fields; documented distinction |
| SIG-G1-6 (overall_quality) | Same dataset | overall_quality may use weighted average of other G1 scores including compression_score as cross-check | ⚠️ Risk of circular dependency if G1-6 labels derived from G1-1..G1-5 |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets.

**Label Convention**: compression_score is 0-1 where 1.0 = perfect quality (lossless or near-lossless), 0.0 = severe compression (extreme JPEG artifacts). Phase 2 derivation: compression_score = jpeg_quality / 100.0. For lossless formats (PNG, lossless JPEG 2000): compression_score = 1.0. For binarized images: compression_score convention TBD (see G1-5-G03 in gap registry).

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G1-5-G01 | — | OHR-Bench `ml_image_quality.compression_score` not populated in L2 metadata | L2 enrichment pipeline not yet run on OHR-Bench | Run VLM labeling pipeline on OHR-Bench; populate `ml_image_quality.compression_score` | _(analysis required)_ |
| G1-5-G02 | — | Phase 2 Augraphy synthetic pipeline not yet created | Script `prepare_multitask_datasets.py iqa` not implemented | Implement IQA sub-command; record jpeg_quality and compute compression_score = quality/100 at generation time | _(analysis required)_ |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G1-5-G03 | compression_score convention for binarized and lossless-format images undefined | 1-bit images have no JPEG artifacts; PNG/lossless images have no compression | Document convention: binarized → 1.0 (no compression artifact present); lossless → 1.0; add assertions in assembly script | _(analysis required)_ |
| G1-5-G04 | Compression-specific VLM SRCC not measured independently | VLM pilot focused on overall_quality only | Run targeted VLM validation on compression_score labels; verify SRCC ≥ 0.65; test with range of JPEG quality levels | _(analysis required)_ |
| G1-5-G05 | Classical JPEG quality factor detector (DCT analysis) SRCC not established | Detector exists in iqa_classical.py but cross-validation against MOS not measured | Compute SRCC of classical JPEG QF detector against DIQA-5000 MOS labels; use as cross-validation if SRCC > 0.5 | _(analysis required)_ |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G1-5-G06 | Multi-round recompression not modeled in Phase 2 | Add chained-compression augmentation type (JPEG → decode → JPEG) to Phase 2 pipeline |
| G1-5-G07 | Phase 1 JPEG quality distribution in DIQA-5000 is unknown — may be biased | Analyze quality-factor distribution of DIQA-5000 images; verify coverage of extreme low-quality |

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
