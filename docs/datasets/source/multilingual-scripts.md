---
dataset_id: multilingual-scripts
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - scanner
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### Multilingual Scripts Collection

> **Quick Stats**: 3,279 images | 4 subdatasets | 4 scripts | Script detection training
>
> **License**: Mixed (CC-BY-4.0 per subdataset) | **Commercial Use**: Yes (with attribution)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multilingual Scripts Collection |
| **Version** | 1.0 |
| **Canonical Name** | `multilingual-scripts` |
| **License** | Mixed CC-BY-4.0 (per subdataset) |
| **Documentation Status** | Partial |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 3,279 |
| **Subdatasets** | 4 |
| **File Format** | PNG |

##### Subdatasets

| Subdataset | Script | Language | Images | Source Type | Notes |
|------------|--------|----------|--------|-------------|-------|
| jssoda | Jpan | ja | 2,000 | Synthetic | Japanese Simple Synthetic OCR; vertical+horizontal |
| nepal_devanagari | Deva | ne | 717 | Real (born_digital/scan) | Atharva Veda PDF pages + 4 newspaper pages at 300 DPI |
| arabic_ocr | Arab | ar | 500 | Real (scanned) | Arabic OCR subset (500-image sample) |
| dzongkha_digits | Tibt | dz | 62 | Synthetic (digital) | Google Jamboard Tibetan digit class-0 subset |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/`
- **Phase(s)**: Phase 10A/10B (Script Detection)
- **Purpose**: Multi-script class training for SIG-G2-1; 4 script families in one collection
- **Parser**: [`MultilingualScriptsParser`](../../src/image_preprocessing_detector/annotation/parsers/multilingual/multilingual_scripts.py) | ✅ Complete
- **L2 File**: `multilingual_scripts_metadata.json`

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/` | ✅ Available | 3,279 PNG files across 4 subdirs |
| **Layer 2 Metadata** | `metadata_registry/json/multilingual_scripts_metadata.json` | ✅ Available | 3,279 records |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~2,500 | Augmented synthetic | Nepal Devanagari pages (717) and Arabic OCR (500) can be augmented with rotations; JSSODa synthetic already has vertical (90°) orientation |
| MNV4-H2 | skew_reg | 🟡 | ~1,200 | Pseudo-label via classical detector | Nepal real scans and Arabic OCR subset exhibit natural skew; JSSODa is clean synthetic |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~1,500 | Pseudo-label via pipeline | Nepal PDF pages at 300 DPI + Arabic scans provide real-world resolution diversity; JSSODa is uniformly clean |
| SIG-G1-1 | blur_score | 🟡 | ~1,200 | Pseudo-label via pipeline | Nepal scans and Arabic OCR subset provide natural blur variation; JSSODa and dzongkha_digits are synthetically clean |
| SIG-G1-2 | noise_score | 🟡 | ~1,200 | Pseudo-label via pipeline | Real-world subsets (nepal + arabic) contribute noise diversity; synthetic subsets are clean negatives |
| SIG-G1-3 | contrast_score | 🟡 | ~1,200 | Pseudo-label via pipeline | Real scanned subsets provide contrast variation; synthetic subsets are high-contrast anchors |
| SIG-G1-4 | skew_score | 🟡 | ~1,000 | Pseudo-label via pipeline | Nepal real pages may have document skew; JSSODa is skew-free synthetic |
| SIG-G1-5 | compression_score | 🟡 | ~1,200 | Pseudo-label via pipeline | Arabic OCR and Nepal JPEG/PNG scans may have JPEG artifacts; JSSODa PNG is lossless |
| SIG-G1-6 | overall_quality | 🟡 | ~1,200 | Pseudo-label via pipeline | Real-world subsets (nepal + arabic) provide IQA diversity; small absolute volume limits primary contribution |
| SIG-G2-1 | script_cls | ✅ | ~3,279 | Ground truth (ISO 15924) | 4 scripts: Jpan=61%, Deva=22%, Arab=15%, Tibt=2%; all confirmed in L2 metadata; strong multi-script diversity |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~2,500 | Augmented synthetic | JSSODa vertical/horizontal orientation labels directly applicable; Nepal+Arabic augmentable |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~1,000 | Pseudo-label via classical detector | Nepal and Arabic real scans contribute post-correction skew data |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~3,279 | Ground truth (content_type=printed) | All 3,279 samples content_type=printed; strong NONE-class anchor for handwriting presence head |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | No handwriting present across any subdataset |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | No handwriting present |
| SIG-G4-4 | presence_reg | ✅ | ~3,279 | Derived (0.0 score) | 100% printed; all samples contribute 0.0 presence anchor for regression |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | No handwriting; not applicable |
| SIG-G5-1 | capture_method_cls | ➖ | 0 | — | capture_method=unknown for all 3,279 samples in L2 metadata; cannot assert real-capture class without enrichment |
| SIG-G5-2 | shadow_reg | ➖ | 0 | — | No shadow annotations; Nepal PDFs are clean born-digital renders; no shadow labels available |
| SIG-G5-3 | warping_reg | ➖ | 0 | — | No warping annotations; PDF-derived pages are flat; no warping labels available |
| SIG-G5-4 | code_cls | ❌ | 0 | — | No code content across any subdataset; all are natural-language document pages or digit images |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~1,500 | Pseudo-label via pipeline | Same rationale as MNV4-H3; Nepal 300 DPI pages and Arabic scans provide real-world resolution range |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 4 script families: CJK/Jpan (61%), Indic/Deva (22%), RTL/Arab (15%), Tibetan/Tibt (2%); best multi-family coverage in the collection |
| 2 | Capture method | 🟡 | Mixed: JSSODa=synthetic, Nepal=born_digital PDF pages, Arabic=scanned, Dzongkha=camera_smartphone (Jamboard); capture_method=unknown in aggregated L2 metadata |
| 3 | Document domain | ❌ | domain_level1=UNK for all 3,279 samples in aggregate; subdatasets span EDU/REL (Nepal Vedic text), GEN (Arabic misc), synthetic (JSSODa) |
| 4 | Layout type | 🟡 | JSSODa: single-column Japanese text (vertical+horizontal); Nepal: book and newspaper layouts; Arabic: OCR document pages; Dzongkha: isolated digit images |
| 5 | Text density | 🟡 | Range from sparse (isolated Dzongkha digits) to dense (Nepal newspaper columns, Arabic document pages); text_scope=mixed for all |
| 6 | Degradation types | 🟡 | Real subsets (Nepal scans, Arabic OCR) have natural degradation; synthetic subsets (JSSODa, Dzongkha) are clean; degradation_types field unpopulated |
| 7 | Resolution/DPI range | 🟡 | Nepal PDF pages at 300 DPI; Arabic OCR at variable scan DPI; JSSODa at consistent synthetic resolution; no explicit DPI metadata |
| 8 | Document age | 🟡 | Nepal Atharva Veda text is ancient content (though PDF conversion is modern); JSSODa and Arabic are contemporary; Dzongkha is 2022 |
| 9 | Text scope | 🟡 | Mixed: JSSODa=line-level, Nepal=page-level, Arabic=page-level, Dzongkha=character-level; text_scope=mixed confirmed |
| 10 | Content flags | ❌ | content_flags empty in aggregate L2 metadata; no has_table, has_figure, or other flags populated |
| 11 | Binarization status | ❌ | No binarized images; all color or grayscale originals |
| 12 | Artifact types | 🟡 | Real-world subsets have natural artifacts; synthetic subsets are clean; no artifact labels in metadata |
| 13 | Color mode | 🟡 | Mixed: JSSODa=color/grayscale synthetic, Nepal=grayscale PDF renders, Arabic=grayscale scans, Dzongkha=RGB digital; content_types=printed confirmed |
| 14 | Font variety | ✅ | Strong cross-script font variety: Japanese typeset fonts (vertical+horizontal), Devanagari book/newspaper fonts, Arabic document fonts, Tibetan digit strokes |

### 13.3 Corpus Role & Constraints

Multilingual-scripts is the **primary multi-script diversity contributor for SIG-G2-1 script_cls**, being the only single-collection source covering 4 distinct script families (CJK, Indic, RTL, Tibetan) with ground-truth ISO 15924 labels. Its value is script breadth, not volume — at 3,279 total images it is supplementary relative to dedicated per-script datasets. The main constraints are: (1) capture_method=unknown for all samples prevents SIG-G5-1 capture classification training; (2) JSSODa (61% of the collection) is synthetic, which may limit naturalness for IQA heads; (3) domain_level1=UNK for all samples prevents domain-stratified sampling.
