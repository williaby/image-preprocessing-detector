---
dataset_id: wsrd
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

#### WSRD (NTIRE Document Shadow Removal Dataset)

> **Quick Stats**: ~1,200 images | Camera-captured | Shadow + shadow-free GT pairs | NTIRE challenge
>
> **License**: Unspecified | **Commercial Use**: Unknown (verify with authors)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | WSRD (NTIRE Document Shadow Removal Dataset) |
| **Version** | 1.0 (WSRD); extended with WSRD+ (NTIRE 2024) |
| **Release Date** | 2023 (NTIRE 2023); 2024 (WSRD+ extension) |
| **Maintainer** | Florin Vasluianu et al. |
| **Paper** | [NTIRE 2023/2024 Document Shadow Removal Challenge](https://github.com/fvasluianu97/WSRD-DNSR) |
| **Repository** | [GitHub: fvasluianu97/WSRD-DNSR](https://github.com/fvasluianu97/WSRD-DNSR) |
| **License** | Unspecified (NTIRE challenge dataset; verify with organizers) |
| **Documentation Status** | Partial |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Shadow-degraded document images (input) |
| **Images** | PNG | Shadow-free ground truth images |
| **Supplementary** | README, Paper | Dataset description, challenge information, citation |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `train/input/`, `train/target/` | Implicit (paired structure) | ~1,000 pairs | ✅ |
| **Validation** | `val/input/`, `val/target/` | Implicit (paired structure) | ~100 pairs | ✅ |
| **Test** | `test/input/` | Challenge test (GT may be withheld) | ~100 | ⚠️ |

**Split Organization Pattern**: `by_folder` (train/val/test with input/target subfolders)

> **Notes**:
>
> - NTIRE 2023 base: ~1,000 train + 100 val + test set
> - NTIRE 2024 WSRD+ extension adds additional samples
> - Test set GT may be withheld for challenge evaluation
> - Total approximately 1,200 image pairs across all splits

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Paired Images** | Directory-based | Document | Shadow input paired with shadow-free GT |
| **Shadow Masks** | [NEEDS_VERIFICATION] | Pixel-level | Shadow region masks (may be available) |

> **Note**: Primary annotation is through paired shadow/clean image structure.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | GitHub README, NTIRE challenge page | Description, citation, challenge rules |
| **Image-level** | Filename/directory structure | Pairing information, split membership |

##### 2.5 Annotation Schema Details

> **Format**: Paired image structure (shadow input + shadow-free GT)

```text
WSRD/
├── train/
│   ├── input/         # Shadow-degraded document images (PNG)
│   │   └── *.png
│   └── target/        # Shadow-free ground truth images (PNG)
│       └── *.png
├── val/
│   ├── input/
│   │   └── *.png
│   └── target/
│       └── *.png
└── test/
    ├── input/
    │   └── *.png
    └── target/        # May be withheld for challenge
        └── *.png

# [NEEDS_VERIFICATION] Exact directory structure after download
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Path to shadow or clean image |
| `pair_type` | str | Yes | "input" (shadow) or "target" (clean) |
| `split` | str | Yes | "train", "val", or "test" |
| `base_name` | str | Yes | Links paired images |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Paired images | `paired_file` | High | Directory-based pairing |
| ✅ Split info | `subset` | High | From directory structure |
| ✅ Capture method | `capture_method` | Medium | Inferred (camera_smartphone) |
| ⚠️ Shadow masks | `shadow_mask` | Medium | [NEEDS_VERIFICATION] if available |
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
| **Local Path** | `01_base_data/camera_captured/wsrd/` |
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
| **Images** | `01_base_data/correction/wsrd/` | ✅ Available | PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Layer 2 Metadata** | `metadata_registry/json/wsrd_layer2.json` | 🔄 In Progress | Enrichment pending |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In Progress - Currently being processed/extracted

#### 4. Dataset Statistics

##### 4.1 Split Coverage

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | ~1,000 pairs | 0 | 0% | ❌ Not started |
| **Validation** | ~100 pairs | 0 | 0% | ❌ Not started |
| **Test** | ~100 | 0 | 0% | ❌ Not started |
| **Total** | ~1,200 | 0 | 0% | ❌ Not started |

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | ~1,200 (input) + ~1,200 (target) |
| **Training Split** | ~1,000 pairs |
| **Validation Split** | ~100 pairs |
| **Test Split** | ~100 (GT may be withheld) |
| **File Format(s)** | PNG |
| **Color Space** | RGB |
| **Annotation Format** | Paired image structure (shadow + shadow-free) |
| **Total Size on Disk** | [NEEDS_PROFILING] |

##### Directory Structure

```text
wsrd/
├── train/
│   ├── input/           # ~1,000 shadow-degraded images
│   └── target/          # ~1,000 shadow-free GT images
├── val/
│   ├── input/           # ~100 shadow-degraded images
│   └── target/          # ~100 shadow-free GT images
└── test/
    ├── input/           # ~100 shadow-degraded images
    └── target/          # GT (may be withheld for challenge)
```

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | GENERAL |
| **Document Types** | Mixed printed documents with cast shadows |
| **Language(s)** | [NEEDS_VERIFICATION] |
| **Acquisition Method** | Camera/smartphone capture with controlled shadow placement |

#### 6. IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Camera-captured documents with controlled shadows |
| **Capture Device** | Camera/smartphone |
| **Original Quality** | Controlled shadow degradation |
| **Known Artifacts** | Document shadows, illumination gradients, contrast reduction |

##### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Shadow** | HIGH | Primary degradation type - cast shadows on documents |
| **Illumination** | HIGH | Uneven lighting from shadow presence |
| **Contrast** | HIGH | Shadow regions have reduced local contrast |
| **Blur** | LOW | Not a primary degradation in this dataset |
| **Noise** | LOW | Secondary artifact |

##### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Variable | Shadow reduces text/background contrast |
| **Color Usage** | Mixed | Shadow color mixing with document colors |
| **Background** | Variable | Shadow intensity varies across document |

##### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Paired shadow removal dataset from NTIRE challenge |
| **Unique Characteristics** | NTIRE challenge benchmark with community evaluation |
| **Complementary Datasets** | SD7K (larger shadow removal), RealDAE (shadow task subset) |
| **Benchmark Suitability** | HIGH - NTIRE challenge standard, pre-split train/val/test |
| **Known Limitations** | Unspecified license; relatively small compared to SD7K |

#### 7. Known Issues & Limitations

- **License Unspecified**: No explicit license - NTIRE challenge terms may apply; verify with organizers
- **Test GT Availability**: Test set ground truth may be withheld for challenge evaluation
- **Small Dataset**: ~1,200 pairs is relatively small for training deep models
- **No Layout Annotations**: Dataset focused on shadow removal, lacks semantic layout labels
- **No Text GT**: No ground truth text transcriptions provided
- **NTIRE Challenge Dependency**: Dataset availability may depend on challenge hosting

#### 8. Representative Samples

> Placeholder - To be populated after dataset download and profiling.

| Sample | Description | Notable Features |
|--------|-------------|------------------|
| - | - | - |

#### 9. References

##### Primary Citation

```bibtex
@inproceedings{vasluianu2023ntire,
  title={NTIRE 2023 Challenge on Document Shadow Removal},
  author={Vasluianu, Florin and others},
  booktitle={CVPRW},
  year={2023}
}
```

##### Related Works

- [SD7K](sd7k.md) - Larger document shadow removal dataset (7K+ images)
- [RealDAE](realdae.md) - Camera document enhancement with shadow task subset

##### Leaderboards

- [NTIRE 2023 Document Shadow Removal Challenge](https://codalab.lisn.upsaclay.fr/)
- [NTIRE 2024 WSRD+ Extension](https://github.com/fvasluianu97/WSRD-DNSR)

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Paired Image Structure**: Shadow input and shadow-free GT must be processed together
- **NTIRE Challenge Format**: Dataset follows NTIRE challenge conventions
- **WSRD+ Extension**: NTIRE 2024 added additional samples (WSRD+) - verify total counts after download

##### 10.2 Implementation Notes

- **Parser Note**: Parser should extract split and pair type from directory structure
- **Quality Computation**: Use PSNR/SSIM between shadow and clean images for quality scoring
- **Capture Method**: Set `camera_smartphone` for shadow input images
- **Shadow Masks**: [NEEDS_VERIFICATION] Check if binary shadow masks are available

##### 10.3 External Resources

- **WSRD-DNSR Model**: Shadow removal model available at [GitHub: fvasluianu97/WSRD-DNSR](https://github.com/fvasluianu97/WSRD-DNSR)
- **NTIRE Challenge**: Annual document shadow removal competition at CVPR workshops

#### 10.4 License and Format

| Property | Value |
|----------|-------|
| **License** | Unspecified (NTIRE challenge) |
| **Commercial Use** | Unknown (verify with organizers) |
| **Image Format** | PNG |
| **Color Space** | RGB |

#### 10.5 Processing Status

Base metadata extraction complete via `annotate_base_metadata_lite.py`. Layer 2 integration complete via `integrate_wsrd_enrichments.py`. Schema compliance: 100% valid (27 fields). Enrichment gaps: domain, language, layout, text content not yet enriched.

#### 10.6 Version History

- **v1.0** (2026-02-13): Initial catalog entry and base metadata extraction

---

#### 11. Layer 2 Audit Summary

Prescreening pass rate: 0% (base metadata only, expected gaps). Schema compliance: 100% (27 fields, all valid). Defect catalog: 6 defects (5 accepted gaps, 1 resolved text_scope fix). Overall grade: D (60-63/100, expected for base-only enrichment).

---

#### 12. Reliability & Bottlenecks

Min confidence: 0.1 (language detection - no OCR run). Bottleneck: Missing enrichments (domain, language, layout, text). Suitable for: Shadow removal training (enrichment gaps not blocking).

---
