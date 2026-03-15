---
dataset_id: ndl-docl
version: "1.0"
license: Public Domain
commercial_use: true
iqa_profiles:
  - scanner
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### NDL-DocL (NDL Document Layout Dataset)

> **Quick Stats**: 2,290 images | Rare books (pre-1868) + modern (post-1868) | Japanese layout + kuzushiji | Historical
>
> **License**: Public Domain Mark (PDM 1.0) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NDL Document Layout Dataset |
| **Version** | 1.0 |
| **Maintainer** | National Diet Library, Japan (NDL Lab) |
| **Source** | [github.com/ndl-lab/layout-dataset](https://github.com/ndl-lab/layout-dataset) |
| **License** | Public Domain Mark (PDM 1.0) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 2,290 |
| **Rare Books (pre-1868)** | 1,219 images |
| **Modern (post-1868)** | 1,071 images |
| **Annotation Format** | Pascal VOC XML bounding boxes |
| **Language** | Japanese (ja) |
| **Script** | Jpan (ISO 15924) |

**Layout Classes -- Rare Books**:

| Class | Description |
|-------|-------------|
| document area | Overall document region |
| kuzushiji | Historical Japanese cursive script |
| typography | Printed text regions |
| illustration | Drawings and artwork |
| seals/stamps | Official stamps and seals |

**Layout Classes -- Modern**:

| Class | Description |
|-------|-------------|
| document area | Overall document region |
| illustration/photos | Photographs and illustrations |
| seals/stamps | Official stamps and seals |
| headline | Headlines and titles |
| caption | Image/figure captions |
| text lines | Body text lines |
| tables | Tabular structures |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanner (library flatbed digitization) |
| **Baseline Quality** | Variable (microfilm scans to high-res digitization) |
| **Text Direction** | Both vertical (tategaki, especially rare books) and horizontal (modern) |
| **Language** | Japanese only |
| **Key Value** | **Historical Japanese layout with kuzushiji handwriting for handwriting supplement** |

##### Training Value

- **Strengths**: Contains kuzushiji (historical Japanese cursive) in rare books subset; layout bounding boxes in Pascal VOC format; two distinct eras with different layout characteristics; Public Domain license (no restrictions)
- **Weaknesses**: Moderate size (2,290 images); annotation schema differs between rare/modern subsets; kuzushiji is a specialized handwriting form
- **Critical Use**: **Kuzushiji samples for section 3.6 handwriting supplement; historical Japanese layout diversity**
- **Corpus Role**: Handwriting presence training (rare books subset); IQA training (microfilm degradation in scanned originals); historical document age coverage

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human (NDL Lab annotators) |
| **Provenance Tier** | Tier 1 (Human-annotated) |
| **Quality Assurance** | Professional library digitization standards; Pascal VOC XML validated |
| **GT Label Coverage** | 100% (layout bounding boxes for all 2,290 images) |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/ndl-docl/full_images/` | ❌ Not downloaded | Requires GitHub clone |
| **Annotations** | `01_base_data/language/multilingual_scripts/ndl-docl/tugidigi-annotation/` | ❌ Not available | Pascal VOC XML bounding boxes (kotenseki/ and kindai/ subfolders) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | Docling layout not yet run |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/ndl-docl/full_images/`
- **Phase(s)**: Stream 4E (handwriting supplement), IQA (historical degradation)
- **Purpose**: Kuzushiji handwriting detection, historical Japanese layout, IQA training (microfilm artifacts)
- **Parser**: ✅ Implemented (`parsers/multilingual/ndl_docl.py` — provides language, script, subset (kotenseki/kindai), has_kuzushiji, document_era, layout_annotations from Pascal VOC XML)
- **Config Entry**: `DATASET_CONFIGS["ndl-docl"]`
- **Training Heads**:
  - SIG-G4-1 (handwriting_presence): Rare books subset contains kuzushiji handwriting regions
  - SIG-G2-1 (script_cls): 100% Jpan; kuzushiji variant provides cursive script coverage
  - SIG-G1-* (IQA): Historical scans exhibit microfilm degradation, contrast issues, bleed-through

---

##### Layer 2 Annotation Summary

> **Status**: Not yet enriched. Pending dataset download and Layer 2 pipeline execution.

---

##### 11. Layer 2 Audit Summary

> **Status**: Audited 2026-02-25. PASS WITH WARNINGS. 5 samples (stub — full dataset not yet downloaded).

| Field | Audit Result |
|-------|-------------|
| `capture_method` | OK: `"scanner_flatbed"` |
| `has_handwriting` | OK: `true` (all 5 sampled are kotenseki subset; kindai subset will need `false`) |
| `domain_level1` | Warning: `"UNK"` — recommend `"HIS"` for kotenseki, `"LIT"` for kindai based on subset field |
| `resolution_category` | Warning: `"standard_300"` but pixel dims 7690×6074 suggest ~400–600 DPI. Recommend `"high_>300"` |
| `text_scope_content_type` | Note: `"handwritten"` is correct for kotenseki; kindai subset is `"printed"` — mixed after full ingest |

**Critical gap**: Only 5 of 2,290 images ingested. Full download and re-ingest required.

---

##### Reliability & Bottlenecks

> **Status**: Not yet computed. Pending Layer 2 enrichment.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~2,290 | Pseudo-label | Rare books likely vertical; modern mixed; requires per-image orientation labeling |
| MNV4-H2 | skew_reg | 🟡 | ~2,290 | Pseudo-label | Scanned documents; classical skew detection applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~2,290 | Pseudo-label | Variable scan quality; resolution labeling pipeline applicable |
| SIG-G1-1 | blur_score | 🟡 | ~2,290 | Pseudo-label | Historical scans may exhibit blur from microfilm digitization |
| SIG-G1-2 | noise_score | 🟡 | ~2,290 | Pseudo-label | Aged paper and microfilm introduce noise |
| SIG-G1-3 | contrast_score | 🟡 | ~2,290 | Pseudo-label | Historical documents have variable contrast; foxing and yellowing |
| SIG-G1-4 | skew_score | 🟡 | ~2,290 | Pseudo-label | Scanned originals; skew expected |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | Depends on distribution format; likely lossless |
| SIG-G1-6 | overall_quality | 🟡 | ~2,290 | Pseudo-label | Wide quality range from microfilm to modern digitization |
| SIG-G2-1 | script_cls | ✅ | ~2,290 | GT-derived | 100% Jpan; kuzushiji variant in rare books provides historical cursive coverage |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~2,290 | Pseudo-label | Requires per-image orientation assessment |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~2,290 | Pseudo-label | Post-correction residual skew from scanned originals |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~1,219 | GT-derived | Rare books subset: kuzushiji regions annotated as layout class; presence derivable from VOC annotations |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~1,219 | Pseudo-label | Kuzushiji legibility varies; requires VLM or expert assessment |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~1,219 | GT-derived | Kuzushiji = specialized (historical cursive); derivable from layout class |
| SIG-G4-4 | presence_reg | 🟡 | ~1,219 | Pseudo-label | Kuzushiji region area / total area; derivable from VOC bounding boxes |
| SIG-G4-5 | legibility_reg | ❌ | 0 | Not applicable | Requires per-region legibility annotation |
| SIG-G5-1 | capture_method_cls | ✅ | ~2,290 | GT-exact | 100% scanner_flatbed (library digitization) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | Not applicable | Flatbed scanner; no shadow variation |
| SIG-G5-3 | warping_reg | ➖ | 0 | Not applicable | Flatbed scanner; no page warping |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Japanese literary/historical text; no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~2,290 | Pseudo-label | Variable digitization quality; RQ pipeline applicable |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Jpan); includes kuzushiji (historical cursive) variant not present in other Japanese datasets |
| 2 | Capture method | ✅ | 100% scanner_flatbed (professional library digitization) |
| 3 | Document domain | ✅ | EDU/HIS (historical rare books), ADM/SCI (modern publications); library collection |
| 4 | Layout type | ✅ | Vertical (rare books) and horizontal (modern); multiple layout classes per era |
| 5 | Text density | ✅ | Variable; dense woodblock prints to sparse illustration-heavy pages |
| 6 | Degradation types | ✅ | Foxing, yellowing, bleed-through, ink fading (historical); microfilm artifacts |
| 7 | Resolution/DPI range | 🟡 | Not yet characterized; library digitization typically 300-600 DPI |
| 8 | Document age | ✅ | **Critical**: pre-1868 (Edo period and earlier) + post-1868 (Meiji onwards); covers HISTORICAL and AGED categories |
| 9 | Text scope | ✅ | Mixed: kuzushiji (handwritten cursive), typography (printed), illustrations |
| 10 | Content flags | ✅ | has_figure (illustrations), has_table (modern subset); layout annotations provide flags |
| 11 | Binarization status | 🟡 | Not characterized; historical scans may include binarized microfilm |
| 12 | Artifact types | ✅ | Seals/stamps, foxing, yellowing, ink fading, bleed-through (historical documents) |
| 13 | Color mode | 🟡 | Not yet characterized; likely mix of grayscale (microfilm) and color (modern digitization) |
| 14 | Font variety | ✅ | Kuzushiji brush styles (pre-1868) + modern mincho/gothic typography (post-1868) |

### 13.3 Corpus Role & Constraints

NDL-DocL provides unique **historical Japanese document coverage** with kuzushiji handwriting in the rare books subset (1,219 images, pre-1868). This makes it a primary contributor for SIG-G4-1 (handwriting_presence) in the Japanese script family and fills the HISTORICAL document age dimension that no other dataset in the corpus covers. The layout annotations in Pascal VOC format enable derivation of handwriting presence and content type labels from region classes. The Public Domain Mark (PDM 1.0) license imposes zero restrictions on use, making it the most permissive dataset in the Japanese vertical text collection.
