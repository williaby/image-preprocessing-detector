#### Doc3D (Document 3D Shape Recovery)

> **Quick Stats**: 100,000 images | 3D geometry GT | Warped documents | Synthetic + rendered
>
> **License**: CC-BY-NC-SA | **Commercial Use**: Research only

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
| **License** | CC-BY-NC-SA-4.0 |
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
| **Full Dataset** | `doc3d/img/` | `doc3d/{gt_type}/` | 100,000 [Official] | ✅ Downloaded (as ZIPs) |
| **Train** | - | - | - | ℹ️ User-defined (by mesh ID) |
| **Validation** | - | - | - | ℹ️ User-defined (by mesh ID) |
| **Test** | - | - | - | ℹ️ User-defined (by mesh ID) |

**Current State**: Dataset downloaded as 16 ZIP files (~107GB visible, 209GB total). Images not yet extracted.

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

doc3d/data/doc3d/  (209GB total, 16 ZIP files)
├── img/              # Warped document images (100K PNG)
├── 3d/               # 3D coordinate arrays (.npy)
├── dmap/             # Depth map arrays (.npy) [added v0.5.1]
├── uv/               # UV coordinate arrays (.npy)
├── bm/               # Backward mapping arrays (.npy, ~14GB per ZIP)
├── alb/              # Albedo maps (.npy, ~276-328MB per ZIP)
├── norm/             # Surface normals (.npy)
└── recon/            # Checkerboard reconstructions (.npy)

# Current State: ZIPs not extracted
# File naming convention: [NEEDS_VERIFICATION after extraction]
# Array shapes and data types: [NEEDS_VERIFICATION]
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

**Parser Status**: ℹ️ Not Implemented - P3 priority dataset, specialized 3D geometry GT not part of Project A core mission (IQA, layout-lite, routing). If dewarping preprocessing becomes required, revisit parser development.

#### 3. Project Usage

- **Path**: `01_base_data/camera_captured/doc3d/`
- **Phase(s)**: Optional - Document dewarping research
- **Purpose**: 3D document geometry recovery, dewarping pre-training
- **Priority**: **P3** - Large dataset, specialized use case

#### 4. Dataset Statistics

##### 4.1 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 100,000 [Official] |
| **Local Storage** | ~209 GB (16 ZIP files) |
| **Ground Truth Types** | 7 (3D coords, depth, UV, backward mapping, albedo, normals, checkerboard) |
| **Document Types** | Rendered documents with realistic 3D deformations (folding, bending, curving) |
| **Image Format** | PNG |
| **Resolution** | Variable (rendered, not scanned) |

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

---
---
