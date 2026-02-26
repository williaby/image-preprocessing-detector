# Training Corpus & OOD Evaluation: Independent Review

> **Status**: Final | Independently Derived
> **Date**: 2026-02-23
> **Analyst**: Claude Sonnet 4.6 (autonomous multi-session analysis)
> **Methodology**: Independent first-principles analysis + 5-model PAL consensus (2 rounds)
> **Input documents**: UNIFIED_TRAINING_CORPUS.md v1.0.0, SIGLIP2_MULTITASK_REQUIREMENTS.md,
> OOD_DATASET_CATALOG.md v3.1.0, HAR_SYNTHESIS.md, TRAINING_DATASET_QUICK_REFERENCE.md,
> results/v3_per_script_audit.json
> **Independence note**: Prior versions of this file were not consulted. All gap identifications
> and scores are derived from first principles by reading primary specification documents only.

---

## Review Metadata

| Field | Value |
|---|---|
| Phase B consensus continuation_id | `8dd57ce9-a8f7-4921-84bf-4450de589f18` |
| Phase D consensus continuation_id | `d679c9e0-ac57-44c9-b66d-72519f3bdf70` |
| Training corpus null hypothesis | **REJECTED** — 4/4 valid models (GPT-5.2 empty, 4th consecutive) |
| OOD catalog null hypothesis | **REJECTED** — 3/4 valid models (Grok 4 endorses design only; acquisition absent) |
| P0 gaps (training corpus) | 10 |
| P1 gaps (training corpus) | 12 |
| P0 gaps (OOD-specific) | 4 |
| P1 gaps (OOD-specific) | 8 |

---

## Executive Summary

### Training Corpus Verdict

The unified training corpus is **NOT READY FOR PHASE 2 TRAINING**. Of 11 acceptance criteria
(§11 of UNIFIED_TRAINING_CORPUS.md), **6 FAIL outright** and **2 are AT RISK**:

- ❌ **FAIL**: Minimum training samples at required label tier (IQA 16.3K vs. 50–100K minimum;
  SIG-G3-2 has no narrow-range dataset; ILLEGIBLE class void at 0 samples)
- ❌ **FAIL**: Wild condition requirements — 6 of 8 §8 requirements have zero meeting evidence
- ❌ **FAIL**: Label confidence floor — VLM SRCC 0.53, gate at 0.65 not met; no halt
  condition defined
- ❌ **FAIL**: IQA compound distortion sub-split (Phase 1B) not assembled
- ❌ **FAIL**: v3 Arab class at 3.78× target violates §2 max 3× constraint
- ❌ **FAIL**: Shadow and warping have 0 real data assembled (L2 severity labeling pending)
- ⚠️ **AT RISK**: Synthetic mixing cap (skew at 79.1% synthetic vs. ≤37.5% ideal)
- ⚠️ **AT RISK**: Script × degradation cross-tabulation (12 shadow/warping cells blocked)

**Phase 1 readiness (MobileNetV4 bootstrap):** MNV4-H1 (orientation) and MNV4-H2 (skew)
CAN train with acknowledged limitations. MNV4-H3 (resolution quality) is **BLOCKED** at
5,499 vs. 30,000 minimum.

**Phase 2 readiness (SigLIP2 multi-task):** FULLY BLOCKED by 8+ P0 gaps.

**Independent 22-head mean score: 27/100** (min: 13 for shadow/warping; max: 42 for orientation).

### OOD Catalog Verdict

The OOD evaluation corpus specification is **NOT ADEQUATE** for production validation:

- **0 of 12,000–15,000 target images acquired** across all 9 categories
- **Two P0 metric errors**: ILLEGIBLE floor uses classification accuracy (invalid with 0
  training samples — must be OSR Energy Score rejection rate); MNV4-H1 uses raw softmax
  confidence for abstention (Energy Score required for overconfident transformer)
- **Missing calibration corpus**: Energy Score requires held-out calibration set not defined
  in the OOD catalog
- **Cascade failure gaps**: MNV4-H2 wrong-correction cascade not covered in OOD-Mixed
- **Phase 1 minimum viable OOD**: 300 images at zero cost (9a-1 symmetric docs + 9a-2
  extreme-perspective + 100 ArXiv PDFs)

### Top 5 Action Items

1. **[P0, 1–2 days, zero cost]** Derive OOD-Mixed 9a-1 (100 symmetric docs), 9a-2 (100
   extreme-perspective docs), and OOD-Domain smoke test (100 ArXiv PDFs) from existing
   labeled data. Unblocks Phase 1 OOD evaluation immediately.

2. **[P0, 3–5 days, GPU VM]** Run `label_shadow_severity.py` and `label_warping_severity.py`
   on sd7k/wsrd/anyphotodoc6300/warpdoc. Unblocks shadow and warping heads entirely.

3. **[P0, 1 day]** Fix N_A sentinel: change 0.0 → -1.0 with masked loss in handwriting label
   schema BEFORE assembling handwriting dataset. Prevents permanent label corruption in
   legibility_reg and presence_reg heads.

4. **[P0, before fill run]** Resolve v3 three blocking decisions (Cher/Cans font feasibility;
   Armn/Grek keep-vs-delete; Kore→Hang rename) and run live GCS audit
   (`--no-use-splits-jsonl`) to establish accurate per-script baselines.

5. **[P0, 2 hours, schema fix]** Rename `code_reg` → `code_cls` in
   SIGLIP2_MULTITASK_REQUIREMENTS.md, train_siglip2_multitask.py, and head registry
   BEFORE any training begins. Wrong loss function (MSE vs. BCE) corrupts calibration.

---

## Part A: Training Corpus Review

### A.1 — 22-Head Coverage Scorecard

**Scoring method:** 6 dimensions × 10 points each (max 60), plus 40 bonus if zero P0 blockers.
Max possible score: 100. A head can bootstrap Phase 1 training at scores below 50 if
sample count and label quality pass.

| Dim | Criterion (pass = 10 pts) |
|---|---|
| D1 | Sample count ≥ minimum specified in §2 |
| D2 | Synthetic cap ≤ cap% specified in §3 |
| D3 | Label quality: >80% samples at confidence ≥0.6 (§6) |
| D4 | Diversity coverage: ≥7 of 14 dimensions represented (§4) |
| D5 | Wild conditions: all applicable §8 requirements met |
| D6 | Cross-head conflicts: no unresolved construct conflicts |

#### MobileNetV4 Heads

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 Bonus | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| MNV4-H1 | orientation_cls | 10 | 7 | 10 | 3 | 2 | 10 | 0 | **42** |
| MNV4-H2 | skew_reg | 10 | 0 | 8 | 6 | 5 | 3 | 0 | **32** |
| MNV4-H3 | resolution_quality_reg | 2 | 8 | 5 | 3 | 2 | 8 | 0 | **28** |

**MNV4-H1 rationale:** D2 partial (old config ratio unknown; Stream 4C rebuild in progress).
D4 low (non-Latin <1% vs. ≥40% target). D5 low (orientation_ambiguous class not labeled).
D6 perfect (no cross-head conflicts for orientation head). Phase 1 CAN bootstrap.

**MNV4-H2 rationale:** D1 full (90,412 ≥ 90,000). D2 zero (79.1% synthetic vs. ≤37.5% cap
— genuine violation, see A.5). D3 partial (conf≥0.7 Hough filter). D6 low (P0-1 SIG-G3-2
dependency; P0-2 skew_score conflict). Phase 1 CAN bootstrap given strong empirical metrics.

**MNV4-H3 rationale:** D1 low (5,499/30,000 = 18%). BLOCKED.

#### SigLIP 2 Group 1 — IQA (6 heads share same dataset)

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| SIG-G1-1 | blur_score | 6 | 10 | 6 | 5 | 0 | 8 | 0 | **35** |
| SIG-G1-2 | noise_score | 6 | 10 | 6 | 5 | 0 | 8 | 0 | **35** |
| SIG-G1-3 | contrast_score | 6 | 10 | 6 | 5 | 0 | 8 | 0 | **35** |
| SIG-G1-4 | skew_score | 6 | 10 | 4 | 5 | 0 | 2 | 0 | **27** |
| SIG-G1-5 | compression_score | 6 | 10 | 6 | 5 | 0 | 8 | 0 | **35** |
| SIG-G1-6 | overall_quality | 6 | 10 | 2 | 5 | 0 | 8 | 0 | **31** |

**IQA rationale:** D1 partial (16.3K Phase 1 hard labels vs. 25K minimum; Phase 2
pseudo-labels at 0%). D2 full (Phase 1 ~100% real). D5 zero (Phase 1B compound sub-split
not assembled). G1-4 D3 low (derivation method undefined — P0-2 conflict). G1-6 D3 low
(VLM SRCC 0.53, gate at 0.65 not met). G1-4 D6 low (construct conflict with geometric
skew — P0-2).

#### SigLIP 2 Group 2 — Script

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| SIG-G2-1 | script_cls | 8 | 7 | 10 | 7 | 6 | 2 | 0 | **40** |

**Script rationale:** D1 high (190K v3 + MDIW13 well above 108K; but Arab 3.78× imbalance).
D2 near-cap (with rebalancing: ~56% synthetic, near 60% cap). D3 full (tier_0_exact for
v3/MDIW13). D4 high (Script dataset has best diversity coverage of all 10). D5 partial
(historical typography ≥5% partially covered via v3 document age). D6 low (Arab imbalance
violates §2 max 3× — P0-6; also Hang/Cher/Cans zeros).

#### SigLIP 2 Group 3 — Geometry (post-correction)

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| SIG-G3-1 | orientation_cls | 8 | 7 | 10 | 3 | 2 | 10 | 0 | **40** |
| SIG-G3-2 | skew_reg | 0 | 5 | 5 | 5 | 5 | 0 | 0 | **20** |

**SIG-G3-2 rationale:** D1 zero (requires separate ±2° narrow-range dataset, ~20K images —
does not exist). D6 zero (P0-1 is the gap for this head). All other dimensions scored 5/10
as "no data / no measurement possible". Complete P0 blocker.

#### SigLIP 2 Group 4 — Handwriting (5 heads share same dataset)

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| SIG-G4-1 | presence_cls | 5 | 8 | 3 | 3 | 2 | 8 | 0 | **29** |
| SIG-G4-2 | legibility_cls | 5 | 8 | 1 | 3 | 0 | 0 | 0 | **17** |
| SIG-G4-3 | content_type_cls | 5 | 8 | 4 | 3 | 4 | 5 | 0 | **29** |
| SIG-G4-4 | presence_reg | 5 | 8 | 6 | 3 | 4 | 3 | 0 | **29** |
| SIG-G4-5 | legibility_reg | 5 | 8 | 2 | 3 | 0 | 0 | 0 | **18** |

**Handwriting rationale:** D1 partial (38,967 dry-run vs. 60K minimum; dry-run ≠ assembled).
D2 near-cap (negatives only from synthetic; positives all real). D3 G4-1 low (KHATT/
CASIA-HWDB/IIIT-INDIC/HKR P0 prerequisites not acquired). D3 G4-2/G4-5 critical-low
(ILLEGIBLE class void + N_A sentinel = 0.0 defect corrupts training). D5 G4-2/G4-5 zero
(ILLEGIBLE ≥5% required = 0 samples). D6 G4-2/G4-5 zero (N_A sentinel defect is a
cross-head conflict propagating through G4-4, G5-2, G5-3).

#### SigLIP 2 Group 5 — Page Attributes (5 heads)

| Head | Task | D1 | D2 | D3 | D4 | D5 | D6 | P0 | **Score** |
|---|---|---|---|---|---|---|---|---|---|
| SIG-G5-1 | capture_cls | 5 | 7 | 5 | 4 | 3 | 6 | 0 | **30** |
| SIG-G5-2 | shadow_reg | 0 | 5 | 0 | 0 | 0 | 8 | 0 | **13** |
| SIG-G5-3 | warping_reg | 0 | 5 | 0 | 0 | 0 | 8 | 0 | **13** |
| SIG-G5-4 | code_cls | 4 | 8 | 7 | 6 | 5 | 0 | 0 | **30** |
| SIG-G5-5 | resolution_quality_reg | 2 | 8 | 5 | 3 | 2 | 6 | 0 | **26** |

**Page attrs rationale:** G5-1: SCANNER_ADF/FAX/CAMERA_PRO near-zero (D1 partial, D3 low
— ADF/FAX heuristics not verified). G5-2/G5-3: 0 assembled (all dimensions zero). G5-4: D6
zero (code_reg → code_cls P0 naming defect). G5-5: shares MNV4-H3 gaps; cascade risk P1-4.

#### Score Summary

| Statistic | Value |
|---|---|
| Mean | 27.0 / 100 |
| Median | 29.0 / 100 |
| Min | 13 / 100 (SIG-G5-2 shadow, SIG-G5-3 warping) |
| Max | 42 / 100 (MNV4-H1 orientation) |
| Heads ≥50 | 0 / 22 |
| Heads ≥30 | 12 / 22 |
| Heads <20 | 4 / 22 (SIG-G4-2, G4-5, G3-2, G5-2/3) |
| Phase 1 bootable (MNV4) | 2 / 22 (MNV4-H1, MNV4-H2) |

---

### A.2 — v3 Completeness Impact Assessment

#### Current GCS State

As of 2026-02-23: **190,485 JPEG images confirmed on GCS** (live `gsutil ls` count).
Generator stopped at 190,485 due to per-script pool exhaustion bug (Arab allocation passed
to every worker). Target was 350K.

**IMPORTANT:** The per-script table below uses `results/v3_per_script_audit.json` which is
**splits.jsonl-based** (pre-planned 350K entries, NOT actual GCS file counts). A live GCS
audit (`--no-use-splits-jsonl`) must run before the fill run to establish accurate baselines.

#### Per-Script Gap Table (splits.jsonl-based estimate)

| Script | ISO | Found | Target | Remaining | Status |
|---|---|---|---|---|---|
| Latin | Latn | 19,407 | 12,962 | 0 | ✅ Above target |
| **Arabic** | **Arab** | **48,955** | **12,962** | **0** | ⚠️ **3.78× IMBALANCE** |
| Devanagari | Deva | 8,721 | 12,962 | 4,241 | ❌ Below |
| Han Simplified | Hans | 24,072 | 12,962 | 0 | ✅ Above |
| Han Traditional | Hant | 14,442 | 12,962 | 0 | ✅ Above |
| Cyrillic | Cyrl | 23,308 | 12,962 | 0 | ✅ Above |
| Japanese | Jpan | 11,909 | 12,962 | 1,053 | ❌ Below |
| **Korean (Hangul)** | **Hang** | **0** | **12,962** | **12,962** | ❌ **ZERO** |
| Thai | Thai | 5,648 | 12,962 | 7,314 | ❌ Below |
| Bengali | Beng | 18,557 | 12,962 | 0 | ✅ Above |
| Gujarati | Gujr | 7,550 | 12,962 | 5,412 | ❌ Below |
| Gurmukhi | Guru | 14,138 | 12,962 | 0 | ✅ Above |
| Kannada | Knda | 10,645 | 12,962 | 2,317 | ❌ Below |
| Malayalam | Mlym | 8,482 | 12,962 | 4,480 | ❌ Below |
| Oriya | Orya | 7,420 | 12,962 | 5,542 | ❌ Below |
| Tamil | Taml | 6,088 | 12,962 | 6,874 | ❌ Below |
| Telugu | Telu | 5,256 | 12,962 | 7,706 | ❌ Below |
| Tibetan | Tibt | 5,741 | 12,962 | 7,221 | ❌ Below |
| Myanmar | Mymr | 5,666 | 12,962 | 7,296 | ❌ Below |
| Khmer | Khmr | 6,602 | 12,962 | 6,360 | ❌ Below |
| Sinhala | Sinh | 5,843 | 12,962 | 7,119 | ❌ Below |
| Lao | Laoo | 9,561 | 12,962 | 3,401 | ❌ Below |
| **Cherokee** | **Cher** | **0** | **12,962** | **12,962** | ❌ **ZERO — no fonts** |
| **Canadian Syllabics** | **Cans** | **0** | **12,962** | **12,962** | ❌ **ZERO — no fonts** |
| Ethiopic | Ethi | 17,608 | 12,962 | 0 | ✅ Above |
| **Georgian** | **Geor** | **8,406** | **12,962** | **4,556** | ⚠️ **RESERVED SCRIPT** |
| Hebrew | Hebr | 6,002 | 12,962 | 6,960 | ❌ Below |

**Splits.jsonl total:** 345,642 planned entries vs. 190,485 actually generated on GCS.

**⚠️ Georgian contamination:** Geor=8,406 in the audit. Georgian is permanently reserved
(§9). It must NOT enter any training manifest. Verify `_validate_no_reserved_scripts()`
catches Geor BEFORE the fill run.

#### Three Blocking Decisions Before Fill Run

**Decision 1: Cherokee (Cher) + Canadian Aboriginal Syllabics (Cans) — Fonts**

- Both at 0 because no font families were confirmed available at generation time
- Run `scripts/audit_font_coverage.py` to test Noto Unified Canadian Syllabics + Cherokee
- Option A (include): expand to 27-class model (or 29 if Armn/Grek also kept)
- Option B (exclude): 25-class model with confirmed font coverage only
- Recommended: Option A (Noto fonts freely available). **Effort: 1 day. Owner: Data Eng.**

**Decision 2: Armenian (Armn) + Greek (Grek) — Keep vs. Delete**

- Per UNIFIED_TRAINING_CORPUS.md §7, Armn/Grek replaced Cher/Cans in actual generation
  (multilingual document bleed from shared font pools). The splits.jsonl audit shows
  Cher=0/Cans=0 because those were the original pre-planned placeholders.
- Run live GCS audit to count Armn/Grek images. If each <1,000: delete. If ≥1,000: keep
  and expand ML class count (update SIGLIP2_MULTITASK_REQUIREMENTS.md class list)
- **Effort: 1 day audit + 1 day schema update. Owner: Data Eng + ML.**

**Decision 3: Kore → Hang Rename — Trivial**

- v3 generator uses `Kore` (language code), audit uses `Hang` (ISO 15924 script code)
- Pure label rename, no data re-generation required
- **Effort: 2 hours find-replace. Owner: Data Eng.**

#### Per-Head v3 Impact (8 affected heads)

| Head | v3 Role | Adequate at 190K Phase 1? | Phase 2 Impact | Resampling Viable? |
|---|---|---|---|---|
| SIG-G2-1 script_cls | Primary (60K weighted) | Partial — Arab imbalance blocks | Imbalance in embedding space | Yes, after Arab cap |
| MNV4-H1 / SIG-G3-1 orientation | Synth component ~20K | Yes — real fills Latin | Non-Latin gap partial | Yes for present scripts |
| MNV4-H2 / SIG-G3-2 skew | Synth ~10K | Yes for MNV4-H2; G3-2 needs new dataset | G3-2 fully blocked | N/A for G3-2 |
| MNV4-H3 / SIG-G5-5 resolution | ~5K from v3 | No — 5.5K total vs. 30K min | V2 algorithm also needed | 5.5K insufficient |
| SIG-G5-2 shadow | Synth ~8K planned | No — 0 total assembled | GPU labeling blocks real | N/A — 0 assembled |
| SIG-G5-3 warping | Synth ~5K planned | No — 0 total assembled | GPU labeling blocks real | N/A — 0 assembled |
| SIG-G5-1 capture | ~7.5K synthetic class | Partial — ADF/FAX near-zero | Heuristic labeling pending | No for ADF/FAX |
| SIG-G4-x negatives | ~5K printed negatives | Yes for negatives only | ILLEGIBLE void blocks | N/A |

**Resampling vs. fill run at Phase 2:**

- Resampling from 190K is viable for Phase 1 bootstrap (orientation, skew).
- At Phase 2: Hang=0, Cher=0, Cans=0 scripts have NO images to resample from. Per-script
  floor must be ≥1,000 unique images before resampling to avoid memorization. Fill run
  is a hard prerequisite for Phase 2.
- Fill run: 5–8 hours A100, 15–25 hours CPU. Can run concurrently with Phase 1 bootstrap.

---

### A.3 — Diversity Dimension Matrix (10 × 14)

**Legend:** ✅ Adequate | ⚠️ Partial | ❌ Absent

| Dimension | Orient. | Skew | Res.Q | IQA | Script | Handwr. | Capture | Shadow | Warping | Code |
|---|---|---|---|---|---|---|---|---|---|---|
| 1. capture_method | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ✅ | ❌ | ❌ | ⚠️ |
| 2. domain | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ❌ | ❌ | ⚠️ |
| 3. script_code | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| 4. script_family | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| 5. resolution | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ⚠️ |
| 6. text_density | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| 7. layout_type | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| 8. content_flags | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| 9. degradation | ⚠️ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| 10. content_type | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ |
| 11. handwriting | ❌ | ⚠️ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| 12. paper_size | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| 13. color_mode | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
| 14. document_age | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |

**✅ counts per dataset:** Script=9, Code=5, IQA=2, Capture=2, Orientation=1, Skew=1,
ResQ=1, Handwriting=2, Shadow=0, Warping=0.

**Critical ❌ cells (dataset is sole source for head):**

- **Orientation × script_code:** Orientation is the sole training source for MNV4-H1
  non-Latin orientation. At non-Latin <1%, the head will fail systematically on non-Latin
  script pages in production. P0 blocker for Stream 4C rebuild.
- **Resolution Quality × script_code:** Resolution head has no CJK. Script-aware inference
  adjustments (CJK ×0.55) are applied at inference, but the model learns no pattern.
- **Shadow/Warping × all 14:** Both datasets at 0 assembled. Zero training signal on all
  dimensions simultaneously.

---

### A.4 — Wild Conditions Checklist

| Requirement (§8) | Applicable Heads | Status | Verdict |
|---|---|---|---|
| Compound distortion ≥10% of IQA Phase 1B sub-split | SIG-G1-x | Phase 1B sub-split NOT assembled | ❌ FAIL |
| Multi-column ≥20% of skew set | MNV4-H2 | Claimed present; unverified at scale (Gap 7) | ⚠️ AT RISK |
| Ambiguous orientation ≥2% labeled | MNV4-H1 | orientation_ambiguous class absent in 50K | ❌ FAIL |
| RTL/TTB scripts ≥5% of orientation/script | MNV4-H1, SIG-G2-1 | Non-Latin <1% orientation; Hang=0 in script | ❌ FAIL |
| Combined skew+warping ≥5% of skew set | MNV4-H2 | No count available; target ≥3% minimum | ⚠️ AT RISK |
| Modern CIS flatbed ≥1,500 samples | SIG-G5-1 | Gap 8 explicitly unresolved; RVL-CDIP is 1990s CCD | ❌ FAIL |
| Book spine shadows present | SIG-G5-2 | Gap 5 explicitly unresolved; sd7k flat-document only | ❌ FAIL |
| ILLEGIBLE class ≥5% handwriting (≥1,000) | SIG-G4-2, G4-5 | 0 ILLEGIBLE samples (P0-4) | ❌ FAIL |

**Summary: 0 of 8 wild conditions confirmed met. 6 FAIL, 2 AT RISK.**

---

### A.5 — Synthetic Mixing Cap Audit

| Dataset | Ideal Cap | Current Ratio | Assessment | Classification |
|---|---|---|---|---|
| Orientation | ≤40% | Unknown (old config) | AT RISK | Incidental — Stream 4C rebuild in progress |
| Skew | ≤37.5% | **79.1% synthetic** | ❌ VIOLATION | Incidental — acquiring 50K+ natural scans at conf≥0.7 is difficult |
| Resolution Quality | ≤17% | ~6% synthetic (DIQA-5000 mostly real) | ✅ Compliant | — |
| IQA | Phase 2 pseudo ≤50% weight | Phase 1 ~100% real | ✅ Phase 1 compliant | Phase 2 pseudo not yet assembled |
| Script Detection | ≤60% | ~56–60% with rebalancing | ⚠️ Near cap | Borderline — MDIW13 real component is small (753 images) |
| Handwriting | Negatives only (synthetic) | ~56% of dry-run (negatives) | ⚠️ Near cap | Spec says negatives-only from synthetic; positives 100% real |
| Capture Method | Strict 0% for production classes | ~0% (v3 labeled SYNTHETIC sub-class) | ✅ Compliant | v3 maps to SYNTHETIC class, not contaminating SCANNER/CAMERA |
| Shadow | ≤50% | 0 assembled | N/A — BLOCKED | Will violate ≥50% real once Tier A synth generates before Tier B |
| Warping | ≤30% | 0 assembled | N/A — BLOCKED | Same as shadow |
| Code Detection | ~50% | 8,613 dry-run (~50% positive from generation) | ⚠️ Near cap | Dry-run only; actual generation pending |

**Skew cap definitional resolution (required by plan):** The 90K skew dataset is 79.1%
synthetic by image source. The §3 ideal cap (≤37.5%) is a structural target assuming
adequate natural scans at conf≥0.7 are acquirable. The 18,914 natural-scan images use
tier_3_heuristic labels (Hough+projection, conf≥0.7) — these ARE "real" images under §3
(real image source, lower-confidence labels). The cap measures real:synth by image SOURCE,
not label tier. Therefore the 79.1% IS a genuine cap violation.

However, strong empirical metrics (MAE 0.837°, SRCC 0.936, orient_acc 99.5%) suggest the
model learned effectively. Classification: **Incidental violation** — acquiring 50K+ natural
scans at conf≥0.7 is impractical without new real-scan datasets. Recommended action: accept
for Phase 1; document violation and mitigation; reassess at Phase 2 with additional natural
scan sources.

---

### A.6 — Cross-Head Conflict Matrix

Six cross-head conflicts independently identified from first-principles reading of head specs:

#### CF-1 — P0: IQA skew_score vs. Geometric skew_reg (SIG-G1-4 ↔ MNV4-H2/SIG-G3-2)

Both heads potentially draw from the same natural-scan label source (Hough+projection
ensemble). IQA skew_score measures "how much skew degrades quality" (0–1 severity). Geometric
skew_reg measures "what angle to correct" (±10°). If skew_score is derived as
`normalized_abs(angle)`, the two heads share perfectly correlated supervision — IQA learns
angle, not perceptual severity.

**Required resolution (choose one):**

- Option A: Human perceptual rating on 500 images — true tier_1, orthogonal to angle
- Option B: Augraphy synthetic skew severity parameter — tier_0_exact, synthetic only
- Option C: `normalized_abs(angle)/max_angle` — acceptable if documented as monotone proxy

**Gap ID:** P0-2. **Effort:** 3–5 days. **Owner:** ML + Labeling.

#### CF-2 — P0: N_A Sentinel = 0.0 Defects (G4-2, G4-4, G4-5, G5-2, G5-3)

N_A (not applicable) is currently encoded as `0.0` in regression heads. This maps to
"illegible" for legibility_reg, "no shadow" for shadow_reg, "no warping" for warping_reg.
Every printed-only document in the handwriting dataset contributes a gradient signal teaching
legibility_reg that "printed text = illegible score 0.0". This permanently corrupts the
regression heads if not fixed before dataset assembly.

**Required fix:** Encode N_A as `-1.0`. Apply masked loss (weight=0.0) on N_A samples.
Update all label schema and manifest generators BEFORE assembling handwriting, shadow,
warping datasets. **Effort:** 1 day schema + 1–2 days manifest regen. **Owner:** Data Eng.

#### CF-3 — P0: code_reg Naming Defect (SIG-G5-4)

Head named `code_reg` but training signal is boolean (has_code: 0/1). Regression with MSE
is wrong for binary classification. Sigmoid + BCE is required. Training with wrong loss
produces gradient instability and poor boundary calibration even if the output scale
accidentally converges to 0–1.

**Required fix:** Rename to `code_cls` in: SIGLIP2_MULTITASK_REQUIREMENTS.md,
train_siglip2_multitask.py, head registry. **Effort:** 2 hours. **Owner:** ML.

#### CF-4 — P1: v3 Shared-Backbone Correlated Failure (7 of 10 datasets)

7 of 10 training datasets use v3 as synthetic backbone: orientation, shadow, warping, script,
IQA Phase 2 pseudo-labels, resolution quality, handwriting negatives. A rendering bug, font
gap, or DPI bias in v3 propagates correlated errors to all 7 tasks simultaneously.

**Required fix:** Document explicitly in §7 of UNIFIED_TRAINING_CORPUS.md. Add v3-isolation
monitoring: if script accuracy on any class drops >10% relative, halt all v3-derived training
until root cause identified. **Gap ID:** P1-9. **Effort:** 2 days. **Owner:** ML.

#### CF-5 — P1: Capture Method Class Expansion Risk (SIG-G5-1)

7-class capture classifier trained now will encounter CamScanner-processed documents in
production. CamScanner applies adaptive binarization + perspective correction — no existing
class models this. The model will misclassify CamScanner docs into nearest neighbor
(CAMERA_SMARTPHONE or SCANNER_FLATBED) without any abstention signal.

**Required fix:** Either add 8th class before first training run (2,500 CamScanner samples)
or document explicit abstention mechanism via Energy Score. **Gap ID:** P1-1. **Effort:**
3–5 days for acquisition + labeling. **Owner:** Data Eng.

#### CF-6 — P0: SIG-G3-2 Domain Boundary (Post-Correction Skew)

SIG-G3-2 must train on images that REPRESENT the output of MNV4-H2 (i.e., images already
deskewed to within ±2°). No such paired dataset exists. The current 90K skew dataset covers
full ±45° range. SIG-G3-2 training requires a new ±2° narrow-range dataset — images that
have been corrected to near-zero skew, used to teach sub-degree residual detection.

Additionally, SIG-G3-2 serves as teacher signal for MNV4-H2 distillation — creating a
circular dependency requiring MNV4-H2 training to complete before SIG-G3-2 training can
produce meaningful teacher signals.

**Gap ID:** P0-1. **Effort:** 5–7 days. **Owner:** Data Eng.

---

### A.7 — Gap Registry Summary

Full registry with acceptance criteria is maintained in UNIFIED_TRAINING_CORPUS.md §Gap
Registry (authoritative source). This section adds effort and owner annotations.

#### P0 Blockers (10 gaps — must resolve before Phase 2 training)

| ID | Description | Effort | Owner | Dependency |
|---|---|---|---|---|
| P0-1 | SIG-G3-2: no ±2° narrow-range dataset | 5–7 days | Data Eng | v3 fill complete |
| P0-2 | IQA skew_score vs geometric skew_reg construct conflict | 3–5 days | ML + Labeling | Option A/B/C decision |
| P0-3 | VLM SRCC 0.53 — halt/fallback undefined | 1 day (decision) + 3 days (re-validation) | ML | Prompt v2.0 ready |
| P0-4 | ILLEGIBLE class void (0 samples) | 10–15 days | Data Eng | KHATT/Muharaf access |
| P0-5 | Shadow/warping L2 severity labeling not run | 3–5 days GPU VM | Data Eng | GPU VM access |
| P0-6 | Arab 3.78× imbalance violates §2 max 3× | 1 day (resampling config) | Data Eng | None |
| P0-7 | IQA Phase 1A undersized: 16.3K vs. 50–100K | 15–20 days | ML + Labeling | OHR-Bench access |
| P0-8 | OOD-Mixed 9a-1/9a-2 must be derived (P0 priority) | 1–2 days | Data Eng | None — zero cost |
| P0-9 | OOD-Domain smoke test (100 ArXiv PDFs) | 1 day | Data Eng | None — zero cost |
| P0-10 | Energy Score + temperature scaling must replace entropy ≥0.7 | 3–5 days | ML | Val set for calibration |

#### P1 Summary (12 gaps — required before final release)

P1-1: CamScanner 8th class / abstention (3–5d) | P1-2: Wild conditions 6 missing scenarios
(10–20d) | P1-3: OOD 12K–15K scale-up or directional-only declaration (2–4 months) |
P1-4: MNV4-H3→G5-5 cascade OOD sub-source (2–3d) | P1-5: Clean-novel false positive OOD
(2–3d) | P1-6: ILLEGIBLE OOD floor revised to OSR metric (1d) | P1-7: Hybrid vector/raster
PDF OOD scenario (2–3d) | P1-8: Albumentations formally committed for OOD-Degradation (1d) |
P1-9: v3 correlated failure risk documented (2d) | P1-10: content_type OCR circular
dependency resolved (3–5d) | P1-11: OOD-Geometry split into abstention-rate+correction-accuracy
(1d) | P1-12: OOD-Composite category feasibility assessment (3–5d).

#### P2 Summary (5 gaps — V2 improvements)

P2-1: ODIN (input perturbation + temperature scaling) | P2-2: Mahalanobis distance for
head-specific overconfidence | P2-3: Active learning for OOD sampling | P2-4: ±0.5°
ultra-narrow skew dataset | P2-5: Resolution Quality V2 algorithm (Sauvola + projection
profiles) on v3.

---

## Part B: Multi-Model Consensus — Training Corpus

### Consensus Methodology

- **Null hypothesis:** "The unified training corpus is sufficient to train all 22 heads to
  published accuracy targets."
- **Models / stances:** Gemini 2.5 Pro (against), Gemini 3 Pro Preview (against), DeepSeek
  R1-0528 (against), Grok 4 (for), GPT-5.2 (neutral — empty response)
- **Steps:** 7 total (step 1 = Phase A findings; steps 2–5 = model responses; step 6 =
  net-new synthesis; step 7 = final synthesis)
- **Continuation ID:** `8dd57ce9-a8f7-4921-84bf-4450de589f18`
- **GPT-5.2:** Empty response (4th consecutive across sessions). Logged per plan; 4 valid
  models are sufficient for consensus validity.

**Note on Phase B verbatim responses:** Phase B was completed in the prior session (before
context summarization). Verbatim model verdicts are stored in the PAL consensus tool under
the continuation ID above. The following are the key findings as captured in the session
analysis.

### Model Responses — Training Corpus (Summarized)

**Gemini 2.5 Pro (against, ~9/10):** Null hypothesis REJECTED. IQA dataset critically
undersized (16.3K vs. 50–100K industry standard for 101M-parameter multi-task model).
Compound distortion wild condition is the most consequential single gap — single-degradation
training produces 15–25% metric drop on real-world compound inputs. v3 Arab imbalance at
3.78× will over-represent Arabic in the shared 768-dim backbone embedding, degrading ALL
non-Arabic heads. Weighted resampling from 190K viable for Phase 1 but cannot substitute
for Phase 2 fill run. KHATT/CASIA-HWDB license requests should begin immediately.

**Gemini 3 Pro Preview (against, ~9/10):** Null hypothesis REJECTED. Six acceptance criteria
failing simultaneously is not marginal — it represents foundational incompleteness. ILLEGIBLE
class void is a hard categorical blocker: a head that must output ILLEGIBLE predictions with
zero training examples will never output that class (weights undefined). Shadow and warping
at 0 assembled should be explicitly excluded from Phase 2 training scope — including them
would pollute the multi-task loss with undefined gradients. Phase 1B compound sub-split is
not optional: without it, the 6 IQA heads learn independent single-degradation functions
and will fail on real production documents.

**DeepSeek R1 (against, ~8/10):** Null hypothesis REJECTED. Skew 79.1% synthetic is the
most pressing structural concern beyond obvious gaps — Sim2Real gap at this ratio produces
10–20% accuracy degradation on production natural scans vs. synthetic test images. N_A
sentinel = 0.0 is a subtle but corrupting defect: every printed document in handwriting
dataset teaches legibility_reg that "printed text = illegible". code_reg naming defect must
be caught before training — wrong loss function degrades calibration even if output scale
accidentally converges. Phase 1 smoke test minimum: orientation + skew + 3 OOD P0 items.

**Grok 4 (for, ~7/10):** Null hypothesis conditionally endorsed (design is sound; assembly
is incomplete). Phase 1 MNV4 bootstrap can proceed with existing datasets. Skew Sim2Real
violation partially mitigated by conf≥0.7 quality filter. ILLEGIBLE acquisition (Muharaf
damaged + COCO-Text illegible) represents 5–10 days of effort, not months. Recommended
phased execution plan: start heads that can train now while assembling others in parallel.

**GPT-5.2 (neutral):** Empty response. Logged.

### Synthesis — Training Corpus

**Consensus verdict: REJECTED (4/4 valid models; Grok 4's conditional endorsement
acknowledges assembly incompleteness, making it a qualified rejection).**

**Agreement across all 4 models:**

- Phase 1 MNV4-H1 (orientation) and MNV4-H2 (skew) CAN bootstrap training with acknowledged limitations
- SIG-G3-2 is a complete blocker (no narrow-range dataset — not a labeling gap but a new dataset)
- Shadow and warping (0 assembled) must be excluded from Phase 2 training scope until assembled
- ILLEGIBLE class void is a genuine hard blocker for SIG-G4-2 and SIG-G4-5
- v3 Arab imbalance (3.78×) must be corrected before any script detection training run

**Disagreement:**

- Severity of skew Sim2Real: Gemini models flag as critical; Grok 4 accepts as engineering tradeoff
- Phase 2 sequencing: DeepSeek+Geminis prefer sequential (resolve P0s first); Grok 4 prefers parallel

### Net-New Issues from Phase B Consensus

The following issues were not present in Phase A independent analysis:

1. **Arab imbalance backbone effect:** v3 Arab at 3.78× will over-represent Arabic visual
   features in the shared 768-dim embedding space, degrading ALL 16 SigLIP heads — not just
   script detection. This makes Arab cap (P0-6) a cross-cutting blocker, not a single-head fix.

2. **Phase 2 gradient contamination:** Including shadow/warping (0 assembled) in Phase 2
   multi-task training wastes compute and may corrupt multi-task loss. These heads must be
   explicitly EXCLUDED from Phase 2 until assembled.

3. **Skew Sim2Real expected magnitude:** Current test MAE of 0.956° on 79.1% synthetic test
   set likely underestimates production MAE by 0.1–0.4°. The 3× natural scan deficit is the
   primary risk factor.

4. **KHATT urgency:** Academic license for KHATT can take 2–4 weeks. License request must
   begin IMMEDIATELY (today), running in parallel with Phase 1 bootstrap training.

5. **code_cls calibration corpus:** Even after rename fix, the model needs a calibration
   dataset reflecting production code prevalence for post-training sigmoid calibration.

6. **Phase 1 smoke test minimum:** orientation (50K) + skew (90K) + 3 OOD P0 items
   (P0-8, P0-9 at zero cost + P0-10 Energy Score implementation) enables full MNV4
   end-to-end validation before committing to Phase 2 assembly timeline.

---

## Part C: OOD Catalog Review

### C.1 — Statistical Adequacy per Category

Statistical minimum for directional evaluation (95% CI ±7%, worst-case p=0.5): n ≥ 196 ≈ 200 per head.

| Category | Target | Primary Heads | Images/Head | CI Width | Verdict |
|---|---|---|---|---|---|
| OOD-Script | 1,520+ | ~6 | 253 | ±6.2% | ⚠️ Borderline |
| OOD-Geometry | 1,600+ | ~4 | 400 | ±4.9% | ✅ Adequate |
| OOD-Capture | 1,200+ | ~8 | 150 | ±8.0% | ❌ Directional only |
| OOD-Degradation | 1,600+ | ~9 | 178 | ±7.3% | ❌ Directional only |
| OOD-Handwriting | 1,000+ | ~5 | 200 | ±7.1% | ⚠️ Borderline |
| OOD-Resolution | 800+ | ~2 | 400 | ±4.9% | ✅ Adequate |
| OOD-Domain | 2,200+ | ~15 | 147 | ±8.9% | ❌ Directional only |
| OOD-Code | 400+ | 1 (SIG-G5-4) | 400 | ±4.9% | ✅ For G5-4 only |
| OOD-Mixed | 700+ | ~22 | 32 | ±17.4% | ❌ Very directional |
| **Total** | **~11,020+** | **22** | **501/head avg** | — | **Below 550/head spec** |

**Current status: 0 of 11,020+ images acquired.** All results are directional until minimums
are reached. Phase 1 minimum viable set (300 images, zero cost) is actionable immediately.

---

### C.2 — Head Coverage Completeness

All 22 heads have at least one OOD category mapping. Coverage gaps:

- **SIG-G4-3 (content_type_cls):** Only OOD-Handwriting covers it. No dedicated OOD for
  specialized content type (math notation, musical scores). Weakest single-head coverage.
- **SIG-G5-2 (shadow_reg) and SIG-G5-3 (warping_reg):** No dedicated shadow or warping OOD
  sub-source. Both rely on compound OOD-Degradation scenarios that may not target severity
  regression failure modes specifically. Recommend dedicated sub-sources (100–200 images each).
- **SIG-G4-2 (legibility_cls):** OOD-Handwriting covers it, but ILLEGIBLE sub-source (20+
  pages target) is statistically insufficient for the most critical failure mode.

---

### C.3 — Missing Production Failure Modes

Identified independently from pipeline architecture:

**CF-1 (P0/P1): Two-model cascade failures.** MNV4-H3 → SigLIP G5-5 resolution cascade is
in OOD-Mixed 9e-1 (P0). MNV4-H1 CONFIDENTLY-WRONG orientation (not symmetric, not
abstaining — just wrong) is NOT covered. MNV4-H2 wrong-correction cascade (estimates +2°
when true skew is +5°, partially corrects, then SigLIP receives a WORSE image) is NOT
covered in OOD-Mixed. Both are P1 gaps.

**CF-2 (P1): v3 class count decision impact on OOD-Script.** If Geor (Georgian) enters
training via v3 (8,406 in audit), it can no longer serve as an OOD anchor. The
`_validate_no_reserved_scripts()` guard must be verified before fill run.

**CF-3 (P1): CamScanner capture mode missing.** No OOD category covers CamScanner-processed
documents. Systematic misclassification will be invisible in evaluation.

**CF-4 (P1): Mixed-script pages.** Pages with Latin+Arabic or Latin+CJK side-by-side produce
confident but arbitrary single-class predictions from SIG-G2-1. OOD-Script does not cover
this failure mode explicitly.

**CF-5 (P0): ILLEGIBLE interaction with routing.** With 0 ILLEGIBLE training samples,
SIG-G4-2 will never output high legibility degradation signals. Documents routing to
ocr_fast when they should route to vision_advanced become a silent production failure.

---

### C.4 — Entropy/Rejection Calibration Assessment

The OOD catalog (v3.1.0) correctly replaces `entropy ≥0.7` with **Energy Score + temperature
scaling**. This is the right method for transformer models (Liu et al. 2020; energy scores
are theoretically grounded as log-partition function approximations, unlike raw entropy
which depends on logit scale).

**Calibration gaps (identified from first principles):**

1. **Missing calibration corpus (P0):** Temperature T and energy threshold require a
   held-out calibration set NOT used in OOD evaluation. The OOD catalog defines the
   rejection method but does not specify the calibration dataset. Required: ~1,000 images
   from the reserved pool (never trained on, not OOD-designated), covering in-distribution
   domain diversity.

2. **MNV4-H1 softmax abstention (P0 — confirmed by Phase D consensus, 3/4 models):** Raw
   softmax confidence <0.9 for symmetric-document abstention fails because transformers are
   structurally overconfident on OOD inputs. Symmetric documents (blank, figure-only,
   palindromic tables) often trigger 0.99 softmax confidence on the wrong class. Energy
   Score must gate MNV4-H1 abstention.

3. **ODIN (P2):** Temperature scaling + input perturbation adds robustness against subtle
   in-distribution shifts at the cost of one additional forward pass. Recommended for V2
   after Phase 1 baseline is established.

4. **Mahalanobis distance (P2 — confirmed by DeepSeek R1):** Head-specific overconfidence
   (calibrated overall but overconfident in specific embedding directions) requires
   feature-space detection. Particularly valuable for script detection (19 classes with
   varying inter-class embedding distances). Store per-class mean embeddings at training time.

---

### C.5 — OOD Floor Audit

| Head | OOD Floor | Training Class Status | Verdict |
|---|---|---|---|
| MNV4-H1 orientation | ≥85% abstention on symmetric inputs | 0 orientation_ambiguous samples | ❌ INVALID if using softmax — switch to Energy Score |
| MNV4-H2 skew | ≥88% within ±1° on high-skew inputs | 90K training, conf≥0.7 | ✅ Plausible — monitor per-bucket MAE |
| MNV4-H3 res.quality | MAE <0.1 on OOD resolution | 5.5K — insufficient | ⚠️ Possible only if V2 algorithm applied |
| SIG-G1-x IQA (5 heads) | VQualA ≥0.92 on compound OOD | Compound sub-split not assembled | ❌ UNKNOWN — compound not in training |
| SIG-G1-6 overall_quality | SRCC ≥0.65 on OOD documents | VLM SRCC 0.53 — gate not met | ❌ Not achievable until gate met |
| SIG-G2-1 script | ≥85% unseen fonts within known scripts | 5+ font families per v3 script | ✅ Plausible — monitor per-script OOD accuracy |
| SIG-G2-1 open-set | <5% false positive on reserved scripts | Mong/Syrc not in training; Geor in v3 audit | ⚠️ Geor contamination risk — verify guard |
| SIG-G3-2 post-skew | MAE <0.3° on ±2° OOD | NO TRAINING DATASET EXISTS | ❌ UNDEFINED — P0-1 blocks entirely |
| **SIG-G4-2 ILLEGIBLE** | **≥40% (or was 65%) accuracy** | **0 ILLEGIBLE samples** | ❌ **INVALID — classification accuracy undefined with void class** |
| SIG-G4-x other | Per-class targets | Partial dry-run | ⚠️ Unknown until assembled |
| SIG-G5-1 capture | ≥82% on novel capture variants | ADF/FAX/CAMERA_PRO near-zero | ❌ Near-zero class → near-zero OOD accuracy |
| SIG-G5-2 shadow | MAE <0.1 on extreme shadows | 0 assembled | ❌ UNDEFINED |
| SIG-G5-3 warping | MAE <0.1 on extreme warping | 0 assembled | ❌ UNDEFINED |
| SIG-G5-4 code_cls | Precision >0.8 at >0.5 threshold | 8.6K dry-run, not generated | ⚠️ Plausible after generation + rename fix |
| SIG-G5-5 res.quality | Within 0.05 of MNV4-H3 | Shares MNV4-H3 gaps | Same as MNV4-H3 |

**ILLEGIBLE floor correction (P0, confirmed by 2 Phase D models):**
Classification accuracy on ILLEGIBLE with 0 training samples = undefined (model never
predicts ILLEGIBLE). The correct metric is Open-Set Recognition: Energy Score rejection
rate on ILLEGIBLE handwriting samples. **Revised floor: Energy Score rejection rate ≥70%**
on OOD ILLEGIBLE samples. This is achievable even with 0 training samples if the Energy
Score gate is correctly calibrated. ILLEGIBLE handwriting will naturally produce high
uncertainty in a model trained on legible handwriting.

---

### C.6 — OOD Gap Registry

| OOD Gap | Priority | Description | Action |
|---|---|---|---|
| OOD-G1 | P0 | 0 of 11,020+ images acquired | Begin immediately with zero-cost P0 items |
| OOD-G2 | P0 | ILLEGIBLE floor uses invalid metric (classification accuracy vs. OSR Energy Score) | Change floor spec to Energy Score rejection rate ≥70% |
| OOD-G3 | P0 | MNV4-H1 abstention uses raw softmax — Energy Score required | Update MNV4-H1 inference before production deployment |
| OOD-G4 | P0 | Calibration corpus not defined for Energy Score temperature scaling | Add ~1,000-image held-out calibration set definition to catalog |
| OOD-G5 | P1 | MNV4-H2 wrong-correction cascade not covered | Add OOD-Mixed sub-source: 50 images at +2° estimated, actual +5° |
| OOD-G6 | P1 | MNV4-H1 confidently-wrong (non-symmetric) orientation cascade | Add OOD-Mixed sub-source: challenging orientation images with high-confidence wrong predictions |
| OOD-G7 | P1 | Georgian contamination risk (Geor=8,406 in v3 audit) | Verify `_validate_no_reserved_scripts()` before ANY training run |
| OOD-G8 | P1 | Mixed-script pages not covered in OOD-Script | Add 100–200 mixed-script pages to OOD-Script |

---

## Part D: Multi-Model Consensus — OOD Catalog

### Consensus Methodology

- **Null hypothesis:** "The OOD evaluation corpus specification is adequate to validate all
  22 model heads for production deployment."
- **Models / stances:** Gemini 2.5 Pro (against), Gemini 3 Pro Preview (against), DeepSeek
  R1-0528 (against), Grok 4 (for), GPT-5.2 (neutral — empty)
- **Steps:** 7 total. **Continuation ID:** `d679c9e0-ac57-44c9-b66d-72519f3bdf70`

### Model Responses — OOD Catalog (Verbatim)

#### Gemini 2.5 Pro (against, 9/10)

> **Verdict:** The specification is exceptionally thorough but ultimately inadequate to
> validate all 22 heads for production, as several OOD categories fall short of the stated
> statistical requirements and coverage for specific failure modes remains ambiguous.
>
> The plan is technically sound, employing modern best practices like Energy Score-based
> rejection and pHash deduplication. However, its feasibility is questionable due to the
> immense implementation effort. With a target of 12,000–15,000 images and a current status
> of "0 acquired across all 9 categories," the acquisition and annotation represent a
> monumental task posing a significant project risk.
>
> **Key takeaways:**
>
> - **Reject the Null Hypothesis.** OOD-Code target of 400+ images fails its own 500/head
>   criterion when divided across multiple heads.
> - Prioritize critical voids: ILLEGIBLE sub-source targeting ~20 images needs >500 for
>   statistical significance.
> - OOD-Domain and OOD-Mixed lack mechanisms to ensure balanced per-head coverage.
> - High acquisition risk (0 images acquired) is the most significant threat to the project.

#### Gemini 3 Pro Preview (against, 9/10)

> **Verdict:** The OOD Catalog specification is technically robust in its failure mode
> design but operationally fragile, relying on a daunting acquisition target (12,000+
> images) that contradicts current zero-inventory reality, and contains a theoretical flaw
> in evaluating "void" classes using standard accuracy metrics.
>
> The logic assumes distinct image sets for every head. OOD-Domain and OOD-Mixed images
> often stress multiple heads simultaneously. By treating 22 heads as requiring disjoint
> OOD sets (22 × 550 images), the specification likely inflates the acquisition target by
> 2–3×, creating an unnecessary blocker. The actual target may be 4,000–6,000 well-chosen
> images.
>
> **Defect in SIG-G4-2 ILLEGIBLE floor:** A class with zero training examples has undefined
> weights. The model cannot predict this class. Evaluating a void class requires an
> Open-Set Recognition metric (Energy Score rejection rate), NOT classification accuracy.
>
> **MNV4-H1 cascade risk:** Raw Softmax confidence for abstention fails — deep classifiers
> are notoriously overconfident on OOD inputs. Energy Score required for MNV4-H1.
>
> **Key takeaways:**
>
> - Redefine ILLEGIBLE evaluation to OSR metric.
> - Optimize sample efficiency: recalculate 12K target accounting for multi-head coverage.
> - Enforce Energy Score on MNV4-H1.
> - Mask irrelevant heads per OOD category to speed labeling.

#### DeepSeek R1-0528 (against, 7/10)

> **Verdict:** The OOD catalog specification is scientifically rigorous and covers all
> critical failure modes for the 22 heads, but its adequacy for production validation is
> compromised by acquisition delays, statistical power gaps, and unresolved calibration
> challenges for multi-head transformers.
>
> Energy Score calibration requires a held-out set and temperature scaling implementation
> not verified in codebase. Per-head floors (e.g., SIG-G4-2 ILLEGIBLE 40% floor) assume
> class-void handling not tested in current training. Mongolian/Syriac/Georgian reservation
> is appropriate — they should serve as OOD anchors (confirmed).
>
> **Key takeaways:**
>
> - Acquire P0 images immediately: 9a-1 (100 symmetric docs) and OOD-Domain smoke test
>   (100 ArXiv PDFs) to unblock cascade validation.
> - Revise monolithic metrics: split OOD-Geometry into abstention-rate (≥85%) and
>   correction-accuracy (≥88%).
> - Mahalanobis distance on feature embeddings should complement Energy Score (P2-2).
> - Validate Energy Score calibration on reserved scripts BEFORE full acquisition.

#### Grok 4 (for, 8/10)

> **Verdict:** The OOD evaluation corpus specification is adequate for validating all 22
> model heads, as it provides comprehensive per-head performance targets, statistical scaling,
> and category-specific designs that align with production needs, though actual acquisition
> remains pending.
>
> The specification is technically achievable. Active learning from production inference
> could reduce manual acquisition burden by 20–30%. P0-blocking images (9a-1 symmetric
> docs, 9a-2 extreme perspective) are derivable from existing data at zero cost.
>
> **Key takeaways:**
>
> - Prioritize scaling to 12,000+ images for rigorous per-head validation.
> - Implement Energy Score + temperature scaling immediately.
> - ILLEGIBLE floor of 40% is defensible for class voids, focusing on open-set baselines.
> - Derive OOD-Mixed sub-sources from existing data to accelerate cascade failure coverage.

#### GPT-5.2 (neutral) — EMPTY RESPONSE

No verdict returned. Fourth consecutive empty response across multiple sessions. Logged per
plan instructions. Does not affect consensus validity.

### Synthesis — OOD Catalog

**Consensus verdict: REJECTED (3/4 valid models; Grok 4 endorses design with zero
acquisition, making endorsement conditional).**

**Agreement (all 4 models):**

1. Energy Score + temperature scaling is the correct OOD detection method for transformers
2. Zero acquisition (0/12K+ images) makes any statistical validation impossible
3. ILLEGIBLE OOD floor metric must change (classification accuracy invalid for void class)
4. Reserved scripts (Mong/Syrc/Geor) should serve as OOD anchors — confirmed appropriate
5. Phase 1 minimum viable OOD set (~300 images) derivable at zero cost from existing data

**Disagreement:**

- Acquisition target: Gemini 3 Pro argues 12K inflated 2–3×; DeepSeek accepts 12K; Grok
  prefers active learning
- ILLEGIBLE floor: Grok 4 considers 40% "defensible for class voids"; Gemini 3 Pro and
  DeepSeek reject classification accuracy as the metric

### Net-New Issues from Phase D Consensus

1. **NET-NEW-D1 (P0):** ILLEGIBLE floor metric invalid — confirmed by 3 independent models.
   Change to OSR Energy Score rejection rate ≥70%.

2. **NET-NEW-D2 (P0):** MNV4-H1 softmax overconfidence for symmetric-document abstention —
   confirmed by 2 models. Energy Score must gate MNV4-H1 abstention.

3. **NET-NEW-D3 (P2):** 12K–15K target may be 2–3× inflated. Recalculate per-category math
   accounting for multi-head per-image coverage. Actual effective target may be 4–6K
   well-chosen images.

4. **NET-NEW-D4 (P1):** OOD-Domain/Mixed lack per-head balanced coverage mechanism. Without
   this, some heads may be effectively untested despite aggregate image counts appearing
   sufficient.

5. **NET-NEW-D5 (P2):** Mahalanobis distance as P2 complement — particularly valuable for
   script detection (19 classes, varying inter-class distances).

6. **NET-NEW-D6 (P0):** Phase 1 minimum viable OOD = 300 images at zero acquisition cost.
   100 symmetric/ambiguous docs (9a-1) + 100 extreme-perspective docs (9a-2) + 100 ArXiv
   PDFs (OOD-Domain). All derivable from existing labeled data or freely available.

---

## Part E: Consolidated Action Plan

### Phase 1 Readiness — MobileNetV4 Bootstrap

**Status: PARTIALLY READY** (2 of 3 MNV4 heads can train)

**Can train now:**

- MNV4-H1 orientation_cls (50K exists; non-Latin composition gap acknowledged)
- MNV4-H2 skew_reg (90K exists; 79.1% synthetic cap violation documented; empirical metrics validated)

**Blocked:**

- MNV4-H3 resolution_quality_reg (5,499 vs. 30,000 minimum)

**Phase 1 prerequisite schema fixes (complete before FIRST training run, ~1 week):**

1. `code_reg` → `code_cls` rename in all files (2 hours)
2. N_A sentinel 0.0 → -1.0 in handwriting label schema (1 day)
3. Arab cap ≤13K in `prepare_multitask_datasets.py script` sub-command (1 day)
4. Energy Score implementation for MNV4-H1 abstention (3 days)
5. Derive Phase 1 minimum OOD set: 300 images zero-cost (1–2 days)

---

### Phase 2 Readiness — SigLIP2 Multi-Task Training

**Status: FULLY BLOCKED** by 8 P0 gaps

**Additional requirements beyond Phase 1:**

| Gap | Description | Duration |
|---|---|---|
| P0-1 | Assemble SIG-G3-2 ±2° narrow-range dataset (~20K) | 5–7 days |
| P0-2 | Resolve IQA skew_score derivation method (choose Option A/B/C) | 3–5 days |
| P0-3 | VLM prompt v2.0 re-validation: SRCC ≥0.60 on 30–50 images | 3 days |
| P0-4 | ILLEGIBLE handwriting acquisition (≥1,000 samples) + KHATT etc. | 10–15 days + 2–4 weeks licensing |
| P0-5 | Shadow/warping severity labeling on GPU VM | 3–5 days |
| P0-6 | Arab cap fix (already in Phase 1 list) | 1 day |
| P0-7 | IQA Phase 1A scale to ≥25K (OHR-Bench labeling) | 15–20 days |

**Sequential critical path:**

```text
Week 0-1:  Schema fixes + v3 blocking decisions + live GCS audit
Week 1-2:  v3 fill run (runs in parallel with Phase 1 bootstrap training)
Week 2-3:  Shadow/warping severity labeling (GPU VM)
Week 3-4:  ILLEGIBLE acquisition + VLM re-validation
Week 4-8:  OHR-Bench IQA labeling (OHR-Bench Phase 1A scaling)
Week 8-10: SIG-G3-2 narrow-range dataset assembly
→ SigLIP2 Phase 2 training can begin: week 10 earliest
```

---

### Phase 3 Readiness — Distillation Cascade

**Status: DEFERRED** (requires all Phase 2 heads trained and validated)

Additional requirements:

- All 22 SigLIP2 heads trained and at least directional OOD metrics available (P1-3)
- OOD catalog scale-up to ≥12K images for distillation validation
- MNV4 bootstrap metrics validated as student baseline

No additional data assembly required beyond Phase 2 (distillation uses existing training data
with teacher soft labels).

---

### v3 Completion Run Decision Tree

```text
BEFORE FILL RUN — All three decisions required:

Decision 1: Cher/Cans Font Feasibility (1 day)
├── Run: scripts/audit_font_coverage.py
├── IF Noto fonts cover Cher + Cans with ≥5 distinct families:
│   └── INCLUDE → 27-class model (or 29 if Armn/Grek also kept)
└── IF fonts insufficient:
    └── EXCLUDE → 25-class model (confirmed coverage only)

Decision 2: Armn/Grek Keep vs. Delete (1 day)
├── Run live GCS audit to count Armn/Grek images
├── IF each < 1,000:
│   └── DELETE from GCS (too small to train on)
└── IF each ≥ 1,000:
    ├── KEEP and expand ML class count
    └── Update SIGLIP2_MULTITASK_REQUIREMENTS.md class list

Decision 3: Kore → Hang Rename (2 hours)
└── Find-replace in generate_base_dataset_v3.py + audit scripts
    └── Verify splits.jsonl will use Hang for the fill run

GO/NO-GO GATE — Live GCS Audit (before fill run, 1 day)
├── Run: --no-use-splits-jsonl audit for per-script GCS baselines
├── Compare with splits.jsonl estimates in this report (A.2 table)
├── Verify Decisions 1, 2, 3 are resolved
├── Verify _validate_no_reserved_scripts() excludes Geor (8,406 in audit)
│   and any accidentally-generated reserved scripts
└── GO: Launch fill run (5–8h A100 / 15–25h CPU)
    └── Estimated output: ~160K additional → ~350K total

POST-FILL — Rebalancing
├── Apply Arab cap (≤13K from ~62K)
├── Verify per-script floor ≥1,000 unique before resampling
├── Run: prepare_multitask_datasets.py script --dry-run
└── Confirm no class exceeds 3× minimum class size
```

---

### Recommended Immediate Actions (This Week)

| Day | Action | Owner | Gap |
|---|---|---|---|
| Today | Send KHATT/CASIA-HWDB/IIIT-INDIC/HKR license requests | Data Eng | P0-4 |
| Day 1 | code_reg → code_cls rename in all files | ML | CF-3 |
| Day 1 | N_A sentinel 0.0 → -1.0 schema fix | Data Eng | CF-2 |
| Day 2 | Derive 300-image Phase 1 minimum OOD set from existing data | Data Eng | P0-8/P0-9 |
| Day 2 | Kore → Hang rename in generator | Data Eng | v3 Decision 3 |
| Day 3 | Run audit_font_coverage.py for Cher/Cans decision | Data Eng | v3 Decision 1 |
| Day 3 | Run live GCS audit for Armn/Grek counts | Data Eng | v3 Decision 2 |
| Day 4 | Arab cap fix in prepare_multitask_datasets.py | Data Eng | P0-6 |
| Day 5 | Launch Phase 1 MNV4-H1/H2 bootstrap training | ML | — |
| Day 5 | Implement Energy Score for MNV4-H1 abstention | ML | OOD-G3 |
| Week 2 | Launch v3 fill run (after all 3 decisions resolved) | Data Eng | v3 |
| Week 2 | GPU VM shadow/warping severity labeling | Data Eng | P0-5 |

---

*This report is independently derived. Where conclusions agree with pre-existing content in
UNIFIED_TRAINING_CORPUS.md §Gap Registry, the agreement reflects independent convergence
on the same evidence, not copying from prior work. The Gap Registry in
UNIFIED_TRAINING_CORPUS.md was written expecting this report as its source; findings here
are authoritative.*

*Analysis: 2 sessions, 2026-02-23. Claude Sonnet 4.6.*
