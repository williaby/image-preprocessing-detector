# Training Data Gap Analysis - Priority Document Types

**Version**: 1.0
**Date**: 2025-11-14
**Purpose**: Identify training data gaps across functional requirements prioritized by critical document types

---

## Executive Summary

**Priority Document Type Classification:**

| Priority | Document Types | Rationale | Training Coverage Status |
|----------|----------------|-----------|--------------------------|
| **P1 (Must Have)** | PDF documents (all types) | Core use case for RAG systems | ⚠️ **Gaps in 12 FRs** |
| **P2 (Should Have)** | Handwritten, Historical/Old documents | Common in archives, critical quality issues | ⚠️ **Limited coverage** |
| **P3 (Critical Business)** | Financial, Legal documents | Business-critical accuracy requirements | ⚠️ **Moderate coverage** |
| **P4 (Nice to Have)** | Multi-lingual documents | Global business support | ✅ **Good coverage (WiLI-2018)** |

**Key Findings:**
- **COCO-Text Misalignment**: Natural scene text (street signs, storefronts) - **DOES NOT** cover any priority document types
- **Critical Gaps**: 12 FRs lack PDF training data (binarization, illumination, warping, bleed-through, perspective, parasitic content, footnotes, figures, vertical text, watermarks, stamps, margin annotations)
- **Handwriting Coverage**: Limited to signatures (SignaTR6K) and general handwriting (IAM) - missing mixed document scenarios
- **Historical Documents**: Minimal coverage - synthetic degradation only, no real historical corpus

---

## Priority Document Type Definitions

### Priority 1: PDF Documents (MUST HAVE)

**Requirement**: All FRs must have PDF training data

**PDF Subtypes:**
1. **Image-Only PDFs**: Scanned documents (most common in archives)
2. **Born-Digital PDFs**: Native PDF creation (modern documents)
3. **Hybrid PDFs**: Mixed scanned + digital content

**Current Coverage**: DocLayNet (80k pages, mixed types), OmniDocBench (1,358 pages)

**Gaps**: 12 FRs lack specific PDF training data (see gap matrix below)

### Priority 2: Handwritten & Historical Documents (SHOULD HAVE)

**Document Types:**
- **Handwritten notes**: Student notes, meeting notes, annotations
- **Signatures**: Contract signatures, form signatures
- **Mixed documents**: Printed text + handwritten annotations
- **Historical manuscripts**: Archives, aged documents, degraded paper
- **Scanned archives**: Old scans with age-related defects

**Current Coverage:**
- ✅ Signatures: SignaTR6K (6k signatures, CC BY 4.0)
- ✅ General handwriting: IAM Database (13,353 lines, MIT)
- ⚠️ Historical: Synthetic degradation only (no real corpus)
- ❌ Mixed documents: No training data

### Priority 3: Financial & Legal Documents (CRITICAL BUSINESS)

**Document Types:**
- **Financial**: Invoices, receipts, bank statements, financial reports, tax forms
- **Legal**: Contracts, court documents, legal briefs, notarized forms

**Current Coverage:**
- ✅ Financial tables: TableBank (417k tables), FinTabNet (14 GB financial tables), PubTabNet (568k tables)
- ✅ Invoices/Receipts: Voxel51 Receipts (713 images), HITL Receipt OCR (192 images), Kaggle Invoices (1,414 images)
- ✅ Financial reports: DocLayNet financial subset
- ⚠️ Legal documents: DocLayNet legal subset only (limited)
- ❌ Contracts: No specific training data
- ❌ Notarized forms: No training data

### Priority 4: Multi-lingual Documents (NICE TO HAVE)

**Document Types:**
- Non-English documents (Spanish, French, German, Chinese, Japanese, Arabic, etc.)
- Mixed scripts (Latin + CJK, Arabic + English)
- International business documents

**Current Coverage:**
- ✅ **EXCELLENT**: WiLI-2018 (235,000 paragraphs, 235 languages, Apache-2.0)
- ✅ CJK support: Wili-2018 includes Chinese, Japanese, Korean
- ✅ Arabic support: Wili-2018 includes Arabic, Farsi, Urdu

---

## FR × Priority Document Type Gap Matrix

**Legend:**
- ✅ **Good coverage**: Multiple datasets, diverse document types
- ⚠️ **Partial coverage**: Limited datasets or document type diversity
- ❌ **No coverage**: Missing training data for this priority type
- 🔲 **Not applicable**: FR doesn't require this document type

### File Format Analysis (FR-2.x)

| FR | Description | PDF | Handwritten | Historical | Financial | Legal | Multi-lingual |
|----|-------------|-----|-------------|------------|-----------|-------|---------------|
| **FR-2.1** | PDF Type Classification | ✅ DocLayNet (80k), OmniDocBench | 🔲 N/A | ⚠️ Synthetic only | ✅ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |
| **FR-2.2** | Office Format Detection | 🔲 N/A (Phase 5) | 🔲 N/A | 🔲 N/A | 🔲 N/A | 🔲 N/A | 🔲 N/A |
| **FR-2.3** | Learned Quality Assessment | ✅ TableBank (50k synthetic) | ❌ No data | ❌ No data | ⚠️ Receipts (1k) | ❌ No data | 🔲 N/A |
| **FR-2.4** | Text Detection Gate | ✅ DocLayNet + TableBank | ⚠️ SignaTR6K | ⚠️ Synthetic only | ✅ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |

**Gap Summary (FR-2.x)**:
- **PDF Coverage**: Good overall, weak on learned quality assessment
- **Handwritten**: Missing for quality assessment
- **Historical**: Only synthetic degradation (no real corpus)

### Image Quality Detection (FR-3.x)

| FR | Description | PDF | Handwritten | Historical | Financial | Legal | Multi-lingual |
|----|-------------|-----|-------------|------------|-----------|-------|---------------|
| **FR-3.1** | Blur Detection | ✅ TableBank (50k synthetic) | ⚠️ Synthetic only | ⚠️ Synthetic only | ✅ TableBank financial | ⚠️ Synthetic | ⚠️ Limited |
| **FR-3.2** | Skew Detection | ✅ TableBank (50k synthetic) | ⚠️ Synthetic only | ⚠️ Synthetic only | ✅ TableBank financial | ⚠️ Synthetic | ⚠️ Limited |
| **FR-3.3** | Noise Detection | ✅ TableBank (10k synthetic) | ⚠️ Synthetic only | ⚠️ Synthetic only | ✅ TableBank financial | ⚠️ Synthetic | ⚠️ Limited |
| **FR-3.4** | Image Resolution | ✅ DocLayNet (mixed DPI) | ⚠️ SignaTR6K | ⚠️ Synthetic | ✅ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |
| **FR-3.5** | DPI Detection | ✅ DocLayNet (mixed DPI) | ⚠️ SignaTR6K | ⚠️ Synthetic | ✅ Mobile receipts | ⚠️ Limited | ⚠️ Limited |
| **FR-3.6** | DPI Upscaling | ✅ Synthetic 72-150 DPI | ⚠️ Limited | ⚠️ Archive samples | ✅ Mobile receipts | ⚠️ Limited | ⚠️ Limited |
| **FR-3.7** | Contrast Assessment | ✅ TableBank (10k synthetic) | ⚠️ Synthetic only | ⚠️ Synthetic fading | ✅ TableBank financial | ⚠️ Synthetic | ⚠️ Limited |
| **FR-3.8** | **Binarization Quality** | ❌ **No specific data** | ⚠️ SignaTR6K variants | ❌ **No real corpus** | ❌ **No data** | ❌ **No data** | 🔲 N/A |
| **FR-3.9** | **Illumination Uniformity** | ❌ **No specific data** | 🔲 N/A | ❌ **No data** | ❌ **No data** | ❌ **No data** | 🔲 N/A |
| **FR-3.10** | **Bleed-Through Detection** | ❌ **No specific data** | 🔲 N/A | ❌ **No real corpus** | ❌ **No data** | ❌ **No data** | 🔲 N/A |
| **FR-3.11** | **Warping/Curvature** | ❌ **Limited** (SynDocDS synthetic) | 🔲 N/A | ❌ **No real corpus** | ❌ **No data** | ❌ **No data** | 🔲 N/A |
| **FR-3.12** | **Perspective Distortion** | ❌ **No specific data** | 🔲 N/A | 🔲 N/A | ❌ **No data** | ❌ **No data** | 🔲 N/A |
| **FR-3.14** | Hybrid IQA (Embedded Images) | ✅ DocLayNet, DocSynth-300K | 🔲 N/A | ⚠️ Limited | ✅ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |

**Gap Summary (FR-3.x)**:
- **Critical PDF Gaps**: Binarization (FR-3.8), Illumination (FR-3.9), Bleed-through (FR-3.10), Warping (FR-3.11), Perspective (FR-3.12)
- **Handwritten**: Mostly synthetic augmentation, missing real degradation
- **Historical**: No real historical corpus for age-related defects (fading, bleed-through, warping)

### Layout Elements (FR-4.x)

| FR | Description | PDF | Handwritten | Historical | Financial | Legal | Multi-lingual |
|----|-------------|-----|-------------|------------|-----------|-------|---------------|
| **FR-4.1** | Layout Detection Model | ✅ DocLayNet (42k), DocSynth-300K | 🔲 N/A | ⚠️ DocLayNet subset | ✅ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |
| **FR-4.2** | Layout Element Detection (11 classes) | ✅ DocLayNet COCO (42k) | 🔲 N/A | ⚠️ DocLayNet subset | ✅ TableBank (417k tables) | ⚠️ DocLayNet legal | ⚠️ Limited |
| **FR-4.3** | Bounding Box Format (COCO) | ✅ DocLayNet COCO | 🔲 N/A | ⚠️ DocLayNet subset | ✅ TableBank COCO | ⚠️ Limited | ⚠️ Limited |
| **FR-4.4** | **Parasitic Content Detection** | ❌ **Limited** (DocLayNet headers/footers) | 🔲 N/A | ⚠️ Limited | ❌ **No specific data** | ❌ **No specific data** | 🔲 N/A |
| **FR-4.5** | **Footnote Linking** | ❌ **Limited** (DocLayNet footnotes) | 🔲 N/A | ⚠️ Limited | ❌ **No specific data** | ⚠️ Legal brief samples | 🔲 N/A |
| **FR-4.6** | **Figure-Caption Linking** | ❌ **Limited** (DocLayNet captions) | 🔲 N/A | ⚠️ Limited | ❌ **No specific data** | ❌ **No data** | 🔲 N/A |
| **FR-4.7** | **Vertical Text Orientation** | ❌ **No PDF-specific data** | 🔲 N/A | 🔲 N/A | ❌ **No data** | ❌ **No data** | ⚠️ WiLI-2018 (CJK) |
| **FR-4.8** | Handwriting Detection (Mixed Docs) | ⚠️ DocLayNet + IAM overlay | ✅ IAM (13k lines), SignaTR6K (6k) | ⚠️ Limited | ❌ **No mixed docs** | ❌ **No mixed docs** | ⚠️ Limited |
| **FR-4.11** | Table Structure Extraction | ✅ PubTables-1M (1M), TableBank (417k), FinTabNet, PubTabNet | 🔲 N/A | ⚠️ Limited | ✅ FinTabNet (14GB), PubTables-1M | ⚠️ Limited | ⚠️ Limited |
| **FR-4.12** | Reading Order Prediction | ⚠️ DocLayNet (synthetic reading order) | 🔲 N/A | ⚠️ Limited | ⚠️ DocLayNet financial | ⚠️ DocLayNet legal | ⚠️ Limited |

**Gap Summary (FR-4.x)**:
- **Critical PDF Gaps**: Parasitic content (FR-4.4), Footnote linking (FR-4.5), Figure-caption linking (FR-4.6), Vertical text (FR-4.7)
- **Handwritten Mixed Docs**: Missing financial/legal forms with handwritten annotations
- **Historical**: Limited layout diversity in historical documents

### Specialized Content Detection (FR-5.x)

| FR | Description | PDF | Handwritten | Historical | Financial | Legal | Multi-lingual |
|----|-------------|-----|-------------|------------|-----------|-------|---------------|
| **FR-5.1** | Mathematical Content | ✅ DocLayNet Formula class | ⚠️ Handwritten equations (limited) | ⚠️ Limited | ⚠️ Limited | 🔲 N/A | ⚠️ Limited |
| **FR-5.2** | Handwritten Content | ⚠️ DocLayNet + handwriting overlay | ✅ SignaTR6K (6k), IAM (13k) | ⚠️ Limited | ❌ **No mixed financial docs** | ❌ **No mixed legal docs** | ⚠️ Limited |
| **FR-5.3** | Language Detection | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited | ✅ **WiLI-2018 (235 languages)** |
| **FR-5.4** | **Watermark Detection** | ❌ **No real corpus** (synthetic only) | 🔲 N/A | ⚠️ Limited | ❌ **No business watermarks** | ❌ **No legal watermarks** | 🔲 N/A |
| **FR-5.5** | **Stamp/Seal Detection** | ⚠️ StaVer (400 images) + DDI-100 | 🔲 N/A | ⚠️ DDI-100 (99k) | ❌ **No customs/official stamps** | ❌ **No notary seals** | ⚠️ Limited |
| **FR-5.6** | Signature Detection | ⚠️ Limited | ✅ SignaTR6K (6k signatures) | ⚠️ Limited | ⚠️ Invoice signatures | ⚠️ Contract signatures | ⚠️ Limited |
| **FR-5.7** | **Margin Annotation Detection** | ❌ **No real corpus** | ⚠️ Limited | ❌ **No manuscript corpus** | 🔲 N/A | ⚠️ Peer review annotations | 🔲 N/A |

**Gap Summary (FR-5.x)**:
- **Critical PDF Gaps**: Watermark detection (FR-5.4), Stamp/seal detection (FR-5.5), Margin annotations (FR-5.7)
- **Handwritten**: Good signature/general coverage, missing mixed document scenarios
- **Historical**: Missing manuscript annotation corpus

---

## Critical Training Data Gaps (Priority P1: PDF Documents)

### High-Priority Gaps (Immediate Action Required)

| FR | Gap Description | Impact | Recommended Dataset | Size | Priority |
|----|-----------------|--------|---------------------|------|----------|
| **FR-3.8** | Binarization Quality | High - Historical archives, faded documents | **DIBCO** (Document Image Binarization Contest) | ~500 MB | **HIGH** |
| **FR-3.9** | Illumination Uniformity | High - Mobile captures, book scans | **DocBank Mobile** or **SmartDoc** | ~200 MB | **HIGH** |
| **FR-3.10** | Bleed-Through Detection | Medium - Historical manuscripts, thin paper | **Historical manuscript corpus** (Yale, LC) | ~1 GB | **MEDIUM** |
| **FR-3.11** | Warping/Curvature | High - Book scans, bound documents | **AnyPhotoDoc 6300** (real camera captures) | ~2 GB | **HIGH** |
| **FR-3.12** | Perspective Distortion | Medium - Mobile captures, desktop photos | **SmartDoc** dataset | ~200 MB | **MEDIUM** |
| **FR-4.4** | Parasitic Content | Medium - Headers, footers, page numbers | **Augment DocLayNet** (annotate headers/footers) | N/A | **MEDIUM** |
| **FR-4.5** | Footnote Linking | Low - Academic papers, legal briefs | **ArXiv papers** + **Legal brief corpus** | ~500 MB | **LOW** |
| **FR-4.6** | Figure-Caption Linking | Medium - Academic papers, technical docs | **ArXiv papers** (figure-rich) | ~500 MB | **MEDIUM** |
| **FR-4.7** | Vertical Text Orientation | Low - Asian languages, rotated labels | **Synthetic rotation** + **CJK corpus** | ~100 MB | **LOW** |
| **FR-5.4** | Watermark Detection | Medium - Legal documents, business docs | **Synthetic watermark overlays** | ~100 MB | **MEDIUM** |
| **FR-5.5** | Stamp/Seal Detection | Medium - Government docs, contracts | **Expand StaVer** + **Government doc corpus** | ~500 MB | **MEDIUM** |
| **FR-5.7** | Margin Annotation Detection | Low - Manuscripts, peer reviews | **Historical manuscript corpus** | ~500 MB | **LOW** |

**Total Additional Training Data Needed**: ~5.6 GB

---

## COCO-Text Evaluation Against Priority Document Types

### COCO-Text Dataset Profile

| Attribute | Details |
|-----------|---------|
| **Dataset** | COCO-Text v2 |
| **Size** | 53 MB (annotations only, images from COCO dataset) |
| **Images** | 63,686 images (natural scenes) |
| **Text Instances** | 173,589 text annotations |
| **Document Types** | **Natural scenes**: Street signs, storefronts, product labels, license plates, building signage |
| **License** | CC-BY-4.0 |

### Priority Document Type Alignment

| Priority | Document Type | COCO-Text Coverage | Alignment Score |
|----------|---------------|-------------------|-----------------|
| **P1** | PDF documents | ❌ **0% - No PDFs** | **0/10** |
| **P2** | Handwritten documents | ❌ **0% - Printed signage only** | **0/10** |
| **P2** | Historical documents | ❌ **0% - Modern scenes only** | **0/10** |
| **P3** | Financial documents | ❌ **0% - No invoices/receipts** | **0/10** |
| **P3** | Legal documents | ❌ **0% - No contracts/forms** | **0/10** |
| **P4** | Multi-lingual documents | ⚠️ **Limited - Some foreign signage** | **2/10** |

**Overall Alignment Score**: **2/60 (3%)** - **CRITICAL MISALIGNMENT**

### Use Case Analysis

**COCO-Text Strengths (Not Relevant to This Project):**
- ✅ Natural scene text detection (street signs, storefronts)
- ✅ Multi-orientation text (angled signs, curved text)
- ✅ Text in images (outdoor advertising, building facades)

**Project Requirements (NOT Met by COCO-Text):**
- ❌ PDF document text detection
- ❌ Printed document layouts (paragraphs, columns)
- ❌ Financial/legal document structure
- ❌ Historical manuscript text
- ❌ Handwritten annotations

### Recommendation: **REMOVE COCO-Text**

**Rationale:**
1. **Zero alignment** with Priority 1-3 document types (PDF, handwritten, historical, financial, legal)
2. **Minimal alignment** with Priority 4 (multi-lingual) - only 2/10 score
3. **Benchmarking cost** - requires downloading COCO images (18 GB)
4. **Better alternatives exist**:
   - **OmniDocBench**: PDF documents with text detection annotations
   - **DocLayNet**: Diverse document layouts with text regions
   - **ICDAR MLT 2019**: Multi-lingual text detection in **documents** (not natural scenes)

**Alternative Use Case**: If project scope expands to **mobile-captured signage** or **street scene text extraction**, reconsider COCO-Text.

**Action**: Remove COCO-Text from benchmark registry and training datasets.

---

## Priority 2 (P2) Gaps: Handwritten & Historical Documents

### Handwritten Document Coverage

| Scenario | Current Coverage | Gap | Recommendation |
|----------|------------------|-----|----------------|
| **Signatures** | ✅ SignaTR6K (6k signatures) | None | Maintain |
| **General handwriting** | ✅ IAM Database (13k lines) | None | Maintain |
| **Mixed documents** (printed + handwritten) | ❌ **No training data** | **HIGH** | **Acquire mixed document corpus** |
| **Handwritten forms** | ⚠️ Limited (synthetic overlay) | **MEDIUM** | **Government form dataset** |
| **Handwritten annotations** | ❌ **No training data** | **MEDIUM** | **Annotated manuscript corpus** |

**Recommended Datasets:**
1. **IAM Forms** (handwritten form filling) - ~500 MB
2. **ICDAR Handwriting Recognition** (mixed documents) - ~1 GB
3. **Annotated manuscript corpus** (margin notes) - ~500 MB

### Historical Document Coverage

| Defect Type | Current Coverage | Gap | Recommendation |
|-------------|------------------|-----|----------------|
| **Age-related fading** | ⚠️ Synthetic only | **HIGH** | **Historical archive corpus** |
| **Bleed-through** | ⚠️ Synthetic only | **HIGH** | **Yale manuscript collection** |
| **Warping/curvature** | ⚠️ Synthetic (SynDocDS) | **MEDIUM** | **Historical bound volumes** |
| **Stains/degradation** | ⚠️ Synthetic (DDI-100) | **MEDIUM** | **Archive degradation corpus** |

**Recommended Datasets:**
1. **Yale Historical Manuscripts** (binarization, fading) - ~1 GB
2. **Library of Congress Archive Samples** (bleed-through, warping) - ~2 GB
3. **DIBCO Challenge** (document binarization) - ~500 MB

---

## Priority 3 (P3) Gaps: Financial & Legal Documents

### Financial Document Coverage

| Document Type | Current Coverage | Gap | Recommendation |
|---------------|------------------|-----|----------------|
| **Invoices** | ✅ Kaggle Invoices (1,414), Mobile receipts (713+192) | None | Maintain |
| **Financial tables** | ✅ FinTabNet (14 GB), PubTabNet (27 GB), TableBank (417k) | None | Maintain |
| **Bank statements** | ⚠️ Limited (DocLayNet subset) | **MEDIUM** | **Bank statement corpus** |
| **Tax forms** | ❌ **No training data** | **MEDIUM** | **IRS form dataset** |
| **Financial reports** | ✅ DocLayNet financial subset | None | Maintain |

**Recommended Datasets:**
1. **Bank Statement Dataset** (multi-page statements) - ~500 MB
2. **Tax Form Dataset** (IRS forms, filled/unfilled) - ~300 MB

### Legal Document Coverage

| Document Type | Current Coverage | Gap | Recommendation |
|---------------|------------------|-----|----------------|
| **Contracts** | ⚠️ DocLayNet legal subset | **HIGH** | **Contract corpus** |
| **Court documents** | ⚠️ DocLayNet legal subset | **MEDIUM** | **Legal brief dataset** |
| **Notarized forms** | ❌ **No training data** | **MEDIUM** | **Notary seal dataset** |
| **Legal briefs** | ⚠️ Limited | **MEDIUM** | **Court filing corpus** |

**Recommended Datasets:**
1. **Contract Dataset** (diverse contract types) - ~1 GB
2. **Legal Brief Corpus** (court filings) - ~500 MB
3. **Notarized Document Dataset** (stamps, seals) - ~300 MB

---

## Recommended Actions (Prioritized)

### Immediate (Phase 2 Week 3-4)

1. **Remove COCO-Text** - 0% alignment with priority document types
2. **Acquire DIBCO Dataset** - Binarization quality (FR-3.8, historical documents)
3. **Download SmartDoc** - Illumination, perspective (FR-3.9, FR-3.12, mobile captures)

### Near-Term (Phase 3 Week 1-2)

4. **Acquire AnyPhotoDoc 6300** - Warping/curvature (FR-3.11, book scans)
5. **Download StaVer** - Stamp/seal detection (FR-5.5, government/legal docs)
6. **Acquire Mixed Handwriting Corpus** - Handwritten annotations on printed documents (FR-4.8, FR-5.2)

### Mid-Term (Phase 3 Week 3-4)

7. **Acquire Historical Manuscript Corpus** - Bleed-through, fading, annotations (FR-3.10, FR-5.7, historical documents)
8. **Expand Financial Dataset** - Bank statements, tax forms (P3 priority)
9. **Expand Legal Dataset** - Contracts, court documents, notary seals (P3 priority)

### Long-Term (Phase 4+)

10. **ArXiv Paper Corpus** - Footnote/figure linking (FR-4.5, FR-4.6, academic documents)
11. **Government Form Dataset** - Handwritten form filling, official stamps (FR-4.8, FR-5.5)
12. **Multi-lingual Expansion** - Already covered by WiLI-2018 (235 languages) - maintain only

---

## Summary Statistics

### Training Data Coverage by Priority

| Priority | Document Type | FRs Applicable | Training Data Coverage | Gap Count |
|----------|---------------|----------------|------------------------|-----------|
| **P1** | PDF documents | 48 FRs | ⚠️ **75% (36/48)** | **12 FRs missing** |
| **P2** | Handwritten | 12 FRs | ⚠️ **50% (6/12)** | **6 FRs limited/missing** |
| **P2** | Historical | 15 FRs | ⚠️ **27% (4/15)** | **11 FRs limited/missing** |
| **P3** | Financial | 25 FRs | ⚠️ **68% (17/25)** | **8 FRs limited/missing** |
| **P3** | Legal | 20 FRs | ⚠️ **50% (10/20)** | **10 FRs limited/missing** |
| **P4** | Multi-lingual | 8 FRs | ✅ **88% (7/8)** | **1 FR limited** |

### Additional Training Data Needed

| Priority | Total Size | High Priority FRs | Estimated Cost (GCS) |
|----------|-----------|-------------------|----------------------|
| **P1 (PDF)** | ~5.6 GB | 5 FRs | $0.11/month |
| **P2 (Handwritten/Historical)** | ~5 GB | 4 FRs | $0.10/month |
| **P3 (Financial/Legal)** | ~2.6 GB | 3 FRs | $0.05/month |
| **Total** | **~13.2 GB** | **12 high-priority FRs** | **$0.26/month** |

---

**Created**: 2025-11-14
**Status**: ✅ Complete - All priority document types analyzed
**Next Steps**: Remove COCO-Text, acquire high-priority datasets (DIBCO, SmartDoc, AnyPhotoDoc)
**Next Review**: Phase 3 Week 1 (after new dataset integration)
