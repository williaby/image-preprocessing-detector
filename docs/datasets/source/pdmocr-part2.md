#### pdmocr-part2 (PDM OCR Dataset Part 2)

> **Quick Stats**: ~3,997 images | 1870s-1960s Japanese documents | Explicit text direction GT | Historical
>
> **License**: Public Domain Mark (PDM 1.0) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PDM OCR Dataset Part 2 |
| **Version** | 1.0 |
| **Maintainer** | National Diet Library (NDL Lab) + Morpho AI Solutions |
| **Source** | [github.com/ndl-lab/pdmocrdataset-part2](https://github.com/ndl-lab/pdmocrdataset-part2) |
| **License** | Public Domain Mark (PDM 1.0) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | ~3,997 |
| **Time Span** | 1870s-1960s |
| **Annotation Format** | NDLOCR XML (3-level hierarchy: PAGE -> LINE -> CHAR) |
| **Key Feature** | Explicit DIRECTION attribute (vertical/horizontal/RTL) at LINE/BLOCK level |
| **Organization** | By decade |
| **Language** | Japanese (ja) |
| **Script** | Jpan (ISO 15924) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanner (library flatbed digitization) |
| **Baseline Quality** | Variable (aged paper, yellowing, foxing, ink fading) |
| **Text Direction** | Both vertical and horizontal with **explicit DIRECTION attribute** |
| **Language** | Japanese only |
| **Key Value** | **Text direction ground truth (is_vertical) at line/block level; JPAN script class** |

##### Training Value

- **Strengths**: Explicit text direction ground truth (vertical/horizontal/RTL) -- unique among Japanese datasets; 3-level annotation hierarchy (PAGE/LINE/CHAR); wider time span than Part 1 (extends to 1960s); larger than Part 1 (~3,997 vs ~2,713); Public Domain license
- **Weaknesses**: Historical documents only (no modern born-digital); NDLOCR XML format requires custom parser; no character normalization info
- **Critical Use**: **Text direction (is_vertical) ground truth for orientation validation; JPAN script class with direction labels**
- **Corpus Role**: Primary source of text direction ground truth for Japanese vertical text; orientation validation complement to JSSODa and VJRODa

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human (NDL Lab + Morpho AI Solutions annotators) |
| **Provenance Tier** | Tier 1 (Human-annotated) |
| **Quality Assurance** | Professional annotation with structured NDLOCR XML hierarchy; direction attribute at line level |
| **GT Label Coverage** | 100% (3-level hierarchy with text direction for all annotated lines/blocks) |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/pdmocr-part2/images/` | ❌ Not downloaded | Requires GitHub clone |
| **Annotations** | - | ❌ Not available | NDLOCR XML with DIRECTION attribute (PAGE/LINE/CHAR hierarchy) |
| **Text/OCR Extracted** | - | ❌ Not extracted | GT text available in XML annotations |
| **Layout Extracted** | - | ❌ Not extracted | Docling layout not yet run |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/pdmocr-part2/images/`
- **Phase(s)**: Script detection, orientation validation
- **Purpose**: Text direction ground truth, Japanese script class training, orientation convention validation
- **Parser**: ✅ Implemented (`parsers/multilingual/pdmocr.py` — shared parser for both pdmocr-part1 and pdmocr-part2; provides language, script, DIRECTION attribute (vertical/horizontal/RTL) at line/block level from NDLOCR XML)
- **Config Entry**: `DATASET_CONFIGS["pdmocr-part2"]`
- **Training Heads**:
  - SIG-G2-1 (script_cls): 100% Jpan across 9 decades of Japanese typography
  - SIG-G3-1 (orientation_cls): Text direction GT (vertical/horizontal/RTL) enables orientation validation

---

##### Layer 2 Annotation Summary

> **Status**: Not yet enriched. Pending dataset download and Layer 2 pipeline execution.

---

##### 11. Layer 2 Audit Summary

> **Status**: Audited 2026-02-25. 50 samples. 3 defects resolved.

| Field | Audit Result |
|-------|-------------|
| `capture_method` | Fixed: was `"scanner"` (invalid enum); corrected to `"scanner_flatbed"` via config |
| `has_handwriting` | Fixed: was `null`; corrected to `false` (historical typography with direction annotations, no handwriting) |
| `domain_level1` | Warning: `"UNK"` — can be resolved from NDC classification in metadata |
| `resolution_category` | Warning: `"standard_300"` but pixel dims ~3292×2704 suggest ~400 DPI. Recommend `"high_>300"` |
| Enrichment opportunity | DIRECTION attribute (vertical/horizontal) in NDLOCR XML is not yet extracted into L2 metadata — high-value field for orientation training |

---

##### Reliability & Bottlenecks

> **Status**: Not yet computed. Pending Layer 2 enrichment.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ✅ | ~3,997 | GT-derived | **Explicit DIRECTION attribute** (vertical/horizontal/RTL) at line/block level; derivable to page-level orientation |
| MNV4-H2 | skew_reg | 🟡 | ~3,997 | Pseudo-label | Scanned documents; classical skew detection applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~3,997 | Pseudo-label | Variable scan quality; RQ pipeline applicable |
| SIG-G1-1 | blur_score | 🟡 | ~3,997 | Pseudo-label | Historical scans; blur from aging and digitization |
| SIG-G1-2 | noise_score | 🟡 | ~3,997 | Pseudo-label | Aged paper introduces grain and noise |
| SIG-G1-3 | contrast_score | 🟡 | ~3,997 | Pseudo-label | Historical degradation; ink fading across decades |
| SIG-G1-4 | skew_score | 🟡 | ~3,997 | Pseudo-label | Scanned originals; skew expected |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | Depends on distribution format |
| SIG-G1-6 | overall_quality | 🟡 | ~3,997 | Pseudo-label | Historical degradation provides quality variation |
| SIG-G2-1 | script_cls | ✅ | ~3,997 | GT-derived | 100% Jpan; 9 decades of Japanese typography evolution |
| SIG-G3-1 | orientation_cls (post) | ✅ | ~3,997 | GT-derived | **Explicit DIRECTION attribute**: vertical, horizontal, RTL at line/block level; validates orientation conventions |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~3,997 | Pseudo-label | Post-correction residual skew |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~3,997 | Pseudo-label | Some historical documents may contain handwritten annotations; not explicitly annotated |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | Not applicable | Handwriting not annotated |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | Not applicable | Handwriting not annotated |
| SIG-G4-4 | presence_reg | ❌ | 0 | Not applicable | No handwriting region annotations |
| SIG-G4-5 | legibility_reg | ❌ | 0 | Not applicable | No handwriting region annotations |
| SIG-G5-1 | capture_method_cls | ✅ | ~3,997 | GT-exact | 100% scanner_flatbed (NDL library digitization) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | Not applicable | Flatbed scanner; no shadow variation |
| SIG-G5-3 | warping_reg | ➖ | 0 | Not applicable | Flatbed scanner; minimal warping |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Historical Japanese text; no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~3,997 | Pseudo-label | Variable digitization quality |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Jpan); spans Meiji through Showa era typography |
| 2 | Capture method | ✅ | 100% scanner_flatbed (NDL professional digitization) |
| 3 | Document domain | 🟡 | Organized by decade; domain mix not explicitly categorized |
| 4 | Layout type | ✅ | **Critical**: explicit vertical/horizontal/RTL direction at line/block level; unique GT |
| 5 | Text density | ✅ | Variable; 3-level hierarchy (PAGE/LINE/CHAR) captures density information |
| 6 | Degradation types | ✅ | Foxing, yellowing, ink fading, contrast loss; degree varies by decade |
| 7 | Resolution/DPI range | 🟡 | Not characterized; NDL standard typically 300-400 DPI |
| 8 | Document age | ✅ | **Critical**: 1870s-1960s spanning HISTORICAL to MODERN; wider range than Part 1 |
| 9 | Text scope | ✅ | 100% printed (typography); character-level annotations in hierarchical XML |
| 10 | Content flags | 🟡 | Not characterized from annotations |
| 11 | Binarization status | 🟡 | Not characterized |
| 12 | Artifact types | ✅ | Age-related degradation; scan-related artifacts |
| 13 | Color mode | 🟡 | Not characterized; likely mix of grayscale and color |
| 14 | Font variety | ✅ | Japanese typography evolution across 9 decades |

### 13.3 Corpus Role & Constraints

pdmocr-part2 is the **only dataset in the corpus with explicit text direction ground truth** (vertical/horizontal/RTL) at the line and block level via the NDLOCR XML DIRECTION attribute. This makes it uniquely valuable for validating orientation conventions and providing supervised signal for SIG-G3-1 orientation detection on Japanese text. Combined with its wider time span (1870s-1960s, extending 20 years beyond Part 1) and larger size (~3,997 images), it serves as the primary Japanese historical text resource for orientation and script detection. The Public Domain Mark (PDM 1.0) license imposes zero restrictions.
