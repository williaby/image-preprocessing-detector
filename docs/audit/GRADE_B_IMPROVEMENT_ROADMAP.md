> **Generated**: 2026-02-14 | **Scorecard Config**: v1.1.0
> **Total Datasets**: 58 with scorecards | **Target**: All datasets Grade B (80+)

## Executive Summary

| Grade | Count | Datasets |
|-------|-------|----------|
| **A** (90+) | 11 | anyphotodoc6300, doclaynet, dzongkha-digits, hindi-synth, mlt19, pubtabnet, smartdoc-qa, sroie, tobacco800, wsrd, yarmouk |
| **B** (80-89) | 32 | bhutan-afs, cocotext, cvsi, diqa-5000, dibco, docreal, financebench, fintabnet, funsd, funsd-plus, hasy, hiertext, im2latex, invoices-kg, mathverse, midv500, mle2e, multimodal-textbook, nepali-handwritten, nist-sd2, nist-sd6, nist-sd19, ocr-quality, ohr-bench, pucit-ohul, realdae, rvl-cdip, sd7k, signatr6k, tablebank, tibhcr, warpdoc |
| **D** (60-69) | 8 | arabic-docs-ocr (86.1), cc-ocr (79.2), docalign12k (76.4), jssoda (86.3), mdiw13 (86.5), muharaf (81.0), omnidocbench (81.8), siw13 (81.0) |
| **F** (<60) | 7 | iam (36.4), document-haystack (23.9), drccbi (23.9), indicdlp (23.9), markushgrapher (23.9), q-doc (23.9), staindoc (23.9) |

**43 datasets already at Grade B+ (74%). 15 datasets need improvement.**

> **Note**: The 6 newly onboarded datasets (document-haystack, drccbi, indicdlp, markushgrapher, q-doc, staindoc) have stub metadata only. Their Grade F reflects empty Layer 2 metadata, not dataset quality issues. Grades will improve as downloads complete and the annotation orchestrator generates full metadata.

---

## What Changed Since Initial Roadmap

The initial roadmap (2026-02-13) identified 31 datasets below Grade B. Through Waves 0-4 of the improvement plan, 22 datasets were elevated:

- **VLM inspection sprint**: Removed VLM cap from all 22 datasets that had placeholder `vlm_corrections.json` stubs
- **Compliance runs**: Added `compliance.json` for 5 datasets missing field_validity dimension
- **Documentation expansion**: Expanded source docs for 10+ datasets (yarmouk, hindi-synth, siw13, etc.)
- **Cross-source fixes**: Fixed comparison reports for dibco, tibhcr, mdiw13, omnidocbench, invoices-kg
- **Defect catalog creation**: Added defect catalogs during VLM inspection for all audited datasets

**Result**: 20 at B+ → 43 at B+ (from 39% to 83%)

---

## The Single Remaining Blocker: Critical Field Caps

All 8 Grade D datasets are capped by the **critical field rule**: datasets with `domain_level1`, `iso639_language`, or `script_family` coverage below 75% cannot advance beyond Grade D. Their raw (uncapped) scores would otherwise qualify for Grade B or C.

**Root cause**: These fields require OCR text extraction followed by LLM-based enrichment, which depends on GPU availability.

| Dataset | Raw Score | Cap Field | Current Coverage | Required |
|---------|-----------|-----------|-----------------|----------|
| mdiw13 | 86.5 | domain_level1 | 0% | >75% |
| jssoda | 86.3 | domain_level1 | 65% | >75% |
| arabic-docs-ocr | 86.1 | domain_level1 | 0% | >75% |
| omnidocbench | 81.8 | domain_level1 | 0% | >75% |
| muharaf | 81.0 | domain_level1 | 50% | >75% |
| siw13 | 81.0 | domain_level1 | 0% | >75% |
| cc-ocr | 79.2 | domain_level1 | 0% | >75% |
| docalign12k | 76.4 | iso639_language | 0% | >75% |

**All 8 require the same pipeline**: OCR text extraction (GPU) → `enrich_metadata_from_llm.py` → re-run prescreening → recompute scorecard.

---

## Per-Dataset Improvement Plan

### Tier 1: Already Grade B+ (43 datasets) -- Maintain

These datasets have achieved Grade B or higher and need no immediate action.

| Dataset | Grade | Score | Lowest Dimension |
|---------|-------|-------|------------------|
| doclaynet | A | 95.7 | cross_source (84.4) |
| sroie | A | 95.7 | doc_completeness (81.8) |
| wsrd | A | 94.7 | field_coverage (86.7) |
| yarmouk | A | 92.7 | field_coverage (85.2) |
| dzongkha-digits | A | 92.6 | field_coverage (87.7) |
| hindi-synth | A | 92.4 | defect_rate (85.7) |
| anyphotodoc6300 | A | 92.1 | vlm_accuracy (75.0) |
| smartdoc-qa | A | 91.9 | cross_source (68.5) |
| mlt19 | A | 90.9 | vlm_accuracy (80.0) |
| tobacco800 | A | 90.8 | cross_source (49.8) |
| pubtabnet | A | 90.4 | cross_source (60.0) |
| diqa-5000 | B | 88.6 | vlm_accuracy (47.2) |
| tablebank | B | 88.5 | vlm_accuracy (75.0) |
| docreal | B | 88.1 | vlm_accuracy (58.3) |
| rvl-cdip | B | 87.2 | vlm_accuracy (66.7) |
| sd7k | B | 87.2 | vlm_accuracy (33.3) |
| fintabnet | B | 87.1 | vlm_accuracy (58.3) |
| nepali-handwritten | B | 86.9 | cross_source (52.5) |
| dibco | B | 86.4 | cross_source (70.5) |
| funsd-plus | B | 86.4 | vlm_accuracy (52.8) |
| cocotext | B | 86.3 | cross_source (11.2) |
| mathverse | B | 86.2 | vlm_accuracy (66.7) |
| multimodal-textbook | B | 86.2 | vlm_accuracy (66.7) |
| hasy | B | 85.8 | defect_rate (75.0) |
| cvsi | B | 85.3 | vlm_accuracy (66.7) |
| mle2e | B | 85.3 | vlm_accuracy (66.7) |
| ohr-bench | B | 85.1 | cross_source (0.0) |
| warpdoc | B | 85.1 | vlm_accuracy (25.0) |
| financebench | B | 84.6 | vlm_accuracy (58.3) |
| im2latex | B | 84.6 | vlm_accuracy (58.3) |
| tibhcr | B | 84.5 | cross_source (63.7) |
| nist-sd19 | B | 84.0 | vlm_accuracy (75.0) |
| pucit-ohul | B | 83.9 | vlm_accuracy (58.3) |
| realdae | B | 83.9 | cross_source (52.8) |
| bhutan-afs | B | 83.5 | doc_completeness (45.5) |
| nist-sd6 | B | 83.3 | vlm_accuracy (66.7) |
| funsd | B | 83.1 | defect_rate (18.0) |
| ocr-quality | B | 82.6 | cross_source (51.9) |
| midv500 | B | 82.1 | cross_source (58.3) |
| nist-sd2 | B | 82.1 | vlm_accuracy (66.7) |
| hiertext | B | 81.7 | doc_completeness (36.4) |
| signatr6k | B | 81.6 | cross_source (46.6) |
| invoices-kg | B | 80.7 | cross_source (48.1) |

---

### Tier 2: Grade D -- Critical Field Capped (8 datasets)

All 8 datasets are capped at Grade D solely due to critical field coverage below 75%. Their raw scores range from 76.4 to 86.5.

#### mdiw13 (raw 86.5, would be B)

- **Cap**: domain_level1 = 0%
- **Challenge**: 290K samples -- largest dataset, needs batch processing
- **Fix**: Run OCR text extraction on VPS GPU, then `enrich_metadata_from_llm.py --dataset mdiw13`
- **Effort**: 8-12h (GPU OCR + LLM enrichment for 290K samples)

#### jssoda (raw 86.3, would be B)

- **Cap**: domain_level1 = 65% (closest to threshold)
- **Fix**: Only need +10% domain coverage. Run domain enrichment on ~700 uncovered samples.
- **Effort**: 2h (smallest effort of all capped datasets)

#### arabic-docs-ocr (raw 86.1, would be B)

- **Cap**: domain_level1 = 0%
- **Fix**: Run OCR text extraction + domain enrichment for 10K samples
- **Effort**: 4h

#### omnidocbench (raw 81.8, would be B)

- **Cap**: domain_level1 = 0%
- **Fix**: Run OCR text extraction + domain enrichment for 1.4K samples
- **Effort**: 2h

#### muharaf (raw 81.0, would be B)

- **Cap**: domain_level1 = 50%
- **Fix**: Run domain enrichment on remaining 50% uncovered samples (12.8K)
- **Effort**: 4h

#### siw13 (raw 81.0, would be B)

- **Cap**: domain_level1 = 0%
- **Fix**: Run OCR text extraction + domain enrichment for 16K samples
- **Effort**: 4h

#### cc-ocr (raw 79.2, would be C without cap)

- **Cap**: domain_level1 = 0%
- **Fix**: Run OCR text extraction + domain enrichment for 7K samples. Note: even with cap removed, raw score is 79.2 (Grade C). Will need additional field_coverage/cross_source improvements to reach B.
- **Effort**: 4h (enrichment) + 2h (score improvement)

#### docalign12k (raw 76.4, would be C without cap)

- **Cap**: iso639_language = 0%
- **Fix**: Run OCR text extraction + language detection for 12K samples. Even with cap removed, raw score 76.4 needs improvement via cross_source agreement fixes and doc expansion.
- **Effort**: 4h (enrichment) + 2h (score improvement)

---

### Tier 3: Grade F -- Newly Onboarded (6 datasets)

These 6 datasets were onboarded on 2026-02-14 with stub metadata (0 samples). Their F grade reflects the absence of Layer 2 metadata, not dataset quality. Each needs: download completion, annotation orchestrator run, then full audit pipeline.

| Dataset | Category | Expected Size | Download Status | Next Step |
|---------|----------|---------------|-----------------|-----------|
| indicdlp | layout | 119K images | Downloading (HuggingFace) | Wait for download, run orchestrator |
| document-haystack | benchmark | 400 PDFs | Complete (552MB) | Convert PDFs to images, run orchestrator |
| staindoc | correction | 5K pairs | Extracting (51GB zip) | Wait for extraction, run orchestrator |
| q-doc | quality | 4,260 images | Code-only repo | Acquire images separately (see paper) |
| drccbi | correction | ~2K images | LFS pulled (821MB zip) | Unzip, run orchestrator |
| markushgrapher | document | 235K samples | Complete (19GB Arrow) | Extract images from Arrow, run orchestrator |

**Estimated effort per dataset**: 2-4h (orchestrator + audit pipeline)
**Total effort for all 6**: ~15h

---

### Tier 4: Grade F -- Blocked (1 dataset)

#### iam (36.4 -- only doc_completeness scored)

**Root cause**: No base metadata file (`iam_metadata.json`) exists. Cannot run any audit scripts.

1. **Run `annotate_base_metadata.py`** on IAM image directory (130K images). Requires GPU for DocLayout-YOLO. **Effort: 2-4h**
2. **Run full audit pipeline**: prescreening, compliance, integration, VLM inspection. **Effort: 4h**
3. **Expand source documentation** (doc_completeness=36.4): Fill 7 more sections. **Effort: 45min**

---

## Prioritized Action Plan

### Wave 1: GPU Enrichment Sprint (Requires GPU availability)

**Effort**: ~30h total | **Impact**: 6 datasets D -> B, 2 datasets D -> C (then need additional work)

**Pipeline per dataset**:

```bash
# 1. Extract OCR text (GPU required)
ssh byron@192.168.1.209 "cd /path && python scripts/extract_text.py --dataset {name}"

# 2. Run LLM enrichment (CPU, uses extracted text)
PYTHONPATH=. uv run python3 scripts/enrich_metadata_from_llm.py --dataset {name}

# 3. Re-run prescreening
PYTHONPATH=. uv run python3 scripts/audit/automated_prescreening.py --dataset {name}

# 4. Recompute scorecard
PYTHONPATH=. uv run python3 scripts/audit/compute_scorecard.py --dataset {name}
```

**Order by effort (smallest first)**:

| # | Dataset | Samples | Cap Field | Current | Effort |
|---|---------|---------|-----------|---------|--------|
| 1 | jssoda | 2,000 | domain_level1 | 65% | 2h |
| 2 | omnidocbench | 1,400 | domain_level1 | 0% | 2h |
| 3 | arabic-docs-ocr | 10,000 | domain_level1 | 0% | 4h |
| 4 | muharaf | 25,700 | domain_level1 | 50% | 4h |
| 5 | siw13 | 16,300 | domain_level1 | 0% | 4h |
| 6 | cc-ocr | 7,000 | domain_level1 | 0% | 6h |
| 7 | docalign12k | 12,000 | iso639_language | 0% | 6h |
| 8 | mdiw13 | 290,000 | domain_level1 | 0% | 12h |

### Wave 2: Score Improvement for cc-ocr and docalign12k

These two have raw scores below 80 even without the cap. After critical field enrichment:

**cc-ocr (raw 79.2 -> 80+ needed)**:

1. Improve field_coverage (currently 79.8%) -- fill missing prescreening fields
2. Fix cross-source agreement if comparison report available
3. Expand source documentation

**docalign12k (raw 76.4 -> 80+ needed)**:

1. Fix vlm_accuracy (currently 8.3%) -- re-inspect VLM samples with corrected methodology
2. Expand source documentation (doc_completeness=63.6%)
3. Improve cross_source agreement

### Wave 3: IAM Base Metadata Generation

**Effort**: ~6h | **Impact**: 1 dataset F -> B potential

1. Run `annotate_base_metadata.py` for IAM (requires GPU for DocLayout-YOLO)
2. Run full audit pipeline (prescreening, compliance, VLM inspection)
3. Expand source documentation

---

## Summary: Effort to All-B

| Action Category | Datasets Impacted | Estimated Hours | Priority |
|----------------|-------------------|-----------------|----------|
| GPU domain enrichment | 6 D-capped (domain) | 20h | P0 |
| GPU language enrichment | 1 D-capped (language) | 6h | P0 |
| Domain partial fill (jssoda) | 1 D-capped | 2h | P0 |
| Score improvement (cc-ocr, docalign12k) | 2 below raw 80 | 4h | P1 |
| IAM base metadata | 1 Grade F | 6h | P2 |
| New dataset onboarding (6 datasets) | 6 Grade F (stub) | 15h | P2 |
| **TOTAL** | **15 datasets** | **~53h** | |

**Key insight**: All remaining Grade D datasets share the same blocker -- critical field enrichment requiring GPU. A single GPU session could process all 8 datasets sequentially, converting them from D to B. This is the highest-ROI action remaining. The 6 newly onboarded datasets need download completion + orchestrator runs before they can be audited.

---

## Grade Distribution After Full Remediation (Projected)

| Grade | Current | After Wave 1 (GPU enrichment) | After All Waves |
|-------|---------|-------------------------------|-----------------|
| A | 11 | 11 | 12+ |
| B | 32 | 38 (+6 from cap removal) | 40+ |
| C | 0 | 2 (cc-ocr, docalign12k if raw < 80) | 0 |
| D | 8 | 0 | 0 |
| F | 1 | 1 (iam) | 0 |
| **B+ total** | **43 (83%)** | **49 (94%)** | **52 (100%)** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-02-14 | Major overhaul: 43/52 at B+ (was 20/51). VLM sprint complete. Only critical field caps remain. |
| 1.0.0 | 2026-02-13 | Initial roadmap: 20/51 at B+, 31 needing improvement across 6 waves. |
