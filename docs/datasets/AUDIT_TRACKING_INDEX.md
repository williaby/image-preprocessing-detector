# Layer 2 Metadata Audit Tracking Index

> **Version**: 4.0.0
> **Last Updated**: 2026-02-14
> **Purpose**: Central dashboard for tracking Layer 2 metadata audit progress across all datasets
> **Related Documentation**:
>
> - [Layer 2 Audit Methodology](../prompts/layer2_audit_prompt.md)
> - [Audit Execution Template](../audit/AUDIT_EXECUTION_TEMPLATE.md)
> - [Audit Report Template](../audit/AUDIT_REPORT_TEMPLATE.md)
> - [Cross-Dataset Known Issues](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json)

---

## Summary Statistics

| Metric | Count | Percentage | Progress Bar |
|--------|-------|------------|--------------|
| **Total Datasets** | 58 | 100% | ████████████████████ 100% |
| **Scorecards Generated** | 58 | 100% | ████████████████████ 100% |
| **Config Registered** | 58 | 100% | ████████████████████ 100% |
| **Deferred** | 3 | 5.2% | █░░░░░░░░░░░░░░░░░░░ 5% |

### Grade Distribution (58 scorecards, v2.0.0)

| Grade | Count | Pct | Datasets |
|-------|-------|-----|----------|
| **A** (>=93) | 6 | 10.3% | doclaynet, dzongkha-digits, fintabnet, mathverse, sroie, wsrd |
| **B** (85-92) | 31 | 53.4% | anyphotodoc6300, arabic-docs-ocr, bhutan-afs, cc-ocr, cvsi, dibco, financebench, funsd, hasy, hindi-synth, im2latex, invoices-kg, jssoda, mdiw13, midv500, mle2e, mlt19, muharaf, multimodal-textbook, nepali-handwritten, nist-sd19, nist-sd2, pucit-ohul, pubtabnet, rvl-cdip, siw13, smartdoc-qa, tablebank, tibhcr, tobacco800, yarmouk |
| **C** (75-84) | 13 | 22.4% | cocotext, diqa-5000, docreal (capped), funsd-plus, hiertext, nist-sd6, ocr-quality, ohr-bench, omnidocbench, realdae, sd7k, signatr6k, warpdoc |
| **D** (65-74) | 1 | 1.7% | docalign12k |
| **F** (<65) | 7 | 12.1% | iam, document-haystack, drccbi, indicdlp, markushgrapher, q-doc, staindoc |

**Audit Coverage**: 58/58 datasets scored (100%) | Mean score: 84.1 | Median score: 88.8

**Key Insights**:

- **58 datasets scored** (52 original + 6 newly onboarded), 3 deferred (doc3d, docsynth, synth-multiscript-250k)
- **v2.0 scoring**: Accuracy-focused with 7 dimensions and 8 grade caps
- **37 datasets at B+ (63.8%)**: 6 Grade A + 31 Grade B
- **Content flag inspection complete** for 51/58 datasets (provenance-based assessment)
- **1 dataset still capped**: docreal (label_accuracy=58.3%, below 70% threshold)
- **13 natural C-grades**: Raw scores 75-85, need quality improvements
- **1 D-grade** (docalign12k): iso639_language <75% coverage
- **7 F-grades**: iam (needs base metadata), 6 newly onboarded (need full audit pipeline)
- **9 cross-dataset known issues** (KI-001 to KI-009) documented

---

## Scorecard Summary Table

<!-- SCORECARD_TABLE_START -->

| Dataset | Score | Grade | Cov | Valid | Doc | Defect | Agree | Label | Conf | Updated |
|---------|-------|-------|-----|------|-----|--------|-------|-------|------|---------|
| anyphotodoc6300 | 90.7 | B | 85 | 100 | 100 | 94 | - | 75 | 100 | 2026-02-16 |
| arabic-docs-ocr | 87.3 | B | 89 | 88 | - | - | - | 80 | 92 | 2026-02-16 |
| bhutan-afs | 89.3 | B | 94 | 89 | 45 | 72 | 96 | 90 | 100 | 2026-02-16 |
| cc-ocr | 85.2 | B | 85 | 96 | 55 | - | - | 85 | 85 | 2026-02-16 |
| cocotext | 81.5 | C | 87 | 96 | 100 | 88 | 11 | 100 | 92 | 2026-02-16 |
| cvsi | 92.3 | B | 89 | 95 | 55 | - | 100 | 95 | 94 | 2026-02-16 |
| dibco | 87.5 | B | 91 | 93 | 55 | - | 87 | 80 | 97 | 2026-02-16 |
| diqa-5000 | 82.8 | C | 92 | 96 | 100 | 84 | 80 | 47 | 98 | 2026-02-16 |
| docalign12k | 68.1 | D | 81 | 96 | 64 | 95 | - | 8 | 85 | 2026-02-16 |
| doclaynet | 93.6 | A | 93 | 97 | 100 | 90 | 79 | 98 | 99 | 2026-02-16 |
| docreal | 85.3 | C | 82 | 96 | 100 | 90 | - | 58 | 100 | 2026-02-16 |
| document-haystack | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| drccbi | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| dzongkha-digits | 93.5 | A | 87 | 100 | 64 | 98 | - | 100 | 92 | 2026-02-16 |
| financebench | 92.3 | B | 88 | 100 | 55 | 85 | - | 95 | 100 | 2026-02-16 |
| fintabnet | 93.8 | A | 91 | 100 | 45 | 98 | - | 95 | 100 | 2026-02-16 |
| funsd | 88.6 | B | 94 | 100 | 73 | 18 | 100 | 95 | 100 | 2026-02-16 |
| funsd-plus | 85.7 | C | 94 | 100 | 91 | 86 | - | 53 | 100 | 2026-02-16 |
| hasy | 93.3 | A | 88 | 100 | 55 | - | - | 95 | 100 | 2026-02-16 |
| hiertext | 88.2 | B | 91 | 94 | 100 | 80 | 70 | 95 | 89 | 2026-02-16 |
| hindi-synth | 90.5 | B | 88 | 93 | 100 | - | 69 | 95 | 100 | 2026-02-16 |
| iam | 36.4 | F | - | - | 45 | - | - | - | - | 2026-02-16 |
| im2latex | 92.6 | B | 88 | 96 | 55 | - | - | 95 | 100 | 2026-02-16 |
| indicdlp | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| invoices-kg | 87.1 | B | 89 | 100 | 55 | 85 | 77 | 80 | 100 | 2026-02-16 |
| jssoda | 92.5 | B | 88 | 94 | 45 | 90 | 100 | 95 | 100 | 2026-02-16 |
| markushgrapher | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| mathverse | 93.3 | A | 91 | 100 | 45 | - | - | 95 | 100 | 2026-02-16 |
| mdiw13 | 89.8 | B | 88 | 90 | 64 | 94 | - | 97 | 88 | 2026-02-16 |
| midv500 | 85.2 | B | 87 | 96 | 55 | 97 | 58 | 90 | 92 | 2026-02-16 |
| mle2e | 92.9 | B | 90 | 94 | 55 | - | 99 | 95 | 97 | 2026-02-16 |
| mlt19 | 91.5 | B | 91 | 96 | 100 | 81 | 96 | 80 | 100 | 2026-02-16 |
| muharaf | 91.2 | B | 87 | 90 | 55 | - | 96 | 95 | 97 | 2026-02-16 |
| multimodal-textbook | 91.2 | B | 87 | 100 | 45 | 97 | - | 95 | 92 | 2026-02-16 |
| nepali-handwritten | 93.9 | A | 88 | 100 | 73 | 96 | 88 | 96 | 100 | 2026-02-16 |
| nist-sd19 | 91.7 | B | 88 | 96 | 45 | 90 | - | 95 | 100 | 2026-02-16 |
| nist-sd2 | 85.3 | B | 88 | 96 | 55 | 85 | 56 | 90 | 100 | 2026-02-16 |
| nist-sd6 | 84.7 | C | 88 | 93 | 64 | 85 | 53 | 90 | 100 | 2026-02-16 |
| ocr-quality | 80.7 | C | 82 | 100 | 73 | 95 | 52 | 85 | 77 | 2026-02-16 |
| ohr-bench | 94.9 | A | 94 | 92 | 100 | 86 | - | 97 | 99 | 2026-02-16 |
| omnidocbench | 84.8 | C | 70 | 99 | 100 | 90 | - | 90 | 74 | 2026-02-16 |
| pubtabnet | 91.1 | B | 91 | 96 | 100 | 80 | 67 | 100 | 100 | 2026-02-16 |
| pucit-ohul | 89.5 | B | 89 | 100 | 55 | 75 | - | 95 | 92 | 2026-02-16 |
| q-doc | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| realdae | 83.7 | C | 92 | 93 | 100 | 91 | 57 | 75 | 92 | 2026-02-16 |
| rvl-cdip | 87.9 | B | 91 | 93 | 64 | 97 | 71 | 85 | 99 | 2026-02-16 |
| sd7k | 79.9 | C | 85 | 96 | 100 | 90 | - | 33 | 100 | 2026-02-16 |
| signatr6k | 93.1 | A | 93 | 96 | 100 | - | 78 | 95 | 99 | 2026-02-16 |
| siw13 | 89.1 | B | 89 | 94 | 45 | - | 100 | 85 | 92 | 2026-02-16 |
| smartdoc-qa | 89.2 | B | 92 | 92 | 100 | 84 | 74 | 92 | 93 | 2026-02-16 |
| sroie | 94.5 | A | 94 | 100 | 82 | 97 | 86 | 93 | 100 | 2026-02-16 |
| staindoc | 6.4 | F | 0 | - | 64 | - | - | - | 0 | 2026-02-16 |
| tablebank | 91.4 | B | 91 | 100 | 64 | 98 | - | 80 | 100 | 2026-02-16 |
| tibhcr | 91.7 | B | 88 | 100 | 55 | - | - | 95 | 94 | 2026-02-16 |
| tobacco800 | 88.2 | B | 94 | 93 | 100 | 86 | 61 | 89 | 99 | 2026-02-16 |
| warpdoc | 77.9 | C | 82 | 96 | 100 | 94 | - | 25 | 100 | 2026-02-16 |
| wsrd | 94.3 | A | 85 | 96 | 100 | 96 | - | 92 | 100 | 2026-02-16 |
| yarmouk | 94.4 | A | 91 | 89 | 100 | - | 100 | 90 | 100 | 2026-02-16 |

<!-- SCORECARD_TABLE_END -->

**Cap Legend**: `crit` = Critical field coverage <75% caps at Grade D. `B->D crit` means uncapped grade would be B but critical field cap downgrades to D. `-` = no cap applied.

**Note**: Scores auto-populated by running:

```bash
python scripts/audit/compute_scorecard.py --all-datasets --update-index
```

---

## Full Dataset Audit Status

### Tier 1: Training-Critical Datasets

Datasets directly used for SigLIP 2 / MobileNetV4 / YOLOv10-doc training.

| Dataset | Status | Grade (Score) | Samples | Config Registered | Top Issue / Note |
|---------|--------|---------------|---------|-------------------|------------------|
| **diqa-5000** | ✅ Complete | **B** (88.6) | 5,500 | Yes | 18 defects (13 resolved, 2 accepted, 3 deferred). VLM 47%, doc 100% |
| **jssoda** | ✅ Complete | D (86.3, B->D crit) | 2,000 | Yes | domain_level1=65% caps grade. 12 defects, 9 resolved. VLM 95% |
| **mlt19** | ✅ Complete | **A** (90.9) | 19,657 | Yes | 17 defects (9 resolved, 1 partial, 3 deferred, 4 accepted). VLM 80%. KI-009 mitigated |
| **ohr-bench** | ✅ Complete | **B** (85.1) | 8,561 | Yes | 7 defects (4 resolved, 3 accepted). VLM 94%. Born-digital benchmark |
| **doclaynet** | ✅ Complete | **A** (95.7) | 81,471 | Yes | 13 defects (12 resolved, 1 partial). GT exploitation strategy. VLM 98% |
| **pubtabnet** | ✅ Complete | **A** (90.4) | 519,030 | Yes | 10 defects (all resolved). VLM 100% (165 images). OOM-safe streaming |
| **tablebank** | ✅ Complete | **B** (88.5) | 278,582 | Yes | VLM 80%. Coverage 93%, validity 96%, defect rate 98% |
| **fintabnet** | ✅ Complete | **B** (87.1) | 97,475 | Yes | VLM 95%. Coverage 93%, validity 96%, defect rate 98% |
| **synth-multiscript-250k** | ⏸️ Deferred | - | 250,000 (generating) | No | Synthetic dataset, generation in progress |
| **realdae** | ✅ Complete | **B** (83.9) | 1,200 | Yes | 5 defects. Coverage 99%, VLM 75%. IQA before/after pairs |
| **hiertext** | ✅ Complete | **B** (81.7) | 11,639 | Yes | 13 defects (11 resolved, 1 partial). Parser GT gold standard handwriting. VLM 95% |

---

### Tier 2: Validation & Supplementary Datasets

Secondary datasets providing diversity, validation, or augmentation.

| Dataset | Status | Grade (Score) | Samples | Config Registered | Top Issue / Note |
|---------|--------|---------------|---------|-------------------|------------------|
| **funsd** | ✅ Complete | **B** (83.1) | 199 | Yes | 11 defects resolved. VLM 95% (199/199). 100% compliance |
| **funsd-plus** | ✅ Complete | **B** (86.4) | 1,139 | Yes | Handwriting detection gap (D03 DEFERRED). VLM 53%. COCO batch ID collision fixed |
| **sroie** | ✅ Complete | **A** (95.7) | 973 | Yes | 14 defects (9 resolved). VLM 93%. GT text bypass. KI-001/008/009 mitigated |
| **cc-ocr** | ✅ Complete | D (79.2, C->D crit) | 6,533 | Yes | domain_level1=0% caps grade. VLM 85%. Needs domain enrichment (GPU) |
| **arabic-docs-ocr** | ✅ Complete | D (86.1, B->D crit) | 10,045 | Yes | domain_level1=0% caps grade. VLM 80%. Needs domain enrichment (GPU) |
| **mdiw13** | ✅ Complete | D (86.5, B->D crit) | 290,213 | Yes | domain_level1=0% caps grade. VLM 97%. Needs domain enrichment (GPU, 290K samples) |
| **siw13** | ✅ Complete | D (81.0, B->D crit) | 16,291 | Yes | domain_level1=0% caps grade. VLM 85%. Needs domain enrichment (GPU) |
| **cvsi** | ✅ Complete | **B** (85.3) | 10,715 | Yes | VLM 95%. Coverage 90%, validity 95%, agreement 100% |
| **mle2e** | ✅ Complete | **B** (85.3) | 1,816 | Yes | VLM 95%. Coverage 91%, validity 94%, agreement 100% |
| **hindi-synth** | ✅ Complete | **A** (92.4) | 80,009 | Yes | VLM 95%. Doc expanded to 100%. Validity 93% |
| **pucit-ohul** | ✅ Complete | **B** (83.9) | 7,401 | Yes | VLM 95%. Coverage 92%, validity 100% |
| **yarmouk** | ✅ Complete | **A** (92.7) | 15,062 | Yes | VLM 90%. Doc expanded to 100%. Validity 89% |
| **tibhcr** | ✅ Complete | **B** (84.5) | 141,698 | Yes | VLM 95%. Coverage 88%, validity 100%. Tibetan handwriting |
| **dzongkha-digits** | ✅ Complete | **A** (92.6) | 62 | Yes | VLM 100%. Coverage 93%, agreement 100%. Defect rate 98% |
| **nepali-handwritten** | ✅ Complete | **B** (86.9) | 958 | Yes | 5 defects (1 resolved, 3 deferred, 1 open). VLM 96% |
| **muharaf** | ✅ Complete | D (81.0, B->D crit) | 25,711 | Yes | domain_level1=50% caps grade. VLM 95%. Needs domain enrichment (GPU) |
| **iam** | ✅ Scorecard | **F** (36.4) | 130,212 | Yes | Doc-only score (36%). No metadata/enrichment data. Needs base metadata (GPU) |
| **cocotext** | ✅ Complete | **B** (86.3) | 63,686 | Yes | VLM 100%. Domain SCN override, language en override. Doc v1.4.0 |
| **hasy** | ✅ Complete | **B** (85.8) | 168,233 | Yes | VLM 95%. Coverage 87%, validity 100% |

---

### Tier 3: Specialized / Low Priority Datasets

Niche, small-sample, or lower-priority datasets.

| Dataset | Status | Grade (Score) | Samples | Config Registered | Top Issue / Note |
|---------|--------|---------------|---------|-------------------|------------------|
| **tobacco800** | ✅ Complete | **A** (90.8) | 1,290 | Yes | Integration script + VLM contact sheet. Coverage 100%, VLM 89% |
| **rvl-cdip** | ✅ Complete | **B** (87.2) | 16,000 | Yes | VLM 85%. Coverage 93%, validity 93%, agreement 80% |
| **midv500** | ✅ Complete | **B** (82.1) | 3,612 | Yes | VLM 90%. Coverage 87%, validity 97%, agreement 58% |
| **smartdoc-qa** | ✅ Complete | **A** (91.9) | 4,260 | Yes | VLM 92%. Coverage 99%. Benchmark-only (NEVER train) |
| **nist-sd2** | ✅ Complete | **B** (82.1) | 5,590 | Yes | VLM 90%. Coverage 87%, agreement 73%. Tax forms synthetic |
| **nist-sd6** | ✅ Complete | **B** (83.3) | 5,595 | Yes | VLM 90%. Coverage 87%, agreement 71%. Tax forms + handprint |
| **nist-sd19** | ✅ Complete | **B** (84.0) | 3,669 | Yes | VLM 95%. Coverage 87%, defect rate 90%. Handwriting digits |
| **dibco** | ✅ Complete | **B** (86.4) | 212 | Yes | VLM 80%. Coverage 95%, validity 100%. Binarization benchmark |
| **signatr6k** | ✅ Complete | **B** (81.6) | 12,514 | Yes | VLM 95%. Coverage 97%, validity 96%, agreement 47% |
| **financebench** | ✅ Complete | **B** (84.6) | 54,121 | Yes | VLM 95%. Coverage 87%, defect rate 85%. Financial PDFs RAG QA |
| **bhutan-afs** | ✅ Complete | **B** (83.5) | 135 | Yes | Coverage 99%, validity 89%, agreement 98%, VLM 90%. Bhutan annual reports |
| **invoices-kg** | ✅ Complete | **B** (80.7) | 1,414 | Yes | VLM 80%. Coverage 88%, defect rate 85%. Invoice images |
| **omnidocbench** | ✅ Complete | D (81.8, B->D crit) | 1,358 | Yes | domain_level1=0% caps grade. VLM 90%. Needs domain enrichment (GPU) |
| **multimodal-textbook** | ✅ Complete | **B** (86.2) | 1,113 | Yes | VLM 95%. Coverage 87%, validity 100%, defect rate 97% |
| **im2latex** | ✅ Complete | **B** (84.6) | 10,000 | Yes | VLM 95%. Coverage 87%, validity 96%. Math formula extraction |
| **mathverse** | ✅ Complete | **B** (86.2) | 6,940 | Yes | VLM 95%. Coverage 93%, validity 100%. Math problems |
| **doc3d** | ⏸️ Deferred | - | 102,064 | No | Document dewarping 3D geometry. No enrichment data |
| **docsynth** | ⏸️ Deferred | - | 300,000 | No | Synthetic layout dataset. No enrichment data |
| **ocr-quality** | ✅ Complete | **B** (82.6) | 1,000 | Yes | VLM 85%. Coverage 86%, validity 100%, agreement 52% |
| **anyphotodoc6300** | ✅ Complete | **A** (92.1) | 6,306 | Yes | Coverage 85%, VLM 75%, doc 100%. Full audit complete |
| **docalign12k** | ✅ Complete | D (76.4, C->D crit) | 30,338 | Yes | iso639_language=0% caps grade. VLM 8%. Needs language enrichment (GPU) |
| **wsrd** | ✅ Complete | **A** (94.7) | 4,500 | Yes | VLM 92%. Domain GENERAL + language en overrides. Coverage 87% |
| **warpdoc** | ✅ Complete | **B** (85.1) | 1,020 | Yes | Domain GENERAL + language en overrides. VLM 25%. Doc 100% |
| **docreal** | ✅ Complete | **B** (88.1) | 200 | Yes | Domain GENERAL + language zh overrides. Doc 100%, VLM 58% |
| **sd7k** | ✅ Complete | **B** (87.2) | 7,239 | Yes | Domain GENERAL override. Doc 100%, VLM 33% |

---

## Grade Cap Analysis

8 datasets show Grade D despite scoring 76-87 in raw score. All are capped by the critical field coverage gate in `compute_scorecard.py`.

### VLM Inspection Cap (0 datasets)

All 52 datasets have completed VLM visual inspection. No VLM caps remain.

### Critical Field Coverage Cap (8 datasets)

Datasets with domain, language, or script coverage below 75% are capped at Grade D. All require OCR text extraction + LLM enrichment (GPU-dependent).

| Dataset | Raw Score | Uncapped Grade | Failing Field | Resolution |
|---------|-----------|----------------|---------------|------------|
| mdiw13 | 86.5 | B | domain_level1=0% | LLM domain enrichment (290K images, GPU) |
| arabic-docs-ocr | 86.1 | B | domain_level1=0% | LLM domain enrichment (GPU) |
| jssoda | 86.3 | B | domain_level1=65% | LLM domain enrichment (GPU) |
| omnidocbench | 81.8 | B | domain_level1=0% | LLM domain enrichment (GPU) |
| muharaf | 81.0 | B | domain_level1=50% | LLM domain enrichment (GPU) |
| siw13 | 81.0 | B | domain_level1=0% | LLM domain enrichment (GPU) |
| cc-ocr | 79.2 | C | domain_level1=0% | LLM domain enrichment (GPU) |
| docalign12k | 76.4 | C | iso639_language=0% | LLM language enrichment (GPU) |

---

## Cross-Dataset Defect Summary

Summary of known issues affecting multiple datasets. See [CROSS_DATASET_KNOWN_ISSUES.json](../../scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json) for full details.

| Issue ID | Title | Severity | Datasets Affected | Status |
|----------|-------|----------|-------------------|--------|
| **KI-001** | Docling layout label casing mismatch | CRITICAL | All 52 datasets using Docling | ✅ Automated fix available |
| **KI-002** | Docling Table detection unreliable on multi-column text | HIGH | Synthetic + multi-column datasets | ⚠️ Manual VLM verification required |
| **KI-003** | Docling Picture detection unreliable on dense text | MEDIUM | Synthetic + dense text datasets | ⚠️ Manual VLM verification required |
| **KI-004** | LLM handwriting detection unreliable on synthetic | HIGH | All synthetic datasets | ✅ Pattern established (override) |
| **KI-005** | LLM cannot detect synthetic capture method | HIGH | jssoda, synth-multiscript-250k, docsynth300k | ✅ Pattern established (override) |
| **KI-006** | LLM formula detection over-flags scientific text | MEDIUM | All datasets with LLM enrichment | ⚠️ Manual VLM verification required |
| **KI-007** | LLM domain classification high UNK rate on generic content | LOW | Generic/narrative content datasets | ✅ Accepted (taxonomy limitation) |
| **KI-008** | Nepali handwritten label noise (character variants) | LOW | nepali-handwritten | ⚠️ Dataset-specific |
| **KI-009** | Latin language conflation (fr/de/it mapped to en) | MEDIUM | mlt19, cocotext (any multi-Latin dataset) | ✅ Mitigated (v5: LLM refinement resolves 1,731/2,671 Latin samples to specific languages) |

**Fix Availability**:

- ✅ **Automated**: `scripts/standardize_layout_labels.py` (KI-001)
- ✅ **Pattern**: Integration script override pattern documented (KI-004, KI-005, KI-007)
- ⚠️ **Manual**: Requires per-dataset VLM inspection (KI-002, KI-003, KI-006)

---

## Audit Methodology Reference

### Process Overview

```text
1. Pre-Audit Setup
   ├─ Register dataset in scripts/audit/audit_config.py
   ├─ Run scripts/audit/select_audit_samples.py (stratified 36 samples)
   └─ Create results/<dataset>/ directory

2. Automated Screening
   ├─ Run scripts/audit/run_prescreening.py
   ├─ Identify fields with <100% pass rate
   └─ Generate baseline defect list

3. VLM Visual Inspection
   ├─ Inspect failing samples (category-based)
   ├─ Inspect passing samples (validation)
   ├─ Document corrections in vlm_corrections.json
   └─ Record findings in defect_catalog.json

4. Integration Script Development
   ├─ Fix defects via scripts/integrate_<dataset>_enrichments.py
   ├─ Apply KI-001 to KI-009 mitigations
   ├─ Re-run prescreening to verify fixes
   └─ Update defect_catalog.json with resolution status

5. Final Audit Report
   ├─ Generate comparison_report.json (before/after)
   ├─ Compute scorecard via compute_scorecard.py
   └─ Update AUDIT_TRACKING_INDEX.md
```

### Key Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **Audit Prompt** | Full methodology, criteria, scoring rubric | [docs/prompts/layer2_audit_prompt.md](../prompts/layer2_audit_prompt.md) |
| **Execution Template** | Per-dataset checklist | [docs/audit/AUDIT_EXECUTION_TEMPLATE.md](../audit/AUDIT_EXECUTION_TEMPLATE.md) |
| **Report Template** | Final report format | [docs/audit/AUDIT_REPORT_TEMPLATE.md](../audit/AUDIT_REPORT_TEMPLATE.md) |
| **Scorecard Config** | Automated scoring rubric | [config/audit_scorecard.yaml](../../config/audit_scorecard.yaml) |
| **Integration Template** | Integration script skeleton | [scripts/audit/integration_script_template.py](../../scripts/audit/integration_script_template.py) |

### Key Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| **select_audit_samples.py** | Stratified sampling (36 samples) | `python scripts/audit/select_audit_samples.py --dataset diqa-5000` |
| **run_prescreening.py** | Automated field validation | `python scripts/audit/run_prescreening.py --dataset diqa-5000` |
| **standardize_layout_labels.py** | Fix KI-001 layout casing | `python scripts/standardize_layout_labels.py --dataset <name>` |
| **compute_scorecard.py** | Generate audit scorecard | `python scripts/audit/compute_scorecard.py --all-datasets --update-index` |
| **integrate_<dataset>_enrichments.py** | Fix defects via integration | `python scripts/integrate_jssoda_enrichments.py` |

---

## Audit Workflow Example

**Step-by-step example using JSSODa audit**:

```bash
# 1. Register dataset config (if not already done)
# Edit scripts/audit/audit_config.py to add jssoda entry

# 2. Select audit samples (stratified 36)
python scripts/audit/select_audit_samples.py --dataset jssoda

# 3. Run automated prescreening
python scripts/audit/run_prescreening.py --dataset jssoda
# Output: scripts/audit/results/jssoda/automated_screening.json

# 4. VLM visual inspection
# - Inspect failing samples (capture_method, domain, content_flags)
# - Inspect passing samples (validation)
# - Document in scripts/audit/results/jssoda/vlm_corrections.json

# 5. Fix KI-001 layout casing issue
python scripts/standardize_layout_labels.py --dataset jssoda

# 6. Develop integration script
# - Create scripts/integrate_jssoda_enrichments.py
# - Apply KI-002 to KI-009 mitigations
# - Merge LLM enrichment, language enrichment, Docling layout
# - Override capture_method, has_handwriting, has_table, etc.

# 7. Run integration script
python scripts/integrate_jssoda_enrichments.py

# 8. Re-run prescreening to verify fixes
python scripts/audit/run_prescreening.py --dataset jssoda
# Expect: 10/13 fields at 100% pass (up from 0/13)

# 9. Create defect catalog
# scripts/audit/results/jssoda/defect_catalog.json
# Document all 12 defects with fix status, root cause, extrapolation risk

# 10. Compute scorecard (once implemented)
python scripts/audit/compute_scorecard.py --dataset jssoda --update-index

# 11. Update this tracking index
# Edit AUDIT_TRACKING_INDEX.md with audit results
```

---

## Next Steps & Priorities

### Immediate Actions (GPU-Dependent - Critical Field Enrichment)

1. **Domain enrichment for 7 crit-capped datasets**: Requires OCR text extraction + LLM classification
   - **Priority**: mdiw13 (86.5, 290K), arabic-docs-ocr (86.1), jssoda (86.3), omnidocbench (81.8), muharaf (81.0), siw13 (81.0), cc-ocr (79.2)
   - **Method**: Run `scripts/enrich_metadata_from_llm.py` with GPU-based OCR text extraction
2. **Language enrichment for docalign12k**: iso639_language=0% needs LLM language detection

### Short-Term (Next Sprint)

1. **IAM rescue**: Currently Grade F (36.4) -- needs base metadata generation via DocLayout-YOLO (GPU)
2. **Cross-source ID mismatch fixes**: 5 datasets have broken comparison_report.json (renamed to .broken). Root cause: UUID-based L2 metadata IDs don't match enrichment source IDs. Fix requires ID normalization in `assemble_comparison.py`

### Long-Term

1. **Deferred datasets**: doc3d, docsynth, synth-multiscript-250k when generation/enrichment ready
2. **Cross-dataset analysis**: Compute aggregate defect statistics, identify new KI patterns
3. **Doc completeness sprint**: 25 datasets at doc_completeness <55% -- expand source docs

---

## Version History

| Version | Date | Changes | Audits Added |
|---------|------|---------|--------------|
| 4.0.0 | 2026-02-14 | VLM sprint complete: all 52 datasets inspected. Grade distribution: 11A + 32B + 0C + 8D + 1F (43 at B+, 83%). 0 VLM caps remaining, 8 critical-field caps. Cross-source ID mismatches fixed (5 datasets). Doc expansion for yarmouk, hindi-synth (both now Grade A). Mean score 85.2, median 85.9 | All 52 datasets (full refresh) |
| 3.0.0 | 2026-02-13 | Complete refresh: all 52 scorecards populated, grade cap analysis added, 3 deferred datasets tracked. Grade distribution: 8A + 12B + 4C + 27D + 1F. All 52 scored datasets registered in audit_config.py. Cap analysis shows 21 VLM-capped, 3 crit-field-capped, 3 low raw score | All 52 datasets |
| 2.1.0 | 2026-02-13 | DocLayNet (81K) audit complete: Grade A (95.7). GT exploitation strategy. 13 defects (12 resolved, 1 partial). VLM 97.9%. Schema v2.3.0 | DocLayNet |
| 2.0.0 | 2026-02-14 | PubTabNet (519K) audit complete: Grade A (90.4). First 500K+ dataset audit. OOM-safe streaming. VLM 100% (165 images). 10 defects (all resolved) | PubTabNet |
| 1.9.0 | 2026-02-14 | WSRD upgraded B(87.0)->A(91.7->94.7) via VLM contact sheet review. Critical field coverage grade cap added to scorecard | WSRD (upgrade) |
| 1.8.0 | 2026-02-14 | ALL 10 Phase 10 datasets at Grade B+ (>=85). Integration scripts for tobacco800, smartdoc-qa. Final: 4xA + 6xB | All 10 Phase 10 datasets |
| 1.7.0 | 2026-02-13 | Phase 10 audit readiness: DIQA-5000 B(88.6), WarpDoc C->B(80.7), COCO-Text B(83.3). Tobacco800/SmartDoc-QA registered. Correction datasets upgraded | DIQA-5000, WarpDoc, Tobacco800, SmartDoc-QA |
| 1.6.0 | 2026-02-13 | MLT19 v5.1: Contact sheet validation (20 sheets, 476 images) | MLT19 (v5.1 validation) |
| 1.5.0 | 2026-02-13 | MLT19 v5: KI-009 Latin refinement, grade C->B (84.22) | MLT19 (v5 update) |
| 1.4.0 | 2026-02-13 | MLT19 v4 integration, KI-008/KI-009, scorecard table | MLT19 (update), KI-008, KI-009 |
| 1.3.0 | 2026-02-12 | Dzongkha-digits audit (62/62 VLM pass, 93.3% prescreening) | Dzongkha-Digits |
| 1.2.0 | 2026-02-12 | Nepali-handwritten audit (Grade B, 87.7) | Nepali-Handwritten |
| 1.1.0 | 2026-02-12 | RealDAE audit (Grade B, 88.9) | RealDAE |
| 1.0.0 | 2026-02-12 | Initial creation with 3 audited datasets | DIQA-5000, JSSODa, MLT19 |

---

## Scorecard Legend

| Metric | Description | Range | Interpretation |
|--------|-------------|-------|----------------|
| **Score** | Weighted composite score | 0-100 | >=90 A, 80-89 B, 70-79 C, 60-69 D, <60 F |
| **Grade** | Letter grade (may be capped) | A to F | Based on score thresholds + grade caps |
| **Cap** | Grade cap applied | - | VLM=missing VLM, crit=critical field <75%, raw=score-based |
| **Coverage** | % of required fields populated | 0-100 | Target: >=95% |
| **Validity** | % of populated fields passing validation | 0-100 | Target: >=98% |
| **Doc** | Documentation completeness | 0-100 | Required fields in source dataset docs |
| **Defects** | Defect rate score (100 - 2*defects) | 0-100 | Higher is better |
| **Agreement** | Cross-source agreement rate | 0-100 | Target: >=90% |
| **VLM** | VLM inspection accuracy | 0-100 | % of VLM-inspected samples passing. `-` = not inspected |

---

**Maintenance Notes**:

- Update this index after EVERY audit completion
- Run `compute_scorecard.py --all-datasets --update-index` to auto-update scorecard table
- Add new datasets to appropriate tier when discovered
- Document new cross-dataset issues in CROSS_DATASET_KNOWN_ISSUES.json
- Keep audit methodology references current with latest process improvements
