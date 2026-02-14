---
dataset_id: sd7k
version: "1.0"
license: Unspecified
commercial_use: false
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
> **License**: Unspecified | **Commercial Use**: Unknown (verify with authors)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SD7K (DocShadow-SD7K) |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Maintainer** | University of Macau (CXH-Research) |
| **Paper** | [ICCV 2023 - High-Resolution Document Shadow Removal](https://github.com/CXH-Research/DocShadow-SD7K) |
| **Repository** | [GitHub: CXH-Research/DocShadow-SD7K](https://github.com/CXH-Research/DocShadow-SD7K) |
| **License** | Unspecified (verify with authors) |
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
| **Known Limitations** | Unspecified license; train count mismatch (6,479 vs 6,478) |

##### 6.5 Benchmark Results

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| **DocShadow** | Shadow Removal | PSNR | [NEEDS_VERIFICATION] | ICCV 2023 |
| **DocShadow** | Shadow Removal | SSIM | [NEEDS_VERIFICATION] | ICCV 2023 |

> **Note**: Verify benchmark results from ICCV 2023 paper.

#### 7. Known Issues & Limitations

- **License Unspecified**: No explicit license - verify with authors before commercial use
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
| **License** | Unspecified |
| **Commercial Use** | Unknown (verify with authors) |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.6 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_sd7k_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.7 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

Prescreening pass rate: 0% (base metadata only, expected gaps). Schema compliance: 100% (27 fields, all valid). Defect catalog: 6 defects (5 accepted gaps, 1 resolved text_scope fix). Overall grade: D (60-63/100, expected for base-only enrichment).

---

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Shadow removal training (enrichment gaps not blocking).

---
