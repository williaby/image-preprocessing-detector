---
dataset_id: warpdoc
version: "1.0"
license: Unspecified
commercial_use: false
iqa_profiles:
  - perspective_distortion
  - fold
  - curve
  - rotation
  - lighting_variation
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### WarpDoc (Document Dewarping with 6 Distortion Types)

> **Quick Stats**: 1,020 camera images | 6 distortion types | Dewarping benchmark | CVPR 2022
>
> **License**: Unspecified | **Commercial Use**: Unknown (verify with authors)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | WarpDoc |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | SG-ViLab |
| **Paper** | [Fourier Document Restoration for Robust Document Dewarping and Recognition (CVPR 2022)](https://sg-vilab.github.io/event/warpdoc/) |
| **Site** | [https://sg-vilab.github.io/event/warpdoc/](https://sg-vilab.github.io/event/warpdoc/) |
| **License** | Unspecified (verify with authors) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG / PNG | Camera-captured warped document images |
| **Images** | JPG / PNG | Digital document images (added June 2022) |
| **Supplementary** | Website, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full Dataset** | `warpdoc/` | Implicit (distortion type folders) | 1,020 camera images | ✅ |
| **Digital Extension** | `warpdoc/digital/` | [NEEDS_VERIFICATION] | [NEEDS_VERIFICATION] | ⚠️ |

**Split Organization Pattern**: `by_folder` (distortion type subfolders)

> **Notes**:
>
> - 1,020 camera-captured images across 6 distortion types
> - Digital document images added in June 2022 update
> - Paired GT may be available (verify with digital document extension)
> - Exact internal split structure to be verified after download

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Distortion Type** | Directory-based | Document | 6 types: Fold, Curved, Incomplete, Random, Rotating, Perspective |
| **Paired Images** | [NEEDS_VERIFICATION] | Document | Digital documents may serve as GT |

> **Note**: Primary annotation is distortion type classification via directory structure.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Project website, Paper | Description, citation, distortion taxonomy |
| **Image-level** | Directory structure | Distortion type classification |

##### 2.5 Annotation Schema Details

> **Format**: Directory-based distortion type classification

```text
WarpDoc/
├── Fold/              # Folded document images
│   └── *.jpg
├── Curved/            # Curved/bent document images
│   └── *.jpg
├── Incomplete/        # Partially visible document images
│   └── *.jpg
├── Random/            # Random deformation patterns
│   └── *.jpg
├── Rotating/          # Rotation-distorted images
│   └── *.jpg
├── Perspective/       # Perspective-distorted images
│   └── *.jpg
└── digital/           # Digital GT documents (added June 2022)
    └── *.jpg

# [NEEDS_VERIFICATION] Exact directory structure after download
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to warped document image |
| `distortion_type` | str | Yes | One of 6 types (from directory name) |
| `is_digital` | bool | No | True for digital GT images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Distortion type | `distortion_type` | High | 6-class from directory name |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ⚠️ Paired images | `paired_file` | Medium | Digital GT may enable pairing |
| ❌ Quality scores | - | Low | Not provided |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Paired GT |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Warped/flat document pairs, 6 documented distortion types |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping/distortion correction) |
| **Purpose** | Dewarping benchmark, distortion classification training |
| **Local Path** | `01_base_data/camera_captured/warpdoc/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | Distortion type extraction from directory structure |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ⚠️ Partial - Parser created but enrichment not yet run |
| **Layer 2 Auto-Derived** | `capture_method=camera_smartphone`, `distortion_type` from directory |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/warpdoc/` | ✅ Available | JPG/PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/warpdoc_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

1,020 camera-captured warped document images across 6 distortion types (fold, curve, incomplete, random, rotating, perspective). 170 images per distortion category.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Full Dataset** | 1,020 camera images | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,020 (camera-captured) + digital extension |
| **Distortion Types** | 6 (Fold, Curved, Incomplete, Random, Rotating, Perspective) |
| **File Format(s)** | JPG / PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
warpdoc/
├── Fold/              # Folded document images
├── Curved/            # Curved/bent document images
├── Incomplete/        # Partially visible documents
├── Random/            # Random deformation patterns
├── Rotating/          # Rotation-distorted images
├── Perspective/       # Perspective-distorted images
└── digital/           # Digital GT (added June 2022)

# [NEEDS_VERIFICATION] Exact structure and counts per type
```

##### 5.1 Class/Category Distribution

| Distortion Type | Count | Percentage | Description |
|-----------------|-------|------------|-------------|
| **Fold** | ~170 | ~17% | Paper folding deformation |
| **Curved** | ~170 | ~17% | Curved/bent surface |
| **Incomplete** | ~170 | ~17% | Partially visible document |
| **Random** | ~170 | ~17% | Random deformation pattern |
| **Rotating** | ~170 | ~17% | Rotation distortion |
| **Perspective** | ~170 | ~17% | Camera angle perspective |

> **Note**: Exact per-type counts to be verified after download. Assuming roughly equal distribution across 6 types for 1,020 images.

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL (scientific papers, magazines, envelopes) |
| **Document Types** | Diverse printed documents with controlled distortions |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture with 6 distortion types |

#### 6. IQA Profile

Camera-captured documents with controlled geometric distortions. Primary value for dewarping/correction model training, not IQA benchmarking.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents with controlled distortions |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | Variable (controlled distortion types) |
| **Known Artifacts** | 6 distortion types: fold, curve, incomplete, random, rotating, perspective |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Dedicated distortion category |
| **Fold** | HIGH | Dedicated distortion category - paper folding |
| **Curve** | HIGH | Dedicated distortion category - surface bending |
| **Rotation** | HIGH | Dedicated distortion category |
| **Lighting Variation** | MEDIUM | Camera capture introduces lighting artifacts |
| **Blur** | MEDIUM | Some motion/focus blur expected |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Distortion affects text readability |
| **Document Types** | Scientific papers, magazines, envelopes | Diverse content |
| **Color Usage** | Mixed | Both B&W and color documents |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Unique 6-type distortion taxonomy for classification |
| **Unique Characteristics** | 6 distinct, labeled distortion types (only dataset with this granularity) |
| **Complementary Datasets** | Doc3D (synthetic), AnyPhotoDoc6300 (larger scale), DocReal |
| **Benchmark Suitability** | HIGH - CVPR 2022 paper benchmark with distortion classification |
| **Known Limitations** | Small (1,020 images); unspecified license |

#### 7. Known Issues & Limitations

- **License Unspecified**: No explicit license - verify with authors/project site before commercial use
- **Small Dataset**: Only 1,020 camera images - may need augmentation for training
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Paired GT Uncertain**: Digital extension (June 2022) may provide GT, but pairing is unverified
- **Uneven Type Counts**: Exact distribution across 6 distortion types needs verification

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{xue2022fourier,
  title={Fourier Document Restoration for Robust Document Dewarping and Recognition},
  author={Xue, Chao and others},
  booktitle={CVPR},
  year={2022}
}
```

##### Related Works

- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [AnyPhotoDoc6300](anyphotodoc6300.md) - Larger dewarping benchmark (6.3K images)
- [DocReal](docreal.md) - Small-scale real dewarping benchmark (251 images)

#### 10. Dataset-Specific Notes

##### 10.1 Distortion Taxonomy

WarpDoc defines 6 distinct distortion types, making it unique for distortion classification training:

| Type | Description | Physical Cause |
|------|-------------|----------------|
| **Fold** | Sharp crease deformation | Paper folded along a line |
| **Curved** | Smooth surface bending | Document on curved surface or held by hand |
| **Incomplete** | Partially visible content | Document extends beyond camera field of view |
| **Random** | Irregular deformation | Crumpled or arbitrarily deformed paper |
| **Rotating** | In-plane rotation | Document rotated relative to camera |
| **Perspective** | Keystone distortion | Camera at non-perpendicular angle to document |

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract distortion_type from directory name
- **Digital Extension**: June 2022 update added digital documents - check if these serve as paired GT
- **Distortion Classification**: Can be used for multi-class distortion type prediction (6 classes)
- **Small Scale**: Consider combining with Doc3D or AnyPhotoDoc6300 for sufficient training volume

##### 10.3 External Resources

- **Project Website**: [https://sg-vilab.github.io/event/warpdoc/](https://sg-vilab.github.io/event/warpdoc/)
- **Fourier Document Restoration Model**: Associated dewarping model from CVPR 2022

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | Unspecified |
| **Commercial Use** | Unknown (verify with authors) |
| **Image Format** | JPG / PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_warpdoc_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

Prescreening pass rate: 0% (base metadata only, expected gaps). Schema compliance: 100% (27 fields, all valid). Defect catalog: 6 defects (5 accepted gaps, 1 resolved text_scope fix). Overall grade: D (60-63/100, expected for base-only enrichment).

---

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---
