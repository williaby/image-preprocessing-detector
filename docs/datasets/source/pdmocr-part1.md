#### pdmocr-part1 (PDM OCR Dataset Part 1)

> **Quick Stats**: ~2,713 images | 1870s-1940s Japanese documents | Character-level bounding boxes | Historical
>
> **License**: Public Domain Mark (PDM 1.0) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PDM OCR Dataset Part 1 |
| **Version** | 1.0 |
| **Maintainer** | National Diet Library (NDL Lab) + LINE Corporation |
| **Source** | [github.com/ndl-lab/pdmocrdataset-part1](https://github.com/ndl-lab/pdmocrdataset-part1) |
| **License** | Public Domain Mark (PDM 1.0) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | ~2,713 |
| **Time Span** | 1870s-1940s |
| **Annotation Format** | JSON + Pascal VOC XML (character-level bounding boxes) |
| **Organization** | By decade (1870, 1880, 1890...) and category (humanities/science) |
| **Character Normalization** | None (preserves archaic kanji forms) |
| **Language** | Japanese (ja) |
| **Script** | Jpan (ISO 15924) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanner (library flatbed digitization) |
| **Baseline Quality** | Variable (aged paper, yellowing, foxing, ink fading) |
| **Text Direction** | Mixed vertical and horizontal (era-dependent; earlier decades predominantly vertical) |
| **Language** | Japanese only |
| **Key Value** | **Historical Japanese text with character-level GT; archaic kanji preservation** |

##### Training Value

- **Strengths**: Character-level bounding boxes (finest granularity among NDL datasets); preserves archaic kanji forms without normalization; dual annotation formats (JSON + Pascal VOC); organized by decade enabling document age stratification; Public Domain license
- **Weaknesses**: Moderate size (~2,713 images); no explicit text direction annotation; historical documents only (no modern coverage)
- **Critical Use**: **JPAN script class training with historical degradation; character-level GT for OCR validation**
- **Corpus Role**: Script detection training (historical Jpan); IQA training (aged paper degradation across 7 decades)

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human (NDL Lab + LINE Corporation annotators) |
| **Provenance Tier** | Tier 1 (Human-annotated) |
| **Quality Assurance** | Professional annotation with archaic kanji preservation; dual format cross-validation |
| **GT Label Coverage** | 100% (character-level bounding boxes + transcriptions for all images) |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/pdmocr-part1/images/` | ❌ Not downloaded | Requires GitHub clone |
| **Annotations** | - | ❌ Not available | JSON + Pascal VOC XML character-level bboxes |
| **Text/OCR Extracted** | - | ❌ Not extracted | GT text available in annotations |
| **Layout Extracted** | - | ❌ Not extracted | Docling layout not yet run |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/pdmocr-part1/images/`
- **Phase(s)**: Script detection, IQA (historical degradation)
- **Purpose**: Japanese script class training, historical IQA degradation, character-level GT
- **Parser**: ✅ Implemented (`parsers/multilingual/pdmocr.py` — shared parser for both pdmocr-part1 and pdmocr-part2; provides language, script, text direction, character-level annotations)
- **Config Entry**: `DATASET_CONFIGS["pdmocr-part1"]`
- **Training Heads**:
  - SIG-G2-1 (script_cls): 100% Jpan with archaic kanji forms
  - SIG-G1-* (IQA): Historical degradation across 7 decades (1870s-1940s) -- yellowing, foxing, ink fading

---

##### Layer 2 Annotation Summary

> **Status**: Not yet enriched. Pending dataset download and Layer 2 pipeline execution.

---

##### 11. Layer 2 Audit Summary

> **Status**: Not yet audited. Pending Layer 2 enrichment.

---

##### Reliability & Bottlenecks

> **Status**: Not yet computed. Pending Layer 2 enrichment.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~2,713 | Pseudo-label | Historical documents; orientation varies; requires per-image labeling |
| MNV4-H2 | skew_reg | 🟡 | ~2,713 | Pseudo-label | Scanned documents; classical skew detection applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~2,713 | Pseudo-label | Variable scan quality across decades; RQ pipeline applicable |
| SIG-G1-1 | blur_score | 🟡 | ~2,713 | Pseudo-label | Historical scans; blur from aging and digitization process |
| SIG-G1-2 | noise_score | 🟡 | ~2,713 | Pseudo-label | Aged paper introduces grain and noise |
| SIG-G1-3 | contrast_score | ✅ | ~2,713 | Pseudo-label | Wide contrast range from ink fading over decades; decade-stratified sampling possible |
| SIG-G1-4 | skew_score | 🟡 | ~2,713 | Pseudo-label | Scanned originals; skew expected |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | Depends on distribution format |
| SIG-G1-6 | overall_quality | 🟡 | ~2,713 | Pseudo-label | Historical degradation provides quality variation; decade-stratified |
| SIG-G2-1 | script_cls | ✅ | ~2,713 | GT-derived | 100% Jpan; archaic kanji forms not normalized; unique historical variant |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~2,713 | Pseudo-label | Requires per-image orientation assessment |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~2,713 | Pseudo-label | Post-correction residual skew |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~2,713 | Pseudo-label | Some documents may contain handwritten annotations; not annotated |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | Not applicable | Handwriting presence not annotated |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | Not applicable | Handwriting presence not annotated |
| SIG-G4-4 | presence_reg | ❌ | 0 | Not applicable | No handwriting region annotations |
| SIG-G4-5 | legibility_reg | ❌ | 0 | Not applicable | No handwriting region annotations |
| SIG-G5-1 | capture_method_cls | ✅ | ~2,713 | GT-exact | 100% scanner_flatbed (NDL library digitization) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | Not applicable | Flatbed scanner; no shadow variation |
| SIG-G5-3 | warping_reg | ➖ | 0 | Not applicable | Flatbed scanner; minimal warping |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Historical Japanese text; no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~2,713 | Pseudo-label | Variable digitization quality; RQ pipeline applicable |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Jpan); archaic kanji forms preserved without normalization |
| 2 | Capture method | ✅ | 100% scanner_flatbed (NDL professional digitization) |
| 3 | Document domain | ✅ | Humanities and science categories; organized by decade |
| 4 | Layout type | 🟡 | Mixed vertical/horizontal; earlier decades predominantly vertical; not explicitly annotated |
| 5 | Text density | ✅ | Variable; dense woodblock-style to spaced modern typography |
| 6 | Degradation types | ✅ | Foxing, yellowing, ink fading, contrast loss, bleed-through; degree increases with document age |
| 7 | Resolution/DPI range | 🟡 | Not characterized; NDL standard typically 300-400 DPI |
| 8 | Document age | ✅ | **Critical**: 1870s-1940s spanning HISTORICAL to AGED categories; decade-stratified |
| 9 | Text scope | ✅ | 100% printed (typography); character-level annotations |
| 10 | Content flags | 🟡 | Not characterized; humanities/science categories suggest varied content |
| 11 | Binarization status | 🟡 | Not characterized; may include binarized microfilm scans |
| 12 | Artifact types | ✅ | Age-related: foxing, yellowing, ink fading; digitization: scan line artifacts |
| 13 | Color mode | 🟡 | Not characterized; likely mix of grayscale and color |
| 14 | Font variety | ✅ | Historical typography spanning Meiji-Showa eras; archaic kanji forms |

### 13.3 Corpus Role & Constraints

pdmocr-part1 provides **character-level bounding box annotations** for historical Japanese documents spanning seven decades (1870s-1940s), making it one of the finest-grained OCR datasets in the corpus. Its preservation of archaic kanji forms without normalization makes it uniquely valuable for SIG-G2-1 script detection where the model must handle historical Japanese variants. The decade-organized structure enables stratified sampling for document age diversity. The Public Domain Mark (PDM 1.0) license imposes zero restrictions.
