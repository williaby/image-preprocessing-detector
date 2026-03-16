---
dataset_id: indicdlp
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - varied_quality
  - scanner_artifacts
  - born_digital
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: partial
---

#### IndicDLP (Indic Document Layout Parser)

> **Quick Stats**: 115,803 images | Mixed born-digital + scanned | 42 layout classes | 12 Indian languages
>
> **License**: MIT | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | IndicDLP (Indic Document Layout Parser) |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Last Updated** | 2025 |
| **Maintainer** | AI4Bharat |
| **Paper** | [IndicDLP: Towards Indic Document Layout Parsing (2025)](https://huggingface.co/datasets/ai4bharat/indicdlp) |
| **Repository** | [HuggingFace: ai4bharat/indicdlp](https://huggingface.co/datasets/ai4bharat/indicdlp) |
| **License** | MIT |
| **Commercial Use** | Yes |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG | Document page images |
| **Annotations** | JSON | COCO-format layout annotations with 42 classes |
| **Supplementary** | README | Dataset description, citation, usage instructions |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/` | `train/annotations.json` | ~95,000 | ✅ |
| **Validation** | `val/` | `val/annotations.json` | ~12,000 | ✅ |
| **Test** | `test/` | `test/annotations.json` | ~12,000 | ✅ |
| **Total** | - | - | ~119,000 | ✅ |

**Split Organization Pattern**: `by_folder` with COCO JSON annotations per split

> **Notes**:
>
> - **GATED DATASET**: HuggingFace access requires accepting terms at the dataset page and authenticating with `huggingface-cli login`
> - Standard train/val/test split organization
> - Each split has dedicated COCO JSON with images, annotations, categories
> - Approximate counts from HuggingFace listing

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | COCO | Region | Layout region coordinates [x,y,w,h] |
| **Layout Classes** | COCO categories | Region | 42 Indic-specific layout classes |
| **Language Tags** | Metadata | Document | 12 Indian languages per image |

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace README | License, citation, class taxonomy |
| **Image-level** | COCO images | Filename, dimensions, language tag |
| **Annotation-level** | COCO annotations | Bounding box, category_id, area |

##### 2.5 Annotation Schema Details

> **Format**: COCO layout detection format with 42 Indic-specific classes

```text
{
  "images": [
    {
      "id": int,
      "file_name": str,
      "width": int,
      "height": int,
      "language": str  # Hindi, Bengali, Tamil, etc.
    }
  ],
  "annotations": [
    {
      "id": int,
      "image_id": int,
      "category_id": int,
      "bbox": [x, y, width, height],
      "area": float
    }
  ],
  "categories": [
    {
      "id": int,
      "name": str  # 42 classes including Indic-specific elements
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | int | Yes | Links annotation to image |
| `bbox` | list | Yes | COCO format [x,y,w,h] |
| `category_id` | int | Yes | Maps to 42 layout classes |
| `language` | str | Yes | ISO 639 language code |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Layout boxes | `layout_annotations` | High | COCO format, 42 classes |
| ✅ Language tags | `iso639_language` | High | 12 Indian languages |
| ✅ Script info | `script_family` | High | Derived from language |
| ❌ Text GT | - | Low | Not provided |
| ❌ Quality scores | - | Low | Compute from IQA analysis |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] - Likely trained annotators at AI4Bharat |
| **Inter-Annotator Agreement** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | [NEEDS_VERIFICATION] - Standard COCO annotation review process expected |
| **GT Label Coverage** | 100% - All images have COCO layout annotations with 42 classes |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (multilingual layout detection) |
| **Purpose** | Training Indic script layout models |
| **Local Path** | `01_base_data/layout/indicdlp/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | COCO annotation parsing, language normalization |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `indicdlp` (layout category) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `indicdlp_annotations` (COCO format, 42 classes) |
| **Layer 2 Auto-Derived** | `script_family` (Devanagari/Bengali/Tamil/etc.), `iso639_language` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for COCO layout field mappings.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/layout/indicdlp/` | ✅ Available | Train/val/test splits |
| **Layout GT** | `01_base_data/layout/indicdlp/{split}/annotations.json` | ✅ COCO format | 42-class taxonomy |
| **Text/OCR GT** | - | ❌ Not provided | No ground truth text |
| **Text/OCR Extracted** | `annotations/indicdlp/ocr/` | ❌ Not extracted | DocLayout-YOLO pending |
| **Layout Extracted** | - | ℹ️ N/A | GT already provided |
| **Layer 2 Metadata** | `metadata_registry/json/indicdlp_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- ℹ️ N/A - Not applicable

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~95,000 | 0 | 0% | ❌ Parser not implemented |
| **Validation** | ~12,000 | 0 | 0% | ❌ Parser not implemented |
| **Test** | ~12,000 | 0 | 0% | ❌ Parser not implemented |
| **Total** | ~119,000 | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ❌ Missing - Split not included in Layer 2 metadata

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 115,803 (verified count) |
| **Training Split** | ~92,642 (80%) |
| **Validation Split** | ~11,580 (10%) |
| **Test Split** | ~11,581 (10%) |
| **Image Dimensions** | Variable (document scans + born-digital) |
| **Resolution (DPI)** | Variable |
| **File Format(s)** | JPG, PNG |
| **Color Space** | RGB / Grayscale |
| **Total Size on Disk** | ~15 GB (estimated) |
| **Annotation Format** | COCO JSON |

##### 4.3 Text Statistics

> **Availability**: ❌ Not Available - No ground truth text provided in source dataset.

##### Directory Structure

```text
indicdlp/
├── train/
│   ├── images/
│   │   └── *.jpg, *.png
│   └── annotations.json
├── val/
│   ├── images/
│   └── annotations.json
└── test/
    ├── images/
    └── annotations.json
```

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Empirical profiling not yet run on this dataset.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | UNKNOWN (mixed Indic documents - government, educational, publications) |
| **Document Types** | Official documents, books, newspapers, forms |
| **Language(s)** | 12 Indian languages (see Section 5.3) |
| **Temporal Range** | Unknown (likely modern + historical scanned documents) |
| **Acquisition Method** | Mixed: born-digital + scanner-flatbed |

##### 5.1 Class/Category Distribution

> **Note**: Distribution across 42 classes not publicly documented. Likely includes standard DocLayNet classes plus Indic-specific elements (e.g., specific header/footer styles, regional layout patterns).

##### 5.2 Class/Category Definitions

> **Purpose**: IndicDLP defines 42 layout classes tailored to Indic document structures.

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Text | - | Body text paragraphs | - |
| Title | - | Document/section titles | - |
| Table | - | Tabular regions | - |
| Figure | - | Images, charts, diagrams | - |
| List-Item | - | Bulleted/numbered lists | - |
| Header | - | Page headers | - |
| Footer | - | Page footers | - |
| Caption | - | Image/table captions | - |
| Formula | - | Mathematical equations | - |
| ... | - | 33 additional Indic-specific classes | - |

> **Notes**:
>
> - Full 42-class taxonomy requires consultation of HuggingFace dataset card
> - Likely includes Indic-specific elements (regional address blocks, specific seal/stamp regions, multilingual section headers)

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Devanagari (Hindi) | hin (Deva) | ~10,000+ | ~8-10% | Primary North Indian script |
| Bengali | ben (Beng) | ~10,000+ | ~8-10% | Bengali script |
| Tamil | tam (Taml) | ~10,000+ | ~8-10% | Dravidian script |
| Telugu | tel (Telu) | ~10,000+ | ~8-10% | Dravidian script |
| Kannada | kan (Knda) | ~8,000+ | ~7-9% | Dravidian script |
| Malayalam | mal (Mlym) | ~8,000+ | ~7-9% | Dravidian script |
| Gujarati | guj (Gujr) | ~8,000+ | ~7-9% | Brahmic script |
| Marathi | mar (Deva) | ~8,000+ | ~7-9% | Devanagari script |
| Odia | ori (Orya) | ~8,000+ | ~7-9% | Odia script |
| Punjabi | pan (Guru) | ~8,000+ | ~7-9% | Gurmukhi script |
| Assamese | asm (Beng) | ~5,000+ | ~4-6% | Bengali-Assamese script |
| Urdu | urd (Arab) | ~5,000+ | ~4-6% | Arabic script (right-to-left) |

**Script Families Present**: Brahmic (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Odia, Gurmukhi), Arabic

> **Notes**:
>
> - Exact distribution not publicly documented; estimates based on ~119K total
> - Covers 10 distinct script families plus Latin (often present in headers/technical terms)
> - Unique challenge: script-confusable characters across Indic scripts

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Mixed: born-digital + scanned historical/government documents |
| **Capture Device** | Flatbed scanners (historical), programmatic rendering (born-digital) |
| **Original Quality** | Varied: clean born-digital to degraded scanned documents |
| **Compression** | JPEG/PNG compression (variable quality) |
| **Known Artifacts** | Scanner noise, page curl, yellowing (historical), JPEG blocking |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | MEDIUM-HIGH | Indic scripts have complex glyphs sensitive to blur |
| **Noise** | MEDIUM | Scanned historical documents show noise artifacts |
| **Skew** | HIGH | Text alignment critical for connected Indic scripts |
| **Contrast** | MEDIUM | Variable quality in scanned historical documents |
| **Compression** | HIGH | JPEG artifacts affect diacritic marks and complex glyphs |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | 8-16pt typical | Small Indic text fragile to blur/compression |
| **Script Complexity** | High | Conjunct consonants, matras, diacritics sensitive to degradation |
| **Font Diversity** | High | Regional fonts vary across languages |
| **Color Usage** | Mixed | B&W historical + color modern documents |
| **Layout Complexity** | Medium-High | Mixed single/multi-column, embedded tables |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Largest multilingual Indic layout dataset |
| **Unique Characteristics** | 12 languages, 42 layout classes, mixed quality |
| **Complementary Datasets** | Combine with DocLayNet for global coverage |
| **Benchmark Suitability** | MEDIUM - Pre-split train/val/test but distribution not fully documented |
| **Known Limitations** | No text GT, limited documentation on class definitions |

#### 7. Known Issues & Limitations

- **No Text Ground Truth**: Layout annotations only; no OCR text provided
- **Class Taxonomy Undocumented**: 42 classes listed but full definitions not in public docs
- **Quality Variance**: Mixed born-digital + scanned creates wide quality range
- **Script Complexity**: Indic scripts require specialized OCR; layout alone insufficient for full pipeline
- **Limited Provenance**: Document sources and temporal range not fully documented
- **No IQA Scores**: Quality assessment requires empirical profiling
- **Language Balance**: Distribution across 12 languages not publicly documented

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling and VLM inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{ai4bharat2025indicdlp,
  title={IndicDLP: Towards Indic Document Layout Parsing},
  author={AI4Bharat},
  year={2025},
  publisher={HuggingFace},
  url={https://huggingface.co/datasets/ai4bharat/indicdlp}
}
```

##### Related Works

- [DocLayNet](doclaynet.md) - Multi-domain layout detection (Latin scripts)
- [MDIW13](mdiw13.md) - Multilingual Indic scene text dataset
- [MLT19](mlt19.md) - Multilingual text detection including Indic scripts

##### Leaderboards

- None currently available

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **42-Class Taxonomy**: Full class definitions require parsing COCO categories JSON; not all documented in README
- **Language Tags**: Each image tagged with one of 12 languages; useful for script-specific model training
- **Mixed Quality**: Historical scanned documents may have poor OCR accuracy despite good layout annotations

##### 10.2 Implementation Notes

- **Parser Priority**: High - enables Indic script layout training
- **Script Mapping**: Use ISO 639 language codes to derive ISO 15924 script codes
- **COCO Format**: Standard COCO layout format enables direct integration with existing pipelines
- **Quality Gating**: Consider IQA profiling to filter low-quality scans before training

##### 10.3 External Resources

- **HuggingFace Dataset Card**: [https://huggingface.co/datasets/ai4bharat/indicdlp](https://huggingface.co/datasets/ai4bharat/indicdlp)
- **AI4Bharat Organization**: [https://ai4bharat.org/](https://ai4bharat.org/)

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser not yet implemented.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser not implemented - no Layer 2 metadata available for reliability analysis.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~40K | Derived (assume 0°) | No explicit rotation labels; most documents likely upright; contributes as 0° class with uncertainty |
| MNV4-H2 | skew_reg | 🟡 Secondary | ~20K scanned | Derived via classical IQA | Scanned subset will have natural skew; classical ensemble labeling applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~40K | Derived via IQA | Mixed quality range (born-digital high, scanned variable); useful mid-range diversity |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~119K | Derived via IQA | Scanned subset contributes blur diversity; born-digital subset provides clean anchors |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~119K | Derived via IQA | Scanned historical documents contribute noise variation |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~119K | Derived via IQA | Variable contrast from historical scans and born-digital |
| SIG-G1-4 | skew_score | 🟡 Secondary | ~20K scanned | Derived via classical IQA | Scanned subset has real skew; flat rendered subset scores 0 |
| SIG-G1-5 | compression_score | 🟡 Secondary | ~119K | Derived via IQA | JPEG compression variable across scanned and born-digital images |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~119K | Derived via IQA | Wide quality range adds distribution diversity |
| SIG-G2-1 | script_cls | ✅ Primary | ~119K | Derived from language tags | 12 language tags map to Deva, Beng, Taml, Telu, Knda, Mlym, Gujr, Orya, Guru, Arab ISO codes; critical Indic script diversity |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~40K | Derived (assume 0°) | Same caveats as MNV4-H1; useful for upright Indic document coverage |
| SIG-G3-2 | skew_reg (post) | 🟡 Secondary | ~20K scanned | Derived via classical IQA | Post-correction skew reference for scanned Indic documents |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | ~119K | Derived (mostly printed) | Predominantly printed documents; strong negative class; some historical docs may have handwritten annotations |
| SIG-G4-2 | handwriting_legibility_cls | ➖ Negative | 0 | N/A | No explicit handwriting legibility annotations; excluded to avoid noise |
| SIG-G4-3 | handwriting_content_type_cls | ➖ Negative | 0 | N/A | No handwriting content type labels available |
| SIG-G4-4 | presence_reg | 🟡 Secondary | ~119K | Derived (mostly 0.0) | Near-0.0 printed document anchor; small fraction may have handwritten notes |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | 0 | N/A | No handwriting legibility labels; excluded |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~119K | Derived from capture method | Mixed born-digital + scanned; real images qualify — born_digital and scanner labels derivable |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | 0 | N/A | No shadow labels; scanned documents may have minor shadows but not annotated |
| SIG-G5-3 | warping_reg | ❌ Not applicable | 0 | N/A | No warping labels; minimal physical warping in flatbed scans |
| SIG-G5-4 | code_cls | 🟡 Secondary | ~5K (est.) | Derived from layout | 42 layout classes may include code/technical text blocks in scientific/educational documents |
| SIG-G5-5 | resolution_quality_reg | 🟡 Secondary | ~119K | Derived via IQA | Mixed DPI range; scanned subset adds lower-resolution diversity |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ Good | 10 distinct Indic scripts: Devanagari (DEVA), Bengali (BENG), Tamil (TAML), Telugu (TELU), Kannada (KNDA), Malayalam (MLYM), Gujarati (GUJR), Odia (ORYA), Gurmukhi (GURU), Arabic (ARAB); critical diversity gap-filler for Indic scripts |
| 2 | Capture method | ✅ Good | Mixed born-digital (programmatic) + flatbed scanner; real images qualify for SIG-G5-1; both capture method classes present |
| 3 | Document domain | 🟡 Partial | Government, educational, and publication documents across Indian languages; domain labels not fully documented but inferrable |
| 4 | Layout type | ✅ Good | 42 Indic-specific layout classes covering multi-column books, newspapers, forms, official documents, single-column text |
| 5 | Text density | ✅ Good | High text density typical of Indic publications; newspapers (dense) through forms (sparse) represented |
| 6 | Degradation types | 🟡 Partial | Scanner artifacts (noise, yellowing, JPEG blocking) present in scanned subset; born-digital subset is clean; no explicit degradation labels |
| 7 | Resolution/DPI range | 🟡 Partial | Variable DPI from mixed sources; born-digital uniform high; scanned subset spans 150-400 DPI range (estimated) |
| 8 | Document age | 🟡 Partial | Mix of modern born-digital and historical scanned documents; temporal range not fully documented but likely spans decades |
| 9 | Text scope | 🟡 Partial | Document-level and region-level layout boxes; no word/character-level text GT |
| 10 | Content flags | ✅ Good | Tables, figures, formulas, headers, footers, captions all present via 42-class COCO taxonomy; no handwriting or code flags |
| 11 | Binarization status | ❌ None | No binarized documents; color/grayscale scans and born-digital only |
| 12 | Artifact types | 🟡 Partial | Scanner noise, page curl (minor), yellowing (historical), JPEG blocking present in scanned subset; no explicit artifact labels |
| 13 | Color mode | 🟡 Partial | Mixed: color born-digital + grayscale/color scans; no forced color-mode curation |
| 14 | Font variety | ✅ Good | High regional font diversity across 12 languages and 10 scripts; Indic typefaces vary significantly across regions and publishers |

### 13.3 Corpus Role & Constraints

IndicDLP's primary training contribution is SIG-G2-1 (script_cls) — it is the largest source of real document images for 10 Indic script families (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Odia, Gurmukhi, Arabic), all of which are critically underrepresented in other layout and IQA datasets. It also contributes to SIG-G5-1 (capture_method_cls) as a real mixed-capture dataset. The MIT license permits unrestricted commercial use with no synthetic mixing constraints. The parser is not yet implemented (Layer 2 metadata pending), so script labels must be derived from the language metadata field in the COCO JSON; shadow and warping regression heads require additional labeling work before this dataset can contribute there.
