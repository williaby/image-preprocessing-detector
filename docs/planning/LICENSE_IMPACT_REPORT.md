---
title: Dataset License Impact Report
owner: ml-team
status: active
tags:
  - licensing
  - datasets
  - compliance
  - training
---

# Dataset License Impact Report

> **Generated**: 2026-02-24
> **Last Updated**: 2026-02-24 (rev 3 — see Corrections & Updates)
> **Scope**: All 62 datasets in DATASET_QUICK_REFERENCE.md
> **Models**: MobileNetV4-Conv-S + SigLIP 2 NAFlex
> **Question**: What license must the model carry under each commercialization scenario?

---

## Corrections & Updates (rev 3, 2026-02-24)

| Dataset | Original finding | Corrected finding | Impact |
|---------|-----------------|-------------------|--------|
| **doc3d** | CC-BY-NC-SA-4.0 — hard blocked commercially | **MIT** (validated via HuggingFace card) | Moves from ❌ to ✅★ in **all** scenarios. Hard-blocked count drops from 4→3 (S1, S2a) and 3→2 (S2b). Unlocks 102K images commercially. |
| **anyphotodoc6300** | "GPL-3.0 or AGPL-3.0 (unclear)" | **GPL-3.0** (dataset, per HuggingFace card); **AGPL-3.0** (code repo, per GitHub). Dataset license governs training. | Clarification only — no scenario status change. |
| **muharaf** | CC-BY-NC-SA-4.0 (single version assumed) | CC-BY-NC-SA-4.0 — but **version uncertainty**: Zenodo shows v2.0, GitHub/arXiv reference v4.0. Restricted/proprietary portion requires USEK contact + ethical-use statement. | Added ⚠️ version flag. Status unchanged (❌ NC commercially). Verify which version applies before use. |
| **financebench** | CC-BY-NC-4.0 | CC-BY-NC-4.0 confirmed — but license **only lives on HuggingFace**; GitHub repo has no LICENSE file. SEC filing PDFs are company-owned copyright (not US government PD), though rarely enforced in research. | Nuance only — no scenario status change. |
| **sd7k** | "Unspecified" | **MIT** (validated via GitHub LICENSE file: Copyright (c) 2023 Nick Chen). Repo sidebar confirms MIT. All CXH-Research dataset repos (StainRestorer, DocUnfold) consistently use MIT. No separate dataset license exists; paper and README impose no additional restrictions. | Moves from ❓ to ✅ in **all** scenarios. Unknown license count drops from 7→6. Unlocks 7,239 shadow images commercially. |
| **wsrd** | "Unspecified" | **CC-BY-NC-SA-4.0** (explicit in GitHub README: "This dataset is made available for academic research purposes only under the CC BY-NC-SA 4.0 license"). Computer Vision Lab, University of Wurzburg. | Moves from ❓ to ❌ NC in S1/S2a/S2b, ✅★ in S3. Hard-blocked count +1 in commercial scenarios. Unlocked in NC scenario (+4,500 shadow images). |
| **omnidocbench** | "Needs verification" | **Apache-2.0** (code) + **Custom non-commercial** (data: "research purposes only, not for commercial use" per OpenDataLab terms). Shanghai AI Laboratory / OpenDataLab. | Moves from ❓ to ❌ NC in S1/S2a/S2b, ⚠️ TOU↓ in S3. Hard-blocked commercially. Lower risk under NC model. |
| **sroie-voxel51** | "Unknown" | **CC-BY-4.0** (declared by Voxel51 on HuggingFace mirror). Caveat: Voxel51 applied this as re-distributor of the ICDAR-2019 SROIE competition data; original competition had research terms. The HF declaration is the only explicit license available. | Moves from ❓ to ✅★ in **all** scenarios. Attribution required. Unlocks 712 receipt images. |
| **warpdoc** | "Unspecified" | **Still unspecified** after thorough search. No GitHub repo, no LICENSE file, no explicit terms found anywhere. NTU Visual Intelligence Lab (Singapore). Only source: Kaggle mirror (inherits Kaggle TOS). | Status unchanged (❓). Recommend contacting authors at NTU. |
| **docalign12k** | "Unspecified" | **Still unspecified** after thorough search. GitHub repo (HCIILAB/DocAlign12K) has no LICENSE file. Lab pattern (HCIILAB/SCUT) strongly suggests non-commercial: M6Doc=CC-BY-NC-ND-4.0, SCUT-EPT=research only. | Status unchanged (❓) but flagged as likely NC based on lab pattern. Higher risk than typical unknown. |
| **drccbi** | "Unknown" | **Still unknown** after thorough search. GitHub repo has no LICENSE file. arXiv paper carries CC-BY-NC-ND-4.0 but this applies to paper text only, not dataset. Dataset includes content derived from DocUNet, SmartDoc-QA, COCO. | Status unchanged (❓). Composite provenance adds complexity; contact authors. |

---

## The Fundamental Legal Question

Whether model weights constitute a "derivative work" of training data is **unsettled law** as of
2026. Cases are pending globally. This report takes the **conservative position** (training =
derivative) for hard-blocked datasets and clearly labels the remaining gray zones. The industry
norm for research-only datasets is mixed — many public models have been trained on IAM, RVL-CDIP,
etc. without formal enforcement, but a public release with a documented model card creates
heightened exposure.

---

## Scenario Summary

| | Scenario 1 | Scenario 2a | Scenario 2b | Scenario 3 |
|-|------------|-------------|-------------|------------|
| **Model License** | MIT | CC-BY-SA-4.0 | GPL-3.0 | CC-BY-NC-SA-4.0 |
| **Commercial Use** | ✅ Yes | ✅ Yes (SA required) | ✅ Yes (GPL copyleft) | ❌ No |
| **User obligation** | None | Must re-share derivatives under CC-BY-SA-4.0 | Derivatives must be GPL-3.0 | Must keep non-commercial + SA |
| **Hard-blocked datasets** | 5 | 5 | 4 | 1 |
| **SA gray zone resolved** | ❌ kuzushiji / hiertext / midv2020 gray | ✅ All three resolved | ❌ Incompatible copyleft | ⚠️ SA+NC conflict |
| **NC datasets unlocked** | ❌ | ❌ | ❌ | ✅ +3 datasets (+84K images) |
| **Research TOU risk** | High (public release) | High | High | Medium (NC intent-aligned) |
| **Clean datasets available** | 35 | 38 | 36 | 38 |
| **SA gray zone datasets** | +3 if accepted | 0 | +3 (worse — copyleft conflict) | +3 (SA+NC conflict) |
| **Research TOU risk datasets** | ~22 | ~22 | ~22 | ~21 |
| **Unknown license datasets** | 3 | 3 | 3 | 3 |
| **Image count (clean only)** | ~2.1M | ~2.6M | ~2.1M | ~2.2M |
| **Image count (+ SA gray)** | ~3.1M | ~2.6M | ~3.1M | ~3.1M |

---

## Scenario 1 — MIT License + Commercial Use

**Current plan.** Most permissive for downstream users (no obligations whatsoever).

### What you gain

- Full commercial freedom for you and all users of the model
- No copyleft obligations — anyone can embed in proprietary products
- Industry standard for open ML models (HuggingFace, PyTorch Hub)

### What you lose

- 5 hard-blocked datasets (see below)
- 3 SA gray-zone datasets require a legal judgment call

### Hard-blocked datasets (exclude or negotiate separate license)

| Dataset | License | Why blocked | Impact |
|---------|---------|-------------|--------|
| **anyphotodoc6300** | GPL-3.0 (dataset) / AGPL-3.0 (code) | GPL requires derivatives to be GPL; MIT is weaker | 6,306 images, dewarping GT |
| **financebench** | CC-BY-NC-4.0 (HuggingFace only; no GitHub LICENSE) | NC prohibits commercial use; MIT allows it | 54,121 images, financial PDFs |
| **muharaf** | CC-BY-NC-SA-4.0 ⚠️ version uncertain (v2.0 vs v4.0) | NC + SA; MIT violates both | 25,711 images, Arabic cursive HW |
| **wsrd** | CC-BY-NC-SA-4.0 (GitHub README) | NC prohibits commercial use; MIT allows it | 4,500 images, shadow removal |
| **omnidocbench** | Custom NC (data: "research purposes only") | NC prohibits commercial use | 1,358 images, benchmark |

### SA gray zone (legal risk, widely accepted industry practice)

| Dataset | License | Risk | Images | Decision |
|---------|---------|------|--------|---------|
| **kuzushiji** | CC-BY-SA-4.0 | SA clause may require CC-BY-SA-4.0 model license | 481,336 | ⚠️ Accept or exclude |
| **hiertext** | CC-BY-SA-4.0 | Same | 11,641 | ⚠️ Accept or exclude |
| **midv2020** | CC BY-SA 2.5 | Same, older version + attribution to Generated Photos | ~4,000 | ⚠️ Accept or exclude |

> **Industry context**: CLIP, DINOv2, and most major vision models were trained on CC-BY-SA data
> and released under Apache/MIT. No enforcement action has occurred. The SA clause's applicability
> to model weights is widely treated as legally inapplicable in practice.

### Replacements for hard-blocked datasets

| Blocked dataset | Replacement | License | Notes |
|-----------------|-------------|---------|-------|
| anyphotodoc6300 (dewarping) | doc3d (MIT ✅) + docreal (MIT) + staindoc (MIT) + warpdoc (unspecified) | MIT / unknown | doc3d now available; covers 3D geometry GT |
| financebench (financial PDFs) | doclaynet (CDLA-Permissive) + pubtabnet (CDLA-Sharing) | Permissive | Different domain distribution |
| muharaf (Arabic HW) | arabic-docs (CC-BY-4.0) + yarmouk (research TOU) | CC-BY-4.0 / TOU | Reduced Arabic HW coverage |
| wsrd (shadow removal) | sd7k (MIT ✅, 7,239 images) | MIT | Larger dataset, same task, fully clean |
| omnidocbench (benchmark) | ohr-bench (CC-BY-4.0, 16K) + doclaynet (CDLA-P) | Permissive / TOU | Different benchmark; adequate alternatives |

---

## Scenario 2a — CC-BY-SA-4.0 License + Commercial Use (Recommended Commercial Alternative)

**Best commercial option** if you want more training data. Resolves the SA gray zone and adds
~496K images (kuzushiji + hiertext + midv2020) to the clean pool.

### What you gain over MIT

- kuzushiji (481,336 images — largest single dataset) fully unlocked
- hiertext and midv2020 fully unlocked
- SA legal risk eliminated for all three datasets
- Commercial use still allowed

### What users must do (compared to MIT)

- Derivatives of your model must also be released under CC-BY-SA-4.0
- Attribution required in all uses
- Same obligations you have to kuzushiji, hiertext, midv2020 flow downstream

### Hard-blocked datasets (5, same as Scenario 1)

| Dataset | License | Why blocked |
|---------|---------|-------------|
| **anyphotodoc6300** | GPL-3.0 (dataset) / AGPL-3.0 (code) | GPL and CC-BY-SA-4.0 are **incompatible copyleft** licenses. FSF explicitly lists them as incompatible. Cannot combine. |
| **financebench** | CC-BY-NC-4.0 | NC clause. CC-BY-SA-4.0 allows commercial use, so using NC data in a commercial-SA model violates NC. |
| **muharaf** | CC-BY-NC-SA-4.0 ⚠️ version uncertain | NC clause blocks commercial use regardless of model license. |
| **wsrd** | CC-BY-NC-SA-4.0 | NC clause blocks commercial use. SA component is compatible but NC is not. |
| **omnidocbench** | Custom NC (data) | NC clause blocks commercial use regardless of model license. |

> Note: Hard-blocked count matches Scenario 1 at 5. doc3d (now MIT) is fully clean in both.
> Net gain over MIT: ~496K images (kuzushiji 481K + hiertext 11K + midv2020 4K) added to the
> unambiguous clean pool via SA resolution.

### SA compatibility summary under CC-BY-SA-4.0

| Dataset | CC-BY-SA status | Result |
|---------|----------------|--------|
| kuzushiji (CC-BY-SA-4.0) | ✅ Same license | Fully compatible |
| hiertext (CC-BY-SA-4.0) | ✅ Same license | Fully compatible |
| midv2020 (CC BY-SA 2.5) | ✅ CC SA 2.5→4.0 one-way upgrade | Compatible (CC allows upgrade) |
| MIT/CC0/Apache datasets | ✅ Less restrictive | All compatible with CC-BY-SA-4.0 model |
| CDLA-Permissive (doclaynet) | ✅ Permissive | Compatible |
| CDLA-Sharing (pubtabnet) | ✅ Data-layer SA only | Does not extend to model weights |

---

## Scenario 2b — GPL-3.0 License + Commercial Use (Limited Value)

Included for completeness. Gains only one dataset (anyphotodoc6300, 6K images) at significant
user-obligation cost. **Not recommended** unless anyphotodoc6300 is specifically critical.

### What you gain over MIT

- anyphotodoc6300 (6,306 images, dewarping) unlocked — the only dataset with GPL-3.0 license

### What users must do (compared to MIT)

- Any application that incorporates or distributes the model must be GPL-3.0
- This practically excludes most commercial SaaS and proprietary products (GPL "infection")
- Users serving the model via API under AGPL-3.0 rules would need to disclose source

### Hard-blocked datasets (4)

| Dataset | License | Why blocked |
|---------|---------|-------------|
| **financebench** | CC-BY-NC-4.0 | NC clause — commercial use still blocked regardless of model license |
| **muharaf** | CC-BY-NC-SA-4.0 ⚠️ version uncertain | Same — NC clause blocks commercial use |
| **wsrd** | CC-BY-NC-SA-4.0 | NC clause — commercial use blocked. SA component conflicts with GPL copyleft. |
| **omnidocbench** | Custom NC (data) | NC clause — commercial use still blocked regardless of model license |

### SA datasets become more problematic under GPL

| Dataset | Under MIT | Under GPL-3.0 | Change |
|---------|-----------|---------------|--------|
| kuzushiji (CC-BY-SA-4.0) | ⚠️ SA gray zone | ⚠️ Incompatible copyleft | Worse — GPL + CC-BY-SA-4.0 explicitly incompatible |
| hiertext (CC-BY-SA-4.0) | ⚠️ SA gray zone | ⚠️ Incompatible copyleft | Same |
| midv2020 (CC BY-SA 2.5) | ⚠️ SA gray zone | ⚠️ Incompatible copyleft | Same |

> FSF and Creative Commons have both documented that GPL-3.0 and CC-BY-SA-4.0 are
> incompatible copyleft licenses for combined works.

---

## Scenario 3 — CC-BY-NC-SA-4.0 License + No Commercial Use

**Research and academic distribution only.** Unlocks the two remaining NC datasets at the cost of
commercial viability. Note: doc3d (102K images) is now MIT and available in all scenarios — it
is **no longer a unique gain** for this scenario.

### What you gain over all commercial scenarios

- financebench (54,121 images of financial PDFs) — high-quality born-digital documents
- muharaf (25,711 images of Arabic cursive HW) ⚠️ verify version before use
- wsrd (4,500 images of shadow removal pairs) — CC-BY-NC-SA-4.0 fully compatible
- Total: ~84K additional images
- omnidocbench (1,358 images) moves from ❌ NC to ⚠️ TOU↓ (lower risk under NC model)
- Research TOU alignment: NC-only model better aligns with intent of academic/research datasets
  (though TOU violations are still technically present for publicly released models)

### What you lose

- All commercial use prohibited for you and all downstream users
- Anyone building a product around your model must obtain a separate commercial license from you

### Hard-blocked datasets (reduced to 1)

| Dataset | License | Why still blocked |
|---------|---------|-------------------|
| **anyphotodoc6300** | GPL-3.0 | GPL allows commercial use; CC-BY-NC-SA-4.0 prohibits it — incompatible license terms. |

### SA datasets remain gray (different reason than commercial scenarios)

| Dataset | Under MIT | Under CC-BY-NC-SA-4.0 | Change |
|---------|-----------|----------------------|--------|
| kuzushiji (CC-BY-SA-4.0) | ⚠️ SA gray zone | ⚠️ SA+NC conflict: CC-BY-SA-4.0 does not permit adding NC restriction | No improvement |
| hiertext (CC-BY-SA-4.0) | ⚠️ SA gray zone | ⚠️ Same | No improvement |
| midv2020 (CC BY-SA 2.5) | ⚠️ SA gray zone | ⚠️ Same | No improvement |

> kuzushiji and hiertext are never clean unless the model license is specifically CC-BY-SA-4.0
> (Scenario 2a). Every other license either violates SA outright or creates a copyleft conflict.

### Research TOU risk under non-commercial

Research-only datasets technically still violate terms of use when publicly released (the TOU
restricts training on the data, not just using the model commercially). However, the practical
enforcement risk is significantly lower because:

1. NC-model intent is aligned with academic dataset policies
2. Institutions are less likely to object to NC research model releases
3. Some TOU holders may consider NC use implicitly allowed

Datasets where NC alignment meaningfully reduces risk: iam, diqa-5000, ohr-bench, rvl-cdip,
fintabnet, smartdoc-qa, sroie, mdiw13, siw13, tibhcr, mle2e, document-haystack, omnidocbench

---

## Complete Dataset Impact Matrix

**Legend**:

- ✅ Clean — usable with no restrictions
- ✅★ Clean — attribution required in model card
- ⚠️ SA — ShareAlike gray zone (legal risk; widely accepted industry practice but unsettled)
- ⚠️ TOU — Research/academic terms of use restriction (breach of contract risk, not copyright)
- ⚠️ TOU↓ — Research TOU but lower risk under no-commercial scenario
- ❌ Blocked — hard legal incompatibility or explicit NC restriction
- ❓ Unknown — license not documented; default = all rights reserved; use at own risk

| Dataset | License | Images | S1: MIT+Comm | S2a: CC-BY-SA+Comm | S2b: GPL+Comm | S3: CC-BY-NC-SA+NC |
|---------|---------|-------:|:---:|:---:|:---:|:---:|
| **pubtabnet** | CDLA-Sharing | 519,030 | ✅ | ✅ | ✅ | ✅ |
| **kuzushiji** | CC-BY-SA-4.0 | 481,336 | ⚠️ SA | ✅★ | ⚠️ SA | ⚠️ SA |
| **docsynth** | Apache-2.0 | 300,000 | ✅ | ✅ | ✅ | ✅ |
| **mdiw13** | Academic | 290,213 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **tablebank** | Apache-2.0 + research clause | 260,025 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **markushgrapher** | CC-BY-4.0 | 172,073 | ✅★ | ✅★ | ✅★ | ✅★ |
| **hasy** | CC0 | 168,233 | ✅ | ✅ | ✅ | ✅ |
| **tibhcr** | Academic | 141,698 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **iam** | Research only | 130,212 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **coco-text** | CC-BY-4.0 | 123,287 | ✅★ | ✅★ | ✅★ | ✅★ |
| **indicdlp** | MIT | 115,803 | ✅ | ✅ | ✅ | ✅ |
| **doc3d** | MIT ✅ (corrected 2026-02-24) | 102,064 | ✅★ | ✅★ | ✅★ | ✅★ |
| **fintabnet** | Research only (IBM) | 97,475 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **iiit-hw-hindi** | Research | 95,430 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **doclaynet** | CDLA-Permissive | 81,471 | ✅ | ✅ | ✅ | ✅ |
| **hindi-synth** | CC0 | 80,009 | ✅ | ✅ | ✅ | ✅ |
| **financebench** | CC-BY-NC-4.0 (HF only; no GitHub LICENSE) | 54,121 | ❌ NC | ❌ NC | ❌ NC | ✅★ |
| **casia-hwdb2-line** | MIT | 52,160 | ✅ | ✅ | ✅ | ✅ |
| **staindoc** | MIT | 15,180 | ✅ | ✅ | ✅ | ✅ |
| **muharaf** | CC-BY-NC-SA-4.0 ⚠️ ver. uncertain | 25,711 | ❌ NC | ❌ NC | ❌ NC | ✅★ |
| **mlt19** | MIT | 19,993 | ✅ | ✅ | ✅ | ✅ |
| **siw13** | Academic | 16,291 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **ohr-bench** | CC-BY-4.0 / research intent | 16,091 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **rvl-cdip** | Academic (IIT-CDIP) | 16,000 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **yarmouk** | Research only | 15,062 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **midv500_data** | MIT | 15,050 | ✅ | ✅ | ✅ | ✅ |
| **midv2020** | CC BY-SA 2.5 | ~4,000 | ⚠️ SA | ✅★ | ⚠️ SA | ⚠️ SA |
| **signatr6k** | Academic | 12,514 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **docalign12k** | Unspecified (likely NC per lab pattern) | ~12,000 | ❓ | ❓ | ❓ | ❓ |
| **hiertext** | CC-BY-SA-4.0 | 11,641 | ⚠️ SA | ✅★ | ⚠️ SA | ⚠️ SA |
| **cvsi** | Academic | 10,715 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **arabic-docs** | CC-BY-4.0 | 10,045 | ✅★ | ✅★ | ✅★ | ✅★ |
| **im2latex** | CC0 | 10,000 | ✅ | ✅ | ✅ | ✅ |
| **pucit-ohul** | Academic | 7,401 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **sd7k** | MIT (corrected 2026-02-24) | 7,239 | ✅ | ✅ | ✅ | ✅ |
| **mathverse** | MIT | 6,940 | ✅ | ✅ | ✅ | ✅ |
| **cc-ocr** | MIT | 6,533 | ✅ | ✅ | ✅ | ✅ |
| **anyphotodoc6300** | GPL-3.0 (dataset) / AGPL-3.0 (code) | 6,306 | ❌ GPL | ❌ GPL+SA incompat | ✅ | ❌ GPL+NC incompat |
| **nist-sd6** | Public Domain | 5,595 | ✅ | ✅ | ✅ | ✅ |
| **nist-sd2** | Public Domain | 5,590 | ✅ | ✅ | ✅ | ✅ |
| **diqa-5000** | Research only | 5,500 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **casia-hwdb2** | Academic | 5,091 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **wsrd** | CC-BY-NC-SA-4.0 (corrected 2026-02-24) | 4,500 | ❌ NC | ❌ NC | ❌ NC | ✅★ |
| **smartdoc-qa** | Research | 4,280 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **q-doc** | Unknown | 4,260 | ❓ | ❓ | ❓ | ❓ |
| **nist-sd19** | Public Domain | 3,669 | ✅ | ✅ | ✅ | ✅ |
| **midv500** | MIT | 3,612 | ✅ | ✅ | ✅ | ✅ |
| **multilingual_scripts** | MIT | 3,279 | ✅ | ✅ | ✅ | ✅ |
| **drccbi** | Unknown (composite provenance) | 325 | ❓ | ❓ | ❓ | ❓ |
| **jssoda** | CC-BY-4.0 | 2,000 | ✅★ | ✅★ | ✅★ | ✅★ |
| **mle2e** | Research | 1,816 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **khatt** | Academic (OOD eval) | ~1,633 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **invoices-kg** | ODbL-1.0 | 1,414 | ✅ | ✅ | ✅ | ✅ |
| **omnidocbench** | Apache-2.0 (code) + Custom NC (data) (corrected 2026-02-24) | 1,358 | ❌ NC | ❌ NC | ❌ NC | ⚠️ TOU↓ |
| **tobacco800** | Academic | 1,290 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **realdae** | Research | 1,200 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **funsd-plus** | CC-BY-4.0 | 1,139 | ✅★ | ✅★ | ✅★ | ✅★ |
| **multimodal-textbook** | Apache-2.0 | 1,113 | ✅ | ✅ | ✅ | ✅ |
| **warpdoc** | Unspecified (no repo/terms found) | 1,020 | ❓ | ❓ | ❓ | ❓ |
| **ocr-quality** | CC0 | 1,000 | ✅ | ✅ | ✅ | ✅ |
| **sroie** | Research (ICDAR) | 973 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **nepali-handwritten** | CC-BY-4.0 | 958 | ✅★ | ✅★ | ✅★ | ✅★ |
| **sroie-voxel51** | CC-BY-4.0 (HuggingFace, Voxel51) (corrected 2026-02-24) | 712 | ✅★ | ✅★ | ✅★ | ✅★ |
| **document-haystack** | Research (benchmark) | 400 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **docreal** | MIT | 200 | ✅ | ✅ | ✅ | ✅ |
| **funsd** | CC-BY-4.0 | 199 | ✅★ | ✅★ | ✅★ | ✅★ |
| **dibco** | Academic | 212 | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU | ⚠️ TOU↓ |
| **bhutan-afs** | Public | 135 | ✅ | ✅ | ✅ | ✅ |
| **dzongkha-digits** | CC-BY-4.0 | 62 | ✅★ | ✅★ | ✅★ | ✅★ |
| **synth-multiscript-v3** | MIT | 190,485 | ✅ | ✅ | ✅ | ✅ |
| **openlid-v2** | Text corpus | — | ✅ | ✅ | ✅ | ✅ |
| **wili-2018** | Text corpus | — | ✅ | ✅ | ✅ | ✅ |

---

## Dataset Count Summary

| Status | S1: MIT+Comm | S2a: CC-BY-SA+Comm | S2b: GPL+Comm | S3: CC-BY-NC-SA+NC |
|--------|:---:|:---:|:---:|:---:|
| ✅ Clean (no attribution) | 21 | 21 | 22 | 21 |
| ✅★ Attribution required | 14 | 17 | 14 | 17 |
| **Total clean** | **35** | **38** | **36** | **38** |
| ⚠️ SA gray zone | 3 | 0 | 3 | 3 |
| ⚠️ TOU risk | 22 | 22 | 22 | 23 (lower risk) |
| ❌ Hard blocked | 5 | 5 | 4 | 1 |
| ❓ Unknown license | 3 | 3 | 3 | 3 |

---

## Image Volume by Status

| Status | S1: MIT+Comm | S2a: CC-BY-SA+Comm | S2b: GPL+Comm | S3: CC-BY-NC-SA+NC |
|--------|-------------:|-------------------:|--------------:|-------------------:|
| ✅ Clean | ~2.1M | ~2.6M | ~2.1M | ~2.2M |
| ⚠️ SA gray zone (if accepted) | +497K | 0 (included above) | +497K | +497K |
| ⚠️ TOU risk (if accepted) | +~450K | +~450K | +~450K | +~451K |
| ❌ Hard blocked | ~92K excluded | ~92K excluded | ~86K excluded | ~6K excluded |
| ❓ Unknown | ~13K unknown | ~13K unknown | ~13K unknown | ~13K unknown |

---

## Key Recommendations

### For commercial MIT (your current plan)

1. **Remove 5 datasets** (anyphotodoc6300, financebench, muharaf, wsrd, omnidocbench) — no
   negotiation needed, they simply can't be included in a commercially-licensed model. doc3d
   (previously believed NC-SA) is confirmed MIT and is now fully available.
2. **Decide on SA gray zone** (kuzushiji, hiertext, midv2020): Industry practice broadly accepts
   this. If you want zero ambiguity, replace kuzushiji with synth-multiscript-v3 (MIT, 190K) which
   has similar script coverage.
3. **Document TOU datasets** in your model card with a clear statement that the model was trained
   with research datasets under their respective terms, and that commercial use of the weights may
   require reviewing those terms. This shifts responsibility to users and is standard practice.

### If kuzushiji is important (CC-BY-SA-4.0 → Scenario 2a)

Switch to **CC-BY-SA-4.0**. You gain 496K images (kuzushiji being by far the largest dataset
in the inventory) and still maintain full commercial viability. The user burden (SA obligation)
is minimal for most ML use cases — embedding model weights in a product doesn't typically create
a "derivative work" that triggers SA in practice.

### If GPL is acceptable (GPL-3.0 → Scenario 2b)

Only worth considering if anyphotodoc6300's paired dewarping GT is uniquely valuable and
irreplaceable. Net gain of 6K images likely does not justify GPL copyleft obligations. Avoid.

### If commercial use isn't needed (CC-BY-NC-SA-4.0 → Scenario 3)

Switch to **CC-BY-NC-SA-4.0** and gain financebench (54K financial PDFs), muharaf (25K
Arabic HW), and wsrd (4.5K shadow removal). doc3d is now MIT and available in all scenarios
regardless. omnidocbench (1.4K) moves to lower-risk TOU. Good choice for a research model
intended for academic use.
Note you can still dual-license — release under CC-BY-NC-SA-4.0 and offer a separate commercial
license for businesses (common model for academic/commercial hybrid products).

### Unknown license datasets (warpdoc, docalign12k, drccbi)

Three datasets remain without an explicit license after thorough investigation:

- **warpdoc** (1,020 images, dewarping): No GitHub repo, no LICENSE, no terms found. Contact NTU
  Visual Intelligence Lab (Singapore). Kaggle mirror inherits Kaggle TOS only.
- **docalign12k** (~12,000 images, alignment): GitHub repo (HCIILAB/DocAlign12K) has no LICENSE.
  Lab pattern (HCIILAB/SCUT) strongly suggests non-commercial (M6Doc=CC-BY-NC-ND-4.0,
  SCUT-EPT=research only). Higher risk than typical unknown — likely NC if clarified.
- **drccbi** (325 images, dewarping): GitHub repo has no LICENSE. arXiv paper is CC-BY-NC-ND-4.0
  but applies to paper text only. Dataset has composite provenance (DocUNet, SmartDoc-QA, COCO
  derived images), adding legal complexity.

Additionally, **q-doc** (4,260 images) remains listed as "Unknown" in the matrix but was not
part of the original audit scope.

Without a license response, treat as "all rights reserved" and exclude from commercial training.
Total unknown image volume: ~13K (down from ~20K after resolving wsrd, omnidocbench, sroie-voxel51).

---

## Appendix: License Compatibility Matrix

| Model License | MIT data | CC0 | CC-BY-4.0 | CC-BY-SA-4.0 | GPL-3.0 | CC-BY-NC-4.0 | CC-BY-NC-SA-4.0 | CDLA-P | CDLA-S | PD |
|---------------|:--------:|:---:|:---------:|:------------:|:-------:|:------------:|:---------------:|:------:|:------:|:--:|
| **MIT** | ✅ | ✅ | ✅ | ⚠️ SA | ❌ | ❌ NC | ❌ NC | ✅ | ✅ | ✅ |
| **Apache-2.0** | ✅ | ✅ | ✅ | ⚠️ SA | ❌ | ❌ NC | ❌ NC | ✅ | ✅ | ✅ |
| **CC-BY-SA-4.0** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ NC | ❌ NC | ✅ | ✅ | ✅ |
| **GPL-3.0** | ✅ | ✅ | ✅ | ❌ incompat | ✅ | ❌ NC | ❌ NC | ✅ | ✅ | ✅ |
| **CC-BY-NC-SA-4.0** | ✅ | ✅ | ✅ | ❌ SA+NC | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

*This report reflects the state of dataset licensing as of 2026-02-24. The legal question of
whether model weights constitute derivatives of training data remains unsettled. Consult legal
counsel before commercial deployment of models trained on research-only datasets.*
