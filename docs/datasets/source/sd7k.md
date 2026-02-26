---
dataset_id: sd7k
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - shadow
  - illumination
  - contrast
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### SD7K (DocShadow-SD7K - High-Resolution Document Shadow Removal)

> **Quick Stats**: ~7,239 image pairs | 30+ occluder types | 350+ documents | ICCV 2023
>
> **License**: MIT | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SD7K (DocShadow-SD7K) |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Maintainer** | University of Macau (CXH-Research) |
| **Paper** | [ICCV 2023 - High-Resolution Document Shadow Removal](https://github.com/CXH-Research/DocShadow-SD7K) |
| **Repository** | [GitHub: CXH-Research/DocShadow-SD7K](https://github.com/CXH-Research/DocShadow-SD7K) |
| **License** | MIT (Copyright (c) 2023 Nick Chen / Xuhang Chen, University of Macau) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Shadow-degraded document images (input) |
| **Images** | PNG | Shadow-free ground truth images (target) |
| **Annotations** | [NEEDS_VERIFICATION] | Occluder annotations may be available |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train (Input)** | `train/input/` | Implicit (paired structure) | 6,479 | ✅ |
| **Train (Target)** | `train/target/` | Implicit (paired structure) | 6,478 | ✅ |
| **Test (Input)** | `test/input/` | Implicit (paired structure) | 760 | ✅ |
| **Test (Target)** | `test/target/` | Implicit (paired structure) | 760 | ✅ |

**Split Organization Pattern**: `by_folder` (train/test with input/target subfolders)

> **Notes**:
>
> - Train: 6,479 input / 6,478 target (1 image count mismatch to verify)
> - Test: 760 input / 760 target
> - No validation split provided (train/test only)
> - 30+ occluder types used to cast shadows, 350+ base documents

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Directory-based | Document | Shadow input paired with shadow-free GT |
| **Shadow Type** | Implicit | Document | Regular and irregular shadows from 30+ occluder types |
| **Occluder Annotations** | [NEEDS_VERIFICATION] | Document | Occluder type/position (may be available) |

> **Note**: Primary annotation is through paired shadow/clean image structure. Shadows generated using 30+ real-world occluder types.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, Paper | Description, citation, occluder taxonomy |
| **Image-level** | Filename/directory structure | Pairing information, split membership |
| **Shadow-level** | [NEEDS_VERIFICATION] | Occluder type, shadow characteristics |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (shadow input + shadow-free target)

```text
SD7K/
├── train/
│   ├── input/         # 6,479 shadow-degraded document images (PNG)
│   │   └── *.png
│   └── target/        # 6,478 shadow-free ground truth images (PNG)
│       └── *.png
└── test/
    ├── input/         # 760 shadow-degraded document images (PNG)
    │   └── *.png
    └── target/        # 760 shadow-free ground truth images (PNG)
        └── *.png
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to shadow or clean image |
| `pair_type` | str | Yes | "input" (shadow) or "target" (clean) |
| `split` | str | Yes | "train" or "test" |
| `base_name` | str | Yes | Links paired images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | Directory-based pairing |
| ✅ Split info | `subset` | High | From directory structure |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ⚠️ Occluder type | `occluder_type` | Medium | [NEEDS_VERIFICATION] if annotated |
| ❌ Quality scores | - | Low | Not provided; compute from pairing |
| ❌ Layout boxes | - | Low | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Shadow/shadow-free document image pairs |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (shadow removal correction) |
| **Purpose** | Document shadow removal training and benchmark |
| **Local Path** | `01_base_data/camera_captured/sd7k/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Pair matching required |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ⚠️ Partial - Parser created but enrichment not yet run |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `has_shadow=True` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/sd7k/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/sd7k_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

SD7K contains ~7,239 shadow-degraded image pairs across train and test splits.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~6,479 input + ~6,478 target | 0 | 0% | ❌ Not started |
| **Test** | 760 input + 760 target | 0 | 0% | ❌ Not started |
| **Total** | ~7,239 input + ~7,238 target | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Input Images** | ~7,239 |
| **Total Target Images** | ~7,238 |
| **Training Split** | 6,479 input / 6,478 target (~90%) |
| **Test Split** | 760 input / 760 target (~10%) |
| **Occluder Types** | 30+ |
| **Base Documents** | 350+ |
| **Shadow Types** | Regular + irregular |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
sd7k/
├── train/
│   ├── input/           # 6,479 shadow-degraded document images
│   └── target/          # 6,478 shadow-free GT images
└── test/
    ├── input/           # 760 shadow-degraded document images
    └── target/          # 760 shadow-free GT images
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL |
| **Document Types** | 350+ diverse printed documents with cast shadows |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture with 30+ real-world occluder types |

##### 5.1 Shadow Composition

| Shadow Category | Description |
|-----------------|-------------|
| **Regular Shadows** | Geometric, predictable shadow patterns |
| **Irregular Shadows** | Complex, organic shadow patterns from diverse occluders |
| **Occluder Types** | 30+ types (hands, books, objects, etc.) |
| **Shadow Coverage** | Variable (partial to extensive document coverage) |

#### 6. IQA Profile

Camera-captured documents with controlled shadow degradation from 30+ occluder types.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents with real occluder shadows |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | High-resolution with controlled shadow degradation |
| **Known Artifacts** | Document shadows (regular + irregular), illumination gradients |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Shadow** | HIGH | Primary degradation - 30+ occluder types |
| **Illumination** | HIGH | Shadow creates illumination non-uniformity |
| **Contrast** | HIGH | Shadow regions have reduced local contrast |
| **Blur** | LOW | Not a primary degradation in this dataset |
| **Noise** | LOW | Secondary artifact |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Shadow reduces text/background contrast |
| **Document Diversity** | HIGH (350+ documents) | Broad coverage of document types |
| **Shadow Diversity** | HIGH (30+ occluders) | Comprehensive shadow pattern coverage |
| **Color Usage** | Mixed | Shadow interacts with document colors |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Largest document shadow removal dataset available |
| **Unique Characteristics** | 30+ occluder types, 350+ documents, high-resolution |
| **Complementary Datasets** | WSRD (NTIRE challenge), RealDAE (shadow task subset) |
| **Benchmark Suitability** | HIGH - Pre-split train/test, ICCV 2023 benchmark |
| **Known Limitations** | Train count mismatch (6,479 vs 6,478) |

##### 6.5 Benchmark Results

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| **DocShadow** | Shadow Removal | PSNR | [NEEDS_VERIFICATION] | ICCV 2023 |
| **DocShadow** | Shadow Removal | SSIM | [NEEDS_VERIFICATION] | ICCV 2023 |

> **Note**: Verify benchmark results from ICCV 2023 paper.

#### 7. Known Issues & Limitations

- **MIT License**: Repository LICENSE file confirms MIT (Copyright 2023 Nick Chen). Applies to code, models, and dataset (no separate dataset license exists).
- **Train Count Mismatch**: 6,479 input vs 6,478 target in training set (1 unpaired image)
- **No Validation Split**: Only train/test splits provided
- **No Layout Annotations**: Dataset focused on shadow removal, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Shadow-Only Focus**: Does not cover other document degradation types (blur, noise, warping)
- **Occluder Annotations**: Availability of per-image occluder type annotations needs verification

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{sd7k2023,
  title={High-Resolution Document Shadow Removal via A Large-Scale Real-World Dataset and A Frequency-Aware Shadow Erasing Net},
  author={CXH-Research, University of Macau},
  booktitle={ICCV},
  year={2023}
}
```

##### Related Works

- [WSRD](wsrd.md) - NTIRE Document Shadow Removal challenge dataset (~1.2K images)
- [RealDAE](realdae.md) - Camera document enhancement with shadow task subset (200 pairs)

##### Leaderboards

- [Papers With Code - Document Shadow Removal](https://paperswithcode.com/task/document-shadow-removal)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Train Count Mismatch**: Training set has 6,479 input images but only 6,478 target images - identify and handle the unpaired sample
- **Paired Image Structure**: Input (shadow) and target (clean) must be processed together
- **Regular vs Irregular**: Shadow types include both regular (geometric) and irregular (organic) patterns

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract split and pair type from directory structure (train/test + input/target)
- **Quality Computation**: Use PSNR/SSIM between shadow and clean images for quality scoring
- **Capture Method**: Set `camera_smartphone` for all images
- **Count Validation**: Verify 1-image mismatch in training set; log warning for unpaired sample
- **High Resolution**: Images may be high-resolution - verify dimensions and set appropriate processing pipeline

##### 10.3 External Resources

- **DocShadow Model**: Shadow removal model available at [GitHub: CXH-Research/DocShadow-SD7K](https://github.com/CXH-Research/DocShadow-SD7K)
- **ICCV 2023 Paper**: Published at International Conference on Computer Vision

##### 10.4 Shadow Diversity

SD7K's key differentiator is shadow diversity:

| Feature | Count | Description |
|---------|-------|-------------|
| **Occluder Types** | 30+ | Hands, books, pens, cups, various objects |
| **Base Documents** | 350+ | Diverse document types and layouts |
| **Shadow Patterns** | Regular + Irregular | Geometric and organic shadow shapes |
| **Coverage Range** | Partial to extensive | Varying shadow area on documents |

This makes SD7K the most comprehensive document shadow removal dataset, significantly larger and more diverse than WSRD (~1.2K) or RealDAE's shadow subset (200 pairs).

#### 10.5 License and Format

| Property | Value |
|----------|-------|
| **License** | MIT |
| **Commercial Use** | Yes (permitted under MIT) |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.6 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_sd7k_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.7 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: C (79.9/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 85.4 | 18% |  |
| Field Validity | 96.3 | 18% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | 90.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **79.9** | | **Grade C** |

##### 11.2 Key Defects

> **Total**: 6 defects (1 resolved, 5 accepted)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | low | ACCEPTED |  |
| D02 | domain_level1 | medium | ACCEPTED |  |
| D03 | iso639_language | low | ACCEPTED |  |
| D04 | layout_detections | low | ACCEPTED |  |
| D05 | text_has_content | low | ACCEPTED |  |
| D06 | text_scope | medium | RESOLVED |  |

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 33.3%

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/sd7k/](../../scripts/audit/results/sd7k/)

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Shadow removal training (enrichment gaps not blocking).

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 7,239 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 7,239 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `resolution` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~7,239 | Synthetic rotation | Documents at canonical orientation; synthetic 90°/180°/270° rotation augmentation applicable |
| MNV4-H2 | skew_reg | ❌ Not applicable | - | - | No skew angle ground truth; camera capture may introduce slight tilt but not annotated |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | - | - | High-resolution images noted but no DPI metadata or resolution quality labels |
| SIG-G1-1 | blur_score | ➖ Negatives only | ~7,239 | Inferred | Target (shadow-free) images serve as high-quality, low-blur anchor examples |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~7,239 | Inferred | Camera-captured input images have incidental noise; clean target images provide contrast |
| SIG-G1-3 | contrast_score | ✅ Primary | ~7,239 | Paired GT | Shadow regions cause quantifiable contrast loss; PSNR/SSIM delta between input/target provides contrast degradation signal across 30+ occluder types |
| SIG-G1-4 | skew_score | ❌ Not applicable | - | - | skew_score is a quality degradation metric (0-1); not annotated |
| SIG-G1-5 | compression_score | ❌ Not applicable | - | - | PNG format; no JPEG compression artifacts |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~7,239 | Paired GT | Input/target pairs enable overall quality contrast scoring; largest such shadow dataset |
| SIG-G2-1 | script_cls | ➖ Negatives only | ~7,239 | Inferred Latin | 100% Latin (en) per stats; 350+ base documents suggest predominant Latin script |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~7,239 | Synthetic rotation | Documents at canonical orientation; rotation augmentation applicable |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | - | - | No sub-degree skew angle ground truth |
| SIG-G4-1 | handwriting_presence_cls | ➖ Negatives only | ~7,239 | Inferred | 350+ diverse printed documents; no handwriting content |
| SIG-G4-2 | handwriting_legibility_cls | ❌ Not applicable | - | - | No handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ Not applicable | - | - | No handwriting present |
| SIG-G4-4 | presence_reg | ➖ Negatives only | ~7,239 | Inferred | Printed documents → 0.0 handwriting presence score |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | - | - | No handwriting present |
| SIG-G5-1 | capture_method_cls | ✅ Primary | 7,239 | Hard label | 100% camera_smartphone per stats; all images camera-captured |
| SIG-G5-2 | shadow_reg | ✅ Primary | ~7,239 | Paired GT (derivable) | Largest document shadow dataset; 30+ occluder types cover regular and irregular shadow patterns; PSNR/SSIM delta between input/target yields continuous 0-1 severity proxy; no direct severity label in source but derivation is reliable |
| SIG-G5-3 | warping_reg | ❌ Not applicable | - | - | No geometric distortion; flat documents with cast shadows only |
| SIG-G5-4 | code_cls | ❌ Not applicable | - | - | Diverse printed documents; no code content annotations |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ❌ Not applicable | - | - | No resolution quality labels; high-resolution noted but not quantified |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ➖ Latin only | 100% Latn (en) per stats; 350+ base documents imply English-dominant coverage |
| 2 | Capture method | ✅ Well-covered | 100% camera_smartphone (7,239 images); largest camera-captured shadow dataset |
| 3 | Document domain | ✅ Well-covered | 100% GENERAL; 350+ diverse base documents provide broad domain representation |
| 4 | Layout type | ❌ Not present | No layout annotations; 350+ document diversity implies varied layouts |
| 5 | Text density | ❌ Not present | No text density labels; variable across 350+ document types |
| 6 | Degradation types | ✅ Well-covered | Shadow (regular + irregular), illumination gradients, contrast reduction; 30+ occluder types = highest shadow diversity of any document shadow dataset |
| 7 | Resolution/DPI range | ❌ Not present | High-resolution noted in dataset description but no DPI metadata in L2 |
| 8 | Document age | ❌ Not present | No document age annotations; modern documents implied |
| 9 | Text scope | 🟡 Partial | 100% page-level scope per stats |
| 10 | Content flags | ❌ Not present | No content flags in L2 metadata |
| 11 | Binarization status | ❌ Not present | RGB color documents; not binarized |
| 12 | Artifact types | ✅ Well-covered | 30+ occluder types provide the most comprehensive shadow artifact taxonomy of any document dataset; regular and irregular shadow patterns both well-represented |
| 13 | Color mode | 🟡 Partial | RGB per stats; 350+ documents imply color and grayscale content but color mode not labeled |
| 14 | Font variety | ❌ Not present | No font annotations; 350+ base documents suggest meaningful font variety |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

SD7K is the primary and largest contributor to the `shadow_reg` head (SIG-G5-2) and a key contributor to `capture_method_cls` (SIG-G5-1), providing 7,239 camera-captured document pairs across 30+ occluder types and 350+ base documents — the most shadow-diverse document dataset available. Shadow severity labels must be derived from the paired GT using pixel-difference metrics (PSNR/SSIM) since no direct 0-1 severity field exists in the source; this derivation is reliable given the high-quality paired structure and should be completed via `label_shadow_severity.py` before final `shadow_reg` training data assembly. The training count mismatch (6,479 input vs 6,478 target) requires handling of one unpaired sample. License is MIT (Copyright 2023 Nick Chen, University of Macau); commercial use permitted.
