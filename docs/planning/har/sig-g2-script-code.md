# Head Adequacy Review: script_code (SIG-G2-1)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: C — Script Detection
> **Adequacy**: ⏳ TBD

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
| Performance Target | Overall accuracy ≥ 90%; Tibetan ≥ 80% (real-only samples only) |
| Primary L2 Field | `language.script_code` (ISO 15924 code) |
| Shared-Data Heads | None (dedicated script detection dataset) |
| Training Phase | Phase 2 — Script Detection |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `language.script_code` _(ISO 15924 4-letter string enum)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Phase 1 ML Classes (10 classes)

1. LATN (Latin) — majority class
2. ARAB (Arabic including Urdu/Persian)
3. HANS (Simplified Chinese)
4. HANT (Traditional Chinese)
5. JPAN (Japanese — Kanji + Kana)
6. KORE (Korean — Hangul)
7. CYRL (Cyrillic)
8. DEVA (Devanagari — Hindi/Sanskrit/Nepali)
9. TIBT (Tibetan) — HIGH RISK: only ~5,200 real samples
10. SE_ASIAN_OTHER (Thai + Khmer + Myanmar + Lao bucket)

### CRITICAL — OOD Reserved Scripts (NEVER in training)

- Mongolian (Mong) — reserved OOD-Script
- Syriac (Syrc) — reserved OOD-Script
- Georgian (Geor) — reserved OOD-Script

Any image with these scripts MUST have `split_type="ood"` in L2 metadata.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| synth-multiscript-v3 | 190,485 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| MDIW13 | 753 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| MLT19 | 20,000 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| CVSI | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 583,000+ images (including synthetic rebalancing)
- **Gap**: _(analysis required — v3 imbalanced: ARAB 3.8× target; TIBT critically undersupplied at ~5,200 real samples)_

### VLM Validation Sampling Tier

_(analysis required — assign Tier 1/2/3 after pool analysis; TIBT likely Tier 3 given scarcity)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G2-01 | synth-multiscript-v3 generator stopped at 190,485 (not 350K target); ARAB over-represented at 3.8× target | HIGH — rebalancing required before training |
| KI-G2-02 | TIBT only ~5,200 real samples — below threshold for 80% accuracy target | HIGH — synthetic augmentation or additional real data required |
| KI-G2-03 | Mongolian (Mong) images exist in synth-multiscript-v3 and MUST be permanently marked split_type="ood" | CRITICAL — one-time v3 audit required before any manifest generation |
| KI-G2-04 | MDIW13 and MLT19 are NOT on GCS (local only at /mnt/e/) | MEDIUM — GCS upload required before Modal training |
| KI-G2-05 | MDIW13 folder names are English (Arabic, Roman, Hindi) not ISO 15924 codes — mapping required | MEDIUM — handled by `_MDIW13_NAME_TO_ISO` dict in prepare script |

### Remediation Path

_(analysis required — enumerate steps after pool gap is quantified; initial steps: 1) run v3 Mong audit, 2) quantify TIBT gap, 3) assess ARAB rebalancing options)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 583,000+ images (including synthetic rebalancing) |
| Assembly Status | 🔄 In Progress — v3 imbalanced, rebalancing required |
| Current Count | 190,485 (v3) + 753 (MDIW13) + 20,000 (MLT19) = ~211,238 before rebalancing |
| Key Risk | TIBT only ~5,200 real samples — highest accuracy risk class |
| Mixing Cap | ≤ 60% synthetic enforced by `scripts/prepare_multitask_datasets.py script` subcommand |
| Assembly Script | `scripts/prepare_multitask_datasets.py script` |

### Class Distribution Requirements

| Class | Min Real Samples | Synthetic Cap | Risk |
| --- | --- | --- | --- |
| LATN | _(analysis required)_ | ≤ 60% | LOW — majority class |
| ARAB | _(analysis required)_ | ≤ 60% | MEDIUM — over-represented in v3 at 3.8× |
| HANS | _(analysis required)_ | ≤ 60% | MEDIUM |
| HANT | _(analysis required)_ | ≤ 60% | MEDIUM |
| JPAN | _(analysis required)_ | ≤ 60% | MEDIUM |
| KORE | _(analysis required)_ | ≤ 60% | MEDIUM |
| CYRL | _(analysis required)_ | ≤ 60% | MEDIUM |
| DEVA | _(analysis required)_ | ≤ 60% | MEDIUM |
| TIBT | ~5,200 real only | ≤ 60% | HIGH — accuracy target at risk |
| SE_ASIAN_OTHER | _(analysis required)_ | ≤ 60% | MEDIUM — bucket class |

**Blockers**:

- One-time v3 audit to mark all Mongolian images as `split_type="ood"` before manifest generation
- TIBT sample count verification and gap quantification
- ARAB rebalancing strategy (downsample or per-class cap)
- MDIW13 and MLT19 GCS upload for Modal access

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL | ≥ 3 methods (born_digital, scanner, camera) | unknown | TBD |
| domain | `domain.level1` | HIGH | ≥ 5 domains | unknown | TBD |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | unknown | TBD |
| script_code | `language.script_code` | CRITICAL | All 10 Phase 1 classes balanced | unknown | TBD |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers (low, standard, high) | unknown | TBD |
| layout_type | `structure.layout_type` | LOW | ≥ 2 types | unknown | TBD |
| degradation | `quality.degradations` | MEDIUM | ≥ 3 types | unknown | TBD |
| text_direction | `language.text_direction` | HIGH | ltr, rtl, ttb represented | unknown | TBD |
| font_variation | _(no dedicated L2 field)_ | MEDIUM | Varied font families per script | unknown | TBD |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | unknown | TBD |
| background_complexity | `image_properties.background` | LOW | Plain and complex | unknown | TBD |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | unknown | TBD |
| mixed_script | `language.is_mixed_script` | LOW | Some mixed-script pages | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Low-resolution script images (≤ 150 DPI) | `resolution.dpi` | ⏳ | analysis required |
| Camera-captured documents (skew, glare, perspective) | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Historical manuscripts (degraded ink, aged paper) | `image_properties.document_age` = historical | ⏳ | analysis required |
| Mixed-script pages (e.g., English + Japanese) | `language.is_mixed_script` | ⏳ | analysis required |
| Right-to-left scripts in document layout context (ARAB, Syrc) | `language.text_direction` = rtl | ⏳ | analysis required |
| Top-to-bottom text (JPAN vertical, Mong TTB) | `language.text_direction` = ttb | ⏳ | TTB only in OOD (Mong); JPAN TTB must be in training |
| Decorative / display fonts (bold, stylized, handwritten-style) | `image_properties.font_style` | ⏳ | analysis required |
| Binarized / grayscale scans | `image_properties.color_mode` | ⏳ | analysis required |
| Very sparse text (few characters per page) | `structure.text_density` | ⏳ | analysis required |
| Watermarked or background-heavy documents | `quality.degradations` | ⏳ | analysis required |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Script (Phase 1, P0, 600 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 1a. Mongolian real (MTHv2) | 100 | MTHv2 dataset | script=Mong, open_set=true, text_direction=ttb | SigLIP 2 | Cross-categorizes with OOD-Geometry (TTB orientation stress) |
| 1b. Mongolian synth-v3 extract | 50 | synth-multiscript-v3 | script=Mong, split_type=ood, open_set=true | SigLIP 2 | Must verify Mong exists in v3 and mark split_type="ood" BEFORE any training manifest is generated |
| 1c. Syriac manuscripts (SANA corpus) | 120 | SANA corpus | script=Syrc, open_set=true, text_direction=rtl, document_age=historical | SigLIP 2 | Historical manuscripts; rtl adds geometry stress |
| 1d. Georgian archives (nplib.ge) | 100 | nplib.ge digital archives | script=Geor, open_set=true | SigLIP 2 | National Parliamentary Library of Georgia |
| 1e. Historical Fraktur | 50 | Fraktur corpus (source TBD) | script=Latn, open_set=false, document_age=historical | SigLIP 2 | Must SHA256 + pHash dedup against RVL-CDIP (high overlap risk) |
| 1f. Ottoman Arabic | 30 | Ottoman archive (source TBD) | script=Arab, open_set=false, document_age=historical | SigLIP 2 | Historical Arabic with distinctive glyph variation |
| 1g. Phase 2 preview scripts | 75 | Various (~25 each: Greek Grek, Armenian Armn, Ethiopic Ethi) | script=Grek/Armn/Ethi, open_set=true | SigLIP 2 | Retire from OOD once Phase 2 expands to include these scripts |
| 1h. Font variation (decorative fonts in trained scripts) | 75 | Synthetic generation | script=trained, open_set=false, font_style=decorative | SigLIP 2 | Tests script head overfitting to specific font shapes |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 1, P0)

### Missing OOD Sub-sources

- MTHv2 dataset — acquisition path to be confirmed
- SANA corpus — access method to be confirmed
- Georgian digital archives — scraping or API access required
- Fraktur corpus — source selection pending (multiple candidates)
- Ottoman archive — source selection pending

### OOD Leakage Risk

**Level**: HIGH

Synth-multiscript-v3 contains Mongolian images that MUST be marked `split_type="ood"` before any training manifest is generated. This is a one-time pre-processing audit with no known automated check in place. Failure to run this audit before manifest generation will silently contaminate OOD evaluation. Mitigation: `_check_ood_leakage()` validation in all `prepare_multitask_datasets.py` subcommands; `_validate_manifest_no_ood()` in train script.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G3-1 (orientation_cls) | JPAN TTB images appear in both script and orientation datasets | Japanese vertical text (text_direction=ttb) must be labeled orientation=0 in orientation dataset. SHA256-keyed global split registry required to prevent train/test leakage across datasets. |
| MNV4-H1 (orientation) | Shares orientation dataset with SIG-G3-1 | Same TTB convention must propagate consistently to all three heads |

### Split Leakage Risk

**Level**: MEDIUM

v3 images appear in multiple contexts — script detection AND orientation synthetic component. The same image file may carry both `language.script_code` and `geometric.orientation_class` labels in different training manifests. Global split registry (SHA256-keyed) is required to ensure an image that is in the orientation val/test set is not in the script training set.

### Label Convention

ISO 15924 4-letter codes (LATN, ARAB, HANS, HANT, JPAN, KORE, CYRL, DEVA, TIBT, and bucket SE_ASIAN_OTHER). Mongolian images from v3 must be permanently marked `split_type="ood"` in L2 sidecar before manifest generation. MDIW13 English folder names must be mapped to ISO codes via `_MDIW13_NAME_TO_ISO` dict before any label use.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G2-G01 | — | synth-multiscript-v3 Mongolian images not yet marked split_type="ood" — OOD leakage risk | v3 generated Mong images before OOD reservation was established | One-time v3 audit: scan splits.jsonl for Mong entries, update L2 sidecars to split_type="ood" | 0.5 days |
| G2-G02 | — | TIBT sample count (~5,200 real) critically below threshold for 80% per-class accuracy target | Limited real Tibetan document sources; generator produced insufficient Tibetan samples | Quantify exact gap; evaluate synthetic augmentation options or additional real data sourcing | 1 day analysis + TBD sourcing |
| G2-G03 | — | ARAB over-represented at 3.8× target in v3 — will bias training without rebalancing | v3 generator bug caused uneven per-script sample counts | Implement per-class cap in `prepare_multitask_datasets.py script` subcommand with downsample or cap | 0.5 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G2-G04 | MDIW13 and MLT19 not on GCS — Modal training cannot access them | Local-only datasets not yet uploaded | Upload to GCS bucket; update dataset registry with GCS paths | 1 day |
| G2-G05 | SE_ASIAN_OTHER bucket composition unverified — Thai/Khmer/Myanmar/Lao balance unknown | Bucket class defined in ML schema but not audited | Audit v3 and CVSI for SE Asian script distribution within bucket | 0.5 days |
| G2-G06 | Historical script coverage (Fraktur, Ottoman Arabic) absent from training data | Training data skews modern | Source historical document samples; assess whether training inclusion is needed or OOD-only is sufficient | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G2-G07 | Mixed-script page coverage limited in training pool | Source or synthesize pages with two script systems co-occurring |
| G2-G08 | Font variation coverage per script not audited | Audit v3 font distribution; add decorative font synthetic samples if dominated by single font family |
| G2-G09 | Phase 2 preview scripts (Grek, Armn, Ethi) sourced only as OOD — no training coverage | Defer to Phase 2 OpenLID expansion; document as known limitation |

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
