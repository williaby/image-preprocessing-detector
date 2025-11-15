# Document Type Priority & Coverage Matrix

**Version**: 1.0
**Date**: 2025-11-14
**Purpose**: Stratify document type populations to ensure adequate training/benchmark coverage across all FRs

---

## Document Type Priority Classification

### Priority Definitions

**Based on project goals (RAG system preprocessing for business/enterprise documents):**

| Priority | Definition | Coverage Requirement |
|----------|------------|---------------------|
| **Required** | Core use cases, must have comprehensive coverage | 100% FR coverage, all file formats |
| **High** | Critical business/legal use cases | 90%+ FR coverage, primary file formats |
| **Medium** | Common scenarios, important for completeness | 70%+ FR coverage, PDF + image formats |
| **Low** | Edge cases, nice-to-have for robustness | 50%+ FR coverage, PDF only |

---

## Document Type Category Priority Ranking

### Required (Must Have - 100% Coverage)

| Document Type | Rationale | File Formats Needed | Example Use Cases |
|---------------|-----------|---------------------|-------------------|
| **Business** | Core enterprise RAG use case - reports, memos, presentations | PDF (all 3 types), DOCX, XLSX, PPTX, JPG/PNG scans | Quarterly reports, meeting minutes, business correspondence |
| **Legal** | High-stakes accuracy requirements - contracts, briefs, filings | PDF (all 3 types), scanned images | Contracts, legal briefs, court documents, compliance docs |

**Justification**: These are the primary use cases for document preprocessing in enterprise RAG systems. Legal documents require highest accuracy (liability/compliance). Business documents are the most common volume.

**Coverage Requirements**:
- All FRs must have training data for Business + Legal document types
- Must cover all PDF types (image-only, born-digital, hybrid)
- Must include both printed and handwritten annotations (signatures, margin notes)

---

### High Priority (Critical - 90%+ Coverage)

| Document Type | Rationale | File Formats Needed | Example Use Cases |
|---------------|-----------|---------------------|-------------------|
| **Financial** | Subset of Business, critical for accuracy - invoices, statements, tax forms | PDF (all 3 types), JPG/PNG receipts, XLSX | Invoices, receipts, bank statements, tax forms, financial reports |
| **Academic** | Large corpus availability, good proxy for structured documents | PDF (born-digital primarily), scanned papers | Research papers, textbooks, dissertations, journals |

**Justification**:
- **Financial**: Subset of Business, but elevated to High Priority due to accuracy requirements (monetary implications)
- **Academic**: Excellent training data availability (ArXiv, PubMed), good proxy for structured documents with tables, figures, equations

**Coverage Requirements**:
- 90%+ FR coverage for Financial (especially table structure, figures, OCR quality)
- 90%+ FR coverage for Academic (layout detection, formula detection, figure-caption linking)
- PDF (all 3 types) + mobile captures (receipts) for Financial
- PDF (born-digital) + scanned papers for Academic

---

### Medium Priority (Important - 70%+ Coverage)

| Document Type | Rationale | File Formats Needed | Example Use Cases |
|---------------|-----------|---------------------|-------------------|
| **Forms** | Common in government, healthcare, legal - structured layouts | PDF (image-only, hybrid), scanned images, JPG/PNG | Government forms, applications, surveys, questionnaires |
| **Technical** | Engineering, manuals, diagrams - specialized content | PDF (born-digital, hybrid), CAD exports | Engineering manuals, schematics, technical specifications, diagrams |
| **Historical** | Archives, digitization projects - unique quality issues | PDF (image-only primarily), scanned images | Manuscripts, archives, old newspapers, historical records |

**Justification**:
- **Forms**: Important for government/healthcare verticals, but more structured (easier to handle)
- **Technical**: Specialized use case (engineering/manufacturing), but growing demand
- **Historical**: Niche (archives, libraries), but represents extreme quality issues (good stress test)

**Coverage Requirements**:
- 70%+ FR coverage (focus on layout detection, handwriting, quality issues)
- Forms: PDF image-only + hybrid (printed forms with handwritten entries)
- Technical: PDF born-digital (CAD exports) + hybrid (annotated manuals)
- Historical: PDF image-only (scanned archives) + degradation artifacts

---

### Low Priority (Nice-to-Have - 50%+ Coverage)

| Document Type | Rationale | File Formats Needed | Example Use Cases |
|---------------|-----------|---------------------|-------------------|
| **Mobile** | Subset of other types (mobile-captured Business/Financial docs) | JPG/PNG only | Mobile-captured receipts, whiteboard photos, desktop captures |
| **Multi-lingual** | Cross-cutting concern (applies to all document types) | Same as source document type | Non-English business docs, international contracts, multi-lingual reports |

**Justification**:
- **Mobile**: Not a true document type - it's a **capture method** for other document types (Business receipts, Forms). Already covered by including mobile captures in Financial/Forms.
- **Multi-lingual**: Not a document type - it's a **language attribute** that applies to other types. Language detection (FR-5.3) already has excellent coverage (WiLI-2018, 235 languages).

**Coverage Requirements**:
- 50%+ FR coverage (mobile-specific issues: illumination, perspective, warping)
- Mobile: JPG/PNG captures of other document types
- Multi-lingual: Ensure WiLI-2018 covers target languages, augment PDF datasets with non-English samples

---

## Revised Document Type Categories (Recommendation)

**Current 8 Categories** (from document-type-coverage.md):
1. Academic
2. Business
3. Historical
4. Mobile
5. Technical
6. Legal
7. Multi-lingual
8. Forms

**Proposed Revision** (stratified by business value):

### Core Document Types (Primary Classification)

| Priority | Document Types | Coverage Target |
|----------|----------------|-----------------|
| **Required** | Business, Legal | 100% FRs |
| **High** | Financial (subset of Business), Academic | 90% FRs |
| **Medium** | Forms, Technical, Historical | 70% FRs |

### Cross-Cutting Attributes (Secondary Classification)

| Attribute | Description | Implementation |
|-----------|-------------|----------------|
| **Capture Method** | Mobile-captured, Desktop-scanned, Professional-scanned | Tag existing document types with capture method |
| **Language** | English, Spanish, French, Chinese, Multi-lingual | Tag existing document types with language attribute |
| **Content Modality** | Printed-only, Handwritten-only, Mixed (printed + handwritten) | Tag existing document types with modality |

**Rationale**: Mobile and Multi-lingual are not standalone document types - they're attributes that apply to other types. This prevents confusion and double-counting.

---

## FR × Document Type × File Format Coverage Matrix

### File Format Taxonomy

**PDF Types** (FR-2.1: PDF Type Classification):
- **Image-only PDF**: Scanned document, no digital text
- **Born-digital PDF**: Native PDF creation (Word → PDF, LaTeX → PDF)
- **Hybrid PDF**: Mixed scanned pages + digital pages

**Image Formats**:
- **JPG/PNG**: Photographs, scans, mobile captures
- **TIFF**: Professional scans, archives

**Office Formats** (Phase 5):
- **DOCX/XLSX/PPTX**: Microsoft Office documents with embedded images

---

### FR-2.1: PDF Type Classification (Phase 2)

**Requirement**: Detect image-only vs born-digital vs hybrid PDFs

**Coverage Needed**:

| Document Type | Image-only PDF | Born-digital PDF | Hybrid PDF | Current Coverage | Gap |
|---------------|----------------|------------------|------------|------------------|-----|
| **Business (Required)** | ✅ Needed | ✅ Needed | ✅ Needed | ⚠️ DocLayNet (limited business subset) | **MEDIUM** - Need more business-specific PDFs |
| **Legal (Required)** | ✅ Needed | ✅ Needed | ✅ Needed | ⚠️ DocLayNet legal subset | **HIGH** - Need contract corpus |
| **Financial (High)** | ✅ Needed | ✅ Needed | ✅ Needed | ⚠️ DocLayNet financial subset | **MEDIUM** - Need invoices, statements |
| **Academic (High)** | ⚠️ Optional | ✅ Needed | ⚠️ Optional | ✅ DocLayNet (42k pages, mixed types) | **LOW** - Good coverage |
| **Forms (Medium)** | ✅ Needed | ⚠️ Optional | ✅ Needed | ❌ No specific form dataset | **HIGH** - Need government forms |
| **Technical (Medium)** | ⚠️ Optional | ✅ Needed | ✅ Needed | ⚠️ Limited (engineering manuals) | **MEDIUM** - Need technical manuals |
| **Historical (Medium)** | ✅ Needed | 🔲 N/A | ⚠️ Optional | ⚠️ Synthetic only | **MEDIUM** - Need real archive scans |
| **Mobile (Low)** | 🔲 N/A (JPG only) | 🔲 N/A | 🔲 N/A | 🔲 N/A | None |
| **Multi-lingual (Low)** | ⚠️ Optional | ⚠️ Optional | ⚠️ Optional | ⚠️ Limited | **LOW** - Augment with non-English PDFs |

**Summary**:
- ✅ **Good coverage**: Academic PDFs (DocLayNet 42k pages, mixed types)
- ⚠️ **Gaps**: Business, Legal, Financial, Forms (need more domain-specific PDFs)
- ❌ **Critical gaps**: Legal contracts (image-only scanned + born-digital), Government forms (image-only + hybrid)

**Recommended Datasets**:
1. **Contract corpus** (Legal): Image-only scanned contracts + born-digital contracts (~1 GB)
2. **Government form dataset** (Forms): Image-only blank forms + hybrid filled forms (~500 MB)
3. **Business document corpus** (Business): Mixed types (reports, memos, presentations) (~1 GB)

---

### FR-2.4: Text Detection Gate (Phase 1)

**Requirement**: Fast text presence detection to route documents to appropriate processing branch

**Coverage Needed**: Diverse text density scenarios across file formats

| Document Type | PDF (all types) | JPG/PNG | Current Coverage | Gap |
|---------------|-----------------|---------|------------------|-----|
| **Business (Required)** | ✅ Needed | ✅ Needed | ⚠️ DocLayNet (text-heavy PDFs) | **MEDIUM** - Need pure-image business docs |
| **Legal (Required)** | ✅ Needed | ⚠️ Optional | ⚠️ DocLayNet legal (text-heavy) | **LOW** - Legal docs are typically text-heavy |
| **Financial (High)** | ✅ Needed | ✅ Needed | ⚠️ Mobile receipts (JPG, text-heavy) | **MEDIUM** - Need image-only financial PDFs |
| **Academic (High)** | ✅ Needed | ⚠️ Optional | ✅ DocLayNet + TableBank (mixed content) | **LOW** - Good coverage |
| **Forms (Medium)** | ✅ Needed | ✅ Needed | ❌ No form dataset | **HIGH** - Need blank forms (low text) + filled forms (high text) |
| **Technical (Medium)** | ✅ Needed | ✅ Needed | ⚠️ TableBank diagrams (low text) | **MEDIUM** - Need technical diagrams (pure image) |
| **Historical (Medium)** | ✅ Needed | ✅ Needed | ⚠️ Synthetic only | **MEDIUM** - Need real historical images |
| **Mobile (Low)** | 🔲 N/A | ✅ Needed | ⚠️ Mobile receipts (text-heavy only) | **HIGH** - Need pure-image mobile captures |
| **Multi-lingual (Low)** | ⚠️ Optional | ⚠️ Optional | ✅ WiLI-2018 (text-heavy) | **LOW** - Good text coverage |

**COCO-Text Applicability**: ✅ **YES - HIGHLY APPLICABLE**

**Rationale**:
- **FR-2.4 requires diverse text density**: 0% text (pure images) → 100% text (text-heavy documents)
- **COCO-Text provides natural scene images** with varying text density:
  - No text: Landscapes, indoor scenes (0% text)
  - Low text: Single sign, small label (5-10% text)
  - Medium text: Multiple signs, storefront (20-40% text)
  - High text: Dense signage, posters (60-80% text)
- **File format**: JPG images (not PDFs) - fills gap for image-format text detection
- **Complements document datasets**: DocLayNet/TableBank are PDF-heavy, COCO-Text provides JPG diversity

**Coverage Enhancement with COCO-Text**:

| Text Density Range | Current Coverage (without COCO-Text) | With COCO-Text | Improvement |
|-------------------|--------------------------------------|----------------|-------------|
| **0% text (pure images)** | ⚠️ Limited (TableBank diagrams) | ✅ Good (natural scenes) | **+40%** |
| **5-20% text (low text)** | ⚠️ Limited (technical diagrams) | ✅ Good (single signs) | **+50%** |
| **20-50% text (medium)** | ⚠️ Moderate (DocLayNet figures) | ✅ Good (storefronts) | **+30%** |
| **50-100% text (high)** | ✅ Good (DocLayNet, academic papers) | ⚠️ Moderate (dense signage) | **+10%** |

**Recommendation**: **KEEP COCO-Text for FR-2.4** - Provides valuable JPG/image format diversity with varying text density, especially for 0-20% text range (pure images → low text).

**COCO-Text Limitations**:
- ❌ Not applicable to FR-2.1 (PDF Type Classification) - only provides JPG images
- ❌ Not applicable to FR-4.x (Layout Detection) - natural scenes have different layout structure than documents
- ✅ **ONLY applicable to FR-2.4** (Text Detection Gate) - text presence detection across file formats

---

### FR-3.1: Blur Detection

**Requirement**: Detect blur in documents/images (all file formats)

**Coverage Needed**:

| Document Type | PDF | JPG/PNG | Current Coverage | Gap |
|---------------|-----|---------|------------------|-----|
| **Business (Required)** | ✅ Needed | ✅ Needed | ⚠️ TableBank synthetic (business tables) | **MEDIUM** - Need real business doc blur |
| **Legal (Required)** | ✅ Needed | ⚠️ Optional | ⚠️ Synthetic only | **MEDIUM** - Need real legal doc blur |
| **Financial (High)** | ✅ Needed | ✅ Needed | ✅ Mobile receipts (real blur) | **LOW** - Good coverage |
| **Academic (High)** | ✅ Needed | ⚠️ Optional | ✅ TableBank (50k synthetic variants) | **LOW** - Good coverage |
| **Forms (Medium)** | ✅ Needed | ✅ Needed | ❌ No form dataset | **HIGH** - Need scanned forms with blur |
| **Technical (Medium)** | ✅ Needed | ✅ Needed | ⚠️ TableBank diagrams (synthetic) | **MEDIUM** - Need real technical doc blur |
| **Historical (Medium)** | ✅ Needed | ✅ Needed | ⚠️ Synthetic degradation | **MEDIUM** - Need real historical blur |
| **Mobile (Low)** | 🔲 N/A | ✅ Needed | ✅ Mobile receipts (motion blur) | **LOW** - Good coverage |
| **Multi-lingual (Low)** | ⚠️ Optional | ⚠️ Optional | ⚠️ Limited | **LOW** |

**COCO-Text Applicability**: ⚠️ **OPTIONAL** - Natural image blur ≠ document blur (different defect types)

**Summary**: Good synthetic coverage (TableBank 50k variants), need real-world blur samples for priority document types (Business, Legal, Forms).

---

### FR-4.2: Layout Element Detection (11 classes)

**Requirement**: Detect layout elements (text, title, table, figure, etc.) in documents

**Coverage Needed**:

| Document Type | PDF | JPG/PNG | Current Coverage | Gap |
|---------------|-----|---------|------------------|-----|
| **Business (Required)** | ✅ Needed | ⚠️ Optional | ⚠️ DocLayNet (limited business subset) | **HIGH** - Need more business layouts |
| **Legal (Required)** | ✅ Needed | ⚠️ Optional | ⚠️ DocLayNet legal subset | **HIGH** - Need legal brief layouts |
| **Financial (High)** | ✅ Needed | ⚠️ Optional | ✅ TableBank (417k tables) + DocLayNet | **LOW** - Good table coverage |
| **Academic (High)** | ✅ Needed | ⚠️ Optional | ✅ DocLayNet (42k pages, 11 classes) | **LOW** - Excellent coverage |
| **Forms (Medium)** | ✅ Needed | ✅ Needed | ❌ No form dataset | **HIGH** - Need form layouts |
| **Technical (Medium)** | ✅ Needed | ⚠️ Optional | ⚠️ Limited (engineering manuals) | **MEDIUM** - Need technical layouts |
| **Historical (Medium)** | ✅ Needed | ⚠️ Optional | ⚠️ DocLayNet subset (limited) | **MEDIUM** - Need historical layouts |
| **Mobile (Low)** | 🔲 N/A | ⚠️ Optional | ❌ No mobile-specific layouts | **LOW** - Mobile is capture method |
| **Multi-lingual (Low)** | ⚠️ Optional | ⚠️ Optional | ⚠️ Limited | **LOW** |

**COCO-Text Applicability**: ❌ **NO** - Natural scene layouts (street scenes) ≠ document layouts (paragraphs, tables, figures)

**Summary**: Excellent academic coverage (DocLayNet), gaps in Business, Legal, Forms document types.

---

### FR-4.11: Table Structure Extraction

**Requirement**: Extract cell-level table structure with HTML output

**Coverage Needed**:

| Document Type | PDF | Current Coverage | Gap |
|---------------|-----|------------------|-----|
| **Business (Required)** | ✅ Needed | ⚠️ PubTables-1M (general tables) | **MEDIUM** - Need business-specific tables |
| **Legal (Required)** | ✅ Needed | ❌ No legal tables | **HIGH** - Need legal table corpus |
| **Financial (High)** | ✅ Needed | ✅ FinTabNet (14 GB) + PubTabNet | **LOW** - Excellent financial table coverage |
| **Academic (High)** | ✅ Needed | ✅ PubTables-1M (1M tables) + TableBank | **LOW** - Excellent academic table coverage |
| **Forms (Medium)** | ✅ Needed | ❌ No form-specific tables | **HIGH** - Need government form tables |
| **Technical (Medium)** | ✅ Needed | ⚠️ TableBank (some technical tables) | **MEDIUM** - Need technical spec tables |
| **Historical (Medium)** | ⚠️ Optional | ❌ No historical tables | **MEDIUM** - Need historical table corpus |

**Summary**: Excellent Financial + Academic coverage, gaps in Business, Legal, Forms.

---

### FR-5.3: Language Detection

**Requirement**: Detect document language (235 languages supported)

**Coverage Needed**:

| Document Type | All Formats | Current Coverage | Gap |
|---------------|-------------|------------------|-----|
| **Business (Required)** | ✅ Needed | ⚠️ WiLI-2018 (limited business docs) | **MEDIUM** - Need business docs in target languages |
| **Legal (Required)** | ✅ Needed | ❌ No legal corpus | **HIGH** - Need international contracts |
| **Financial (High)** | ✅ Needed | ❌ No financial corpus | **MEDIUM** - Need international invoices |
| **Academic (High)** | ✅ Needed | ✅ WiLI-2018 (235k paragraphs, 235 languages) | **LOW** - Excellent coverage |
| **All other types** | ⚠️ Optional | ✅ WiLI-2018 (general language ID) | **LOW** - Good general coverage |

**Summary**: Excellent general language coverage (WiLI-2018), need domain-specific multi-lingual corpora (Legal, Business, Financial).

---

## Priority Training Data Gaps Summary

### Required Document Types (Business, Legal) - 100% Coverage Target

| FR | Business Gap | Legal Gap | Recommended Dataset | Priority |
|----|--------------|-----------|---------------------|----------|
| **FR-2.1** | MEDIUM - Need more business PDFs (all 3 types) | HIGH - Need contract corpus | Business doc corpus (1 GB), Contract dataset (1 GB) | **HIGH** |
| **FR-2.4** | MEDIUM - Need pure-image business docs | LOW - Legal docs are text-heavy | Business image corpus (500 MB) | **MEDIUM** |
| **FR-3.x** (IQA) | MEDIUM - Need real blur/noise/contrast samples | MEDIUM - Need real degradation samples | Business/Legal quality corpus (500 MB) | **MEDIUM** |
| **FR-4.2** | HIGH - Need business layouts (memos, reports) | HIGH - Need legal brief layouts | Business layout corpus (1 GB), Legal brief dataset (500 MB) | **HIGH** |
| **FR-4.11** | MEDIUM - Need business tables | HIGH - Need legal tables | Business table corpus (500 MB), Legal table dataset (300 MB) | **HIGH** |
| **FR-5.3** | MEDIUM - Need multi-lingual business docs | HIGH - Need international contracts | Multi-lingual business corpus (500 MB), International contract dataset (500 MB) | **MEDIUM** |

**Total for Required Types**: ~6.3 GB additional training data

---

### High Priority Document Types (Financial, Academic) - 90% Coverage Target

| FR | Financial Gap | Academic Gap | Recommended Dataset | Priority |
|----|---------------|--------------|---------------------|----------|
| **FR-2.1** | MEDIUM - Need more invoice/statement PDFs | LOW - Good coverage (DocLayNet) | Financial doc corpus (500 MB) | **MEDIUM** |
| **FR-4.11** | LOW - Excellent (FinTabNet, PubTabNet) | LOW - Excellent (PubTables-1M) | None needed | **LOW** |
| **FR-5.3** | MEDIUM - Need multi-lingual invoices | LOW - Excellent (WiLI-2018) | Multi-lingual invoice dataset (300 MB) | **LOW** |

**Total for High Priority Types**: ~800 MB additional training data

---

### Medium Priority Document Types (Forms, Technical, Historical) - 70% Coverage Target

| FR | Forms Gap | Technical Gap | Historical Gap | Recommended Dataset | Priority |
|----|-----------|---------------|----------------|---------------------|----------|
| **FR-2.1** | HIGH - Need government forms | MEDIUM - Need technical manuals | MEDIUM - Need archive scans | Government form dataset (500 MB), Technical manual corpus (500 MB), Archive scan dataset (1 GB) | **HIGH** |
| **FR-2.4** | HIGH - Need blank/filled forms | MEDIUM - Need pure-image diagrams | MEDIUM - Need historical images | (Covered above) | **MEDIUM** |
| **FR-3.x** (IQA) | HIGH - Need scanned forms with defects | MEDIUM - Need technical diagram quality | HIGH - Need real historical degradation | Historical degradation corpus (1 GB) | **HIGH** |
| **FR-4.2** | HIGH - Need form layouts | MEDIUM - Need technical layouts | MEDIUM - Need historical layouts | (Covered above) | **MEDIUM** |

**Total for Medium Priority Types**: ~3 GB additional training data

---

## COCO-Text Re-evaluation

### FR-Specific Applicability Matrix

| FR | COCO-Text Applicable? | Rationale | Keep/Remove Decision |
|----|----------------------|-----------|---------------------|
| **FR-2.1** (PDF Type Classification) | ❌ NO | Only provides JPG images, not PDFs | **Remove from FR-2.1** |
| **FR-2.4** (Text Detection Gate) | ✅ **YES** | Provides JPG diversity with 0-100% text density range | **KEEP for FR-2.4** |
| **FR-3.1** (Blur Detection) | ⚠️ OPTIONAL | Natural image blur ≠ document blur, but useful for robustness | **Optional - Low priority** |
| **FR-4.2** (Layout Detection) | ❌ NO | Natural scene layouts ≠ document layouts | **Remove from FR-4.2** |
| **FR-4.x** (All other layout FRs) | ❌ NO | Not applicable to document layout tasks | **Remove** |
| **FR-5.3** (Language Detection) | ⚠️ OPTIONAL | Some foreign text, but limited | **Optional - Low priority** |

### Overall COCO-Text Recommendation

**Decision**: **KEEP COCO-Text, but scope to FR-2.4 only**

**Rationale**:
1. **High value for FR-2.4**: Fills critical gap for image-format text detection with 0-20% text density
2. **Small size**: 53 MB (annotations only), images from existing COCO dataset
3. **File format diversity**: Provides JPG coverage to complement PDF-heavy datasets
4. **No value for other FRs**: Remove from FR-2.1, FR-4.x benchmarks

**Updated benchmark registry** (recommended):
```yaml
# KEEP for Text Detection Gate
- name: cocotext-text-detection-gate
  phase: 2
  task: text_detection
  dataset: cocotext
  metrics:
    - text_presence_accuracy
    - text_density_correlation
  applicable_frs: [FR-2.4]  # ONLY FR-2.4

# REMOVE from other FRs (not applicable)
# - FR-2.1 (PDF Type Classification) - COCO-Text is JPG only
# - FR-4.2 (Layout Detection) - Natural scenes ≠ document layouts
```

---

## Recommended Actions

### Immediate (Phase 2 Week 3-4)

1. **Scope COCO-Text to FR-2.4 only** - Remove from FR-2.1, FR-4.x benchmarks
2. **Acquire government form dataset** (Forms, Required gap) - ~500 MB
3. **Acquire contract corpus** (Legal, Required gap) - ~1 GB

### Near-Term (Phase 3 Week 1-2)

4. **Acquire business document corpus** (Business, Required gap) - ~1 GB
5. **Acquire legal brief dataset** (Legal, Required gap) - ~500 MB
6. **Expand financial document coverage** (Financial, High Priority gap) - ~500 MB

### Mid-Term (Phase 3 Week 3-4)

7. **Acquire technical manual corpus** (Technical, Medium Priority) - ~500 MB
8. **Acquire historical archive scans** (Historical, Medium Priority) - ~1 GB
9. **Expand multi-lingual coverage** (Business/Legal, Required gap) - ~1 GB

**Total Additional Training Data**: ~6.5 GB (Required + High Priority types)

---

**Created**: 2025-11-14
**Status**: ✅ Complete - Document type priorities defined, FR coverage gaps identified
**Next Steps**: Update document-type-coverage.md with priority rankings, scope COCO-Text to FR-2.4
**Next Review**: Phase 3 Week 1 (after new dataset integration)
