# Grade B Improvement Roadmap

> **Generated**: 2026-02-14 | **Scorecard Config**: v1.1.0
> **Total Datasets**: 51 with scorecards | **Target**: All datasets Grade B (80+)

## Executive Summary

| Grade | Count | Datasets |
|-------|-------|----------|
| **A** (90+) | 8 | anyphotodoc6300, doclaynet, mlt19, pubtabnet, smartdoc-qa, sroie, tobacco800, wsrd |
| **B** (80-89) | 12 | bhutan-afs, cocotext, diqa-5000, docreal, funsd, funsd-plus, hiertext, nepali-handwritten, ohr-bench, realdae, sd7k, warpdoc |
| **C** (70-79) | 4 | midv500 (73.1), multimodal-textbook (75.7), ocr-quality (74.1), rvl-cdip (78.7) |
| **D** (60-69) | 26 | See detailed table below |
| **F** (<60) | 1 | iam (36.4) |

**20 datasets already at Grade B+. 31 datasets need improvement.**

---

## The Two Universal Blockers

### Blocker 1: Missing VLM Inspection (Caps 22 datasets at Grade D)

The single largest blocker. The `vlm_accuracy` dimension is **required** -- if missing, the grade is hard-capped at D regardless of the raw score. This affects 22 datasets whose raw scores would otherwise qualify for B or higher.

**Resolution**: Perform VLM visual inspection using `select_audit_samples.py --phase6` for sample selection, then create `vlm_corrections.json` with `passing_sample_accuracy` field. Minimum 10 passing samples + 5 failing samples required.

**Estimated effort per dataset**: 15-45 minutes (small), 1-2 hours (large >100K)

### Blocker 2: Missing Artifacts (Reduces scoreable dimensions)

Many datasets lack `compliance.json`, `defect_catalog.json`, or `comparison_report.json`. When dimensions cannot be scored, the remaining dimensions get inflated weights, making individual weaknesses more impactful.

**Resolution**: Run missing audit scripts:

- `audit_schema_compliance.py --dataset {name}` for compliance.json
- Create defect_catalog.json during VLM review
- `assemble_comparison.py --dataset {name}` for comparison_report.json (multi-source only)

---

## Per-Dataset Improvement Plan

### Tier 1: Already Grade B+ (20 datasets) -- Maintain

These 20 datasets need no immediate action for the Grade B target.

| Dataset | Grade | Score | Lowest Dimension | Quick Win |
|---------|-------|-------|------------------|-----------|
| sroie | A | 95.7 | doc_completeness (81.8) | -- |
| doclaynet | A | 95.7 | cross_source (84.4) | -- |
| wsrd | A | 94.7 | field_coverage (86.7) | -- |
| anyphotodoc6300 | A | 92.1 | vlm_accuracy (75.0) | Re-inspect VLM samples |
| smartdoc-qa | A | 91.9 | cross_source (68.5) | -- |
| tobacco800 | A | 90.8 | cross_source (49.8) | -- |
| pubtabnet | A | 90.4 | cross_source (60.0) | -- |
| mlt19 | A | 90.9 | vlm_accuracy (80.0) | -- |
| diqa-5000 | B | 88.6 | vlm_accuracy (47.2) | Re-inspect VLM samples |
| sd7k | B | 87.2 | vlm_accuracy (33.3) | Re-inspect VLM samples |
| nepali-handwritten | B | 86.9 | cross_source (52.5) | -- |
| funsd-plus | B | 86.4 | vlm_accuracy (52.8) | Re-inspect VLM samples |
| cocotext | B | 86.3 | cross_source (11.2) | -- |
| ohr-bench | B | 85.1 | cross_source (0.0) | -- |
| warpdoc | B | 85.1 | vlm_accuracy (25.0) | Re-inspect VLM samples |
| docreal | B | 88.1 | vlm_accuracy (58.3) | Re-inspect VLM samples |
| realdae | B | 83.9 | cross_source (52.8) | -- |
| bhutan-afs | B | 83.5 | doc_completeness (45.5) | Expand source doc |
| funsd | B | 83.1 | defect_rate (18.0) | Resolve open defects |
| hiertext | B | 81.7 | doc_completeness (36.4) | Expand source doc |

---

### Tier 2: Grade C (4 datasets) -- Moderate Effort

| # | Dataset | Score | Grade | Gap to B |
|---|---------|-------|-------|----------|
| 1 | rvl-cdip | 78.7 | C | 1.3 pts |
| 2 | multimodal-textbook | 75.7 | C | 4.3 pts |
| 3 | ocr-quality | 74.1 | C | 5.9 pts |
| 4 | midv500 | 73.1 | C | 6.9 pts |

#### rvl-cdip (78.7 -> 80+ needed, gap: 1.3 pts)

1. **VLM re-inspection** (vlm_accuracy=0.0): Current VLM corrections show 0% accuracy. Re-inspect with corrected samples to get realistic VLM score. Even 50% VLM would add ~5 pts. **Effort: 1h**
2. **Expand source documentation** (doc_completeness=63.6): Fill 4 more sections in `docs/datasets/source/rvl-cdip.md`. **Effort: 30min**
3. **Fix field validity issues** (field_validity=92.7): Address the 7.3% invalid fields. **Effort: 1h**

#### multimodal-textbook (75.7 -> 80+ needed, gap: 4.3 pts)

1. **VLM re-inspection** (vlm_accuracy=0.0): Current VLM corrections show 0% accuracy. Re-inspect properly. **Effort: 30min**
2. **Expand source documentation** (doc_completeness=45.5): Fill 6 more sections. **Effort: 30min**
3. **Improve field coverage** (field_coverage=86.7): Fill missing prescreening fields. **Effort: 1h**

#### ocr-quality (74.1 -> 80+ needed, gap: 5.9 pts)

1. **VLM re-inspection** (vlm_accuracy=0.0): Current VLM corrections show 0% accuracy. Re-inspect properly. **Effort: 30min**
2. **Expand source documentation** (doc_completeness=54.6): Fill 5 more sections. **Effort: 30min**
3. **Improve cross-source agreement** (cross_source=51.9): Investigate source disagreements, fix systematic enrichment errors. **Effort: 2h**

#### midv500 (73.1 -> 80+ needed, gap: 6.9 pts)

1. **VLM re-inspection** (vlm_accuracy=0.0): Current VLM corrections show 0% accuracy. Re-inspect properly -- ID documents need careful VLM validation. **Effort: 1h**
2. **Expand source documentation** (doc_completeness=45.5): Fill 6 more sections. **Effort: 30min**
3. **Improve cross-source agreement** (cross_source=58.3): Fix script_family="other" issue found in Phase 1+2. **Effort: 1h**

---

### Tier 3: Grade D -- VLM-Capped (22 datasets where VLM unlocks B)

These datasets have raw scores >= 80 but are capped at D solely because VLM inspection hasn't been performed. **Performing VLM inspection is the ONLY action needed** to unlock their natural grade.

| # | Dataset | Raw Score | Would-Be Grade | Actions Beyond VLM |
|---|---------|-----------|----------------|-------------------|
| 1 | **tablebank** | 89.6 | B | None -- VLM only |
| 2 | **dzongkha-digits** | 91.8 | A | None -- VLM only |
| 3 | **fintabnet** | 86.2 | B | None -- VLM only |
| 4 | **jssoda** | 86.8 | B | Fix domain_level1 >75% (critical field cap) + VLM |
| 5 | **arabic-docs-ocr** | 85.7 | B | Run compliance + VLM |
| 6 | **mathverse** | 84.9 | B | Expand docs (45.5%) + VLM |
| 7 | **financebench** | 83.3 | B | Expand docs (54.6%) + VLM |
| 8 | **im2latex** | 83.0 | B | Expand docs (54.6%) + VLM |
| 9 | **nist-sd19** | 82.6 | B | Expand docs (45.5%) + VLM |
| 10 | **nist-sd6** | 82.5 | B | None -- VLM only |
| 11 | **pucit-ohul** | 82.5 | B | Expand docs (45.5%) + VLM |
| 12 | **mle2e** | 81.6 | B | Expand docs (45.5%) + VLM |
| 13 | **cvsi** | 81.6 | B | Expand docs (45.5%) + VLM |
| 14 | **nist-sd2** | 81.2 | B | None -- VLM only |

**14 datasets reach Grade B with VLM inspection alone** (or VLM + minor doc expansion).

---

### Tier 4: Grade D -- Needs VLM + Score Improvement (8 datasets)

These have raw scores below 80, so VLM alone won't reach Grade B. Need both VLM inspection AND score improvements.

#### docalign12k (76.4, needs +3.6 pts after VLM)

- **Cap**: Critical field (iso639_language=0%) -- must fix FIRST

1. **Fix iso639_language** enrichment: Run language detection pipeline to populate language for all 30K samples. This removes the critical field cap. **Effort: 4h**
2. **Perform VLM inspection**: Required to remove VLM cap. **Effort: 2h**
3. **Expand source documentation** (doc_completeness=63.6): Fill 4 more sections. **Effort: 30min**

#### mdiw13 (77.8, needs +2.2 pts after VLM)

- **Cap**: Critical field (domain_level1=0%) AND cross-source agreement=0.0%

1. **Enrich domain_level1**: Run domain classification for 290K samples. This removes the critical field cap. **Effort: 8h (large dataset)**
2. **Fix cross-source agreement** (0.0%): Investigation needed -- possibly enrichment source mismatch. **Effort: 4h**
3. **Expand source documentation** (doc_completeness=63.6): Fill 4 more sections. **Effort: 30min**

#### siw13 (77.5, needs +2.5 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. **Effort: 1h**
2. **Expand source documentation** (doc_completeness=36.4): Fill 7 more sections -- biggest doc gap. **Effort: 45min**
3. **Run defect catalog**: Missing, would add defect_rate dimension. **Effort: 1h**

#### muharaf (78.4, needs +1.6 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. **Effort: 1h**
2. **Expand source documentation** (doc_completeness=54.6): Fill 5 more sections. **Effort: 30min**
3. **Improve field validity** (90.2%): Address invalid fields. **Effort: 1h**

#### signatr6k (79.8, needs +0.2 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. Likely sufficient alone. **Effort: 1h**
2. **Improve cross-source agreement** (46.6%): Fix enrichment disagreements. **Effort: 1h**
3. **Expand source documentation** (doc_completeness=45.5): Fill 6 more sections. **Effort: 30min**

#### invoices-kg (77.1, needs +2.9 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. **Effort: 30min**
2. **Improve cross-source agreement** (48.1%): Fix enrichment disagreements across 4 sources. **Effort: 2h**
3. **Expand source documentation** (doc_completeness=45.5): Fill 6 more sections. **Effort: 30min**

#### omnidocbench (71.8, needs +8.2 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. **Effort: 30min**
2. **Fix cross-source agreement** (0.0%): Investigate complete disagreement between sources. **Effort: 2h**
3. **Expand source documentation** (doc_completeness=54.6) and improve field coverage (83.5%). **Effort: 1h**

#### dibco (75.8, needs +4.2 pts after VLM)

1. **Perform VLM inspection**: Removes VLM cap. Only 212 samples -- fast. **Effort: 15min**
2. **Fix cross-source agreement** (0.0%): LLM image_id mismatch with metadata stems. **Effort: 1h**
3. **Expand source documentation** (doc_completeness=54.6): Fill 5 more sections. **Effort: 30min**

---

### Tier 5: Grade D -- Low Score, Needs Substantial Work (6 datasets)

These datasets have raw scores well below 80 and are missing multiple artifacts.

#### hasy (74.6, only 2/6 dims scored)

1. **Run compliance check** (field_validity=null): Missing compliance.json eliminates 25% weighted dimension. **Effort: 30min**
2. **Run defect catalog creation**: Missing, eliminates 15% weighted dimension. **Effort: 1h**
3. **Perform VLM inspection**: Required for Grade B. **Effort: 2h (168K samples, use phase6 sampling)**

- **Additional**: Expand docs (54.6%), improve field_coverage (86.7%)

#### cc-ocr (66.9, only 2/6 dims scored)

1. **Run compliance check** (field_validity=null): Missing. **Effort: 30min**
2. **Run defect catalog + comparison report**: Missing. **Effort: 1h**
3. **Perform VLM inspection**: Required. **Effort: 30min**

- **Additional**: Expand docs (45.5%), improve field_coverage (79.8% -- lowest)

#### yarmouk (68.5, only 2/6 dims scored)

1. **Run compliance check** (field_validity=null): Missing. **Effort: 30min**
2. **Run defect catalog**: Missing. **Effort: 1h**
3. **Perform VLM inspection**: Required. **Effort: 1h**

- **Additional**: Expand docs (27.3% -- lowest of all datasets)

#### hindi-synth (64.4, only 2/6 dims scored)

1. **Run compliance check** (field_validity=null): Missing. **Effort: 30min**
2. **Run defect catalog**: Missing. **Effort: 1h**
3. **Perform VLM inspection**: Required. **Effort: 1h (80K synthetic, use phase6)**

- **Additional**: Expand docs (27.3% -- very low)

#### tibhcr (71.9, cross-source=0.0%)

1. **Fix cross-source agreement** (0.0%): Investigate enrichment source mismatch. **Effort: 2h**
2. **Run defect catalog**: Missing. **Effort: 1h**
3. **Perform VLM inspection**: Required. **Effort: 2h (141K, use phase6)**

- **Additional**: Expand docs (45.5%)

#### omnidocbench (71.8) -- covered in Tier 4 above

---

### Tier 6: Grade F (1 dataset) -- Blocked

#### iam (36.4 -- only doc_completeness scored)

**Root cause**: No base metadata file (`iam_metadata.json`) exists.

1. **Run annotate_base_metadata.py** on IAM image directory to generate base metadata. **Effort: 2-4h (130K images)**
2. **Run full audit pipeline** (screening, compliance, integration, VLM). **Effort: 4h**
3. **Expand source documentation** (doc_completeness=36.4): Fill 7 more sections. **Effort: 45min**

- **Note**: This is the only dataset that requires running the base metadata generation pipeline first.

---

## Prioritized Action Plan

### Wave 1: VLM Inspection Sprint (Unlocks 14 datasets to B+)

**Effort**: ~20 hours | **Impact**: 14 datasets D -> B

Process smallest-first, batch by contact sheets:

1. dibco (212) -- 15 min
2. omnidocbench (1.4K) -- 30 min
3. invoices-kg (1.4K) -- 30 min
4. nist-sd2 (5.6K) -- 45 min
5. nist-sd6 (5.6K) -- 45 min
6. nist-sd19 (3.7K) -- 30 min
7. mathverse (6.9K) -- 45 min
8. pucit-ohul (7.4K) -- 45 min
9. im2latex (10K) -- 1h
10. cvsi (10.7K) -- 1h
11. mle2e (1.8K) -- 30 min
12. financebench (54K) -- 2h
13. fintabnet (97K) -- 2h
14. tablebank (278K) -- 3h
15. dzongkha-digits (1.1K) -- 30 min (unlocks A!)

### Wave 2: Compliance + Defect Sprint (Unlocks missing dimensions)

**Effort**: ~8 hours | **Impact**: 6 datasets gain 2-4 dimensions each

Run `audit_schema_compliance.py` and create defect catalogs for:
cc-ocr, yarmouk, hindi-synth, hasy, tibhcr, signatr6k

### Wave 3: Documentation Sprint (Universal +3-8 pts)

**Effort**: ~12 hours | **Impact**: 25+ datasets gain 3-8 pts on doc_completeness

Fill missing sections in `docs/datasets/source/{name}.md` for all datasets with doc_completeness < 80%.

### Wave 4: Critical Field Remediation (Unlocks 3 capped datasets)

**Effort**: ~16 hours | **Impact**: Removes critical field cap for 3 datasets

1. **docalign12k**: Run language enrichment pipeline (iso639_language=0%)
2. **mdiw13**: Run domain classification pipeline (domain_level1=0%)
3. **jssoda**: Fix domain_level1 coverage (currently 65%, need >75%)

### Wave 5: VLM Re-inspection for Grade C datasets

**Effort**: ~4 hours | **Impact**: 4 datasets C -> B

Re-inspect VLM samples for rvl-cdip, multimodal-textbook, ocr-quality, midv500 with proper correction methodology.

### Wave 6: IAM Base Metadata Generation

**Effort**: ~6 hours | **Impact**: 1 dataset F -> B potential

Run `annotate_base_metadata.py` for IAM, then full audit pipeline.

---

## Summary: Effort to All-B

| Action Category | Datasets Impacted | Estimated Hours | Priority |
|----------------|-------------------|-----------------|----------|
| VLM inspection (new) | 22 D-capped | 20h | P0 |
| VLM re-inspection | 4 Grade C | 4h | P0 |
| Compliance runs | 6 missing | 3h | P1 |
| Defect catalogs | 6 missing | 6h | P1 |
| Documentation expansion | 25+ datasets | 12h | P2 |
| Critical field remediation | 3 capped | 16h | P1 |
| IAM base metadata | 1 Grade F | 6h | P2 |
| Cross-source fixes | 5 datasets | 10h | P2 |
| **TOTAL** | **31 datasets** | **~77h** | |

**Key insight**: VLM inspection alone (24h of effort) would move 14 datasets from D to B and 4 from C to B, covering **18 of 31 datasets needing improvement**. This is the highest-ROI action by far.

---

## Grade Distribution After Full Remediation (Projected)

| Grade | Current | After Wave 1 (VLM) | After All Waves |
|-------|---------|---------------------|-----------------|
| A | 8 | 9 (+dzongkha-digits) | 10+ |
| B | 12 | 25 (+13 from VLM) | 39+ |
| C | 4 | 1 (iam still blocked) | 0 |
| D | 26 | 15 (need more work) | 1 (iam, if metadata still missing) |
| F | 1 | 1 (iam) | 0 (if base metadata generated) |
| **B+ total** | **20 (39%)** | **34 (67%)** | **50+ (98%)** |
