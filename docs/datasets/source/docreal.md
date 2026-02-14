---
dataset_id: docreal
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - perspective_distortion
  - warping
baseline_quality: null
training_suitable: true
benchmark_suitable: true
documentation_status: partial
---

#### DocReal (Document Dewarping Benchmark)

> **Quick Stats**: 251 images | 201 distorted + 50 scanned GT | Camera-captured + scanner | MIT license
>
> **License**: MIT | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocReal |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | irisXcoding et al. |
| **Paper** | [Robust Document Dewarping via Attention-Enhanced Control Point Prediction](https://github.com/irisXcoding/DocReal) |
| **Repository** | [GitHub: irisXcoding/DocReal](https://github.com/irisXcoding/DocReal) |
| **License** | MIT |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Camera-captured distorted document images (201 images) |
| **Images** | PNG | Flatbed-scanned ground truth images (50 images) |
| **Supplementary** | README, Paper | Dataset description and citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Distorted** | `DocReal/distorted/` | Implicit (filename-based pairing) | 201 | ✅ |
| **Scanned (GT)** | `DocReal/scanned/` | Implicit (filename-based pairing) | 50 | ✅ |

**Split Organization Pattern**: `by_folder` (distorted vs scanned subfolders)

> **Notes**:
>
> - 201 distorted images (camera-captured with various warping)
> - 50 scanned images serving as ground truth
> - Multiple distorted variants per scanned document (doc_id maps distorted to scanned)
> - No explicit train/val/test split provided (user-defined)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Filename-based | Document | Distorted images paired with scanned GT via doc_id |
| **Capture Method** | Directory-based | Document | "distorted" = camera, "scanned" = flatbed scanner |

> **Note**: Primary annotation is through paired image structure. Scanned images serve as dewarping ground truth.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, Paper | Description, citation, methodology |
| **Image-level** | Filename pattern | Document ID linking distorted to scanned GT |

##### 2.5 Annotation Schema Details

> **Format**: Filename-based pairing structure

```text
DocReal/
├── distorted/
│   ├── {doc_id}_{variant}.png    # Camera-captured distorted images
│   ├── 001_01.png                # Document 001, variant 01
│   ├── 001_02.png                # Document 001, variant 02
│   └── ...
└── scanned/
    ├── {doc_id}.png              # Flatbed-scanned ground truth
    ├── 001.png                   # Document 001 GT
    └── ...

# Multiple distorted variants per scanned document
# doc_id links distorted to scanned GT
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to distorted or scanned image |
| `doc_id` | str | Yes | Document identifier linking distorted to GT |
| `variant` | str | No | Distortion variant index (distorted images only) |
| `capture_type` | str | Yes | "distorted" (camera) or "scanned" (flatbed) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | doc_id-based pairing |
| ✅ Capture method | `capture_method` | High | camera_smartphone (distorted) / scanner_flatbed (scanned) |
| ✅ Document ID | `doc_id` | High | From filename pattern |
| ❌ Quality scores | - | Low | Not provided; compute from pairing |
| ❌ Layout boxes | - | Low | Not provided |
| ❌ Text GT | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training (dewarping correction) |
| **Purpose** | Dewarping benchmark, correction model evaluation |
| **Local Path** | `01_base_data/camera_captured/docreal/` |
| **Subset Used** | Full dataset |
| **Preprocessing** | doc_id-based pair matching required |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Parser Status** | ⚠️ Partial - Parser created but enrichment not yet run |
| **Layer 2 Auto-Derived** | `capture_method` (camera_smartphone or scanner_flatbed), `has_warping=True` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/correction/docreal/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/docreal_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

DocReal contains 251 images: 201 camera-captured distorted and 50 flatbed-scanned ground truth.

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Distorted** | 201 | 0 | 0% | ❌ Not started |
| **Scanned (GT)** | 50 | 0 | 0% | ❌ Not started |
| **Total** | 251 | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 251 |
| **Distorted Images** | 201 (camera-captured) |
| **Scanned GT Images** | 50 (flatbed scanner) |
| **Variants per Document** | ~4 distorted per scanned (~201/50) |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
docreal/
├── distorted/           # 201 camera-captured distorted images
│   ├── {doc_id}_{variant}.png
│   └── ...
└── scanned/             # 50 flatbed-scanned ground truth images
    ├── {doc_id}.png
    └── ...
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL |
| **Document Types** | Mixed printed documents |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone (distorted), flatbed scanner (GT) |

#### 6. IQA Profile

Camera-captured documents with perspective distortion and warping, paired with flatbed-scanned GT.

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured distorted + flatbed-scanned GT |
| **Capture Device** | Camera/smartphone (distorted), flatbed scanner (GT) |
| **Original Quality** | Variable distortion (camera), clean (scanner) |
| **Known Artifacts** | Perspective distortion, warping, lighting variation |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Perspective Distortion** | HIGH | Primary degradation from camera capture |
| **Warping** | HIGH | Document surface deformation |
| **Lighting Variation** | MEDIUM | Camera capture introduces lighting artifacts |
| **Blur** | MEDIUM | Some motion/focus blur expected |
| **Noise** | LOW | Secondary artifact |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Warping distorts text readability |
| **Color Usage** | Mixed | Both B&W and color documents |
| **Multi-Variant** | Yes | Multiple distortion variants per document enable controlled comparison |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Small but real-world paired data with MIT license |
| **Unique Characteristics** | Multiple distorted variants per GT; clean MIT license |
| **Complementary Datasets** | AnyPhotoDoc6300 (larger), WarpDoc (distortion types), Doc3D (synthetic) |
| **Benchmark Suitability** | HIGH - Real paired data with scanner GT enables rigorous evaluation |
| **Known Limitations** | Very small (251 images); limited document diversity |

#### 7. Known Issues & Limitations

- **Very Small Dataset**: Only 251 images total (201 distorted + 50 GT) - insufficient for standalone training
- **Limited Document Diversity**: Only 50 unique documents with multiple distorted variants
- **No Explicit Splits**: No train/val/test split provided - user must define
- **No Layout Annotations**: Dataset focused on dewarping, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **Variant Imbalance**: Number of distorted variants per document may be uneven

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@misc{docreal2024,
  title={Robust Document Dewarping via Attention-Enhanced Control Point Prediction},
  author={irisXcoding},
  year={2024},
  url={https://github.com/irisXcoding/DocReal}
}
```

##### Related Works

- [AnyPhotoDoc6300](anyphotodoc6300.md) - Larger dewarping benchmark (6.3K images)
- [WarpDoc](warpdoc.md) - 6 distortion types (1K images)
- [Doc3D](doc3d.md) - Synthetic 3D warped documents (100K images)
- [RealDAE](realdae.md) - Camera document enhancement (same capture paradigm)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Multi-Variant Pairing**: Each scanned GT document has multiple distorted variants (avg ~4)
- **Scanned as GT**: Flatbed-scanned images serve as dewarping ground truth (not digital originals)
- **No Distortion Labels**: Unlike WarpDoc, distortion types are not explicitly categorized

##### 10.2 Implementation Notes

- **Parser Note**: Extract doc_id from filename pattern `{doc_id}_{variant}.png` (distorted) and `{doc_id}.png` (scanned)
- **Quality Computation**: Use SSIM/MS-SSIM/LD between distorted and scanned images for quality scoring
- **Capture Method**: Set `camera_smartphone` for distorted, `scanner_flatbed` for scanned
- **Small Scale**: Best used as evaluation benchmark; combine with larger datasets for training
- **MIT License**: One of the few dewarping datasets with a permissive open-source license

##### 10.3 External Resources

- **DocReal Repository**: [GitHub: irisXcoding/DocReal](https://github.com/irisXcoding/DocReal)
- **Attention-Enhanced Control Point Model**: Associated dewarping model in the repository

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | MIT |
| **Commercial Use** | Yes |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_docreal_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

Prescreening pass rate: 0% (base metadata only, expected gaps). Schema compliance: 100% (27 fields, all valid). Defect catalog: 6 defects (5 accepted gaps, 1 resolved text_scope fix). Overall grade: D (60-63/100, expected for base-only enrichment).

---

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Correction/dewarping training (enrichment gaps not blocking).

---
