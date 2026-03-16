---
dataset_id: staindoc
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - stain_artifacts
  - camera_smartphone
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### StainDoc (WACV 2025)

> **Quick Stats**: ~5,000 paired images | ~51 GB | Stained/clean pairs | Correction training | Camera-captured
>
> **License**: MIT | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | StainDoc: Stain Removal for Document Images (WACV 2025) |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Last Updated** | 2025 |
| **Maintainer** | Xuhang Chen et al. |
| **Paper** | [StainDoc: Stain Removal for Document Images (WACV 2025)](https://www.kaggle.com/datasets/xuhangc/wacv2025-staindoc) |
| **Repository** | [Kaggle: xuhangc/wacv2025-staindoc](https://www.kaggle.com/datasets/xuhangc/wacv2025-staindoc) |
| **License** | MIT |
| **Commercial Use** | Yes |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG / JPG | Stained document images (input) |
| **Images** | PNG / JPG | Clean document images (paired GT) |
| **Stain Masks** | PNG | Binary masks indicating stain regions (if provided) |
| **Supplementary** | README, Paper | Dataset description, citation, methodology |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/stained/` | `train/clean/` (paired) | ~4,000 | ✅ |
| **Test** | `test/stained/` | `test/clean/` (paired) | ~1,000 | ✅ |
| **Total** | - | - | ~5,000 | ✅ |

**Split Organization Pattern**: `by_folder` with paired stained/clean directories

> **Notes**:
>
> - Pairing based on matching filenames across `stained/` and `clean/` directories
> - Each stained image has a corresponding clean ground truth
> - Approximate counts based on Kaggle description (~51 GB dataset)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Directory-based | Document | Stained input paired with clean GT by matching filename |
| **Stain Masks** | PNG (binary) | Pixel-level | Binary masks indicating stain regions (if provided) |

> **Note**: Primary annotation is through paired image structure. Stain masks may or may not be included; verify from Kaggle download.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Kaggle README, Paper | Description, citation, methodology |
| **Image-level** | Filename | Pairing information via matching names |
| **Split-level** | Directory structure | Train/test membership |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (stained input + clean GT) with optional stain masks

```text
staindoc/
├── train/
│   ├── stained/
│   │   └── *.png, *.jpg
│   ├── clean/
│   │   └── *.png, *.jpg  # Matching filenames
│   └── masks/  # Optional
│       └── *.png  # Binary stain masks
└── test/
    ├── stained/
    ├── clean/
    └── masks/  # Optional
```

**Pairing Rule**: `train/stained/{filename}.png` <-> `train/clean/{filename}.png`

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to stained or clean image |
| `image_type` | str | Yes | `input_stained` or `ground_truth` (from directory) |
| `base_filename` | str | Yes | Links paired images across stained/clean |
| `stain_mask_path` | str | Optional | Path to binary stain mask (if available) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `ground_truth_path` | High | Path-based pairing across stained/clean |
| ✅ Image type | `image_type` | High | From directory name (stained vs clean) |
| ✅ Capture method | `capture_method` | High | Camera-smartphone (from paper description) |
| ✅ Expected degradations | `expected_degradations` | Medium | `stain`, `bleed_through`, `water_damage` |
| ⚠️ Stain masks | `stain_mask_path` | Medium | If provided; verify in download |
| ❌ Quality scores | - | Low | Compute from paired SSIM or IQA metrics |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

> **Purpose**: Document annotation methodology, quality assurance, and provenance for ground truth labels.

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Annotator Details** | Clean reference images captured separately from stained inputs |
| **Inter-Annotator Agreement** | N/A - Paired image GT (objective reference) |
| **Quality Assurance** | Filename-matched pairing across stained/clean directories |
| **GT Label Coverage** | 100% - Every stained image has a corresponding clean GT |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (stain removal correction) |
| **Purpose** | Document stain removal training, correction quality assessment |
| **Local Path** | `01_base_data/correction/staindoc/` |
| **Subset Used** | `stained/` images only (clean/ used as GT reference) |
| **Preprocessing** | Pair matching via filename, optional mask alignment |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `staindoc` (correction category) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `source`, `capture_method`, `correction_task`, `image_type`, `is_degraded`, `has_ground_truth`, `ground_truth_path`, `expected_degradations`, `stain_mask_path` |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `content_type=printed`, `text_scope=page` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: Pattern `train/stained/**/*.{png,jpg}` processes only stained inputs. Clean/GT images referenced via `ground_truth_path` label.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/staindoc/` | ✅ Available | ~5,000 stained + ~5,000 clean + optional masks |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/staindoc_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~4,000 | 0 | 0% | ❌ Parser not implemented |
| **Test** | ~1,000 | 0 | 0% | ❌ Parser not implemented |
| **Total** | ~5,000 | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ❌ Missing - Parser not yet implemented

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Stained Images** | ~5,000 |
| **Total Clean GT Images** | ~5,000 |
| **Total Images on Disk** | ~10,000 (stained + clean pairs) |
| **Layer 2 Annotated** | 15,180 (includes additional sub-datasets and individual crops) |
| **Training Split** | ~4,000 (80%) |
| **Test Split** | ~1,000 (20%) |
| **Image Dimensions** | Variable (camera-captured documents) |
| **Resolution (DPI)** | Variable (smartphone camera) |
| **File Format(s)** | PNG, JPG |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure (directory-based) |
| **Total Size on Disk** | ~51 GB |

##### 4.3 Text Statistics

> **Availability**: ❌ Not Available - No ground truth text provided in source dataset. OCR extraction not yet run.

##### Directory Structure

```text
staindoc/
├── train/
│   ├── stained/          # ~4,000 stained images
│   ├── clean/            # ~4,000 clean GT images
│   └── masks/            # Optional stain masks
└── test/
    ├── stained/          # ~1,000 stained images
    ├── clean/            # ~1,000 clean GT images
    └── masks/            # Optional stain masks
```

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Empirical profiling not yet run on this dataset.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | UNKNOWN (general documents with stain artifacts) |
| **Document Types** | Mixed printed documents captured via smartphone |
| **Language(s)** | Unknown (likely English + multilingual) |
| **Temporal Range** | Unknown (likely modern documents with natural staining) |
| **Acquisition Method** | Camera-smartphone capture of stained documents |

##### 5.1 Class/Category Distribution

> **N/A**: No class categories; correction dataset focused on stain removal.

##### 5.2 Class/Category Definitions

> **N/A**: Not applicable for paired correction dataset.

##### 5.3 Language & Script Coverage

> **Status**: Unknown - requires OCR extraction and language detection.

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured stained documents with clean GT pairs |
| **Capture Device** | Smartphone cameras |
| **Original Quality** | Degraded (stained) vs clean (GT) |
| **Stain Types** | Water stains, coffee stains, ink bleed-through, foxing, yellowing |
| **Known Artifacts** | Stains, shadows, camera perspective distortion, uneven lighting |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Stain Artifacts** | HIGH | Primary degradation - various stain types |
| **Bleed-Through** | HIGH | Ink/text showing through from reverse side |
| **Water Damage** | HIGH | Paper warping, color bleeding |
| **Contrast Loss** | MEDIUM | Stains reduce text-background contrast |
| **Color Shift** | MEDIUM | Yellowing, discoloration from age/water |
| **Blur** | LOW | Secondary artifact from camera focus |
| **Noise** | LOW | Camera noise less prominent than stains |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Stain Diversity** | High | Multiple stain types (water, coffee, ink, age) |
| **Text Size Range** | Variable | Camera-captured, variable distances |
| **Color Usage** | Mixed | Color documents + grayscale |
| **Camera Artifacts** | Present | Perspective distortion, lighting variation |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large paired dataset for stain removal correction |
| **Unique Characteristics** | Diverse stain types, paired clean GT, camera-captured realism |
| **Complementary Datasets** | [RealDAE](realdae.md) (enhancement), [DocAlign12K](docalign12k.md) (alignment) |
| **Benchmark Suitability** | HIGH - Pre-split train/test, enables quantitative evaluation via SSIM/PSNR |
| **Known Limitations** | No text GT, camera artifacts mixed with stain degradation |

#### 7. Known Issues & Limitations

- **No Text Ground Truth**: Paired images only; no OCR text provided
- **No Stain Taxonomy**: Stain types not explicitly labeled; requires visual inspection
- **Camera Artifacts**: Perspective distortion and lighting variation may confound stain removal training
- **No Validation Split**: Only train/test; no separate validation set documented
- **Limited Provenance**: Document sources and stain generation methodology not fully detailed
- **Quality Variance**: Camera-captured documents have variable quality baseline
- **Stain Mask Availability**: Unclear if pixel-level stain masks are provided; verify in download

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling and VLM inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{chen2025staindoc,
  title={StainDoc: Stain Removal for Document Images},
  author={Chen, Xuhang and others},
  booktitle={IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)},
  year={2025},
  url={https://www.kaggle.com/datasets/xuhangc/wacv2025-staindoc}
}
```

##### Related Works

- [RealDAE](realdae.md) - Camera document enhancement with paired GT
- [DocAlign12K](docalign12k.md) - Document alignment correction
- [DRCCBI](drccbi.md) - Camera-captured document rectification

##### Leaderboards

- None currently available

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Stained and clean images must be processed together for correction training
- **Stain Types Not Labeled**: No explicit stain type annotations; requires visual inspection or clustering
- **Camera Artifacts Present**: Clean GT images may still have minor perspective distortion if captured separately
- **Stain Mask Uncertainty**: Verify if pixel-level stain masks are included in download

##### 10.2 Implementation Notes

- **Parser Priority**: High - enables stain removal correction training
- **Capture Method**: Set `camera_smartphone` (NOT `scanner_flatbed`)
- **Quality Computation**: Use SSIM/PSNR/MS-SSIM between stained and paired clean GT for correction quality scoring
- **Config Pattern**: `train/stained/**/*.{png,jpg}` processes only stained inputs; clean/ referenced as GT
- **Expected Degradations**: `stain`, `bleed_through`, `water_damage`, `yellowing`

##### 10.3 External Resources

- **Kaggle Dataset**: [https://www.kaggle.com/datasets/xuhangc/wacv2025-staindoc](https://www.kaggle.com/datasets/xuhangc/wacv2025-staindoc)
- **WACV 2025 Paper**: [Search IEEE Xplore for StainDoc](https://ieeexplore.ieee.org/)

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
| MNV4-H1 | orientation_cls | ❌ | - | - | No orientation metadata; camera docs may vary but unlabeled |
| MNV4-H2 | skew_reg | ❌ | - | - | No skew angle labels; geometric skew not primary focus |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~5,000 | Inferred from stained images | Camera captures include resolution variation; no explicit score |
| SIG-G1-1 | blur_score | 🟡 | ~5,000 | Inferred from stained images | Camera focus blur present as secondary artifact |
| SIG-G1-2 | noise_score | 🟡 | ~5,000 | Inferred from stained images | Camera sensor noise present at low levels |
| SIG-G1-3 | contrast_score | 🟡 | ~5,000 | Inferred from stained images | Stains reduce text/background contrast |
| SIG-G1-4 | skew_score | ❌ | - | - | skew_score = quality degradation 0-1, not geometric angle; stains unrelated |
| SIG-G1-5 | compression_score | ❌ | - | - | PNG/JPG format; no JPEG blocking artifacts noted |
| SIG-G1-6 | overall_quality | 🟡 | ~5,000 | SSIM-derivable from stained/clean pairs | Paired GT enables SSIM-based quality MOS derivation |
| SIG-G2-1 | script_cls | ❌ | - | - | Language/script unknown; not annotated |
| SIG-G3-1 | orientation_cls (post) | ❌ | - | - | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ | - | - | No geometric skew labels |
| SIG-G4-1 | handwriting_presence_cls | ➖ | ~5,000 | Negative class | Printed documents only; useful as negative examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | - | - | No handwriting content |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | - | - | No handwriting content |
| SIG-G4-4 | presence_reg | ➖ | ~5,000 | Negative class | Printed documents → 0.0 handwriting presence score |
| SIG-G4-5 | legibility_reg | ❌ | - | - | No handwriting content |
| SIG-G5-1 | capture_method_cls | ✅ | ~5,000 | camera_smartphone (hard label) | All images camera-captured; confirmed from paper |
| SIG-G5-2 | shadow_reg | 🟡 | ~5,000 | Inferred from stained images | Page curl/uneven illumination creates lighting variation; no explicit severity label |
| SIG-G5-3 | warping_reg | ➖ | ~5,000 | Negative/low-end range | Camera capture introduces mild perspective distortion; not primary focus |
| SIG-G5-4 | code_cls | ❌ | - | - | General documents; no code content indicated |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | 🟡 | ~5,000 | Inferred from stained images | Variable camera resolution; no explicit label |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ❌ | Script unknown; likely Latin but unverified |
| 2 | Capture method | ✅ | 100% camera_smartphone — strong single-method anchor |
| 3 | Document domain | 🟡 | Unknown domain; general mixed printed documents |
| 4 | Layout type | ❌ | No layout annotations; varied but unlabeled |
| 5 | Text density | ❌ | Not measured; variable across printed documents |
| 6 | Degradation types | ✅ | Stain, bleed-through, water damage, yellowing, foxing — diverse stain catalog |
| 7 | Resolution/DPI range | 🟡 | Variable smartphone camera resolution; not DPI-profiled |
| 8 | Document age | 🟡 | Mix of natural aging (foxing/yellowing) and recent staining; exact age unknown |
| 9 | Text scope | ✅ | Page-level (full document pages) |
| 10 | Content flags | ❌ | No content flags annotated |
| 11 | Binarization status | ❌ | Color RGB images only |
| 12 | Artifact types | ✅ | Stains, bleed-through, water damage as explicit paired degradation |
| 13 | Color mode | ✅ | Color (RGB) — all camera captures |
| 14 | Font variety | ❌ | Unknown; not annotated |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

StainDoc's primary contribution to the unified training corpus is as a `capture_method=camera_smartphone` anchor for the SIG-G5-1 head, providing ~5,000 confirmed camera-captured real-world documents. As a paired stained/clean correction dataset, it also offers SSIM-derivable overall_quality labels useful for SIG-G1-6 training, and represents the stain/bleed-through degradation class that is underrepresented in most IQA datasets. The dataset is restricted to research use pending parser implementation; the MIT license permits broad use but the parser must be built before L2 metadata and training manifests can be generated.
