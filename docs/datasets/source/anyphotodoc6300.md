---
dataset_id: anyphotodoc6300
version: "1.0"
license: GPL-3.0
commercial_use: false
iqa_profiles:
  - perspective_distortion
  - warping
  - lighting_variation
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### AnyPhotoDoc6300 (Document Dewarping Benchmark)

> **Quick Stats**: 6,300 images | Camera-captured | Warped + flat GT pairs | Dewarping benchmark
>
> **License**: GPL-3.0 (code; check dataset terms) | **Commercial Use**: No (GPL-3.0)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | AnyPhotoDoc6300 |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | hanquansanren et al. |
| **Paper** | [DvD: Decoupled Dewarping](https://github.com/hanquansanren/DvD) |
| **Repository** | [GitHub: hanquansanren/DvD](https://github.com/hanquansanren/DvD) |
| **HuggingFace** | [hanquansanren/AnyPhotoDoc6300](https://huggingface.co/datasets/hanquansanren/AnyPhotoDoc6300) |
| **License** | GPL-3.0 (code; verify dataset license separately) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Camera-captured warped document images |
| **Images** | PNG | Flat/rectified ground truth images |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full Dataset** | `anyphotodoc6300/` | Implicit (paired structure) | 6,300 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (user-defined or paired folder structure)

> **Notes**:
>
> - Dataset provides camera-captured warped images paired with flat/rectified ground truth
> - Exact internal split structure to be verified after download
> - Total 6,300 images (warped + corresponding GT pairs)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Filename/directory-based | Document | Warped input paired with flat/rectified GT |
| **Dewarping GT** | Implicit | Document | Flat version serves as dewarping target |

> **Note**: Primary annotation is through paired warped/flat image structure. No explicit quality scores or bounding boxes provided.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace page, GitHub README | Description, citation, download instructions |
| **Image-level** | Filename/directory structure | Pairing information, capture conditions |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (warped input + flat/rectified GT)

```text
AnyPhotoDoc6300/
├── warped/            # Camera-captured warped document images (PNG)
│   └── *.png
└── flat/              # Flat/rectified ground truth images (PNG)
    └── *.png

# [NEEDS_VERIFICATION] Exact directory structure after download
# Images are paired by filename correspondence
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to warped or flat image |
| `pair_type` | str | Yes | "warped" or "flat" (from directory/filename) |
| `base_name` | str | Yes | Links paired images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | Filename-based pairing |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ❌ Quality scores | - | Low | Not provided; compute from pairing (SSIM/MS-SSIM) |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Corrected/distorted document pairs for dewarping |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping/correction) |
| **Purpose** | Dewarping benchmark, correction model training |
| **Local Path** | `01_base_data/camera_captured/anyphotodoc6300/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Pair matching required |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ✅ Available - Parser created, enrichment pending |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `has_warping=True` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/anyphotodoc6300/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/anyphotodoc6300_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

Camera-captured document dewarping benchmark with 6,300 distorted images across 8 layout categories, 3 warping patterns, and 3 lighting conditions.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Full Dataset** | 6,300 | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 6,300 |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
anyphotodoc6300/
├── warped/              # Camera-captured warped documents
│   └── *.png
└── flat/                # Flat/rectified ground truth
    └── *.png

# [NEEDS_VERIFICATION] Exact structure after download
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL (scientific papers, magazines, mixed documents) |
| **Document Types** | Diverse printed documents with camera-induced warping |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture (warped), digital/flatbed (GT) |

#### 6. IQA Profile

Documents exhibit real-world camera capture degradations including perspective distortion, surface warping, and uneven lighting. Primary value is as paired GT for correction model training.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents (real-world warping) |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | Variable (real camera capture conditions) |
| **Known Artifacts** | Perspective distortion, warping, lighting variation |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Primary degradation type - camera angle variation |
| **Warping** | HIGH | Document surface deformation from capture |
| **Lighting Variation** | HIGH | Uneven illumination from camera capture |
| **Blur** | MEDIUM | Some motion/focus blur expected |
| **Noise** | MEDIUM | Camera sensor noise |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Warping distorts text proportionally |
| **Line/Grid Density** | Variable | Grid structures sensitive to warping |
| **Color Usage** | Mixed (B&W and color) | Color documents in source material |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large paired dataset for dewarping correction |
| **Unique Characteristics** | Camera-captured warped documents with flat GT |
| **Complementary Datasets** | Doc3D (synthetic warping), WarpDoc, DocReal |
| **Benchmark Suitability** | HIGH - Paired GT enables quantitative evaluation (SSIM/MS-SSIM/LD) |
| **Known Limitations** | GPL-3.0 license may restrict commercial use |

#### 7. Known Issues & Limitations

- **License Uncertainty**: Code is GPL-3.0; dataset license may differ - verify before commercial use
- **No Explicit Quality Scores**: Quality must be computed from paired comparison (SSIM, MS-SSIM)
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Domain Coverage**: [NEEDS_VERIFICATION] - Verify diversity of document types after download

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{dvd2024,
  title={DvD: Decoupled Dewarping},
  author={hanquansanren},
  year={2024},
  url={https://github.com/hanquansanren/DvD}
}
```

##### Related Works

- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [WarpDoc](warpdoc.md) - Document dewarping with 6 distortion types
- [DocReal](docreal.md) - Small-scale real dewarping benchmark

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Warped and flat images must be processed together for quality comparison
- **GT Quality**: Flat/rectified GT images serve as dewarping targets
- **No Deformation Parameters**: Warping severity not explicitly annotated (compute from image comparison)

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract pair type from directory/filename structure
- **Quality Computation**: Use SSIM/MS-SSIM/LD between warped and flat images for quality scoring
- **Capture Method**: Set `camera_smartphone` for warped images; GT images are flat/digital

##### 10.3 External Resources

- **DvD Model**: Decoupled dewarping model available at [GitHub: hanquansanren/DvD](https://github.com/hanquansanren/DvD)
- **HuggingFace**: [hanquansanren/AnyPhotoDoc6300](https://huggingface.co/datasets/hanquansanren/AnyPhotoDoc6300)

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | GPL-3.0 (code; verify dataset terms) |
| **Commercial Use** | No |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_anyphotodoc6300_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

Prescreening pass rate: 0% (base metadata only, expected gaps). Schema compliance: 100% (27 fields, all valid). Defect catalog: 6 defects (5 accepted gaps, 1 resolved text_scope fix). Overall grade: D (60-63/100, expected for base-only enrichment).

---

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---
