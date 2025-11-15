# Additional Dataset Review - Coverage Analysis

**Date**: 2025-11-14 (Updated: Added VidOre V3 Finance)
**Purpose**: Evaluate 8 external datasets for potential coverage improvements
**Reviewer**: Claude Code (Automated Analysis)

---

## Executive Summary

**Recommendation**: ⚠️ **CONDITIONAL** - Only VidOre V3 Finance has potential value for FR-4.4

**Rationale**: 7/8 datasets target already-SUFFICIENT FRs (100%+). VidOre V3 Finance could help FR-4.4 (parasitic content) but has limitations (small corpus, no explicit annotations).

**Cost Savings**: Avoiding 7 irrelevant datasets saves ~100 hours. VidOre integration = 8-12 hours for marginal FR-4.4 benefit.

**Updated Recommendation**: Monitor FR-4.4 weak supervision progress (currently 16%). If it fails, consider VidOre as fallback before commercial annotation.

---

## Current Coverage Gaps (Priority Order)

| FR ID | Requirement | Current | Target | Status | Priority |
|-------|-------------|---------|--------|--------|----------|
| FR-4.4 | Parasitic Content Detection | 0 | 10,000 | ❌ CRITICAL GAP | P0 (in progress) |
| FR-7.1 | DQS Routing Matrix | 6,400 | 57,500 | ⚠️ PARTIAL | P1 (can scale) |
| FR-2.1 | Document Classification | 71,694 | 10,000 | ✅ SUFFICIENT | P3 (done) |
| FR-5.1 | Handwriting Detection | 10,373 | 10,000 | ✅ SUFFICIENT | P3 (done) |
| FR-4.2.6 | Table Detection | 58,022 | 2,000 | ✅ SUFFICIENT | P3 (done) |
| FR-4.2.7 | Figure/Formula Detection | 45,976 | 1,500 | ✅ SUFFICIENT | P3 (done) |

---

## Dataset Evaluations

### 1. NIST Special Database 19 (Handwriting)

**Source**: https://www.nist.gov/srd/nist-special-database-19

**Dataset Details**:
- **Size**: 810,000 handwritten character images (3,600 writers)
- **Content**: Handprinted forms, isolated digits, uppercase, lowercase, free text
- **Format**: ZIP archives (PDF user guides)
- **License**: Public domain
- **Quality**: High (ground-truth classifications, hand-checked)

**Target FR**: FR-5.1 (Handwriting Detection)

**Current Status**: ✅ SUFFICIENT (10,373/10,000 samples, 103.7%)

**Analysis**:
- ✅ **Pros**: Massive scale, public domain, high quality, government-backed
- ❌ **Cons**: FR-5.1 already met (103.7% coverage)
- ❌ **Cons**: IAM Handwriting (current dataset) is text-line focused, NIST is character-focused
- ❌ **Cons**: Integration effort (~20 hours) for 3.7% improvement not justified

**Recommendation**: ❌ **REJECT** - No meaningful coverage improvement

**Estimated Integration Effort**: 20-30 hours (download, format conversion, annotation alignment)

---

### 2. FormulaNet (Mathematical Formulas)

**Source**: https://github.com/felix-schmitt/FormulaNet

**Dataset Details**:
- **Size**: 46,672 pages (44,338 train, 2,334 val)
- **Content**: Mathematical formulas from arXiv STEM documents
- **Format**: COCO JSON annotations (13 label types including formulas)
- **License**: CC-BY-4.0
- **Quality**: Good (FCOS baseline mAP ~0.75)

**Target FR**: FR-4.2.7 (Figure/Formula Detection)

**Current Status**: ✅ SUFFICIENT (45,976/1,500 samples, 3065.1%)

**Analysis**:
- ✅ **Pros**: COCO format (compatible), specialized formula annotations
- ❌ **Cons**: FR-4.2.7 already exceeded by 3065% (30× requirement)
- ❌ **Cons**: Copyright restrictions - must download from arXiv manually (no direct access)
- ❌ **Cons**: DocLayNet "Picture" class already covers formulas (class 7)

**Recommendation**: ❌ **REJECT** - Already over 30× target, copyright friction

**Estimated Integration Effort**: 30-40 hours (arXiv scraping, format alignment, deduplication)

---

### 3. Kleister-Charity (UK Charity Reports)

**Source**: https://github.com/applicaai/kleister-charity

**Dataset Details**:
- **Size**: 2,778 documents (1,729 train, 440 dev, 609 test)
- **Content**: PDF reports from British charitable organizations
- **Format**: TSV with 4 OCR variants (pdf2djvu, Tesseract, Textract, hybrid)
- **License**: Open-access research data (UK Charity Commission source)
- **Quality**: Medium (multi-OCR but focused on KIE task)

**Target FR**: FR-2.1 (Document Classification) - "Charity Report" document type

**Current Status**: ✅ SUFFICIENT (71,694/10,000 samples, 716.9%)

**Analysis**:
- ✅ **Pros**: Niche document type (charity reports)
- ❌ **Cons**: FR-2.1 already exceeded by 716% (7× requirement)
- ❌ **Cons**: Small dataset (2,778 samples) with narrow domain (UK charities only)
- ❌ **Cons**: Focused on Key Information Extraction (KIE), not document preprocessing
- ❌ **Cons**: Would add <4% to existing classification dataset

**Recommendation**: ❌ **REJECT** - Minimal value for already saturated FR

**Estimated Integration Effort**: 10-15 hours (git-annex download, PDF extraction, classification mapping)

---

### 4. Kleister-NDA (Legal Non-Disclosure Agreements)

**Source**: https://github.com/applicaai/kleister-nda

**Dataset Details**:
- **Size**: 540 documents (254 train, 83 dev, 203 test)
- **Content**: NDAs from SEC Edgar Database
- **Format**: TSV with multi-OCR extractions
- **License**: Open-source (SEC source, no explicit license)
- **Quality**: Medium (KIE-focused)

**Target FR**: FR-2.1 (Document Classification) - "Legal NDA" document type

**Current Status**: ✅ SUFFICIENT (71,694/10,000 samples, 716.9%)

**Analysis**:
- ✅ **Pros**: Legal document type (diversifies document classification)
- ❌ **Cons**: FR-2.1 already exceeded by 716%
- ❌ **Cons**: Tiny dataset (540 samples) - adds <1% to existing corpus
- ❌ **Cons**: KIE task focus, not preprocessing quality assessment
- ❌ **Cons**: Very narrow domain (legal NDAs only)

**Recommendation**: ❌ **REJECT** - Too small, wrong task focus, FR already saturated

**Estimated Integration Effort**: 8-12 hours (similar to Kleister-Charity)

---

### 5. SciTSR (Scientific Table Structure Recognition)

**Source**: https://github.com/Academic-Hammer/SciTSR

**Dataset Details**:
- **Size**: 15,000 tables (12,000 train, 3,000 test)
- **Content**: Scientific tables from academic papers
- **Format**: JSON (cell structure, LaTeX, relations), PDF + images
- **License**: MIT
- **Quality**: High (cell-level annotations, LaTeX ground-truth)

**Target FR**: FR-4.2.6 (Table Detection)

**Current Status**: ✅ SUFFICIENT (58,022/2,000 samples, 2901.1%)

**Analysis**:
- ✅ **Pros**: MIT license, detailed cell structure annotations, LaTeX ground-truth
- ✅ **Pros**: Focused on complex table structures (716 complicated examples)
- ❌ **Cons**: FR-4.2.6 already exceeded by 2901% (29× requirement)
- ❌ **Cons**: DocLayNet covers table detection (class 6) extensively
- ❌ **Cons**: Pre-processed chunks "may contain noise" (per creators)
- ⚠️ **Note**: Could be useful for Phase 3+ (table structure recognition sub-task)

**Recommendation**: ❌ **REJECT** (for Phase 1-2) - FR already 29× target
**Future Consideration**: ⚠️ **DEFER** to Phase 3 (table structure sub-task)

**Estimated Integration Effort**: 25-35 hours (PDF extraction, annotation conversion, relation mapping)

---

### 6. PokemonCards (Trading Card Images)

**Source**: https://huggingface.co/datasets/TheFusion21/PokemonCards

**Dataset Details**:
- **Size**: 13,139 trading cards (9.28 MB)
- **Content**: Pokemon trading cards with captions
- **Format**: Parquet (image URLs, auto-generated captions)
- **License**: CC-BY-NC-4.0 (non-commercial)
- **Quality**: Medium (machine-generated captions)

**Target FRs**:
- FR-4.4 (Parasitic Content Detection) - borders, frames, watermarks
- FR-7.1 (DQS Routing Matrix) - high-quality, structured layouts

**Current Status**:
- FR-4.4: ❌ CRITICAL GAP (0/10,000 samples)
- FR-7.1: ⚠️ PARTIAL (6,400/57,500 samples)

**Analysis**:
- ✅ **Pros**: Highly structured layouts (borders, frames, logos)
- ✅ **Pros**: Consistent quality (professional card designs)
- ✅ **Pros**: Could provide DQS routing samples (high structural complexity)
- ❌ **Cons**: **License incompatible** - CC-BY-NC-4.0 restricts commercial use
- ❌ **Cons**: Trading card borders ≠ document headers/footers/watermarks
- ❌ **Cons**: Not representative of real document parasitic content
- ❌ **Cons**: FR-4.4 needs document-specific annotations (headers, footers, page numbers)
- ❌ **Cons**: Too narrow domain (gaming cards vs. business documents)

**Recommendation**: ❌ **REJECT** - License incompatible, poor domain match

**Estimated Integration Effort**: 15-20 hours (image download, border detection, annotation creation)

**Note**: If pursuing FR-4.4, better to generate synthetic parasitic content from DocLayNet (headers/footers/watermarks) than use trading cards.

---

### 7. FinePDFs-Edu (Educational PDF Extractions)

**Source**: https://huggingface.co/datasets/HuggingFaceFW/finepdfs-edu

**Dataset Details**:
- **Size**: Large-scale (70+ languages, multiple parquet files)
- **Content**: **TEXT EXTRACTIONS ONLY** (not PDF files or images)
- **Format**: Parquet (text, metadata, quality scores)
- **License**: Croissant standard documentation
- **Quality**: High (educational content filtering, LID scores)

**Target FR**: None (text-only dataset)

**Analysis**:
- ❌ **Cons**: **No visual content** - only extracted text
- ❌ **Cons**: Image preprocessing detector requires PDFs/images, not text
- ❌ **Cons**: Cannot assess layout, quality, or preprocessing needs from text alone
- ❌ **Cons**: Wrong modality for entire project scope

**Recommendation**: ❌ **REJECT** - Not applicable (text-only)

**Estimated Integration Effort**: N/A (incompatible modality)

---

### 8. VidOre V3 Finance (Financial Document RAG Benchmark)

**Source**: https://huggingface.co/datasets/vidore/vidore_v3_finance_en

**Dataset Details**:
- **Size**: 2,940 pages from 6 unique financial documents
- **Content**: Banking annual reports (JPMorgan Chase 2024 Form 10-K filings)
- **Format**: Parquet (markdown text, images, metadata, bounding boxes)
- **License**: Not explicitly specified
- **Quality**: High (professionally formatted financial reports)

**Target FRs**:
- FR-4.4 (Parasitic Content Detection) - headers, footers, page numbers in financial reports
- FR-2.1 (Document Classification) - "Financial Report" document type
- FR-7.1 (DQS Routing Matrix) - high-quality, complex financial layouts

**Current Status**:
- FR-4.4: ❌ CRITICAL GAP (0/10,000 samples)
- FR-2.1: ✅ SUFFICIENT (71,694/10,000 samples, 716.9%)
- FR-7.1: ⚠️ PARTIAL (6,400/57,500 samples)

**Analysis**:
- ✅ **Pros**: Financial reports typically have consistent headers/footers/page numbers
- ✅ **Pros**: High-quality professional documents (banking sector)
- ✅ **Pros**: Bounding box annotations already provided (though for RAG eval)
- ✅ **Pros**: 2,940 pages could contribute to FR-4.4 coverage
- ✅ **Pros**: Complex layouts (tables, charts, multi-column) useful for FR-7.1
- ⚠️ **Mixed**: RAG evaluation focus (not preprocessing), but annotations adaptable
- ❌ **Cons**: Very small corpus (6 unique documents = low diversity)
- ❌ **Cons**: No explicit parasitic content annotations (would need to generate)
- ❌ **Cons**: Single domain (banking) limits generalization
- ❌ **Cons**: FR-2.1 already at 716% (marginal value)

**Parasitic Content Potential**:
Financial reports typically contain:
- **Headers**: Company name, document title, section headers
- **Footers**: Page numbers, copyright notices, disclosure statements
- **Watermarks**: "Confidential", "Draft", regulatory marks
- **Repeating Elements**: Navigation aids, chapter markers

However:
- Only 6 unique documents (limited header/footer diversity)
- Would need to generate bounding boxes for parasitic elements (not annotated)
- Better alternatives: DocLayNet (69K pages) or synthetic generation

**DQS Routing Potential**:
- High structural complexity (tables, multi-column, charts)
- Consistent high quality (professional reports)
- Could add 2,940 samples to FR-7.1 (currently 6,400/57,500)
- Represents 5.1% progress toward target

**Recommendation**: ⚠️ **CONDITIONAL ACCEPT** (as FR-4.4 fallback)

**Priority**: P2 - Monitor FR-4.4 weak supervision progress (currently 16% at 408/2587 docs). If weak supervision completes successfully, VidOre not needed. If it fails, VidOre could provide fallback option before commercial annotation.

**Estimated Integration Effort**: 8-12 hours
- Download from HuggingFace (2-3 hours, ~2.9K pages)
- Extract parasitic content patterns (3-4 hours)
- Generate bounding box annotations (3-5 hours)
- Validate against FR-4.4 schema

**Cost-Benefit**:
- **If FR-4.4 weak supervision succeeds**: ❌ Not needed
- **If FR-4.4 weak supervision fails**: ✅ Useful fallback (29.4% of 10K target)
- **For FR-7.1**: ⚠️ Marginal (5.1% progress, can scale existing weak supervision instead)

**Decision Tree**:
```
FR-4.4 Weak Supervision (2,587 docs in progress)
    ↓
[Completes Successfully?]
    ↓                    ↓
   YES                  NO
    ↓                    ↓
Skip VidOre      Try VidOre (2.9K pages)
    ↓                    ↓
                  [Still insufficient?]
                         ↓
                  Commercial annotation
                  (ScaleAI, $500)
```

---

## Summary Comparison Table

| Dataset | Size | Target FR | Current Coverage | Gap Closed | License | Effort (hrs) | Recommendation |
|---------|------|-----------|------------------|------------|---------|--------------|----------------|
| NIST DB-19 | 810K | FR-5.1 | 103.7% | +0% | Public | 20-30 | ❌ REJECT |
| FormulaNet | 46.7K | FR-4.2.7 | 3065.1% | +0% | CC-BY-4.0 | 30-40 | ❌ REJECT |
| Kleister-Charity | 2.8K | FR-2.1 | 716.9% | +0% | Open | 10-15 | ❌ REJECT |
| Kleister-NDA | 540 | FR-2.1 | 716.9% | +0% | Open | 8-12 | ❌ REJECT |
| SciTSR | 15K | FR-4.2.6 | 2901.1% | +0% | MIT | 25-35 | ❌ REJECT (defer Phase 3) |
| PokemonCards | 13.1K | FR-4.4, FR-7.1 | 0%, 11.1% | Poor match | CC-BY-NC-4.0 | 15-20 | ❌ REJECT (license) |
| FinePDFs-Edu | Large | None | N/A | N/A | Croissant | N/A | ❌ REJECT (text-only) |
| **VidOre V3 Finance** | **2.9K** | **FR-4.4** | **0%** | **+29.4%** | **Unspecified** | **8-12** | **⚠️ CONDITIONAL** (FR-4.4 fallback) |

---

## Alternative Recommendations for Critical Gaps

### FR-4.4: Parasitic Content Detection (CRITICAL GAP)

**Current Approach**: Weak supervision script generating from DocLayNet (in progress)

**Alternatives** (if weak supervision fails):
1. ✅ **Synthetic generation**: Add headers/footers/watermarks to DocLayNet pages
   - Effort: 15-20 hours
   - Cost: $0
   - Quality: High (controllable annotations)

2. ✅ **PubLayNet subset**: 360K+ document images with layout annotations
   - Effort: 10-15 hours (already have dataset)
   - Cost: $0
   - Quality: High (real documents)

3. ⚠️ **Commercial annotation**: ScaleAI/Labelbox on existing PDFs
   - Effort: 5-10 hours (setup)
   - Cost: $500 (10K samples @ $0.05/sample)
   - Quality: Very high (human annotations)

**Recommendation**: Continue with weak supervision (in progress at 16%). If it fails, use synthetic generation (option 1).

### FR-7.1: DQS Routing Matrix (PARTIAL - 11.1%)

**Current Approach**: Weak supervision generated 6,400 samples (7/9 bins)

**Scaling Options**:
1. ✅ **Generate more from DocLayNet**: Scale to 57,500 samples
   - Effort: 1 hour (re-run with larger sample size)
   - Cost: $0
   - Quality: Same as current (classical CV metrics)

2. ✅ **Sample from DocSynth-300K**: 300K synthetic samples available
   - Effort: 2-3 hours (adapt script)
   - Cost: $0
   - Quality: High (synthetic but diverse)

3. ✅ **Combine DocLayNet + DocSynth**: 60K balanced samples
   - Effort: 3-4 hours
   - Cost: $0
   - Quality: Best (real + synthetic diversity)

**Recommendation**: Scale weak supervision to 60K samples using DocLayNet + DocSynth (option 3).

---

## Cost-Benefit Analysis

### Integration Costs (if pursued)

| Dataset | Integration Effort | Expected Gain | ROI |
|---------|-------------------|---------------|-----|
| NIST DB-19 | 20-30 hours | +3.7% on FR-5.1 | ❌ Negative |
| FormulaNet | 30-40 hours | +0% on FR-4.2.7 | ❌ Negative |
| Kleister-Charity | 10-15 hours | +3.9% on FR-2.1 | ❌ Negative |
| Kleister-NDA | 8-12 hours | +0.8% on FR-2.1 | ❌ Negative |
| SciTSR | 25-35 hours | +0% on FR-4.2.6 | ❌ Negative |
| PokemonCards | 15-20 hours | Poor domain match | ❌ Negative |
| FinePDFs-Edu | N/A | N/A (incompatible) | ❌ N/A |

**Total Wasted Effort**: 108-152 hours if all pursued

**Total Gain**: <4% on already-saturated FRs (negligible model performance impact)

### Opportunity Cost

**Alternative uses of 100-150 hours**:
- ✅ Phase 1B: DPI upscaling implementation (10 hours)
- ✅ Phase 2: ML-based IQA training (80-100 hours)
- ✅ Phase 3: YOLOv8 layout detection fine-tuning (40-50 hours)
- ✅ Production hardening: API, monitoring, deployment (50-60 hours)

**Recommendation**: Invest time in Phase 1B-2 progression instead of dataset integration.

---

## Final Recommendations

### Immediate Actions (Next 7 Days)

1. ✅ **Continue FR-4.4 weak supervision** (parasitic content) - in progress (16% complete)
2. ✅ **Scale FR-7.1 weak supervision** to 60K samples (3-4 hours)
3. ❌ **Do NOT pursue** 7/8 reviewed datasets (NIST, FormulaNet, Kleister×2, SciTSR, PokemonCards, FinePDFs)
4. ⚠️ **Monitor VidOre V3 Finance** as FR-4.4 fallback (conditional on weak supervision failure)

### Phase Planning

**Phase 1 (Classical Methods)**: ✅ COMPLETE (except FR-4.4 in progress)

**Phase 1B (DPI Upscaling)**: 🎯 NEXT PRIORITY
- Integrate proven upscaling from data_ingestor project
- 10-15 hour effort, 100% test success rate

**Phase 2 (ML for IQA)**: 🎯 AFTER 1B
- MobileNetV3/EfficientNet multi-label classification
- Train on 50K weak supervision samples (already generated)

**Phase 3 (ML for Layout)**: 🎯 AFTER PHASE 2
- YOLOv8 fine-tuning on DocLayNet + DocSynth
- Table structure recognition (SciTSR could be revisited here)

---

## Licensing Summary

| Dataset | License | Commercial Use | Attribution Required | Restrictions |
|---------|---------|----------------|---------------------|--------------|
| NIST DB-19 | Public Domain | ✅ Yes | ❌ No | None |
| FormulaNet | CC-BY-4.0 | ✅ Yes | ✅ Yes | Share-alike |
| Kleister-Charity | Open (UK Gov) | ✅ Yes | ⚠️ Unclear | Cite source |
| Kleister-NDA | Open (SEC) | ✅ Yes | ⚠️ Unclear | Cite source |
| SciTSR | MIT | ✅ Yes | ✅ Yes | None |
| PokemonCards | CC-BY-NC-4.0 | ❌ **NO** | ✅ Yes | Non-commercial |
| FinePDFs-Edu | Croissant | ✅ Yes | ⚠️ Unclear | N/A (text-only) |

**Note**: PokemonCards is the only dataset with commercial use restrictions.

---

## Conclusion

**Overall Assessment**: ⚠️ **1 of 8 datasets (VidOre) has conditional value; 7 should be rejected**

**Key Findings**:
1. All target FRs are already SUFFICIENT (100%+) except FR-4.4 and FR-7.1
2. FR-4.4 (parasitic content) weak supervision in progress (16% @ 408/2,587 docs)
3. VidOre V3 Finance could provide fallback if weak supervision fails (2.9K pages = 29.4% of target)
4. FR-7.1 (DQS routing) can scale using existing DocLayNet + DocSynth
5. Integration effort (100-150 hours for all 7 rejected datasets) far exceeds marginal value

**Recommendation**:
- ✅ **Focus on Phase 1B** (DPI upscaling) and Phase 2 (ML-based IQA)
- ✅ **Scale FR-7.1** weak supervision to 60K samples (3-4 hours)
- ✅ **Monitor FR-4.4** weak supervision progress (currently 16% complete)
- ⚠️ **Bookmark VidOre V3 Finance** as FR-4.4 fallback (only download if weak supervision fails)
- ❌ **Reject 7/8 reviewed datasets** for Phase 1-2 (NIST, FormulaNet, Kleister×2, SciTSR, PokemonCards, FinePDFs)

**Decision Path for FR-4.4**:
```
1. Wait for weak supervision completion (ETA: ~5-6 hours @ current rate)
2. If success (≥10K samples): ✅ FR-4.4 closed, skip VidOre
3. If partial (5K-10K): ⚠️ Consider VidOre supplement
4. If failure (<5K): ⚠️ Try VidOre (2.9K pages) → Commercial annotation if still short
```

**Future Consideration**:
- ⚠️ **SciTSR** could be revisited in Phase 3 for table structure recognition sub-task (not detection)
- ⚠️ **VidOre V3 Finance** saved as FR-4.4 contingency option

---

**Analysis Complete**: 2025-11-14 (Updated with VidOre V3 Finance)
**Reviewed By**: Claude Code (Automated Dataset Analysis)
**Datasets Evaluated**: 8 (7 rejected, 1 conditional)
**Next Review**: After FR-4.4 weak supervision completion or Phase 1B finish
