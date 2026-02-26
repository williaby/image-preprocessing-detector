---
dataset_id: q-doc
version: "1.0"
license: Unknown
commercial_use: unknown
iqa_profiles:
  - quality_benchmark
  - camera_smartphone
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### Q-Doc (Quality Assessment for Document Images)

> **Quick Stats**: ~4,260 images | Quality scores | Camera-captured | IQA benchmark
>
> **License**: Unknown (verify with authors) | **Commercial Use**: Unknown

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Q-Doc: Quality Assessment for Document Images |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Last Updated** | 2025 |
| **Maintainer** | cydxf (GitHub user) |
| **Paper** | [Q-Doc Quality Assessment Paper (2025)](https://github.com/cydxf/Q-Doc) |
| **Repository** | [GitHub: cydxf/Q-Doc](https://github.com/cydxf/Q-Doc) |
| **License** | Unknown (unstated - verify with authors) |
| **Commercial Use** | Unknown (verify with authors) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG | Camera-captured document images |
| **Annotations** | JSON / CSV | Quality scores (MOS or objective metrics) |
| **Supplementary** | README, Paper | Dataset description, citation, evaluation protocol |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/` | `train_scores.json` | ~3,400 | ⚠️ Verify |
| **Test** | `test/` | `test_scores.json` | ~860 | ⚠️ Verify |
| **Total** | - | - | ~4,260 | ⚠️ Verify |

**Split Organization Pattern**: `by_folder` with separate score annotations (likely)

> **Notes**:
>
> - **BLOCKER**: The GitHub repository ([cydxf/Q-Doc](https://github.com/cydxf/Q-Doc)) contains only VLM evaluation code (GPT, LLaMA 3.2, Gemini, DeepSeek-VL2, etc.) -- no images or annotations are hosted in the repo.
> - The code uses `load_dataset()` from HuggingFace but the dataset name is left blank (`ds = load_dataset() # 填入数据集名称`).
> - No public HuggingFace dataset found under `cydxf` or `Q-Doc` search terms.
> - Images may need to be requested directly from the authors or sourced from a different distribution channel.
> - Exact split structure, counts, and quality score format remain unverified.

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Quality Scores** | JSON / CSV | Image-level | Overall quality assessment (MOS or objective) |
| **Degradation Types** | JSON (optional) | Image-level | Specific degradation labels (blur, noise, etc.) |

> **Note**: Verify exact annotation schema from GitHub repository. May include multi-dimensional quality scores or single overall score.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, Paper | Description, citation, benchmark metrics |
| **Image-level** | Annotations JSON | Quality scores, degradation types (if provided) |
| **Split-level** | Directory structure | Train/test membership |

##### 2.5 Annotation Schema Details

> **Format**: Quality scores per image (exact schema requires repository verification)

```text
# Expected structure (verify from repository):
{
  "images": [
    {
      "image_id": str,
      "filename": str,
      "quality_score": float,  # 0-100 or 1-5 MOS
      "degradation_types": [str],  # Optional
      "metadata": {
        "capture_method": str,
        "document_type": str
      }
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | str | Yes | Unique image identifier |
| `quality_score` | float | Yes | Overall quality assessment |
| `degradation_types` | list | Optional | Specific degradation labels |
| `capture_method` | str | Optional | Camera or scanner |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Quality scores | `quality_overall_mos` | High | MOS or objective quality metric |
| ✅ Image metadata | `capture_method`, `document_type` | Medium | If provided in annotations |
| ⚠️ Degradation types | `expected_degradations` | Medium | If explicitly labeled |
| ❌ Layout boxes | - | N/A | Not applicable for quality benchmark |
| ❌ Text GT | - | Low | Likely not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | [NEEDS_VERIFICATION] - Likely Human Expert (MOS) or Automatic (computed metrics) |
| **Provenance Tier** | [NEEDS_VERIFICATION] - Tier 1 if MOS, Tier 2 if computed |
| **Annotator Details** | [NEEDS_VERIFICATION] - Check GitHub repository for annotation protocol |
| **Inter-Annotator Agreement** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | [NEEDS_VERIFICATION] |
| **GT Label Coverage** | 100% - All ~4,260 images have quality scores |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (IQA model training/validation) |
| **Purpose** | IQA benchmark, quality score validation |
| **Local Path** | `02_benchmark_only/q-doc/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Quality score normalization, image standardization |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `q_doc` (quality category) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `quality_overall_mos`, `expected_degradations`, `capture_method` |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `has_human_mos=true` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: Quality benchmark datasets require MOS normalization and optional degradation type mapping.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/q-doc/` | ✅ Available | ~4,260 images |
| **Quality Scores** | `02_benchmark_only/q-doc/annotations/*.json` | ✅ Available | MOS or objective scores |
| **Text/GT** | - | ❌ Not provided | Likely not included |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/q_doc_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~3,400 | 0 | 0% | ❌ Parser not implemented |
| **Test** | ~860 | 0 | 0% | ❌ Parser not implemented |
| **Total** | ~4,260 | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ❌ Missing - Parser not yet implemented

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | ~4,260 |
| **Training Split** | ~3,400 (80%) |
| **Test Split** | ~860 (20%) |
| **Image Dimensions** | Variable (camera-captured) |
| **Resolution (DPI)** | Variable (smartphone camera) |
| **File Format(s)** | JPG, PNG |
| **Color Space** | RGB / Grayscale |
| **Annotation Format** | JSON / CSV (quality scores) |
| **Total Size on Disk** | ~5 GB (estimated) |

##### 4.3 Text Statistics

> **Availability**: ❌ Not Available - No ground truth text provided (quality benchmark focus).

##### Directory Structure

```text
q-doc/
├── train/
│   ├── images/
│   │   └── *.jpg, *.png
│   └── scores.json
└── test/
    ├── images/
    └── scores.json
```

> **Note**: Exact structure requires verification from GitHub repository.

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Quality scores provided in dataset; empirical profiling optional for validation.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | UNKNOWN (general documents with quality variation) |
| **Document Types** | Mixed printed documents captured via smartphone |
| **Language(s)** | Unknown (likely multilingual) |
| **Temporal Range** | Unknown (recent smartphone captures) |
| **Acquisition Method** | Camera-smartphone capture with intentional quality variation |

##### 5.1 Class/Category Distribution

> **N/A**: Quality benchmark; no class categories, only quality scores.

##### 5.2 Class/Category Definitions

> **N/A**: Not applicable for quality benchmark dataset.

##### 5.3 Language & Script Coverage

> **Status**: Unknown - requires OCR extraction and language detection.

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents with quality annotations |
| **Capture Device** | Smartphone cameras |
| **Original Quality** | Intentionally varied (blur, noise, lighting, perspective) |
| **Quality Range** | Wide range from poor to excellent |
| **Known Artifacts** | Blur, noise, shadows, perspective distortion, uneven lighting |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Primary quality degradation factor |
| **Noise** | MEDIUM-HIGH | Camera sensor noise at low light |
| **Lighting** | HIGH | Uneven illumination affects quality |
| **Perspective Distortion** | MEDIUM | Camera angle affects perceived quality |
| **Contrast** | MEDIUM | Variable lighting creates contrast issues |
| **Compression** | LOW | JPEG quality variation |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Quality Variation** | High | Wide range enables IQA model training |
| **Camera Artifacts** | High | Realistic smartphone capture conditions |
| **Text Size Range** | Variable | Blur affects small text more severely |
| **Degradation Diversity** | High | Multiple degradation types (blur, noise, lighting) |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Quality-annotated dataset for IQA model training |
| **Unique Characteristics** | Camera-captured documents with quality scores |
| **Complementary Datasets** | [DIQA-5000](diqa-5000.md), [OHR-Bench](ohr-bench.md), ~~[IQA-Phase7-165K](iqa-phase7-165k.md)~~ *(EXCLUDED — dataset FLAWED; see BATCH_1_IQA_SUMMARY.md §5)* |
| **Benchmark Suitability** | HIGH - Pre-split train/test with quality scores |
| **Known Limitations** | Unknown license, limited documentation, smaller than DIQA-5000 |

#### 7. Known Issues & Limitations

- **License Unknown**: No explicit license provided - contact authors before commercial use
- **Limited Documentation**: Repository documentation may be sparse; paper required for details
- **Smaller than DIQA-5000**: ~4,260 images vs 5,500+ in DIQA-5000
- **No Text GT**: Quality benchmark focus; no OCR ground truth
- **Quality Score Type**: Unclear if MOS (human-annotated) or computed objective metrics
- **Degradation Labels**: Unknown if specific degradation types are labeled
- **Limited Provenance**: Document sources and capture methodology not fully detailed

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling and VLM inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{cydxf2025qdoc,
  title={Q-Doc: Quality Assessment for Document Images},
  author={cydxf},
  year={2025},
  publisher={GitHub},
  url={https://github.com/cydxf/Q-Doc}
}
```

##### Related Works

- [DIQA-5000](diqa-5000.md) - Document IQA benchmark with MOS
- [OHR-Bench](ohr-bench.md) - Multi-degradation IQA benchmark
- [CLIQ](cliq.md) - Camera-captured document quality assessment

##### Leaderboards

- None currently available

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Quality Score Type**: Verify if MOS (human-annotated) or objective computed metrics
- **Score Normalization**: Determine score range (0-1, 1-5, 0-100) for normalization
- **Degradation Labels**: Check if specific degradation types (blur, noise) are labeled beyond overall score

##### 10.2 Implementation Notes

- **Parser Priority**: High - fills gap for camera-captured document IQA benchmark
- **Repository Verification**: Clone GitHub repository to confirm exact schema and file structure
- **Capture Method**: Set `camera_smartphone` based on paper description
- **Benchmark Usage**: Useful for validating SigLIP-2 IQA heads on camera-captured documents
- **MOS Flag**: Set `has_human_mos=true` if quality scores are human-annotated

##### 10.3 External Resources

- **GitHub Repository**: [https://github.com/cydxf/Q-Doc](https://github.com/cydxf/Q-Doc)
- **Paper**: Check repository for preprint link or conference proceedings

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser not yet implemented.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser not implemented - no Layer 2 metadata available for reliability analysis.

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ Not applicable | - | - | Quality benchmark only; no orientation labels |
| MNV4-H2 | skew_reg | ❌ Not applicable | - | - | No geometric angle labels provided |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~4,260 | Inferred from quality score | Quality scores correlate with resolution; no direct pixel-level label |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~3,400 | Inferred | Blur is a primary degradation factor; may map from per-degradation labels if present |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~3,400 | Inferred | Camera noise expected; inferred if degradation breakdown available |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~3,400 | Inferred | Lighting/contrast variation noted; inferred from overall quality signal |
| SIG-G1-4 | skew_score | ❌ Not applicable | - | - | Skew degradation score not a documented quality dimension for this dataset |
| SIG-G1-5 | compression_score | ❌ Not applicable | - | - | Low compression sensitivity noted; no JPEG compression label |
| SIG-G1-6 | overall_quality | ✅ Primary | ~3,400 | Quality score (MOS or objective) | Core dataset purpose; image-level quality scores covering full quality range |
| SIG-G2-1 | script_cls | ❌ Not applicable | - | - | Script unknown; no OCR or script labels; camera-captured mixed-language documents |
| SIG-G3-1 | orientation_cls (post) | ❌ Not applicable | - | - | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | - | - | No geometric skew labels |
| SIG-G4-1 | handwriting_presence_cls | ➖ Negatives only | ~3,400 | Implicit NONE class | Printed documents; no handwriting labels; useful as negative examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ Not applicable | - | - | No handwriting content |
| SIG-G4-3 | handwriting_content_type_cls | ❌ Not applicable | - | - | No handwriting content |
| SIG-G4-4 | presence_reg | ➖ Negatives only | ~3,400 | Implicit 0.0 | Printed docs provide zero-handwriting anchor for regression |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | - | - | No handwriting content |
| SIG-G5-1 | capture_method_cls | 🟡 Secondary | ~3,400 | Inferred camera_smartphone | Camera-captured documents; capture method derivable from dataset provenance |
| SIG-G5-2 | shadow_reg | 🟡 Secondary | ~3,400 | Inferred | Shadows from camera capture expected; no explicit severity label |
| SIG-G5-3 | warping_reg | 🟡 Secondary | ~3,400 | Inferred | Perspective distortion present; no explicit warping severity label |
| SIG-G5-4 | code_cls | ➖ Negatives only | ~3,400 | Implicit NONE class | General document images; no code-containing documents expected |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ✅ Primary | ~3,400 | Quality score (normalised) | Same quality scores drive both MNV4-H3 and this head; train-split images |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ❌ Not present | Language/script unknown; no OCR run; likely mixed but unverified |
| 2 | Capture method | 🟡 Partial | Camera-smartphone only; no scanner or born-digital examples |
| 3 | Document domain | ❌ Not present | Domain unknown; general documents with intentional quality variation |
| 4 | Layout type | ❌ Not present | No layout labels; parser not yet implemented |
| 5 | Text density | ❌ Not present | Not annotated; no OCR run |
| 6 | Degradation types | ✅ Well-covered | Wide range: blur, noise, lighting, perspective distortion, contrast |
| 7 | Resolution/DPI range | 🟡 Partial | Variable smartphone-camera resolution; no DPI metadata |
| 8 | Document age | ❌ Not present | All recent smartphone captures; no aged or historical material |
| 9 | Text scope | ❌ Not present | Not annotated |
| 10 | Content flags | ❌ Not present | No content flags in annotations |
| 11 | Binarization status | ❌ Not present | Not annotated; likely full-color RGB images |
| 12 | Artifact types | ✅ Well-covered | Blur, noise, shadows, perspective distortion, uneven lighting all present |
| 13 | Color mode | 🟡 Partial | Mixed RGB and grayscale; not explicitly labelled per image |
| 14 | Font variety | ❌ Not present | No font metadata; unverified |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

Q-Doc is a pure IQA benchmark dataset whose primary contribution is image-level overall quality scores for camera-captured document images, making it a targeted source for the SIG-G1-6 overall_quality and SIG-G5-5 resolution_quality_reg heads. The dataset is small (~4,260 images), secondary qualities such as blur and noise are inferrable but not explicitly labelled per degradation dimension, and the unknown license requires author verification before any training use. Parser implementation is a prerequisite before any Layer 2 metadata or enrichment-derived labels are available.
