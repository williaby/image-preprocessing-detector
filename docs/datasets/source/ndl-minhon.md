#### ndl-minhon (NDL Classical Books OCR Dataset -- Minna de Honkoku)

> **Quick Stats**: 32,822 images | 523,283 line annotations | Kuzushiji + classical Chinese | Crowdsourced GT
>
> **License**: CC-BY-SA 4.0 | **Commercial Use**: Yes (copyleft -- derivatives must use same license)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NDL Classical Books OCR Dataset (Minna de Honkoku) |
| **Version** | v1 (4,688 images) + v2 (28,134 images) |
| **Maintainer** | National Diet Library (NDL Lab) + crowdsourced via Minna de Honkoku platform |
| **Source** | [github.com/ndl-lab/ndl-minhon-ocrdataset](https://github.com/ndl-lab/ndl-minhon-ocrdataset) |
| **License** | CC-BY-SA 4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 32,822 (v1: 4,688 + v2: 28,134) |
| **Line Annotations** | 523,283 |
| **Annotation Format** | Line-level bounding boxes with text transcriptions |
| **Key Feature** | isVertical flag per annotation |
| **Content** | Kuzushiji (pre-Edo) + classical Chinese texts (pre-Qing) |
| **Image Source** | IIIF endpoints (various Japanese archives) |
| **Language** | Japanese (ja) |
| **Script** | Hani (ISO 15924) — kuzushiji manuscripts use Kanji-derived Han script; `Jpan` would apply to modern mixed scripts |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanner (library/archive flatbed digitization via IIIF) |
| **Baseline Quality** | Variable (centuries-old manuscripts; wide quality range from well-preserved to heavily degraded) |
| **Text Direction** | Predominantly vertical (classical Japanese/Chinese); isVertical flag in annotations |
| **Language** | Japanese + classical Chinese |
| **Key Value** | **Largest kuzushiji dataset; historical handwriting for section 3.6 handwriting supplement** |

##### Training Value

- **Strengths**: Largest kuzushiji dataset available (32,822 images, 523K line annotations); crowdsourced transcriptions from dedicated Minna de Honkoku platform; isVertical flag provides text direction GT; covers pre-Edo Japanese and pre-Qing Chinese classical texts; line-level bounding boxes enable region-based handwriting detection
- **Weaknesses**: CC-BY-SA 4.0 copyleft license propagates to derivatives; crowdsourced annotations may have variable quality; IIIF image sourcing may introduce resolution variability; kuzushiji is highly specialized (pre-modern Japanese cursive)
- **Critical Use**: **Dominant kuzushiji handwriting source for SIG-G4-1 handwriting_presence training**
- **Corpus Role**: Primary historical handwriting contributor; fills handwriting_content_type = specialized; largest single Japanese vertical text resource

> **WARNING**: CC-BY-SA 4.0 is a copyleft license. Any derivative datasets or models trained exclusively on this data must be released under CC-BY-SA 4.0 or compatible terms. When mixed with non-copyleft datasets, consult legal guidance on ShareAlike scope.

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Crowdsourced (Minna de Honkoku platform volunteers) |
| **Provenance Tier** | Tier 2 (Crowdsourced) |
| **Quality Assurance** | Platform-based review; community consensus on transcriptions; v2 larger and expected higher quality |
| **GT Label Coverage** | 100% (line-level bounding boxes + text transcriptions + isVertical flag for all 523K annotations) |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/ndl-minhon/images/` | ❌ Not downloaded | Images sourced from IIIF endpoints; requires download script |
| **Annotations** | - | ❌ Not available | Line-level bboxes + transcriptions + isVertical flag |
| **Text/OCR Extracted** | - | ❌ Not extracted | GT transcriptions available in annotations |
| **Layout Extracted** | - | ❌ Not extracted | Docling layout not yet run |

##### Project Usage

- **Path**: `01_base_data/handwriting/ndl-minhon/images/`
- **Phase(s)**: Stream 4E (handwriting supplement), section 3.6
- **Purpose**: Kuzushiji handwriting detection training, historical vertical text, handwriting content type classification
- **Parser**: ✅ Implemented (`parsers/handwriting/ndl_minhon.py` — provides language, script, isVertical flag, line-level bounding boxes, text transcriptions)
- **Config Entry**: `DATASET_CONFIGS["ndl-minhon"]`
- **Training Heads**:
  - SIG-G4-1 (handwriting_presence): **DOMINANT class** -- nearly all images contain handwriting
  - SIG-G4-2 (handwriting_legibility): Variable legibility across centuries of manuscripts
  - SIG-G4-3 (handwriting_content_type): Specialized (kuzushiji historical cursive)

---

##### Layer 2 Annotation Summary

> **Status**: Not yet enriched. Pending dataset download and Layer 2 pipeline execution.

---

##### 11. Layer 2 Audit Summary

> **Status**: Audited 2026-02-25. 500 samples. 2 defects resolved. Cleanest audit in group.

| Field | Audit Result |
|-------|-------------|
| `capture_method` | Fixed: was `"scanner"` (invalid enum); corrected to `"scanner_flatbed"` via config |
| `has_handwriting` | OK: `true` on 100% of 500 samples — best-validated field in the group |
| `iso15924_script` | Deliberate: `"Hani"` (not `"Jpan"`) — kuzushiji manuscripts are Kanji-dominant with no hiragana/katakana; dataset card updated to explain |
| `domain_level1` | Warning: `"UNK"` — unambiguously `"HIS"` (pre-Edo manuscripts); deferred to domain pass |
| `resolution_category` | Warning: `"standard_300"` but pixel dims ~3142×2480 suggest ~380 DPI. Recommend `"high_>300"` |
| License | Note: CC-BY-SA 4.0 copyleft — any derivative works must use same license |

---

##### Reliability & Bottlenecks

> **Status**: Not yet computed. Pending Layer 2 enrichment.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~32,822 | GT-derived | isVertical flag in annotations; predominantly vertical (classical texts); derivable to page orientation |
| MNV4-H2 | skew_reg | 🟡 | ~32,822 | Pseudo-label | Scanned manuscripts; classical skew detection applicable; variable scan alignment |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~32,822 | Pseudo-label | IIIF-sourced images with variable resolution; RQ pipeline applicable |
| SIG-G1-1 | blur_score | 🟡 | ~32,822 | Pseudo-label | Centuries-old manuscripts; ink diffusion and paper degradation cause blur |
| SIG-G1-2 | noise_score | ✅ | ~32,822 | Pseudo-label | Aged paper with foxing, staining, and noise; rich degradation variety |
| SIG-G1-3 | contrast_score | ✅ | ~32,822 | Pseudo-label | Ink fading over centuries; wide contrast range from well-preserved to heavily degraded |
| SIG-G1-4 | skew_score | 🟡 | ~32,822 | Pseudo-label | Scanned manuscripts; variable alignment |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | IIIF delivery format varies; typically JPEG |
| SIG-G1-6 | overall_quality | ✅ | ~32,822 | Pseudo-label | Wide quality range; centuries of aging provide natural quality distribution |
| SIG-G2-1 | script_cls | ✅ | ~32,822 | GT-derived | 100% Hani; kuzushiji (historical cursive) + classical Chinese characters; annotated as Han script due to Kanji dominance |
| SIG-G3-1 | orientation_cls (post) | ✅ | ~32,822 | GT-derived | isVertical flag; predominantly vertical (classical Japanese/Chinese texts) |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~32,822 | Pseudo-label | Post-correction residual skew |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~32,822 | GT-exact | **DOMINANT class**: virtually all images contain handwritten kuzushiji; largest handwriting presence source |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~32,822 | Pseudo-label | Variable legibility; well-preserved brush strokes to heavily faded manuscripts; VLM assessment needed |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | ~32,822 | GT-derived | 100% specialized (kuzushiji = pre-modern Japanese cursive); unique content type |
| SIG-G4-4 | presence_reg | ✅ | ~32,822 | GT-derived | Handwriting dominates; presence ratio derivable from line bbox area / page area |
| SIG-G4-5 | legibility_reg | 🟡 | ~32,822 | Pseudo-label | Requires per-line legibility assessment; not in current annotations |
| SIG-G5-1 | capture_method_cls | ✅ | ~32,822 | GT-exact | 100% scanner_flatbed (library/archive digitization) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | Not applicable | Flatbed scanner; no shadow variation |
| SIG-G5-3 | warping_reg | 🟡 | ~32,822 | Pseudo-label | Some manuscripts may show page curl or warping from binding; not annotated |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Classical Japanese/Chinese texts; no code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~32,822 | Pseudo-label | IIIF-sourced; variable resolution |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Hani); kuzushiji (historical cursive) + classical Chinese characters; annotated as Hani (not Jpan) because pre-Edo manuscripts are predominantly Kanji-based with no hiragana/katakana mixing |
| 2 | Capture method | ✅ | 100% scanner_flatbed (library/archive digitization via IIIF) |
| 3 | Document domain | ✅ | EDU/HIS (classical literature, historical records); specialized classical collection |
| 4 | Layout type | ✅ | Predominantly vertical (classical Japanese/Chinese text); isVertical flag in annotations |
| 5 | Text density | ✅ | Variable; dense calligraphic manuscripts to sparsely annotated pages |
| 6 | Degradation types | ✅ | **Rich variety**: foxing, ink fading, paper yellowing, staining, insect damage, water damage; centuries of aging |
| 7 | Resolution/DPI range | 🟡 | IIIF-sourced; variable resolution across archives; not yet characterized |
| 8 | Document age | ✅ | **Critical**: pre-Edo period and earlier (centuries old); fills HISTORICAL category exclusively |
| 9 | Text scope | ✅ | 100% handwritten (kuzushiji brush calligraphy); line-level annotations |
| 10 | Content flags | 🟡 | Classical texts; may contain illustrations (e-maki style); not yet characterized |
| 11 | Binarization status | 🟡 | Not characterized; likely all color from IIIF digitization |
| 12 | Artifact types | ✅ | **Extensive**: foxing, ink diffusion, paper degradation, binding artifacts, seal stamps, repair patches |
| 13 | Color mode | 🟡 | Not characterized; IIIF typically serves color images |
| 14 | Font variety | ✅ | **Unique**: kuzushiji brush calligraphy with wide stylistic variation across centuries and scribes |

### 13.3 Corpus Role & Constraints

ndl-minhon is the **largest kuzushiji dataset** in the corpus (32,822 images, 523K line annotations) and serves as the **dominant contributor for SIG-G4-1 handwriting_presence** where nearly all images contain handwritten content. It uniquely fills the handwriting_content_type = specialized class (kuzushiji historical cursive) and provides the deepest HISTORICAL document age coverage. The crowdsourced annotations from the Minna de Honkoku platform provide line-level bounding boxes with isVertical flags, enabling both handwriting detection and orientation training. **License caution**: CC-BY-SA 4.0 copyleft requires derivative works to maintain the same license, which may constrain how trained models or derived datasets are distributed. When mixing with non-copyleft datasets, ensure the ShareAlike obligation is properly scoped.
