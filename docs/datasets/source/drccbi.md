---
dataset_id: drccbi
version: "1.0"
license: Unknown (verify with authors before production use)
commercial_use: unknown
iqa_profiles:
  - dewarping
  - camera_smartphone
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### DRCCBI (Document Rectification and Camera-Captured Benchmark Images)

> **Quick Stats**: Camera dewarping pairs | Paired GT | Camera-captured | Dewarping benchmark
>
> **License**: Unknown (verify with authors) | **Commercial Use**: Unknown

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DRCCBI (Document Rectification and Camera-Captured Benchmark Images) |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Last Updated** | 2025 |
| **Maintainer** | HorizonParadox (GitHub user) |
| **Paper** | [DRCCBI Paper (2025) - if available](https://github.com/HorizonParadox/DRCCBI) |
| **Repository** | [GitHub: HorizonParadox/DRCCBI](https://github.com/HorizonParadox/DRCCBI) |
| **License** | Unknown (unstated - verify with authors) |
| **Commercial Use** | Unknown (verify with authors) |
| **Documentation Status** | Partial |

> **License Note**: License status unknown and not stated in repository. Not suitable for production use without
> explicit license verification from authors. Research use assumed but should be confirmed before any deployment.

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG | Warped/distorted camera-captured documents (input) |
| **Images** | JPG / PNG | Rectified flat documents (paired GT) |
| **Supplementary** | README | Dataset description, citation (if available) |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/warped/` | `train/flat/` (paired) | Unknown | ⚠️ Verify |
| **Test** | `test/warped/` | `test/flat/` (paired) | Unknown | ⚠️ Verify |
| **Total** | - | - | Unknown | ⚠️ Verify |

**Split Organization Pattern**: `by_folder` with paired warped/flat directories (expected)

> **Notes**:
>
> - Exact split structure and counts need verification from GitHub repository
> - Pairing likely based on matching filenames across `warped/` and `flat/` directories
> - Dataset size unknown; check repository for details

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Directory-based | Document | Warped input paired with flat GT by matching filename |
| **Dewarping Masks** | PNG (optional) | Pixel-level | Displacement maps or warp grids (if provided) |

> **Note**: Primary annotation is through paired image structure. Check repository for displacement maps or warp grids.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README | Description, citation, methodology (if available) |
| **Image-level** | Filename | Pairing information via matching names |
| **Split-level** | Directory structure | Train/test membership |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (warped input + flat GT)

```text
drccbi/
├── train/
│   ├── warped/
│   │   └── *.png, *.jpg
│   └── flat/
│       └── *.png, *.jpg  # Matching filenames
└── test/
    ├── warped/
    └── flat/
```

**Pairing Rule**: `train/warped/{filename}.png` <-> `train/flat/{filename}.png`

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to warped or flat image |
| `image_type` | str | Yes | `input_warped` or `ground_truth` (from directory) |
| `base_filename` | str | Yes | Links paired images across warped/flat |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `ground_truth_path` | High | Path-based pairing across warped/flat |
| ✅ Image type | `image_type` | High | From directory name (warped vs flat) |
| ✅ Capture method | `capture_method` | High | Camera-smartphone (from dataset description) |
| ✅ Expected degradations | `expected_degradations` | Medium | `warping`, `perspective_distortion`, `curl` |
| ⚠️ Displacement maps | `warp_grid_path` | Low | If provided; verify in repository |
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
| **Annotator Details** | Flat reference images captured/scanned separately from camera-warped inputs |
| **Inter-Annotator Agreement** | N/A - Paired image GT (objective reference) |
| **Quality Assurance** | Filename-matched pairing across warped/flat directories |
| **GT Label Coverage** | 100% - Every warped image has a corresponding flat GT |

---

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (camera dewarping correction) |
| **Purpose** | Document dewarping training, camera correction quality assessment |
| **Local Path** | `01_base_data/correction/drccbi/` |
| **Subset Used** | `warped/` images only (flat/ used as GT reference) |
| **Preprocessing** | Pair matching via filename |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `drccbi` (correction category) |
| **Parser Status** | ❌ Not Implemented |
| **Layer 1 Fields** | `source`, `capture_method`, `correction_task`, `image_type`, `is_degraded`, `has_ground_truth`, `ground_truth_path`, `expected_degradations` |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `content_type=printed`, `text_scope=page` |
| **Config Entry** | Pending implementation |

> **Parser Reference**: Pattern `train/warped/**/*.{png,jpg}` processes only warped inputs. Flat/GT images referenced via `ground_truth_path` label.

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/drccbi/` | ✅ Available | Warped + flat pairs |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/drccbi_layer2.json` | ❌ Not generated | Parser not yet implemented |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | Unknown | 0 | 0% | ❌ Parser not implemented |
| **Test** | Unknown | 0 | 0% | ❌ Parser not implemented |
| **Total** | Unknown | 0 | 0% | ❌ Parser not implemented |

**Split Status Legend**:

- ❌ Missing - Parser not yet implemented

> **Note**: Repository verification required to determine dataset size.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Warped Images** | Unknown |
| **Total Flat GT Images** | Unknown |
| **Image Dimensions** | Variable (camera-captured documents) |
| **Resolution (DPI)** | Variable (smartphone camera) |
| **File Format(s)** | PNG, JPG (verify) |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure (directory-based) |
| **Total Size on Disk** | Unknown |

##### 4.3 Text Statistics

> **Availability**: ❌ Not Available - No ground truth text provided in source dataset.

##### Directory Structure

```text
drccbi/
├── train/
│   ├── warped/          # Camera-captured warped documents
│   └── flat/            # Rectified flat GT documents
└── test/
    ├── warped/
    └── flat/
```

> **Note**: Exact structure requires verification from GitHub repository.

##### Baseline Quality Metrics

> **Source**: [NEEDS_PROFILING] - Empirical profiling not yet run on this dataset.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | UNKNOWN (general documents with camera capture distortion) |
| **Document Types** | Mixed printed documents captured via smartphone |
| **Language(s)** | Unknown (likely multilingual) |
| **Temporal Range** | Unknown (recent smartphone captures) |
| **Acquisition Method** | Camera-smartphone capture with perspective/warping distortion |

##### 5.1 Class/Category Distribution

> **N/A**: No class categories; correction dataset focused on dewarping.

##### 5.2 Class/Category Definitions

> **N/A**: Not applicable for paired correction dataset.

##### 5.3 Language & Script Coverage

> **Status**: Unknown - requires OCR extraction and language detection.

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured warped documents with flat GT pairs |
| **Capture Device** | Smartphone cameras |
| **Original Quality** | Degraded (warped/distorted) vs flat (GT) |
| **Warp Types** | Perspective distortion, page curl, cylindrical warping |
| **Known Artifacts** | Warping, shadows, camera perspective, uneven lighting |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Warping** | HIGH | Primary degradation - page curl, cylindrical distortion |
| **Perspective Distortion** | HIGH | Camera angle creates geometric distortion |
| **Shadows** | MEDIUM | Page curl creates self-shadowing |
| **Blur** | LOW | Secondary artifact from camera motion |
| **Lighting** | MEDIUM | Uneven illumination from camera flash |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Warp Diversity** | High | Multiple warp types (curl, cylindrical, perspective) |
| **Text Size Range** | Variable | Camera-captured, variable distances |
| **Color Usage** | Mixed | Color documents + grayscale |
| **Camera Artifacts** | Present | Perspective, lighting, shadows |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Paired dataset for camera document dewarping |
| **Unique Characteristics** | Camera-captured warp realism, paired flat GT |
| **Complementary Datasets** | [DocAlign12K](docalign12k.md) (synthetic alignment), [WarpDoc](warpdoc.md) (warping), [AnyPhotoDoc6300](anyphotodoc6300.md) (dewarping) |
| **Benchmark Suitability** | HIGH - Enables quantitative evaluation via SSIM/MS-SSIM |
| **Known Limitations** | Unknown license, limited documentation, dataset size unknown |

#### 7. Known Issues & Limitations

- **License Unknown**: No explicit license provided - contact dataset authors before commercial or production use
- **Limited Documentation**: GitHub repository may lack detailed README
- **Dataset Size Unknown**: Number of images not documented; requires repository clone
- **No Text Ground Truth**: Paired images only; no OCR text provided
- **No Warp Taxonomy**: Warp types not explicitly labeled; requires visual inspection
- **Camera Artifacts**: Perspective distortion and lighting variation may confound dewarping training
- **No Validation Split**: Split structure unclear; may only have train/test

#### 8. Representative Samples

> Placeholder - To be populated during dataset profiling and VLM inspection.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{horizonparadox2025drccbi,
  title={DRCCBI: Document Rectification and Camera-Captured Benchmark Images},
  author={HorizonParadox},
  year={2025},
  publisher={GitHub},
  url={https://github.com/HorizonParadox/DRCCBI}
}
```

##### Related Works

- [DocAlign12K](docalign12k.md) - Synthetic document alignment correction
- [WarpDoc](warpdoc.md) - Document warping dataset
- [AnyPhotoDoc6300](anyphotodoc6300.md) - Camera-captured dewarping benchmark
- [DocReal](docreal.md) - Small-scale real dewarping benchmark

##### Leaderboards

- None currently available

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Warped and flat images must be processed together for dewarping training
- **Warp Types Not Labeled**: No explicit warp type annotations; requires visual inspection or clustering
- **Camera Artifacts Present**: Flat GT images may still have minor lighting/shadow artifacts if captured separately

##### 10.2 Implementation Notes

- **Parser Priority**: Medium - fills gap for camera-captured dewarping benchmark
- **Repository Verification**: Clone GitHub repository to confirm exact schema, file structure, and dataset size
- **Capture Method**: Set `camera_smartphone` based on dataset description
- **Quality Computation**: Use SSIM/MS-SSIM between warped and paired flat GT for dewarping quality scoring
- **Config Pattern**: `train/warped/**/*.{png,jpg}` processes only warped inputs; flat/ referenced as GT
- **Expected Degradations**: `warping`, `perspective_distortion`, `curl`, `cylindrical_distortion`

##### 10.3 External Resources

- **GitHub Repository**: [https://github.com/HorizonParadox/DRCCBI](https://github.com/HorizonParadox/DRCCBI)
- **Related Work**: Check repository for associated paper or conference submission

---

#### 11. Layer 2 Audit Summary

> **Status**: No audit performed. Parser not yet implemented.

---

#### 12. Reliability & Bottlenecks

> **Status**: Parser not implemented - no Layer 2 metadata available for reliability analysis.

---
