# Head Adequacy Review: script_code (SIG-G2-1)

> **Status**: ✅ Complete — Needs Work
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: C — Script Detection
> **Adequacy**: ⚠️ Needs Work

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G2-1 |
| Model | SigLIP 2 NAFlex |
| Group | G2 — Script Detection |
| Head Name | script_code |
| Task Type | Classification — 10 classes (Phase 1); expanding to full OpenLID in Phase 2 |
| Output Format | Softmax probability distribution over script classes |
| Priority | P0 |
| Performance Target | Macro F1 ≥ 0.85 across all 10 Phase 1 classes |
| Primary L2 Field | `language.script_code` (ISO 15924 code) |
| Shared-Data Heads | None (dedicated script detection dataset) |
| Training Phase | Phase 2 — Script Detection |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `language.script_code` _(ISO 15924 4-letter string enum)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (synthetic) for synth-multiscript-v3; tier_1_annotation (human-folder-labeled) for MDIW13

**Audit-Derived Defects**: synth-multiscript-v3 DDR grade is 13.8/100 — label completeness 0% (tier_unknown, L2 sidecar
population incomplete). Per-class counts for 25 of 27 scripts in v3 are unverified beyond the known ARAB ~49K figure.

### Phase 1 ML Classes (10 classes)

1. LATN (Latin) — majority class in most document corpora
2. ARAB (Arabic, including Urdu/Persian written in Naskh)
3. HANS (Simplified Chinese)
4. HANT (Traditional Chinese)
5. JPAN (Japanese — Kanji + Kana mixed)
6. HANG (Korean — Hangul)
7. HEBR (Hebrew)
8. CYRL (Cyrillic)
9. DEVA (Devanagari — Hindi/Sanskrit/Nepali)
10. THAI (Thai)

### CRITICAL — OOD Reserved Scripts (NEVER in training)

- Mongolian (Mong) — reserved OOD-Script
- Syriac (Syrc) — reserved OOD-Script
- Georgian (Geor) — reserved OOD-Script

Any image with these scripts MUST have `split_type="ood"` in L2 metadata.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| synth-multiscript-v3 | 350,012 | Partial — L2 sidecar labels incomplete (tier_unknown) | ~100% of images have script label in sidecar path; L2 population 0% | Tier_0 (exact by construction) | 13.8/100 DDR — remediation required | Yes, with rebalancing and ARAB cap |
| MDIW13 | 753 | Yes — folder-level labels, English names | 100% of 753 images | Tier_1 (folder label = ground truth) | Not formally audited | Yes, after `_MDIW13_NAME_TO_ISO` mapping |
| MLT19 | 20,000 | Partial — `script_code` via metadata | ~70% estimated | Tier_1 | Not audited for this project | Conditionally — requires L2 field population |
| CVSI | Unknown | Unknown | Unknown | Unknown | Not audited | Not confirmed usable — requires acquisition |

### Per-Class Coverage Analysis

| Phase 1 Class | v3 Synthetic | MDIW13 Real | Total Real | Real ≥ 83 | Gap Risk |
| --- | --- | --- | --- | --- | --- |
| LATN | Present (high, exact count unknown) | ~83 (Roman folder) | ~83 | Yes | LOW — majority class |
| ARAB | ~49,000 (overrepresented 3.8×) | ~83 (Arabic folder) | ~83 | Yes | MEDIUM — must downsample synth |
| HANS | Present (exact count unknown) | ~83 (Chinese folder, likely HANS) | ~83 | Yes | MEDIUM — MDIW13 "Chinese" label ambiguous (HANS vs HANT) |
| HANT | Uncertain — may be merged with HANS in v3 | 0 | 0 | No | HIGH — zero real data; sim-to-real gap risk |
| JPAN | Present (~30% TTB vertical in v3) | ~83 (Japanese folder) | ~83 | Yes | MEDIUM — TTB convention must be verified |
| HANG | Present | ~83 (Korean folder) | ~83 | Yes | LOW-MEDIUM |
| HEBR | Present | 0 | 0 | No | HIGH — zero real data; CYRL-LATN confusion risk analogous |
| CYRL | Present | 0 | 0 | No | HIGH — zero real data; shares glyph shapes with LATN |
| DEVA | Present | ~83 (Hindi folder) | ~83 | Yes | LOW-MEDIUM |
| THAI | Uncertain — may be grouped in SE_ASIAN_OTHER bucket | 0 | 0 | No | HIGH — zero real data; class existence in v3 unverified |

**Summary**: 4 of 10 Phase 1 classes (HANT, HEBR, CYRL, THAI) have zero real training images.

### Usable Pool Summary

- **Total usable synthetic (before ARAB cap)**: 350,012 images
- **Total usable real**: 753 images (MDIW13), of which ~500 map to Phase 1 classes after excluding BENG/KNDA/TAML
- **Training target**: ≥ 5,000 images per class (consensus recommendation for ViT-B Macro F1 ≥ 0.85)
- **Gap**: HANT, HEBR, CYRL, THAI have 0 real samples; ARAB requires ~35K synthetic downsampling; THAI class existence in v3 unverified

### Mixing Cap Analysis

The `prepare_multitask_datasets.py script` subcommand enforces ≤ 60% synthetic per class. With 753 total
real images (~500 usable for Phase 1), strict enforcement of this cap at the class level means classes with
zero real data (HANT, HEBR, CYRL, THAI) would contribute zero training samples — making these 4 classes
completely absent from training. The cap must either be relaxed to a global-level cap (e.g., total dataset ≤ 80%
synthetic) or waived per-class for synth-only classes, with compensating augmentation applied to approximate
real scan characteristics.

### VLM Validation Sampling Tier

- LATN, ARAB, HANS, DEVA, HANG, JPAN: **Tier 2** — sufficient synthetic volume; MDIW13 real anchor available
- HANT, HEBR, CYRL, THAI: **Tier 3** — zero real data; any validation is synthetic-only until real samples acquired

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| SCRIPT-D01 | synth-multiscript-v3 | `language.script_code` | L2 sidecar population 0% — labels exist in generation metadata but not in L2 enrichment JSON | Open |
| SCRIPT-D02 | synth-multiscript-v3 | `language.script_code` | Per-class distribution unknown beyond ARAB ~49K; 17 scripts reported below 12,963 target | Open |
| SCRIPT-D03 | MDIW13 | `language.script_code` | English folder names (Arabic, Roman, Hindi) require `_MDIW13_NAME_TO_ISO` mapping before use | Open |
| SCRIPT-D04 | MDIW13 | `language.script_code` | "Chinese" folder label ambiguous — may be HANS, HANT, or mixed; cannot use for HANT training without verification | Open |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G2-01 | synth-multiscript-v3 generator bug caused uneven per-script counts; ARAB ~49K (~3.8× target); 17 scripts below target | HIGH — rebalancing required before training |
| KI-G2-02 | HANT, HEBR, CYRL, THAI have zero real training images — 40% of Phase 1 classes are synth-only | CRITICAL — sim-to-real gap risk; Macro F1 target at risk for these classes |
| KI-G2-03 | Mongolian (Mong) images may exist in synth-multiscript-v3 and MUST be permanently marked `split_type="ood"` | CRITICAL — one-time v3 audit required before any manifest generation |
| KI-G2-04 | MDIW13 and MLT19 not on GCS (local only at /mnt/e/) | MEDIUM — GCS upload required before Modal training |
| KI-G2-05 | MDIW13 folder names are English (Arabic, Roman, Hindi) not ISO 15924 — mapping required | MEDIUM — handled by `_MDIW13_NAME_TO_ISO` dict in prepare script |
| KI-G2-06 | THAI class may not exist as a standalone class in v3 — may be inside SE_ASIAN_OTHER bucket | HIGH — class composition audit required |
| KI-G2-07 | ≤60% synthetic cap is unachievable for HANT/HEBR/CYRL/THAI with zero real data — cap enforcement would exclude these classes entirely | CRITICAL — cap policy must be revised before assembly can run |

### Remediation Path

1. Run one-time v3 Mongolian audit: scan `splits.jsonl` for `script_code=Mong`, update L2 sidecars to `split_type="ood"` (0.5 days)
2. Audit v3 per-class distribution: count images per `script_code` value across all splits (0.5 days)
3. Verify THAI class existence in v3 or its SE_ASIAN_OTHER bucket composition (0.5 days)
4. Revise mixing cap policy: allow ≥ 80% synthetic globally with per-class augmentation to approximate real scan characteristics for synth-only classes (1 day)
5. Source real data for HANT, HEBR, CYRL, THAI — minimum 200–500 images per class from public archives, ICDAR datasets, or Wikimedia scraping (2–5 days sourcing)
6. Cap ARAB synthetic at ~12,500 to match next-largest class and apply inverse class frequency weighting (0.5 days)

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | ≥ 50,000 images (5,000 per class × 10 classes after rebalancing) |
| Assembly Status | ⚠️ Blocked — per-class cap policy conflict; real data gaps in 4 classes |
| Current Usable | 350,012 synthetic (imbalanced) + ~500 real (MDIW13 Phase 1 subset) |
| Key Risk | 4 of 10 Phase 1 classes have zero real data; ARAB 3.8× overrepresented |
| Mixing Cap | ≤ 60% synthetic per class (current policy — must be revised for synth-only classes) |
| Assembly Script | `scripts/prepare_multitask_datasets.py script` |

### Class Distribution Requirements

| Class | Min Real Samples | Synthetic Cap (revised) | Risk |
| --- | --- | --- | --- |
| LATN | ≥ 200 | ≤ 80% global | LOW — majority class |
| ARAB | ≥ 200 | Hard cap at ~12,500 synth | MEDIUM — must downsample aggressively |
| HANS | ≥ 200 | ≤ 80% global | MEDIUM — MDIW13 label ambiguity |
| HANT | ≥ 200 (must acquire) | Allow 100% synth + augmentation until real acquired | HIGH — zero real data |
| JPAN | ≥ 200 | ≤ 80% global | MEDIUM — TTB convention must be consistent |
| HANG | ≥ 200 | ≤ 80% global | LOW-MEDIUM |
| HEBR | ≥ 200 (must acquire) | Allow 100% synth + augmentation until real acquired | HIGH — zero real data |
| CYRL | ≥ 200 (must acquire) | Allow 100% synth + augmentation until real acquired | HIGH — zero real data; LATN confusion risk |
| DEVA | ≥ 200 | ≤ 80% global | LOW-MEDIUM |
| THAI | ≥ 200 (must acquire) | Allow 100% synth + augmentation until real acquired | HIGH — zero real data; class audit required |

**Blockers**:

- One-time v3 audit to mark all Mongolian images as `split_type="ood"` before manifest generation
- Per-class distribution audit of v3 to verify all 10 Phase 1 classes have sufficient synthetic volume
- Real data acquisition for HANT, HEBR, CYRL, THAI (minimum 200 images each)
- Mixing cap policy revision for classes with zero real data
- MDIW13 and MLT19 GCS upload for Modal access

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 32/100 (estimated — computed from available evidence before full assembly)

The primary diversity concern for script_code is script class balance. synth-multiscript-v3 provides good
coverage of document-type, resolution, and color mode variation by design (v3 spec: 60% color / 30%
grayscale / 10% binarized; 80% modern / 15% aged / 5% historical; 7 DPI tiers). The critical gap is
capture_method: synth-multiscript-v3 is 100% synthetic across all 350K images, and MDIW13 provides only
~753 real scanned images. Four Phase 1 classes have no real (scanner or camera) capture representation at all.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| script_code | `language.script_code` | CRITICAL | All 10 Phase 1 classes balanced ≥ 5K each | ARAB ~49K; 17 scripts below target; THAI unverified | 20/100 — severe imbalance |
| capture_method | `capture_method.method` | CRITICAL | ≥ 3 methods (born_digital, scanner, camera) | Synthetic only (350K); MDIW13 scanner (~500 usable real images) | 20/100 — camera capture absent |
| domain | `domain.level1` | HIGH | ≥ 5 domains | v3 generates multiple document types by design; MDIW13 printed docs only | 55/100 — synthetic variety but unaudited |
| text_direction | `language.text_direction` | HIGH | ltr, rtl, ttb represented | v3 has rtl (ARAB/HEBR), ttb (JPAN 30%, HANS/HANT 10%); verified in v3 spec | 70/100 — good by design |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers (low, standard, high) | v3 has 7 DPI tiers by design (72–600 DPI) | 75/100 — good by design |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | v3: 60% color / 30% grayscale / 10% binarized by design | 80/100 — good by design |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | v3: 80% modern / 15% aged / 5% historical by design | 75/100 — good by design |
| font_variation | _(no dedicated L2 field)_ | MEDIUM | Varied font families per script | v3 uses multiple font families per script by design; exact diversity unaudited | 50/100 — unaudited |
| degradation | `quality.degradations` | MEDIUM | ≥ 3 types | v3 pristine base; degradation applied at derivation time — script view uses clean images | 30/100 — minimal degradation in script view |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | v3 generates mixed types; MDIW13 is printed-document-only | 50/100 — unaudited |
| layout_type | `structure.layout_type` | LOW | ≥ 2 types | Mixed in v3 by design | 50/100 — not a primary concern |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | Mixed in v3 by design | 50/100 — not a primary concern |
| background_complexity | `image_properties.background` | LOW | Plain and complex | Varies in v3 | 50/100 — not a primary concern |
| mixed_script | `language.is_mixed_script` | LOW | Some mixed-script pages | v3 has multilingual compositions but exact % unaudited | 30/100 — limited and unaudited |

**Weighted Overall Estimate**: 32/100 — driven down by critical failures in script_code balance (weight: CRITICAL)
and capture_method real-world coverage (weight: CRITICAL).

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 28/100 (estimated)

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Low-resolution script images (≤ 150 DPI) | `resolution.dpi` | ⚠️ Partial | v3 has 72–150 DPI tier by design; per-script coverage at low DPI unverified; Chinese/Arabic stroke detail collapses at 72 DPI |
| Camera-captured documents (skew, glare, perspective) | `capture_method.method` = camera_smartphone | ❌ Missing | v3 is 100% synthetic; MDIW13 is flatbed scanner; no camera-captured script data in pool |
| Historical manuscripts (degraded ink, aged paper) | `image_properties.document_age` = historical | ⚠️ Partial | v3 has 5% historical by design but affects all scripts equally; dedicated historical samples for non-Latin scripts absent |
| Mixed-script pages (e.g., English + Japanese, Arabic + Latin) | `language.is_mixed_script` | ⚠️ Partial | v3 has multilingual compositions; exact mixed-script % and per-pair coverage unaudited |
| Right-to-left scripts in document layout context (ARAB, HEBR) | `language.text_direction` = rtl | ⚠️ Partial | v3 has RTL layouts for ARAB/HEBR by design; no real RTL scanned documents in pool |
| Top-to-bottom text (JPAN vertical, historical Mongolian TTB) | `language.text_direction` = ttb | ⚠️ Partial | v3 has JPAN TTB at 30%; Mongolian TTB is OOD-only (not in training) |
| Decorative / display fonts (bold, calligraphic, brush strokes) | `image_properties.font_style` | ❌ Missing | v3 font coverage unaudited; decorative font styles likely underrepresented for non-Latin scripts; calligraphic ARAB and brush-stroke CJK absent |
| Binarized / grayscale scans with thresholding artifacts | `image_properties.color_mode` | ⚠️ Partial | v3 has 10% binarized by design; Sauvola vs Otsu threshold artifacts from real scanning absent |
| Very sparse text (few characters per page — logo, letterhead) | `structure.text_density` | ⚠️ Partial | Mixed density in v3; dedicated sparse-text edge cases unverified |
| CYRL/LATN confusion zone (shared glyph shapes) | _(no L2 field)_ | ❌ Not covered | CYRL trained 100% synthetic; LATN has real scans; model may learn scan artifacts as LATN discriminator |
| Mathematical formulas (Latin glyphs, non-LATN context) | _(no L2 field)_ | ❌ Not covered | Formula-heavy pages not in v3; model may misclassify formula pages |
| OOD open-set rejection (Mongolian, Syriac, Georgian) | `language.script_code` = Mong/Syrc/Geor | ❌ Not yet testable | OOD-Script dataset not acquired; threshold calibration impossible until acquired |

**Key wild condition gaps**:

1. Camera-captured documents completely absent — all 350K synthetic, 753 MDIW13 flatbed scanner only
2. CYRL/LATN confusion zone: differential capture modality (CYRL synthetic, LATN real) risks feature shortcut
3. OOD open-set rejection untestable until OOD-Script images acquired
4. Decorative and calligraphic font styles likely underrepresented for ARAB and CJK scripts

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Script (Phase 1, P0, 600 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 1a. Mongolian real (MTHv2) | 100 | MTHv2 dataset | script=Mong, open_set=true, text_direction=ttb | SigLIP 2 | Cross-categorizes with OOD-Geometry (TTB orientation stress) |
| 1b. Mongolian synth-v3 extract | 50 | synth-multiscript-v3 | script=Mong, split_type=ood, open_set=true | SigLIP 2 | Must verify Mong exists in v3 and mark split_type="ood" BEFORE any training manifest is generated |
| 1c. Syriac manuscripts (SANA corpus) | 120 | SANA corpus | script=Syrc, open_set=true, text_direction=rtl, document_age=historical | SigLIP 2 | Historical manuscripts; RTL adds geometry stress |
| 1d. Georgian archives (nplib.ge) | 100 | nplib.ge digital archives | script=Geor, open_set=true | SigLIP 2 | National Parliamentary Library of Georgia |
| 1e. Historical Fraktur | 50 | Project Gutenberg + Wikimedia Commons | script=Latn, open_set=false, document_age=historical | SigLIP 2 | Must SHA256 + pHash dedup against RVL-CDIP (high overlap risk) |
| 1f. Ottoman Arabic | 30 | Ottoman archives (Library of Congress) | script=Arab, open_set=false, document_age=historical | SigLIP 2 | Historical Arabic with distinctive glyph variation |
| 1g. Phase 2 preview scripts | 75 | Various (~25 each: Greek Grek, Armenian Armn, Ethiopic Ethi) | script=Grek/Armn/Ethi, open_set=true | SigLIP 2 | Retire from OOD once Phase 2 expands to include these scripts |
| 1h. Font variation (decorative fonts in trained scripts) | 75 | Synthetic generation | script=trained, open_set=false, font_style=decorative | SigLIP 2 | Tests script head overfitting to specific font shapes |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 1, P0) — all 8 sub-sources pending

### Missing OOD Sub-sources

- MTHv2 dataset — acquisition path to be confirmed
- SANA corpus — access method to be confirmed
- Georgian digital archives — scraping or API access required
- Fraktur corpus — source selection pending (multiple candidates)
- Ottoman archive — source selection pending

### OOD Leakage Risk

**Level**: HIGH

synth-multiscript-v3 contains Mongolian images that MUST be marked `split_type="ood"` before any training
manifest is generated. This is a one-time pre-processing audit with no known automated check in place. Failure
to run this audit before manifest generation will silently contaminate OOD evaluation. Mitigation:
`_check_ood_leakage()` validation in all `prepare_multitask_datasets.py` subcommands;
`_validate_manifest_no_ood()` in train script.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G3-1 (orientation_cls) | JPAN TTB images appear in both script and orientation datasets | Japanese vertical text (text_direction=ttb) must be labeled orientation=0 in orientation dataset. SHA256-keyed global split registry required to prevent train/test leakage across datasets. |
| MNV4-H1 (orientation) | Shares orientation dataset with SIG-G3-1 | Same TTB convention must propagate consistently to all three heads |
| SIG-G1-1 through SIG-G1-6 (IQA heads) | synth-multiscript-v3 is source for IQA Phase 2 synthetic view | Same base images serve both script detection and IQA pseudo-label derivation — global split registry prevents the same image appearing in script train set and IQA test set |

### Split Leakage Risk

**Level**: MEDIUM

v3 images appear in multiple contexts — script detection AND IQA synthetic derivation AND orientation
synthetic component. The same image file may carry `language.script_code`, `geometric.orientation_class`,
and augmentation parameter labels in different training manifests. Global split registry (SHA256-keyed) is
required to ensure an image in the orientation val/test set is not in the script training set.

### Label Convention

ISO 15924 4-letter codes (LATN, ARAB, HANS, HANT, JPAN, HANG, HEBR, CYRL, DEVA, THAI). Mongolian images from
v3 must be permanently marked `split_type="ood"` in L2 sidecar before manifest generation. MDIW13 English
folder names must be mapped to ISO codes via `_MDIW13_NAME_TO_ISO` dict before any label use. MDIW13 "Chinese"
folder must be audited before use — do not assign to HANT without verification.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| SCRIPT-G01 | SCRIPT-D03 | synth-multiscript-v3 Mongolian images not yet marked split_type="ood" — OOD leakage risk | v3 generated Mong images before OOD reservation was established | One-time v3 audit: scan splits.jsonl for Mong entries, update L2 sidecars to split_type="ood" | 0.5 days |
| SCRIPT-G02 | SCRIPT-D01 | Mixing cap (≤60% synthetic) is unachievable for HANT, HEBR, CYRL, THAI with zero real data — strict enforcement excludes these 4 classes entirely from training | Gap in real data sourcing; no budget allocated for real-data acquisition for these scripts | Revise mixing policy: allow up to 90% synthetic globally (not per-class) OR waive per-class cap for zero-real-data classes with compensating augmentation | 1 day policy + 0.5 days script update |
| SCRIPT-G03 | SCRIPT-D02 | Per-class distribution of synth-multiscript-v3 unknown — need to verify which of the 10 Phase 1 classes are under 5,000 images | v3 generator bug caused uneven distribution; actual counts per script unreported beyond ARAB ~49K | Run v3 class count audit: parse splits.jsonl, count per `script_code`, report gap vs 5K/class target | 0.5 days |
| SCRIPT-G04 | — | THAI class existence in v3 unverified — may be inside SE_ASIAN_OTHER bucket rather than standalone THAI class | v3 ML schema may group SE Asian scripts differently than Phase 1 class schema | Audit v3 ML labels for THAI vs SE_ASIAN_OTHER; if bucket-only, implement THAI extraction logic or source THAI separately | 0.5 days audit + TBD fix |
| SCRIPT-G05 | — | Zero real training images for HANT, HEBR, CYRL, THAI — 40% of Phase 1 classes are synth-only | No real dataset acquisition planned for these scripts; MDIW13 does not cover them | Source minimum 200–500 real images per class: HANT (Taiwan digital libraries, ICDAR CJK), HEBR (Ben Zvi Institute, Wikimedia), CYRL (Russian National Library open collections), THAI (BEST corpus, Thai NLP public datasets) | 2–5 days per class |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| SCRIPT-G06 | ARAB over-represented at ~49K synthetic (~3.8× next-largest class) — will bias model toward Arabic | v3 generator bug; ARAB accumulated disproportionately | Implement per-class hard cap at ~12,500 synthetic images in `prepare_multitask_datasets.py script`; add inverse class frequency weighting to loss | 0.5 days |
| SCRIPT-G07 | MDIW13 "Chinese" folder label ambiguous — cannot use for HANT training without verification | MDIW13 uses generic "Chinese" label that likely maps to HANS (simplified), not HANT (traditional) | Inspect MDIW13 sample images manually (10–20 images); if all simplified Chinese, label as HANS only and mark HANT as unrepresented in MDIW13 | 0.5 days |
| SCRIPT-G08 | MDIW13 and MLT19 not on GCS — Modal training cannot access them | Local-only datasets not yet uploaded | Upload to GCS bucket `gs://image_detection_b/`; update dataset registry with GCS paths | 1 day |
| SCRIPT-G09 | Camera-capture modality completely absent for all script classes | synth-multiscript-v3 is 100% synthetic; MDIW13 is flatbed scanner | Source camera-captured script samples or apply scan simulation augmentation (ScanNet-style noise, perspective warp, glare) to synthetic images for at-risk classes | 2 days |
| SCRIPT-G10 | CYRL/LATN confusion risk from differential capture modality (CYRL: 100% synth, LATN: ~83 real) | Zero real data for CYRL while LATN has real anchor in MDIW13 | Apply identical augmentation to CYRL synthetic samples as to LATN synthetic to equalize modality distribution; acquire real CYRL images (see SCRIPT-G05) | 1 day augmentation + real data per SCRIPT-G05 |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| SCRIPT-G11 | Mixed-script page coverage limited and unaudited | Audit v3 multilingual composition %; synthesize additional bilingual pages (ARAB+LATN, JPAN+LATN) if coverage < 5% |
| SCRIPT-G12 | Font variation coverage per script not audited — decorative/calligraphic styles likely underrepresented | Audit v3 font distribution per script; add decorative font synthetic samples for ARAB (Naskh/Thuluth calligraphic) and CJK (brush stroke) |
| SCRIPT-G13 | Phase 2 preview scripts (Grek, Armn, Ethi) sourced only as OOD — no training coverage | Defer to Phase 2 OpenLID expansion; document as known limitation |
| SCRIPT-G14 | MLT19 usability unconfirmed — `script_code` L2 field population status unknown | Run MLT19 L2 field audit; if script labels available in metadata, this source could add 20K real multilingual images covering multiple Phase 1 classes |

---

## Section 9 — Multi-Model Consensus

**Status**: ✅ Complete — 2-model consensus (google/gemini-2.5-pro + google/gemini-3-pro-preview)

**Adequacy Rating (pre-consensus)**: Needs Work — 4 of 10 Phase 1 classes have zero real data; ARAB 3.8×
overrepresented; ≤60% synthetic cap creates assembly blocker; OOD-Script not acquired.

**Analyst Summary**: The synth-multiscript-v3 + MDIW13 combination is materially insufficient for Phase 1
training at Macro F1 ≥ 0.85. The critical failure is that HANT, HEBR, CYRL, and THAI have zero real training
images, meaning: (a) the ≤60% synthetic cap policy, applied strictly per-class, excludes these 4 classes
entirely from training manifests; and (b) even if the cap is relaxed, the model will be trained 100%
synthetically for these classes, creating a high-risk sim-to-real gap that the consensus models assess as
likely to prevent the F1 target from being met. ARAB overrepresentation (~49K vs target ~12,500) introduces
additional bias. The OOD-Script set is not yet acquired, making open-set rejection threshold calibration
impossible. The overall dataset design is sound in concept — synth-multiscript-v3 is a well-designed base
with good DPI, color mode, and document age diversity — but the real-data gap in 4 classes and the generator
distribution bug are blocking prerequisites.

**Consensus Summary**:

Both models converged on a verdict of "Needs Work / Blocked" with high confidence (9/10 and 10/10).

**Gemini 2.5 Pro** (9/10 confidence, verdict: "Needs Work"):

- Macro F1 ≥ 0.85 "highly unrealistic" with current data configuration
- HANT/HEBR/CYRL/THAI zero real data = fundamental sim-to-real gap; model will overfit to synthetic artifacts
- Recommended per-class minimum: 500–1,000 diverse real images for ViT-B fine-tuning
- MDIW13's ~83 images per class insufficient for robust training
- ARAB downsampling required (aggressive) or class-aware loss weighting
- OOD rejection untestable without acquired images; threshold cannot be calibrated
- Specific CYRL risk: CYRL shares glyph shapes with LATN; differential modality training teaches scan artifacts as LATN discriminator

**Gemini 3 Pro Preview** (10/10 confidence, verdict: "Blocked"):

- Identified the ≤60% cap as mathematically constrictive: with 753 total real images, strict application forces
  zero training samples for HANT/HEBR/CYRL/THAI (cap enforcement = class exclusion, not just volume reduction)
- Recommended per-class minimum: ~5,000 images per class for SigLIP 2 ViT-B to reach F1 ≥ 0.85
- MDIW13 "Chinese" label likely = HANS only; using it for HANT training introduces label poisoning
- Feature shortcut learning risk: model learns generation artifacts (perfect kerning, no noise) as class features for synth-only scripts
- Entropy threshold recommendation: Max_Prob < 0.6 OR normalized entropy > 1.5 (natural log) as starting baseline; must be calibrated on acquired OOD images
- Immediate actions: suspend per-class 60% cap, acquire ~200 real images each for HANT/HEBR/CYRL/THAI as validation anchor, cap ARAB at count of second-largest class

**Points of agreement across both models**:

1. Per-class minimum for Macro F1 ≥ 0.85 with ViT-B: 500–5,000 real or diverse images per class
2. ARAB downsampling is essential before training; 49K is 3–4× excessive
3. Zero real data for 4 of 10 classes is the primary risk factor
4. OOD acquisition must be prioritized on the critical path (not deferred)
5. MDIW13 "Chinese" label must be audited before use for HANS/HANT distinction

**Divergence note**: Gemini 3 Pro interprets the ≤60% cap as applying globally to produce a ~1,882-image
ceiling. In practice, `prepare_multitask_datasets.py` applies the cap per-class, meaning synth-only classes
produce zero samples rather than reducing the overall pool. The practical outcome (zero training samples for
4 classes) is the same regardless of interpretation. The cap policy must be revised in either interpretation.

**Final Rating**: ⚠️ Needs Work

Training cannot proceed in the current state. SCRIPT-G01 through SCRIPT-G05 (all P0 blockers) must be
resolved before a valid training manifest can be generated. Training with the current pool would produce a
model with no representation for 40% of Phase 1 classes.

**Top Recommendations** (priority order):

1. **SCRIPT-G01 (0.5 days)**: Run v3 Mongolian OOD audit immediately — OOD leakage risk affects all downstream evaluation
2. **SCRIPT-G02 (1.5 days)**: Revise mixing cap policy to allow 100% synthetic for zero-real-data classes, compensated by scan-simulation augmentation
3. **SCRIPT-G03 + SCRIPT-G04 (1 day)**: Audit v3 per-class distribution and verify THAI class existence
4. **SCRIPT-G05 (2–5 days per class)**: Source minimum 200 real images each for HANT, HEBR, CYRL, THAI — this is the critical path bottleneck
5. **SCRIPT-G06 (0.5 days)**: Cap ARAB synthetic at ~12,500; implement inverse class frequency weighting in loss function
6. **OOD-Script acquisition**: Begin acquisition of MTHv2 (Mongolian), SANA corpus (Syriac), Georgian archives — these unblock OOD threshold calibration

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 28/100 | 9.8 |
| 14-Dimension Coverage | 25% | 32/100 | 8.0 |
| Wild Condition Coverage | 20% | 28/100 | 5.6 |
| OOD Design Quality | 20% | 45/100 | 9.0 |
| **Overall** | 100% | — | **32.4** |

**Grade**: ⚠️ Needs Work — P0 blockers prevent training manifest assembly; real data gaps in 4 Phase 1
classes are the primary risk factor for Macro F1 target.

**Score rationale**:

- Source Pool Adequacy (28/100): penalized heavily for zero real data in 4 of 10 classes, unknown per-class
  synth distribution, and ARAB 3.8× overrepresentation; partial credit for 350K synthetic volume and MDIW13 real anchor
- 14-Dimension Coverage (32/100): capture_method and script_code balance both score critical failures;
  resolution/color_mode/document_age dimensions score well by v3 design
- Wild Condition Coverage (28/100): camera capture absent, OOD rejection untestable, CYRL/LATN confusion
  zone unaddressed; partial credit for RTL/TTB coverage in v3
- OOD Design Quality (45/100): design is methodologically sound with 8 well-chosen sub-sources; penalized
  for 0/600 images acquired and entropy threshold uncalibrated
