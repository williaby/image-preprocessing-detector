# HAR Synthesis: Cross-Head Dataset Adequacy Analysis

> **Status**: ✅ Complete
> **Version**: 1.0
> **Created**: 2026-02-25
> **Updated**: 2026-03-06
> **Branch**: `docs/har-systematic-head-review`
>
> Synthesizes findings across all 22 Head Adequacy Reviews (HARs).
> Each HAR audits one training head against its source pool, 14-dimension diversity,
> wild condition coverage, and OOD design.

---

## Summary Dashboard

> **IQA Transition (2026-03-06)**: Group 1 IQA changed from 6 individual degradation heads
> (SIG-G1-1 through G1-6) to 3 DIQA-aligned dimensions (iqa_overall, iqa_sharpness,
> iqa_color_fidelity) using DeQA-Doc pseudo-labels gated by Mahalanobis OOD detection.
> See [DEQA_DOC_PSEUDO_LABELING.md](DEQA_DOC_PSEUDO_LABELING.md). The 6 original G1 HARs
> are superseded; individual degradation heads are deferred to Phase F.

| Metric | Value |
| --- | --- |
| Total heads reviewed | **19** (was 22; 6 old G1 heads replaced by 3 DIQA-aligned) |
| ✅ Ready (≥75, no P0) | **0** |
| ⚠️ Needs Work (50–74 or P0 ≤5d) | **10** |
| ❌ Blocked (<50 or unresolvable P0) | **6** |
| ✅ Resolved via DeQA-Doc pipeline | **3** (SIG-G1-1 iqa_overall, SIG-G1-2 iqa_sharpness, SIG-G1-3 iqa_color_fidelity) |
| Total P0 gaps across all heads | **53** (was 72; 19 IQA P0s resolved by DeQA-Doc pseudo-labeling) |
| Heads with 0 P0 gaps | **7** (MNV4-H1, MNV4-H2, SIG-G1-1, SIG-G1-2, SIG-G1-3, SIG-G3-1, SIG-G3-2) |
| Median score | **39/100** (non-IQA heads unchanged) |
| Lowest score | **14/100** (SIG-G4-5 legibility_reg) |
| Highest score | **65/100** (SIG-G5-5 resolution_quality_reg) |

**IQA heads are now unblocked.** DIQA-5000 provides 3.5K human-labeled ground truth (weight=1.0) and DeQA-Doc pseudo-labels cover the remaining corpus with OOD-gated sample weights. The SigLIP 2 Warmup phase can now proceed with IQA + Script training. All other heads retain their original status — the Geometry batch (MNV4-H1/H2, SIG-G3-1/G3-2) has 0 P0 gaps and assembled datasets.

---

## Section 1 — Gap Registry Summary

All gap IDs from Sections 8 of all 22 HARs, grouped by root cause type.

### Root Cause Group 1 — L2 Field Not Populated (Highest Impact)

These gaps block entire assembly pipelines. No training data can be produced without resolving them.

| Root Cause | Fields Affected | Heads Blocked | Gap IDs |
| --- | --- | --- | --- |
| `physical_degradation.shadow_severity` = 0% in all L2 | sd7k, wsrd, realdae, v3 shadows | SIG-G5-2 | SHADOW-G01, SHADOW-G02 |
| `physical_degradation.warping_severity` = 0% in all L2 | doc3d, SmartDoc-QA, v3 warps | SIG-G5-3 | WARP-G01, WARP-G02, WARP-G04 |
| `resolution.resolution_quality_score` = 18% labeled | only DIQA-5000 (5.5K/30K) | MNV4-H3, SIG-G5-5 | RQ-G01 through RQ-G04 |
| `handwriting_assessment.*` = 0% for most datasets | IAM, Muharaf, PUCIT-OHUL | SIG-G4-1 through G4-5 | PRESENCE-G01, LEG-G01, CTYPE-G01 |
| ~~`ml_image_quality.*` Phase 1 curated path~~ | ~~DIQA-5000 (200/5.5K scored)~~ | ~~SIG-G1-1 through G1-6~~ | ~~BLUR-G01, NOISE-G01, CONTRAST-G01, SKEW-G01, COMP-G01, OVERALL-G01~~ **RESOLVED**: Replaced by 3-dim DIQA scheme (iqa_overall, iqa_sharpness, iqa_color_fidelity). DIQA-5000 GT (3.5K train) + DeQA-Doc pseudo-labels with OOD gating. Individual degradation heads deferred to Phase F. |

### Root Cause Group 2 — Script Not Yet Created

These scripts exist in the plan but have not been implemented.

| Script | Purpose | Heads Unblocked | Effort |
| --- | --- | --- | --- |
| `label_shadow_severity.py` | Extract shadow GT from sd7k/wsrd; generate severity from clean pairs | SIG-G5-2 | 3–4 days |
| `label_warping_severity.py` | Extract warping severity from doc3d 3D mesh (after formula defined) | SIG-G5-3 | 3–4 days |
| Warping derivation formula | Define `severity = f(3D_mesh_curvature)` before above script | SIG-G5-3 | 2 days |
| ~~IQA VLM prompt v2.0 at scale~~ | ~~Scale from 200 → 2,000–5,000 images with orientation-independent scoring~~ | ~~SIG-G1-1 through G1-6~~ | **SUPERSEDED** by DeQA-Doc pseudo-labeling pipeline. See [DEQA_DOC_PSEUDO_LABELING.md](DEQA_DOC_PSEUDO_LABELING.md) |
| Pixel-ratio handwriting presence tool | Ink coverage → handwriting presence score for MARGINAL/PARTIAL classes | SIG-G4-1, G4-4 | 3–5 days |
| `generate_code_detection_dataset.py --full-run` | Script exists; dry-run done; full run not yet executed | SIG-G5-4 | 0.5 days |

### Root Cause Group 3 — Source Dataset Gap (Structural)

These cannot be resolved by labeling existing data — new data must be acquired or synthesized.

| Gap Description | Heads Affected | Severity |
| --- | --- | --- |
| ILLEGIBLE handwriting: ~0 labeled examples (curation bias in all handwriting corpora) | SIG-G4-2, G4-5 | ❌ Critical |
| MIXED_TYPED_HW: ~0 natural examples across all candidate datasets | SIG-G4-3 | ❌ Critical |
| Mid-range handwriting presence scores (0.2–0.7): <3K examples | SIG-G4-4 | ❌ Critical |
| CAMERA_PROFESSIONAL, SCANNER_ADF, FAX capture classes: 0 labeled | SIG-G5-1 | ⚠️ High |
| Book gutter shadow pattern: absent from training (only in OOD) | SIG-G5-2 | ⚠️ High |
| ADF scanner curl warping type: absent from all sources | SIG-G5-3 | ⚠️ High |
| Script pool: 4 ISO classes have 0 real images (TIBT, KHMR, SINH, JAVA) | SIG-G2-1 | ⚠️ High |

### Root Cause Group 4 — Schema/Sentinel Defects

These are data-quality bugs that will corrupt training if not fixed before any labels are generated.

| Defect | Head | Description | Fix Required |
| --- | --- | --- | --- |
| N_A sentinel = 0.0 | SIG-G4-5, SIG-G4-4 | legibility_score and presence_score use 0.0 for N_A, same as "fully illegible/absent" — trains head toward 0 for all printed pages | Change N_A to -1.0; add masked loss to ignore N_A during gradient computation |
| Capture method 3→7 class expansion | SIG-G5-1 | L2 stores born_digital/scanner/camera_* (3 classes); head requires 7-class enum | Define 6-class reduction schema; update L2 labeling for MIDV500/SmartDoc-QA entries |
| MIDV500/SmartDoc-QA misclassified as CAMERA_PROFESSIONAL | SIG-G5-1 | Both are smartphone captures, not professional camera | Re-label to CAMERA_SMARTPHONE in L2 metadata |
| code_reg labeled as regression (MAE metric) | SIG-G5-4 | Task is binary classification (BCE + boolean label, 0/1); tracking MAE is meaningless | Rename head to code_cls; switch metric to AUC/F1 in config |

### Root Cause Group 5 — Distribution Mismatch

These datasets have the right content but wrong class balance for training.

| Mismatch | Head | Description |
| --- | --- | --- |
| Script imbalance: 8.6× class ratio (LATN 100K vs TIBT/JAVA near-0) | SIG-G2-1 | Class weights alone insufficient; synthetic generation for 4 rare scripts required |
| Handwriting presence bimodal: 0.0 (printed) and ~0.95 (HW corpora), void at 0.2–0.7 | SIG-G4-4 | No mid-range training data; Pearson r achievable spuriously on bimodal test set |
| DIQA-5000 OHR orientation: 48% of Q5 (high MOS) images rotated 90° → VLM penalizes rotation | SIG-G1-6 | Non-rotated SRCC=0.53 vs all-image SRCC=0.39; pre-filter by orientation before IQA scoring |
| OOD-4c (book gutter shadow) at 100 images: insufficient for stable MAE regression evaluation | SIG-G5-2 | Minimum ≥250 images needed for ±0.01 MAE confidence interval |

---

## Section 2 — Audit Defect Cross-Reference

Where specific dataset audit defect codes (D-codes) or Known Issues (KI-codes) directly block head training:

| Defect Code | Source Dataset | Blocks Heads | Description |
| --- | --- | --- | --- |
| KI-G5-5-01 | DIQA-5000 | MNV4-H3, SIG-G5-5 | V1 precision gap (IQR 9.0px vs target 2-3px) — resolution quality scores need V2 algorithm before training |
| KI-G1-6-01 | DIQA-5000 | SIG-G1-6 | Rotation construct mismatch: 48% of Q5 images are rotated 90°; VLM-MOS correlation artificially suppressed |
| KI-G4-5-01 | All handwriting datasets | SIG-G4-5, SIG-G4-4 | N_A sentinel = 0.0 defect in scaffold — must be fixed before ANY handwriting labels are generated |
| KI-G5-1-01 | MIDV500, SmartDoc-QA | SIG-G5-1 | Capture method misassignment: both labeled CAMERA_PROFESSIONAL in L2; should be CAMERA_SMARTPHONE |
| KI-G4-2-01 | IAM, HierText, COCO-Text | SIG-G4-2 | Curation bias: all curated HW datasets select legible examples; ILLEGIBLE/POOR classes have ~0 coverage |
| KI-G4-3-01 | All handwriting datasets | SIG-G4-3 | MIXED_TYPED_HW structurally absent: no corpus systematically creates typed+handwritten mixed pages |
| G5-3-DEF-01 | doc3d | SIG-G5-3 | 3D mesh data exists but scalar severity derivation formula not defined; field unpopulated in L2 |

---

## Section 3 — Blocker Dependency Graph

Which P0 gaps block which heads, with dependency ordering.

```text
label_shadow_severity.py (SHADOW-G01)
  └─ depends on: [none — implement directly]
  └─ unblocks: SIG-G5-2 (shadow_reg)

warping_severity derivation formula (WARP-G02) ← must come FIRST
  └─ depends on: [domain expertise decision]
  └─ enables: label_warping_severity.py (WARP-G01)
                └─ unblocks: SIG-G5-3 (warping_reg)

resolution_quality V2 algorithm (RQ-G02)
  └─ depends on: V1 precision gap root cause identified
  └─ enables: label_resolution_quality.py on OHR-Bench + RealDAE
                └─ unblocks: MNV4-H3 and SIG-G5-5 (resolution_quality_reg)

N_A sentinel fix (KI-G4-5-01) ← must come BEFORE any HW labeling
  └─ depends on: schema decision (use -1.0 with masked loss)
  └─ MUST precede: all handwriting_assessment.* L2 labeling

pixel_ratio presence tool (PRESENCE-G01)
  └─ depends on: [implement from IAM ink coverage literature]
  └─ enables: presence_score labeling for MARGINAL/PARTIAL/SUBSTANTIAL classes
                └─ unblocks: SIG-G4-1 (presence_cls), SIG-G4-4 (presence_reg)

ILLEGIBLE HW data acquisition
  └─ depends on: new data collection pipeline (VLM-guided selection + spot-check)
  └─ unblocks: SIG-G4-2 (legibility_cls), SIG-G4-5 (legibility_reg)

~~IQA VLM prompt v2.0 at scale (OVERALL-G01)~~ — SUPERSEDED
  └─ RESOLVED by DeQA-Doc pseudo-labeling pipeline (2026-03-06)
  └─ IQA heads now use 3-dim DIQA scheme: iqa_overall, iqa_sharpness, iqa_color_fidelity
  └─ DIQA-5000 GT (3.5K train, weight=1.0) + DeQA-Doc pseudo-labels (OOD-gated weights)
  └─ unblocks: SIG-G1-1 (iqa_overall), SIG-G1-2 (iqa_sharpness), SIG-G1-3 (iqa_color_fidelity)

capture_method schema clarification
  └─ depends on: decision on 6-class vs 7-class schema
  └─ enables: re-labeling MIDV500/SmartDoc-QA + SCANNER_ADF labeling
                └─ unblocks: SIG-G5-1 (capture_cls)

code detection full run (CODE-G02)
  └─ depends on: negative contamination validation (CODE-G01), style ratio fix (CODE-G04)
  └─ unblocks: SIG-G5-4 (code_reg) — most P0 gaps are fast-resolvable
```

**Critical path for earliest training start**: Geometry batch (MNV4-H1/H2, SIG-G3-1/G3-2) — 0 P0 gaps, data assembled. Training can begin NOW for these 4 heads.

---

## Section 4 — Training Phase Risk Map

SigLIP 2 training phases per `SIGLIP2_MULTITASK_REQUIREMENTS.md`:

| Phase | Heads Trained | P0 Gaps | Assembly Status | Risk |
| --- | --- | --- | --- | --- |
| **Warmup** (5 ep): IQA + Script | G1-1 (iqa_overall), G1-2 (iqa_sharpness), G1-3 (iqa_color_fidelity), G2-1 | **0 P0 in G1** (resolved); 5 P0 in G2 | G1: ✅ DIQA-5000 GT + DeQA-Doc pseudo-labels ready; G2: 0/108K assembled | ⚠️ IQA can start NOW; Script still blocked on assembly |
| **Expand** (5 ep): + Orientation + Skew | G3-1, G3-2 | 0 P0 each | ✅ 50K orient + 90K skew assembled | ✅ Can add these heads once Warmup checkpoint exists |
| **Full** (20–40 ep): All 16 SigLIP heads | All G1–G5 heads | 53 total P0 | Mixed — IQA + Geometry ready, G4/G5 blocked | ⚠️ Phase blocked on G4/G5 data (handwriting, page attrs) |
| **Refine** (5–10 ep): Fine-tuning all heads | All 16 | — | — | ❌ Cannot start until Full phase completes |
| **MobileNetV4** (separate): H1/H2/H3 | MNV4-H1, H2, H3 | 0 / 0 / 3 | H1+H2: ✅ Ready; H3: blocked on RQ | ⚠️ H1+H2 can train; H3 blocked |

**Key finding (updated 2026-03-06)**: SigLIP 2 Warmup phase is **partially unblocked** — IQA heads can now train using DIQA-5000 ground truth (3.5K train, weight=1.0) and DeQA-Doc pseudo-labels with OOD-gated sample weights. Script training data still requires synth-multiscript assembly and class-weight rebalancing. An IQA-only warmup can proceed immediately.

**MobileNetV4 can start training** for H1 (orientation) and H2 (skew) immediately. H3 (resolution quality) requires RQ V2 labeling.

---

## Section 5 — Prioritized Remediation Backlog

Ordered by: (heads unblocked × data volume unlocked) / engineering effort

| Priority | Action | Effort | Heads Unblocked | Data Volume Unlocked |
| --- | --- | --- | --- | --- |
| **P0.1** | **Start MNV4-H1 + MNV4-H2 training** | 0.5 days (setup) | MNV4-H1, MNV4-H2 | 50K + 90K ✅ assembled |
| **P0.2** | **Fix N_A sentinel defect** (change to -1.0 + masked loss in schema) | 1 day | Prerequisite for all G4 | Prevents corrupt handwriting labels |
| **P0.3** | **Fix code_reg head classification** (rename code_cls, switch AUC/F1 metric) | 1 day | SIG-G5-4 documentation | Prevents metric tracking failure |
| ~~**P0.4**~~ | ~~**Validate IQA VLM prompt v2.0**~~ **SUPERSEDED** by DeQA-Doc pseudo-labeling (2026-03-06). IQA heads now use 3-dim DIQA scheme with DIQA-5000 GT + OOD-gated pseudo-labels. | — | ~~SIG-G1-6~~ → SIG-G1-1/2/3 resolved | — |
| **P0.5** | **label_shadow_severity.py** (implement + run on sd7k/wsrd + construct NONE class from clean pairs) | 5–7 days | SIG-G5-2 | 15K+ images unlocked |
| **P0.6** | **Resolution quality V2 + OHR-Bench + RealDAE labeling** (Sauvola+projection improvement → label 8.5K+1.2K) | 7–10 days | MNV4-H3, SIG-G5-5 | 15.2K → 30K target met |
| **P0.7** | **Capture method schema clarification + re-labeling** (6-class schema, MIDV500/SmartDoc-QA fixes, FAX heuristic) | 5–7 days | SIG-G5-1 | 50K capture dataset unlocked |
| **P0.8** | **Warping derivation formula + label_warping_severity.py** | 9–12 days | SIG-G5-3 | 20K+ images unlocked |
| **P0.9** | **Code detection full run** (fix neg contamination + style ratio, execute) | 2–3 days | SIG-G5-4 | 10K dataset assembled |
| ~~**P0.10**~~ | ~~**IQA VLM labeling at scale**~~ **SUPERSEDED** by DeQA-Doc pseudo-labeling (2026-03-06). Full corpus covered by per-dimension mPLUG-Owl2-7B models with OOD-gated sample weights. | — | ~~SIG-G1-1 through G1-6~~ resolved | — |
| **P1.1** | **Script pool rebalancing** (synthetic generation for TIBT/KHMR/SINH/JAVA; enforce ≤60% synthetic cap) | 2–3 weeks | SIG-G2-1 | 108K script dataset assembled |
| **P1.2** | **Handwriting presence tool** (pixel-ratio ink coverage; pixel binarization; IAM validation) | 5–7 days | SIG-G4-1, SIG-G4-4 (partially) | Labels for MARGINAL/PARTIAL/SUBSTANTIAL presence |
| **P1.3** | **ILLEGIBLE handwriting data acquisition** (VLM-guided selection pipeline from OCR-rejected documents) | 3–5 weeks | SIG-G4-2, SIG-G4-5 | ILLEGIBLE/POOR class void resolved |
| **P1.4** | **MIXED content type data acquisition** (MIXED_TYPED_HW: forms, OCR-rejected hybrid pages) | 4–6 weeks | SIG-G4-3 | MIXED class structural gap addressed |
| **P1.5** | **Complete handwriting harmonization** (all G4 heads: presence + legibility + content_type + regression labels) | 8–12 weeks | SIG-G4-1 through G4-5 | 60K handwriting dataset assembled |
| **P2.1** | **Expand OOD-4c book gutter shadow** (100 → ≥250 images for stable regression evaluation) | 1–2 days | SIG-G5-2 OOD quality | MAE ±0.01 confidence interval met |
| **P2.2** | **Add binarized-doc examples to shadow + warping + IQA training** | 3–5 days | SIG-G5-2, G5-3, G1-1 through G1-5 | Removes 0/100 binarized coverage gap |
| **P2.3** | **Synthetic script generation for rare ISO classes** (post-ILP allocation) | 2–3 weeks | SIG-G2-1 (already in P1.1) | Quality improvement for rare classes |

**Estimated time to first full SigLIP Warmup phase**: ~4–6 weeks (IQA unblocked via DeQA-Doc; dominated by script pool rebalancing + code detection full run). Was ~10–14 weeks before DeQA-Doc transition.

**Estimated time to MobileNetV4 H1+H2 first training checkpoint**: **This week** — data is assembled.

---

## Section 6 — Cross-Head Patterns

Systemic gaps affecting multiple heads simultaneously.

### Pattern 1 — Binarized-Document Coverage Gap (13+ heads)

Every head tested against binarized (1-bit) documents shows a coverage gap. This pattern affects:

- SIG-G1-1 through G1-5 (IQA): blur/noise/contrast detection behaves differently on binarized documents; binarization is an IQA-relevant condition (binarized = severe information loss)
- SIG-G5-2 (shadow): shadow on binarized documents produces no gradient signal; detector will output ~0.0 unreliably
- SIG-G5-3 (warping): edge-only warping cues remain after binarization; specific calibration needed
- SIG-G5-4 (code): code on binarized scans loses syntax highlighting, becomes monochrome characters only
- MNV4-H1, SIG-G3-1 (orientation): already partially covered by RVL-CDIP (scanned binarized docs)
- SIG-G2-1 (script): synth-multiscript v3 has some binarized examples via augmentation

**Remediation**: Add a 10% binarized-document stratum to every non-geometry training dataset during Stream 4C assembly. Use existing v3 binarized augmentation pipeline.

### Pattern 2 — Compound Degradation Absent From All Heads

No training dataset includes images with two simultaneous degradation types applied. Real-world documents frequently have:

- Shadow + blur (phone camera in dim room)
- Warping + noise (aged warped document)
- Low resolution + skew (far-away photo of tilted document)

This affects: SIG-G1-1 through G1-5 (Phase 2 synthetic), SIG-G5-2, SIG-G5-3, MNV4-H2/H3.

**Remediation**: During Phase 2 synthetic IQA generation (100K), include a 15% compound-degradation stratum where 2 degradation types are simultaneously applied. Record both labels in L2 metadata.

### Pattern 3 — ~~VLM Labeling Bottleneck~~ RESOLVED via DeQA-Doc (2026-03-06)

~~The IQA-curated Phase-1 path (16K images) depends entirely on VLM scoring.~~ This bottleneck is **resolved** by the DeQA-Doc pseudo-labeling pipeline.

**Previous state** (pre-2026-03-06): VLM scoring was at 200/5,500 images (3.6%), SRCC 0.53 (non-rotated) — below 0.65 target. This blocked all 6 G1 heads.

**Resolution**: DeQA-Doc (VQualA 2025 champion) per-dimension mPLUG-Owl2-7B models generate pseudo-labels for all 3 DIQA dimensions (overall, sharpness, color_fidelity) across the entire unified corpus. OOD gating via Mahalanobis distance (AUROC 0.9963) assigns reliability-weighted sample weights. DIQA-5000 ground truth (3.5K train) provides weight=1.0 anchor labels. See [DEQA_DOC_PSEUDO_LABELING.md](DEQA_DOC_PSEUDO_LABELING.md).

**Impact**: IQA training can start immediately. The VLM labeling path for IQA is no longer needed. VLM scoring may still be useful for future Phase F individual degradation heads but is not on the critical path.

### Pattern 4 — OOD Deployment Gap (19 of 22 heads)

Only 4 Geometry heads (MNV4-H1, MNV4-H2, SIG-G3-1, SIG-G3-2) have partially adequate OOD design. All other heads score below 50/100 on OOD Design Quality because:

- OOD Phase 4 collection has not started
- Most heads have <4 OOD sub-sources for their specific failure modes
- OOD category definitions exist but images not yet collected

This is a planning risk: training can begin on some heads but OOD evaluation infrastructure is not yet in place.

**Remediation**: OOD collection should begin in parallel with training data preparation. The 100-image book-gutter-shadow sub-source is feasible in 1–2 days of photography. Prioritize OOD sub-sources that have no current analog in training.

### Pattern 5 — Camera-Capture Under-Representation (8+ heads)

Most training datasets are born-digital or flatbed-scanner. Camera-captured documents (mobile phone, professional camera) are under-represented in:

- IQA heads: blur/noise/contrast detection patterns differ for camera captures
- Orientation, skew: camera captures introduce perspective distortion
- Shadow, warping: these degradations are almost exclusively camera-capture phenomena
- Capture classification: training must have camera examples across all 7 classes

The production pipeline will predominantly receive camera-captured documents (mobile upload workflow). This is the highest-risk deployment gap.

**Remediation**: Audit each assembled training dataset for `capture_method=CAMERA_*` representation. Target ≥30% camera-captured images in all IQA, shadow, and warping training datasets.

### Pattern 6 — Handwriting Group Systemic Failure (5 heads blocked)

All 5 G4 heads are blocked. Combined they require:

- ILLEGIBLE/POOR class: ~0 → 12,000+ examples needed
- MIXED_TYPED_HW: ~0 → 6,000+ examples needed
- Mid-range presence scores: <3K → 8,000+ needed
- Consistent legibility annotation protocol across 8 datasets
- N_A sentinel fix applied before any labeling

**Estimated total effort to unblock all 5 G4 heads**: 8–12 weeks with 2 dedicated engineers.

**Recommendation**: Treat G4 as a separate Track. Defer G4 from SigLIP Warmup/Expand phases. Add G4 only in Phase 3 (Full training, 20–40 epochs) after data is assembled.

---

## Section 7 — Verification Checklist

Per plan requirements:

- [x] `ls docs/planning/har/*.md | wc -l` → 22 ✅
- [x] All 22 HARs have Section 9 status ≠ "Pending" ✅
- [x] `HAR_MASTER_INDEX.md` has 22 rows, no blank adequacy ratings ✅
- [x] `HAR_SYNTHESIS.md` exists with gap registry and prioritized remediation backlog ✅
- [ ] Every P0 gap has a remediation action assigned — ✅ All P0 gaps assigned in HAR Sections 8 and this backlog

---

## Appendix A — Full Score Table

| Head ID | Head Name | Score | Grade | P0 Gaps | P1 Gaps |
| --- | --- | --- | --- | --- | --- |
| MNV4-H1 | orientation | 63/100 | ⚠️ Needs Work | 0 | 3 |
| MNV4-H2 | skew_reg | 55/100 | ⚠️ Needs Work | 0 | 3 |
| MNV4-H3 | resolution_quality | 26/100 | ⚠️ Needs Work | 3 | 3 |
| SIG-G1-1 | iqa_overall (was blur/noise/contrast/skew/compression/overall) | ✅ Resolved | ✅ Resolved via DeQA-Doc | 0 | 0 |
| SIG-G1-2 | iqa_sharpness | ✅ Resolved | ✅ Resolved via DeQA-Doc | 0 | 0 |
| SIG-G1-3 | iqa_color_fidelity | ✅ Resolved | ✅ Resolved via DeQA-Doc | 0 | 0 |
| SIG-G2-1 | script_code | 32/100 | ⚠️ Needs Work | 5 | 3 |
| SIG-G3-1 | orientation_cls | 52/100 | ⚠️ Needs Work | 0 | 3 |
| SIG-G3-2 | skew_reg | 46/100 | ⚠️ Needs Work | 0 | 3 |
| SIG-G4-1 | presence_cls | 32/100 | ❌ Blocked | 5 | 3 |
| SIG-G4-2 | legibility_cls | 21/100 | ❌ Blocked | 4 | 3 |
| SIG-G4-3 | content_type_cls | 25/100 | ❌ Blocked | 6 | 4 |
| SIG-G4-4 | presence_reg | 26/100 | ❌ Blocked | 4 | 4 |
| SIG-G4-5 | legibility_reg | 14/100 | ❌ Blocked | 6 | 4 |
| SIG-G5-1 | capture_cls | 59/100 | ⚠️ Needs Work | 4 | 3 |
| SIG-G5-2 | shadow_reg | 28/100 | ❌ Blocked | 3 | 4 |
| SIG-G5-3 | warping_reg | 17/100 | ❌ Blocked | 4 | 3 |
| SIG-G5-4 | code_reg | 55/100 | ⚠️ Needs Work | 5 | 5 |
| SIG-G5-5 | resolution_quality_reg | 39/100 | ⚠️ Needs Work | 4 | 3 |
| **Total (19 heads)** | | | 3 Resolved / 0 Ready / 10 Needs Work / 6 Blocked | **53** | **52** |
