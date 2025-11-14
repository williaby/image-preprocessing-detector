# Document Type Coverage Matrix

**Version**: 2.0
**Date**: 2025-01-13 (Updated with Phase 3+ datasets)
**Purpose**: Define required document types for training and testing each detection capability

## Overview

This matrix ensures comprehensive coverage across document types for each functional requirement. Different document types exhibit different characteristics (e.g., math equations in textbooks vs. handwritten notes), requiring diverse training and testing data.

**Document Type Categories**:
1. **Academic**: Papers, journals, textbooks, dissertations
2. **Business**: Reports, contracts, invoices, receipts
3. **Historical**: Manuscripts, archives, scanned documents
4. **Mobile**: Mobile camera captures (varied lighting, angles)
5. **Technical**: Diagrams, schematics, manuals, blueprints
6. **Legal**: Contracts, court documents, notarized forms
7. **Multi-lingual**: Non-English, mixed scripts, Asian languages
8. **Forms**: Government forms, applications, surveys

---

## Image Quality Detection (IQA)

### FR-3.1: Blur Detection

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | TableBank (synthetic blur) | **DIQA-5000** (document blur) | Text-heavy, printed |
| **Mobile Captures** | Synthetic mobile captures | **DIQA-5000** (authentic) | Motion blur, camera shake |
| **Historical** | Synthetic degradation | DocLayNet historical subset | Age-related blur, poor focus |
| **Business Docs** | Synthetic degradation | DocLayNet business subset | Printer/scanner artifacts |
| **Technical Diagrams** | Synthetic blur on diagrams | Engineering drawing samples | Line clarity critical |

**Coverage**:
- ✅ **Training**: TableBank (50k synthetic blur variants)
- ✅ **Validation**: **DIQA-5000** (document-specific blur assessment) → **Fallback**: LIVE/CSIQ until released
- ✅ **Test Fixtures**: 5 blur samples (clean, slight, moderate, severe, extreme)

### FR-3.2: Skew Detection

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | TableBank (synthetic rotation) | DocLayNet PDFs | Scanned documents |
| **Mobile Captures** | Synthetic rotation (-45° to +45°) | Mobile capture dataset | Camera angle variations |
| **Forms** | Synthetic skew on forms | Government form samples | Alignment critical |
| **Historical** | Synthetic rotation | Historical archive samples | Scanner misalignment |

**Coverage**:
- ✅ **Training**: TableBank (50k synthetic rotation variants, -15° to +15°)
- ✅ **Validation**: DocLayNet (100 random PDFs with natural skew)
- ✅ **Test Fixtures**: 8 skew samples (0°, ±2°, ±5°, ±10°, ±15°)

### FR-3.3: Noise Detection

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Historical** | Synthetic noise + degradation | Historical manuscript samples | Age-related noise, stains |
| **Photocopies** | Synthetic salt-and-pepper noise | Scanned photocopy samples | Photocopier artifacts |
| **Low-Quality Scans** | Synthetic Gaussian noise | Low-res scan samples | Scanner noise |
| **Mobile Captures** | Synthetic noise | LIVE Challenge (authentic noise) | Camera sensor noise |

**Coverage**:
- ✅ **Training**: TableBank (10k synthetic noise variants: Gaussian, salt-and-pepper)
- ✅ **Validation**: **DIQA-5000** (document noise assessment) → **Fallback**: LIVE/CSIQ until released
- ✅ **Test Fixtures**: 5 noise samples (clean, slight, moderate, severe, combined)

### FR-3.7: Contrast Assessment

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Faded Documents** | Synthetic contrast reduction | Historical faded samples | Age-related fading |
| **Poor Scans** | Synthetic low-contrast | Low-quality scan samples | Scanner settings |
| **Mobile Captures** | Synthetic lighting variations | Mobile capture dataset | Poor lighting conditions |
| **Photocopies** | Synthetic contrast loss | Photocopy samples | Generation loss |

**Coverage**:
- ✅ **Training**: TableBank (10k synthetic contrast variants, 0-100% reduction)
- ✅ **Validation**: **DIQA-5000** (document contrast/color fidelity) → **Fallback**: LIVE/CSIQ until released
- ✅ **Test Fixtures**: 5 contrast samples (high, normal, low, very low, extreme)

### FR-3.8: Binarization Quality (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Historical Manuscripts** | Synthetic degradation | Yale historical collection | Poor text/background separation |
| **Faded Documents** | Synthetic fading + noise | Degraded document samples | Age-related issues |
| **Photocopies** | Synthetic photocopy artifacts | Multi-generation photocopies | Generation loss |
| **Handwritten Notes** | SignaTR6K synthetic variants | SignaTR6K real samples | Ink variation |

**Coverage**:
- ⏳ **Training**: TableBank + historical degradation (5k samples, Phase 2)
- ⏳ **Validation**: Yale historical manuscript dataset (ground-truth binarization)
- ⏳ **Test Fixtures**: 8 binarization samples (clean, faded, noisy, bleed-through, mixed)

### FR-3.9: Illumination Uniformity (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Mobile Captures** | Synthetic shadow/lighting | Smartphone dataset (DocBank Mobile) | Camera flash, shadows |
| **Book Scans** | Synthetic spine shadow | Book scan samples | Binding shadows |
| **Historical** | Synthetic uneven lighting | Archive scan samples | Old scanner artifacts |
| **Desktop Photography** | Synthetic desk lighting | Desktop capture samples | Uncontrolled lighting |

**Coverage**:
- ⏳ **Training**: Synthetic lighting gradients (5k samples, Phase 2)
- ⏳ **Validation**: Mobile capture dataset (authentic lighting issues)
- ⏳ **Test Fixtures**: 5 illumination samples (uniform, gradient, shadow, spotlight, mixed)

### FR-3.10: Bleed-Through Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Historical Manuscripts** | Synthetic bleed-through | Historical archive samples | Thin paper, age |
| **Double-Sided Printing** | Synthetic reverse-side text | Double-sided document samples | Thin paper |
| **Newspaper** | Synthetic newsprint bleed | Newspaper scan samples | Thin newsprint |
| **Notebooks** | Synthetic notebook bleed | Student notebook samples | Thin notebook paper |

**Coverage**:
- ⏳ **Training**: Synthetic bleed-through (dual-side simulation, 3k samples, Phase 3)
- ⏳ **Validation**: Historical manuscript dataset (real bleed-through)
- ⏳ **Test Fixtures**: 5 bleed-through samples (none, slight, moderate, severe, extreme)

### FR-3.11: Warping/Curvature (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Book Scans** | Synthetic spine curvature | Book scan dataset | Binding curvature |
| **Bound Documents** | Synthetic warping | Bound report samples | Binding stress |
| **Mobile Captures** | **SynDocDS** (synthetic warping) | **AnyPhotoDoc 6300** (camera captures) | Angle distortion |
| **Historical Bound** | Synthetic age-related warping | Historical bound volumes | Age + binding |

**Coverage**:
- ✅ **Training**: **DocRes pretrained** or SynDocDS (synthetic warping, ~15 GB, Phase 3)
- ✅ **Validation**: **AnyPhotoDoc 6300** (6,300 camera-captured warped documents)
- ⏳ **Test Fixtures**: 5 warping samples (flat, slight curve, moderate, severe, extreme)

### FR-3.12: Perspective Distortion (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Mobile Captures** | Synthetic perspective transform | Smartphone dataset | Camera angle |
| **Desktop Photography** | Synthetic trapezoidal distortion | Desktop capture samples | Angled shooting |
| **Whiteboard Photos** | Synthetic perspective | Whiteboard capture dataset | Classroom captures |

**Coverage**:
- ⏳ **Training**: Synthetic perspective (homography, 5k samples, Phase 2)
- ⏳ **Validation**: SmartDoc dataset (mobile document capture)
- ⏳ **Test Fixtures**: 5 perspective samples (frontal, slight, moderate, severe, extreme)

---

## Layout Elements (Object Detection)

### FR-4.2: Layout Element Detection (DocLayNet 11 Classes)

| Element Class | Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|---------------|------------------|--------------|-----------|
| **Text** | Academic papers | DocLayNet COCO (42k pages) | DocLayNet val (6.5k pages) | Main body text |
| **Title** | All documents | DocLayNet COCO | DocLayNet val | Document titles |
| **List-Item** | Academic, business | DocLayNet COCO | DocLayNet val | Bulleted/numbered lists |
| **Table** | Academic, financial | TableBank (417k tables) | DocLayNet val | Structured data |
| **Picture** | Academic, technical | DocLayNet COCO | DocLayNet val | Figures, charts |
| **Caption** | Academic | DocLayNet COCO | DocLayNet val | Figure/table captions |
| **Formula** | Academic, technical | DocLayNet COCO | DocLayNet val | Math equations |
| **Footnote** | Academic, legal | DocLayNet COCO | DocLayNet val | Page footnotes |
| **Page-Header** | Academic, business | DocLayNet COCO | DocLayNet val | Repeating headers |
| **Page-Footer** | Academic, business | DocLayNet COCO | DocLayNet val | Repeating footers |
| **Section-Header** | Academic, technical | DocLayNet COCO | DocLayNet val | Section titles |

**Coverage**:
- ✅ **Training**: DocLayNet COCO annotations (42,075 pages)
- ✅ **Validation**: DocLayNet validation set (6,480 pages)
- ✅ **Test Fixtures**: 5 DocLayNet samples (diverse layouts)

### FR-4.4: Parasitic Content Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | DocLayNet (headers/footers) | Academic paper corpus | Conference formatting |
| **Business Reports** | DocLayNet financial | Corporate report samples | Company headers |
| **Legal Documents** | Legal document corpus | Legal brief samples | Court formatting |
| **Textbooks** | Textbook samples | Educational publisher samples | Page numbering, chapters |

**Coverage**:
- ⏳ **Training**: DocLayNet Page-Header/Page-Footer annotations (Phase 3)
- ⏳ **Validation**: Academic paper corpus (IEEE, ACM formatting)
- ⏳ **Test Fixtures**: 5 samples (academic, business, legal, textbook, mixed)

### FR-4.5: Footnote Linking (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | DocLayNet + superscript detection | Academic corpus | Citation footnotes |
| **Legal Documents** | Legal document corpus | Legal brief samples | Case law citations |
| **Historical Manuscripts** | Historical annotation dataset | Manuscript samples | Scholarly notes |

**Coverage**:
- ⏳ **Training**: DocLayNet Footnote class + superscript detection (Phase 3)
- ⏳ **Validation**: Academic paper corpus (footnote-heavy)
- ⏳ **Test Fixtures**: 5 samples (academic, legal, historical, mixed, complex)

### FR-4.6: Figure-Caption Linking (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | DocLayNet Caption/Picture annotations | Academic corpus | Research figures |
| **Technical Manuals** | Technical documentation samples | Manual samples | Diagrams |
| **Textbooks** | Textbook samples | Educational samples | Instructional figures |

**Coverage**:
- ⏳ **Training**: DocLayNet Caption + Picture classes (Phase 2)
- ⏳ **Validation**: Academic paper corpus (figure-rich)
- ⏳ **Test Fixtures**: 5 samples (above caption, below caption, side caption, far caption, no caption)

### FR-4.7: Vertical Text Orientation (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Asian Languages** | Chinese/Japanese/Korean corpus | Wili-2018 Asian subset | Vertical writing |
| **Technical Diagrams** | Rotated label dataset | Engineering drawing samples | Rotated labels |
| **Mobile Captures** | Synthetic rotation (0°/90°/180°/270°) | Mobile capture dataset | Camera orientation |
| **Posters** | Poster/flyer dataset | Advertising samples | Mixed orientations |

**Coverage**:
- ⏳ **Training**: Wili-2018 (235k paragraphs) + synthetic rotation (Phase 3)
- ⏳ **Validation**: Asian language corpus (CJK documents)
- ⏳ **Test Fixtures**: 8 samples (0°, 90°, 180°, 270° for each: text, diagram)

---

## Specialized Content Detection

### FR-5.1: Mathematical Content (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Academic Papers** | DocLayNet Formula class | ArXiv paper samples | Research equations |
| **Textbooks** | Textbook equation dataset | Educational samples | Teaching materials |
| **Technical Documentation** | Technical manual samples | Engineering docs | Technical formulas |
| **Handwritten Notes** | Handwritten equation dataset | Student notes | Handwritten math |

**Coverage**:
- ⏳ **Training**: DocLayNet Formula annotations (Phase 3)
- ⏳ **Validation**: ArXiv paper corpus (math-heavy)
- ⏳ **Test Fixtures**: 8 samples (printed simple, printed complex, handwritten, mixed, inline, display, multi-line, nested)

### FR-5.2: Handwritten Content (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Signatures** | SignaTR6K (6k signatures) | SignaTR6K test set | Signature detection |
| **Handwritten Notes** | IAM Handwriting Database | Student notes | Note-taking |
| **Forms** | Handwritten form dataset | Government forms | Form filling |
| **Mixed Documents** | DocLayNet + handwriting overlay | Annotated documents | Margin notes |

**Coverage**:
- ⏳ **Training**: SignaTR6K (6,000 signatures) + IAM Database (Phase 2)
- ⏳ **Validation**: SignaTR6K test set (smoke: 100 samples, full: 6k)
- ⏳ **Test Fixtures**: 5 samples (signature, cursive, print, mixed, margin notes)

### FR-5.3: Language Detection (Phase 2)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Multi-lingual** | Wili-2018 (235 languages) | Wili-2018 test set | Language ID |
| **Academic Papers** | Multi-lingual corpus | ArXiv multi-lingual | Research publications |
| **Business Docs** | International business samples | Contract samples | Global business |
| **Asian Scripts** | CJK corpus (Chinese, Japanese, Korean) | Asian language samples | Non-Latin scripts |

**Coverage**:
- ✅ **Training**: Wili-2018 (235,000 paragraphs, 235 languages)
- ✅ **Validation**: Wili-2018 test set
- ✅ **Test Fixtures**: 10 language samples (en, es, fr, de, zh, ja, ar, ru, hi, ko)

### FR-5.4: Watermark Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Legal Documents** | Watermarked contract dataset | Legal document samples | "CONFIDENTIAL", "DRAFT" |
| **Business Reports** | Corporate watermark dataset | Business doc samples | Company logos |
| **Official Certificates** | Certificate dataset | Government certificate samples | Security features |
| **Security Documents** | Security paper dataset | Bank statement samples | Background patterns |

**Coverage**:
- ⏳ **Training**: Synthetic watermark dataset (text, logo, pattern, 3k samples, Phase 3)
- ⏳ **Validation**: Real-world watermarked documents (business/legal corpus)
- ⏳ **Test Fixtures**: 5 samples (text watermark, logo, diagonal, repeating pattern, none)

### FR-5.5: Stamp/Seal Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Government Documents** | **DDI-100** (99,870 images) | **StaVer** (200 stamped) | Official seals |
| **Contracts** | **DDI-100** (stamps, hole punches) | Contract samples | Notary seals |
| **Historical Archives** | **DDI-100** (noise artifacts) | Archive samples | Wax seals, official stamps |
| **International Shipping** | **StaVer** (400 images) | Customs forms | Customs stamps |

**Coverage**:
- ✅ **Training**: **StaVer** (400 images: 200 stamped, 200 clean) + **DDI-100** (99,870 images with stamps, hole punches)
- ✅ **Validation**: StaVer test split + Government document corpus
- ⏳ **Test Fixtures**: 10 samples (circular seal, rectangular stamp, multiple stamps, overlapping, faint, hole punches)

### FR-5.6: Signature Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Contracts** | SignaTR6K (6k signatures) | Contract corpus | Legal signatures |
| **Forms** | Handwritten form dataset | Government forms | Form signatures |
| **Legal Documents** | Legal signature dataset | Legal brief samples | Attorney signatures |
| **Invoices/Receipts** | Invoice signature dataset | Business transaction samples | Authorization signatures |

**Coverage**:
- ⏳ **Training**: SignaTR6K (6,000 signatures, Phase 3)
- ⏳ **Validation**: SignaTR6K test set + contract corpus
- ⏳ **Test Fixtures**: 5 samples (contract signature, form signature, receipt, multiple signatures, none)

### FR-5.7: Margin Annotation Detection (Phase 3)

| Document Type | Training Dataset | Test Dataset | Rationale |
|---------------|------------------|--------------|-----------|
| **Historical Manuscripts** | Annotated manuscript dataset | Archive samples | Scholarly notes |
| **Academic Papers** | Peer review annotation dataset | Reviewer comments | Editorial notes |
| **Annotated Drafts** | Draft annotation dataset | Writing samples | Author revisions |
| **Student Assignments** | Student annotation dataset | Educational samples | Teacher comments |

**Coverage**:
- ⏳ **Training**: Annotated manuscript dataset (2k samples, Phase 3)
- ⏳ **Validation**: Historical archive corpus (annotation-heavy)
- ⏳ **Test Fixtures**: 5 samples (margin notes, highlight, strikethrough, insertion, mixed)

---

## Dataset Availability Matrix

### Phase 1-2 Datasets (Current)

| Dataset | Size | License | Training Use | Benchmark Use | Status |
|---------|------|---------|--------------|---------------|--------|
| **TableBank** | 46.38 GB, 417k tables | Apache-2.0 | ✅ Yes | ✅ Yes | ✅ Downloaded |
| **DocLayNet** | 40.97 GB, 80k pages | CDLA-Permissive-1.0 | ✅ Yes | ✅ Yes | ✅ Symlinked from data_ingestor |
| **LIVE** | 1 GB, 779 images | Academic (cite) | ❌ No (validation only) | ✅ Yes (fallback) | ⏳ Download in Phase 2 |
| **CSIQ** | 2 GB, 866 images | Academic (cite) | ❌ No (validation only) | ✅ Yes (fallback) | ⏳ Download in Phase 2 |
| **LIVE Challenge** | 2 GB, 1,162 images | Academic (cite) | ❌ No (validation only) | ✅ Yes | ⏳ Download in Phase 2 |
| **Wili-2018** | 2.85 GB, 235k paragraphs | Apache-2.0 | ✅ Yes | ✅ Yes | ✅ Downloaded |
| **OmniDocBench** | 5.95 GB | Apache-2.0 | ✅ Yes | ✅ Yes (**PRIMARY**) | ✅ Downloaded |
| **PubTabNet** | 970 MB | MIT | ✅ Yes | ✅ Yes | ✅ Downloaded |
| **SignaTR6K** | 116 MB, 6k signatures | CC BY 4.0 | ✅ Yes | ✅ Yes | ✅ Downloaded |

### Phase 3+ Datasets (NEW - Research Analysis 2025-01-13)

| Dataset | Size | License | Training Use | Benchmark Use | Status |
|---------|------|---------|--------------|---------------|--------|
| **DIQA-5000** | ~3.9 GB, 5k images | TBD | ❌ No (benchmark only) | ✅ Yes (**REPLACES LIVE/CSIQ**) | ⚠️ Pending Release (Sept 2025) |
| **DocSynth-300K** | ~50 GB, 300k layouts | Apache-2.0 | ✅ Yes (**6x larger than TableBank**) | ✅ Yes | ⏳ Phase 3 Week 1 |
| **PubTables-1M** | ~25 GB, 1M tables | Apache-2.0 | ✅ Yes (**Table structure FR-4.11**) | ✅ Yes | ⏳ Phase 3 Week 1 |
| **IAM Handwriting** | 266 MB, 13,353 lines | Academic (cite) | ✅ Yes (**FR-4.8: 95% target**) | ✅ Yes | ⏳ Phase 2 Week 4 |
| **StaVer** | ~50 MB, 400 images | CC BY-NC-SA 4.0 | ✅ Yes (**Stamp detection FR-5.5**) | ✅ Yes | ⏳ Phase 3 Week 2 |
| **DDI-100** | ~5 GB, 99,870 images | Research (assume) | ✅ Yes (**Stamps, hole punches FR-4.4**) | ⚠️ No benchmark | ⏳ Phase 3 Week 2 |
| **AnyPhotoDoc 6300** | ~2 GB, 6,300 images | Research | ❌ No | ✅ Yes (**Dewarping benchmark**) | ⏳ Phase 3 Week 3 |
| **ROOR** | ~500 MB (est.) | CC BY 4.0 | ⚠️ Optional | ✅ Yes (**Reading order**) | ⏳ Phase 4-5 (optional) |
| **SynDocDS** | ~15 GB synthetic | Apache-2.0 (inferred) | ⚠️ Optional (**DocRes covers**) | ❌ No | ⏳ Phase 3+ (conditional) |

### Legacy Datasets (Phase 2-3 Optional)

| Dataset | Size | License | Training Use | Benchmark Use | Status |
|---------|------|---------|--------------|---------------|--------|
| **SmartDoc** | ~200 MB | Academic | ❌ No (validation only) | ✅ Yes | ⏳ Phase 2+ (optional) |
| **DocUNet Dataset** | ~1 GB | Academic | ❌ No (validation only) | ✅ Yes | ⏳ Phase 3+ (optional) |

**Key Changes (2025-01-13)**:
- **DIQA-5000**: **PRIMARY** document IQA benchmark (replaces LIVE/CSIQ when released)
- **DocSynth-300K**: 6x larger than TableBank for layout detection training
- **PubTables-1M**: **NEW** for table structure extraction (FR-4.11)
- **StaVer + DDI-100**: Combined 100,270 images for stamp/artifact detection (FR-5.5, FR-4.4)
- **IAM Handwriting**: **ELEVATED** to training dataset (FR-4.8: 95% accuracy target)
- **AnyPhotoDoc 6300**: **NEW** dewarping benchmark (validates DocRes preprocessing)
- **SynDocDS**: **OPTIONAL** (DocRes unified model handles shadow removal)

---

## Coverage Gaps and Mitigation

### Phase 1 Gaps (COMPLETE)

- ✅ **Mobile Captures**: LIVE Challenge provides authentic mobile defects
- ✅ **Real-World Calibration**: DocLayNet validation proved critical (ADR-011)
- ✅ **Diverse Document Types**: TableBank + DocLayNet cover academic, financial, business

### Phase 2 Gaps (PLANNED)

- ⚠️ **Handwritten Equation Dataset**: Limited public datasets → Use synthetic generation
- ⚠️ **Watermarked Documents**: Limited public datasets → Use synthetic watermark overlay
- ⚠️ **Mobile Lighting Issues**: SmartDoc download required

### Phase 3 Gaps (IDENTIFIED)

- ⚠️ **Book Scan Dataset**: DocUNet dataset (academic license) or synthetic generation
- ⚠️ **Stamp/Seal Dataset**: Limited availability → Synthetic generation + manual collection
- ⚠️ **Margin Annotation Dataset**: Limited availability → Use historical manuscript archives

---

## Recommendations

### Priority 1: Phase 2 Week 1 (Immediate)

1. **Download External IQA Datasets**: LIVE, CSIQ, LIVE Challenge (validation-only)
2. **Generate Synthetic Training Data**: 50k TableBank samples with Albumentations
3. **Extract Test Fixtures**: 8 IQA samples from LIVE dataset

### Priority 2: Phase 2 Week 2-3 (Training Preparation)

1. **Download SmartDoc Dataset**: Mobile capture perspective distortion
2. **Generate Synthetic Perspective**: Homography transforms on TableBank
3. **Validate Document Type Coverage**: Ensure all FR document types represented

### Priority 3: Phase 3 Planning (Future)

1. **Acquire DocUNet Dataset**: Book scan warping (academic license)
2. **Synthetic Watermark Generation**: Create training dataset for watermark detection
3. **Historical Manuscript Corpus**: Archive access for bleed-through, annotations

---

**Created**: 2025-11-13 (Phase 2 Week 1 - Documentation Phase)
**Status**: 🚧 **In Progress** - Document type coverage matrix complete
**Next Steps**: Download Phase 2 validation datasets, validate coverage gaps
**Next Review**: Phase 2 Week 3 (after training dataset generation)
