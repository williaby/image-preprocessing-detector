---
dataset_id: vjroda
version: "1.0"
license: Unknown
commercial_use: unknown
iqa_profiles:
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### VJRODa (Vertical Japanese Real-world OCR Dataset)

> **Quick Stats**: 100 images | Vertical Japanese government PDFs | Real-world | OOD evaluation
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Vertical Japanese Real-world OCR Dataset |
| **Version** | 1.0 |
| **Maintainer** | LLM-JP / National Institute of Informatics |
| **Source** | [gitlab.llm-jp.nii.ac.jp/datasets/vjroda](https://gitlab.llm-jp.nii.ac.jp/datasets/vjroda) |
| **Paper** | [arXiv:2511.15059](https://arxiv.org/abs/2511.15059) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 100 |
| **Text Direction** | 100% vertical (tategaki) |
| **Source Documents** | Japanese government PDFs |
| **Rendering** | 150 DPI from PDF |
| **File Format** | PNG (rendered from PDF) |
| **Language** | Japanese (ja) |
| **Script** | Jpan (ISO 15924) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (PDF rendering at 150 DPI) |
| **Baseline Quality** | Clean (born-digital origin) |
| **Text Direction** | 100% vertical (tategaki) |
| **Language** | Japanese only |
| **Key Value** | **Real-world vertical Japanese text for OOD evaluation** |

##### Training Value

- **Strengths**: 100% real-world vertical Japanese text from government PDFs; provides authentic tategaki samples; CC-BY-4.0 permissive license
- **Weaknesses**: Small dataset (100 images); born-digital only (no scan artifacts); single domain (government/administrative); 150 DPI is below optimal (300 DPI target)
- **Critical Use**: **OOD evaluation set for JPAN vertical text and script detection validation**
- **Corpus Role**: Validation/evaluation only (too small for training); complements JSSODa synthetic data with real-world samples

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human (text transcriptions with structural tags) |
| **Provenance Tier** | Tier 1 (Human-annotated) |
| **Quality Assurance** | Header/footer/caption tags in transcriptions; curated from government PDFs |
| **GT Label Coverage** | 100% (text transcriptions for all 100 images) |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/vjroda/` | ❌ Not downloaded | Requires GitLab clone |
| **Text/GT** | - | ❌ Not available | Text transcriptions with header/footer/caption tags |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | Docling layout not yet run |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/vjroda/`
- **Phase(s)**: OOD evaluation
- **Purpose**: Vertical text orientation validation, Japanese script detection validation
- **Parser**: ✅ Implemented (`parsers/multilingual/vjroda.py` — provides language, script, is_vertical, text_orientation, transcription, source_url)
- **Config Entry**: `DATASET_CONFIGS["vjroda"]`
- **Training Heads**:
  - SIG-G2-1 (script_cls): Validation only -- 100% Jpan, real-world vertical text
  - SIG-G3-1 (orientation_cls): Validation only -- vertical text orientation convention check

---

##### Layer 2 Annotation Summary

> **Status**: Not yet enriched. Pending dataset download and Layer 2 pipeline execution.

---

##### 11. Layer 2 Audit Summary

> **Status**: Audited 2026-02-25. 18 samples (full partial-download set). 3 defects resolved.

| Field | Audit Result |
|-------|-------------|
| `capture_method` | Fixed: was `"scanner"` (invalid enum); corrected to `"scanner_flatbed"` via config |
| `has_handwriting` | Fixed: was `null`; corrected to `false` (100% printed government documents) |
| `resolution_category` | Warning: `"standard_300"` assigned by DPI=null default; actual ~100 DPI (834px wide). Recommend `"low_<150"` after DPI estimation pass |
| `domain_level1` | Warning: `"ADM"` — correct for government docs; no further action needed |
| Schema drift | Cross-cutting: flat field structure vs. schema nested objects (pipeline-level issue, not dataset-specific) |

**Remaining gap**: Only 18 of ~100 images downloaded. Full ingest required once download is complete.

---

##### Reliability & Bottlenecks

> **Status**: Not yet computed. Pending Layer 2 enrichment.

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | Not applicable | Too small for training (100 images); OOD eval only |
| MNV4-H2 | skew_reg | ➖ | 0 | Not applicable | Born-digital PDFs; zero skew by construction |
| MNV4-H3 | resolution_quality_reg | ➖ | 0 | Not applicable | 150 DPI uniform; not informative for RQ training |
| SIG-G1-1 | blur_score | ➖ | 0 | Not applicable | Born-digital; no blur variation |
| SIG-G1-2 | noise_score | ➖ | 0 | Not applicable | Born-digital; no noise |
| SIG-G1-3 | contrast_score | ➖ | 0 | Not applicable | Born-digital; clean contrast |
| SIG-G1-4 | skew_score | ➖ | 0 | Not applicable | Born-digital; zero skew |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | PNG lossless from PDF rendering |
| SIG-G1-6 | overall_quality | ➖ | 0 | Not applicable | Born-digital; uniformly clean |
| SIG-G2-1 | script_cls | 🔍 | ~100 | GT-derived | 100% Jpan; OOD evaluation set for Japanese script detection |
| SIG-G3-1 | orientation_cls (post) | 🔍 | ~100 | GT-derived | 100% vertical text (tategaki); orientation convention validation |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | Not applicable | Born-digital; zero skew |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | Not applicable | Government PDFs; 100% printed text |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | Not applicable | No handwriting |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | Not applicable | No handwriting |
| SIG-G4-4 | presence_reg | ❌ | 0 | Not applicable | No handwriting |
| SIG-G4-5 | legibility_reg | ❌ | 0 | Not applicable | No handwriting |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | Not applicable | Born-digital; not a real capture method |
| SIG-G5-2 | shadow_reg | ❌ | 0 | Not applicable | Born-digital; no shadows |
| SIG-G5-3 | warping_reg | ❌ | 0 | Not applicable | Born-digital; no warping |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Japanese government text; no code content |
| SIG-G5-5 | resolution_quality_reg | ➖ | 0 | Not applicable | 150 DPI uniform; not informative |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Jpan); real-world Japanese vertical text complement to JSSODa |
| 2 | Capture method | ✅ | 100% born_digital (PDF rendering at 150 DPI) |
| 3 | Document domain | ✅ | 100% ADM (government/administrative PDFs) |
| 4 | Layout type | ✅ | 100% vertical (tategaki); real-world government document layouts |
| 5 | Text density | 🟡 | Government PDFs likely medium-to-high density; not yet characterized |
| 6 | Degradation types | ❌ | Born-digital; no degradation |
| 7 | Resolution/DPI range | ❌ | Uniform 150 DPI; below project target of 300 DPI |
| 8 | Document age | ❌ | Modern government documents only |
| 9 | Text scope | ✅ | 100% printed; structural tags (header/footer/caption) present |
| 10 | Content flags | 🟡 | Not yet characterized; government PDFs may contain tables/figures |
| 11 | Binarization status | ❌ | Not characterized; likely all color |
| 12 | Artifact types | ❌ | Born-digital; no artifacts expected |
| 13 | Color mode | 🟡 | Not yet characterized |
| 14 | Font variety | 🟡 | Government PDFs; likely limited to standard mincho/gothic families |

### 13.3 Corpus Role & Constraints

VJRODa serves exclusively as an **OOD evaluation set** for Japanese vertical text (tategaki). At only 100 images it is too small for training, but it provides critical real-world validation samples that complement JSSODa's synthetic vertical text. Its born-digital origin means it contributes no IQA training signal, but confirms that orientation conventions (vertical text = 0 deg upright) hold on authentic government documents. The CC-BY-4.0 license permits unrestricted use.
