---
dataset_id: doc3d
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - synthetic
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### Doc3D (Document 3D Shape Recovery)

> **Quick Stats**: 100,000 images | 3D geometry GT | Warped documents | Synthetic + rendered
>
> **License**: MIT | **Commercial Use**: Yes (with attribution)
>
> **⚠️ LICENSE CORRECTION (2026-02-24)**: Catalog previously stated CC-BY-NC-SA (research only). Independent
> validation against the GitHub LICENSE file and HuggingFace dataset card confirmed the actual license is **MIT**.
> No non-commercial restriction exists. Both the dataset repo (`doc3D-dataset`) and the DewarpNet code repo
> use identical MIT text. Note: some upstream input textures used during synthetic generation were sourced from
> CC-licensed material (Yes! Magazine), but the published dataset itself is MIT-licensed. HuggingFace access
> is gated (requires sharing contact info), but this is a data-sharing agreement, not a license restriction.
>
> **⚠️ CAPTURE METHOD WARNING — HISTORICAL PATH MISLOCATION**
> Doc3D is stored on disk under `01_base_data/camera_captured/doc3d/` due to a
> historical naming error at download time. **Every image in this dataset is a
> fully synthetic 3D Blender render — no real camera was ever involved.**
> `capture_method` is explicitly set to `CaptureMethod.SYNTHETIC` in
> `datasets.py`. Do NOT infer capture_method from the folder path. A regression
> test in `tests/unit/annotation/config/test_datasets.py`
> (`TestCameraCaptureFolderSyntheticGuard`) enforces this value and will fail
> if it is changed without justification. See **Section 10.5** below for full context.

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Doc3D: A Document 3D Dataset for 3D Shape Recovery |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Maintainer** | Sagnik Das et al. (Stony Brook University) |
| **Paper** | [DewarpNet: Single-Image Document Unwarping (ICCV 2019)](https://www3.cs.stonybrook.edu/~cvl/projects/dewarpnet/storage/paper.pdf) |
| **Repository** | [GitHub: cvlab-stonybrook/doc3D-dataset](https://github.com/cvlab-stonybrook/doc3D-dataset) |
| **HuggingFace** | [StonyBrook-CVLab/doc3D-dataset](https://huggingface.co/datasets/StonyBrook-CVLab/doc3D-dataset) |
| **License** | MIT (validated 2026-02-24; see correction note above) |
| **GCS** | **⚠️ EXCLUDED** - Intentionally not replicated to GCS due to size (~209GB) |
| **Documentation Status** | Partial (v1.2.0 in progress) |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Warped document renderings (100K images) |
| **3D Coordinates** | NPY | 3D spatial coordinates for shape recovery |
| **Depth Maps** | NPY | Distance from camera plane (added v0.5.1) |
| **UV Maps** | NPY | 2D texture coordinates |
| **Backward Mapping** | NPY | Reverse deformation field |
| **Albedo** | NPY | Surface reflectance maps |
| **Normals** | NPY | Surface normal vectors |
| **Checkerboard** | NPY | Calibration pattern ground truth |
| **3D Mesh Files** | OBJ | Source 3D geometry (available via email request) |
| **Metadata** | README | Download scripts, version history, citation |

##### 2.2 Dataset Split Locations

> **Split Organization Pattern**: `single_dir_with_manifest` (user-defined)
>
> **Note**: Dataset authors recommend user-defined splits based on mesh IDs (GitHub issue #8).
> No official train/val/test split provided.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full Dataset** | `doc3d/img/` | `doc3d/{gt_type}/` | 102,064 [Verified] | ✅ Extracted |
| **Train** | - | - | - | ℹ️ User-defined (by mesh ID) |
| **Validation** | - | - | - | ℹ️ User-defined (by mesh ID) |
| **Test** | - | - | - | ℹ️ User-defined (by mesh ID) |

**Current State**: Images fully extracted (102,064 PNG files, 24 GB). Organized in 21 mesh ID subdirectories under `img/`.

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/camera_captured/doc3d/data/doc3d/img/` | ✅ Extracted | 102,064 PNG files (448x448, RGBA) |
| **Albedo** | `01_base_data/camera_captured/doc3d/data/doc3d/alb_*.zip` | ⬇️ Downloaded (not extracted) | 8 ZIPs (~2.3 GB) |
| **Backward Mapping** | `01_base_data/camera_captured/doc3d/data/doc3d/bm_*.zip` | ⬇️ Downloaded (not extracted) | 8 ZIPs (~105 GB) |
| **Depth Maps** | - | ❌ Not downloaded | 21 ZIPs (optional, for warping severity) |

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **3D Coordinates** | NPY | Image-level | 3D spatial coordinates for document surface |
| **Depth Maps** | NPY | Pixel-level | Distance from camera plane (z-depth) |
| **UV Maps** | NPY | Pixel-level | 2D texture coordinates for mapping |
| **Backward Mapping** | NPY | Pixel-level | Reverse deformation field for unwarping |
| **Albedo** | NPY | Pixel-level | Surface reflectance (intrinsic color) |
| **Normals** | NPY | Pixel-level | Surface normal vectors (3D orientation) |
| **Checkerboard** | NPY | Image-level | Calibration pattern ground truth |

> **Version Note**: v0.5 initially lacked depth maps; added in v0.5.1

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README.md (local) | Download instructions, HuggingFace mirror, version history |
| **Dataset-level** | GitHub repo | Download scripts, issue tracker, citation |
| **Image-level** | [NEEDS_VERIFICATION] | Mesh ID linking (filename-based or separate manifest) |
| **Mesh-level** | OBJ files (restricted) | 3D geometry (available via email request to authors) |

##### 2.5 Annotation Schema Details

> **Format**: NumPy arrays (.npy) for geometric data

```text
[Empirically Derived from filesystem]

doc3d/data/doc3d/
├── img/                     # 102,064 warped document images (PNG, 448x448, RGBA)
│   ├── 1/                   # Mesh ID 1 (4,999 images)
│   │   ├── 1000_4-pp_Page_847-Pwi0001.png
│   │   └── ...
│   ├── 2/ ... 21/           # 21 mesh ID subdirectories (~5,000 images each)
├── alb_1.zip - alb_8.zip   # Albedo maps (NPY, ~2.3 GB compressed, not extracted)
├── bm_1.zip, bm_10-16.zip  # Backward mapping (NPY, ~105 GB compressed, not extracted)
└── img_1.zip - img_21.zip  # Image ZIPs (24 GB, can be deleted after verification)

# File naming convention: {mesh_id}_{variant}-{doc_type}_Page_{page}-{hash}0001.png
# Image dimensions: 448x448 pixels, RGBA mode, PNG format
# Mesh IDs: 1-21 (21 directories, ~5,000 images per mesh)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `mesh_id` | str/int | Yes | Links image to source 3D mesh (prevents data leakage) |
| `image_path` | str | Yes | Path to warped document image (PNG) |
| `gt_type` | str | Varies | One of 7 ground truth types (3d/dmap/uv/bm/alb/norm/recon) |
| `deformation_params` | dict | Unknown | [NEEDS_VERIFICATION] Deformation parameters if available |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ 3D coordinates | - | Low | Specialized use (dewarping research) |
| ✅ Depth maps | - | Medium | Could inform IQA (warping severity detection) |
| ✅ UV maps | - | Low | Texture mapping (limited IQA value) |
| ✅ Backward mapping | - | Low | Deformation reversal (specialized) |
| ✅ Normals | - | Low | Surface orientation (specialized) |
| ✅ Albedo | - | Low | Surface reflectance (lighting invariant) |
| ❌ Text GT | - | N/A | Not provided (focus is 3D geometry) |
| ❌ Layout GT | - | N/A | Not provided (focus is 3D geometry) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

**Parser Status**: ℹ️ Not Implemented - P3 priority dataset, specialized 3D geometry GT not part of Prepare-Doc core mission (IQA, layout-lite, routing). If dewarping preprocessing becomes required, revisit parser development.

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Synthetic 3D warped document generation, 7 GT types (depth, UV, normals) exact by construction |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

- **Path**: `01_base_data/camera_captured/doc3d/`
- **Phase(s)**: Optional - Document dewarping research
- **Purpose**: 3D document geometry recovery, dewarping pre-training
- **Priority**: **P3** - Large dataset, specialized use case

#### 4. Dataset Statistics

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/camera_captured/doc3d/data/doc3d/img/` | ✅ Available | 102,064 PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### 4.1 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 102,064 [Verified] |
| **Local Storage** | ~131 GB (24 GB extracted images + 107 GB auxiliary ZIPs) |
| **Ground Truth Types** | 7 (3D coords, depth, UV, backward mapping, albedo, normals, checkerboard) |
| **Document Types** | Rendered documents with realistic 3D deformations (folding, bending, curving) |
| **Image Format** | PNG |
| **Resolution** | 448x448 pixels (fixed, rendered) |
| **Color Mode** | RGBA (4-channel) |
| **Mesh ID Groups** | 21 directories (~5,000 images each) |

#### 10. Dataset-Specific Notes

##### 10.1 GCS Exclusion Note

> **⚠️ INTENTIONALLY EXCLUDED FROM GCS REPLICATION**
>
> Doc3D is not replicated to Google Cloud Storage due to its large size (~209GB).
> The dataset is maintained locally at `/mnt/e/image_detection/01_base_data/camera_captured/doc3d/`.
> If GCS replication is required in the future, consider selective upload of essential subsets.

**Download Source**:

- **Primary**: HuggingFace mirror (requires authentication)
- **Alternative**: Individual download scripts (GitHub: cvlab-stonybrook/doc3D-dataset)
- **3D Mesh Files**: Email authors for OBJ format meshes

##### 10.2 Version History

| Version | Release Date | Changes |
|---------|--------------|---------|
| v0.5 | 2019 | Initial release (lacked depth maps) |
| v0.5.1 | [NEEDS_VERIFICATION] | Added depth maps |
| v1.0 | [NEEDS_VERIFICATION] | Current version (catalog entry) |

> **Note**: Version 0.5 initially lacked depth map ground truth. This was added in v0.5.1.
> Verify current version by checking downloaded files.

##### 10.3 Split Recommendation

> **From Authors** (GitHub issue #8): "Train and test split should be done based on the mesh IDs"
>
> **Rationale**: Prevents data leakage - same mesh ID with different deformations should not appear in both train and test.
>
> **Implementation**: If using this dataset, create splits by grouping images by mesh ID, then randomly assigning mesh IDs to train/val/test.

##### 10.4 Ground Truth Access

**Included in Download**:

1. 3D Coordinates
2. Depth Maps (v0.5.1+)
3. UV Maps
4. Backward Mapping
5. Albedo
6. Normals
7. Checkerboard

**Requires Email Request**:

- 3D Mesh Files (OBJ format)
- Contact: [Authors listed in ICCV 2019 paper]

##### 10.5 Historical Path Mislocation and Capture Method Guard

Doc3D was placed under `01_base_data/camera_captured/` when it was first
downloaded in 2025. The folder name was chosen because the rendered images
visually resemble camera-captured warped documents (realistic lighting,
perspective, shadows). However:

- All 102,064 images are **Blender 3D renders** from 21 source mesh IDs.
- The dataset paper (DewarpNet, ICCV 2019) explicitly describes synthetic
  generation via 3D mesh deformation.
- Ground truth types (depth maps, UV maps, backward mapping, surface normals)
  are only available because the generation process is synthetic.

**Discovered**: 2026-02-24 during a systematic `camera_captured/` audit
triggered by a Layer 2 metadata review.

**Resolution applied**:

1. `datasets.py` — `capture_method=CaptureMethod.SYNTHETIC` hardcoded with a
   warning comment. This is the authoritative value; the folder path is not used.
2. `validate_dataset_configs()` — new check flags any `camera_captured/` dataset
   with `capture_method=UNKNOWN` so future additions cannot slip through.
3. `test_datasets.py` — `TestCameraCaptureFolderSyntheticGuard` regression suite
   pins `doc3d.capture_method == SYNTHETIC` and asserts all `camera_captured/`
   datasets have an explicit (non-UNKNOWN) capture method.

**Files NOT moved**: The 102K images remain at their current path to avoid
breaking the `audit_config.py` entry, `download_doc3d_images.py`, and any
external references. The metadata is correct; the storage path is the artefact.

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ | - | - | Fixed 448x448 rendered images; orientation not varied across samples |
| MNV4-H2 | skew_reg | ❌ | - | - | No planar skew angle labels; 3D deformation ≠ 2D skew |
| MNV4-H3 | resolution_quality_reg | ❌ | - | - | Fixed 448x448 synthetic resolution; not representative of real DPI variation |
| SIG-G1-1 | blur_score | ❌ | - | - | Synthetic renders are uniformly sharp; no blur degradation |
| SIG-G1-2 | noise_score | ❌ | - | - | Synthetic renders have no camera sensor noise |
| SIG-G1-3 | contrast_score | ❌ | - | - | Uniform synthetic lighting; no real contrast degradation |
| SIG-G1-4 | skew_score | ❌ | - | - | skew_score = quality degradation 0-1; not applicable to 3D warp geometry |
| SIG-G1-5 | compression_score | ❌ | - | - | PNG format; no compression artifacts |
| SIG-G1-6 | overall_quality | ❌ | - | - | Synthetic renders have consistent quality; no IQA variation to learn |
| SIG-G2-1 | script_cls | ❌ | - | - | Language/script unknown; not annotated |
| SIG-G3-1 | orientation_cls (post) | ❌ | - | - | No orientation labels |
| SIG-G3-2 | skew_reg (post) | ❌ | - | - | No geometric skew labels |
| SIG-G4-1 | handwriting_presence_cls | ➖ | ~102,000 | Negative class | Rendered printed documents; useful as large-scale negative examples |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | - | - | No handwriting content |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | - | - | No handwriting content |
| SIG-G4-4 | presence_reg | ➖ | ~102,000 | Negative class | Rendered printed docs → 0.0 handwriting presence score |
| SIG-G4-5 | legibility_reg | ❌ | - | - | No handwriting content |
| SIG-G5-1 | capture_method_cls | ➖ | ~102,000 | Synthetic (negative for real classes) | Synthetic renders; useful as synthetic class examples if model includes synthetic category |
| SIG-G5-2 | shadow_reg | ❌ | - | - | Albedo maps model reflectance not shadow; no shadow severity labels |
| SIG-G5-3 | warping_reg | ✅ | ~102,000 | Derivable from backward mapping / depth maps | Primary dataset for 3D document warping; backward mapping + depth maps enable warping severity computation |
| SIG-G5-4 | code_cls | ❌ | - | - | General rendered documents; no code content indicated |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ❌ | - | - | Fixed synthetic resolution; not representative of real DPI variation |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ❌ | Script unknown; rendered from mixed source docs but unverified |
| 2 | Capture method | 🟡 | Synthetic rendering via 3D mesh deformation; distinct from camera or scanner |
| 3 | Document domain | ❌ | Unknown domain; source documents for rendering not documented |
| 4 | Layout type | ❌ | No layout annotations; varied by source document |
| 5 | Text density | ❌ | Not measured; variable across rendered documents |
| 6 | Degradation types | ✅ | 3D warping (folding, bending, curving, page curl) — most comprehensive warp geometry dataset available |
| 7 | Resolution/DPI range | ❌ | Fixed 448x448 synthetic resolution; no DPI variation |
| 8 | Document age | ❌ | All modern synthetic renders; no aging artifacts |
| 9 | Text scope | ✅ | Page-level (full document page renders) |
| 10 | Content flags | ❌ | No content flags annotated |
| 11 | Binarization status | ❌ | RGBA color renders only |
| 12 | Artifact types | ✅ | 3D geometric deformation: fold, bend, curl — seven GT types including depth and normal maps |
| 13 | Color mode | 🟡 | RGBA (4-channel); alpha channel present but unusual for training |
| 14 | Font variety | ❌ | Derived from source documents; not systematically varied |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

Doc3D's dominant contribution to the unified training corpus is the `warping_reg` head (SIG-G5-3), where its 102,064 synthetically rendered 3D-deformed documents with accompanying backward mapping and depth map annotations provide the richest geometric warp supervision of any available dataset. Because all samples are synthetic renders at fixed 448x448 resolution with no noise, blur, or real camera artifacts, the dataset contributes only minimally to IQA heads and cannot be used for capture method, resolution quality, or script classification training. The MIT license permits commercial use with attribution, and at ~209 GB the dataset is intentionally excluded from GCS; warping severity labels must be derived by extracting scalar statistics from the existing backward mapping NPY files, which have been downloaded but not yet extracted.
