# Doc3D Dataset Extraction - Handoff Document

> **Date**: 2026-02-06
> **Priority**: P3 (Nice-to-have, not blocking current work)
> **Estimated Time**: 2-4 hours (mostly download wait time)
> **Disk Space Required**: ~400 GB free on E: drive (828 GB currently available)

## 1. Background

Doc3D is a 100,000-image dataset of synthetically warped documents with 3D geometry ground truth (DewarpNet, ICCV 2019). It's relevant for training geometric distortion/warping detection models for the IQA pipeline.

**Prepare-Doc use case**: Detect document warping/curling as an IQA quality issue. The primary data we need are the **document images** (`img/`) and optionally the **depth maps** (`dmap/`) for warping severity labels.

## 2. Current State

### What's On Disk

| Location | Contents |
|----------|----------|
| `/mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/doc3d/` | 16 ZIP files (209 GB) |
| `/mnt/e/image_detection/01_base_data/camera_captured/doc3d_repo/` | Cloned GitHub repo with download scripts |
| `/mnt/e/image_detection/01_base_data/camera_captured/doc3d/README.md` | Local access instructions |

### Downloaded ZIPs (Partial - HuggingFace snapshot)

| Type | Files Present | Size | Description |
|------|--------------|------|-------------|
| `alb_1.zip` - `alb_8.zip` | 8 of 8 | ~2.3 GB | Albedo/surface reflectance (NPY) |
| `bm_1.zip`, `bm_10.zip` - `bm_16.zip` | 8 of 21 | ~107 GB | Backward mapping (NPY) |
| **`img_*.zip`** | **0 of 21** | **NOT DOWNLOADED** | **Document images (PNG) - NEEDED** |
| `wc_*.zip` | 0 of 21 | NOT DOWNLOADED | World coordinates (NPY) |
| `uv_*.zip` | 0 of 21 | NOT DOWNLOADED | UV texture maps (NPY) |
| `dmap_*.zip` | 0 of 21 | NOT DOWNLOADED | Depth maps (NPY) |
| `norm_*.zip` | 0 of 21 | NOT DOWNLOADED | Surface normals (NPY) |
| `recon_*.zip` | 0 of 21 | NOT DOWNLOADED | Checkerboard reconstructions (NPY) |

### Critical Gap

**The actual document images (`img_*.zip`) were never downloaded.** The HuggingFace `snapshot_download` only grabbed albedo and partial backward mapping files. The 100K PNG images that we need for IQA training are completely missing.

## 3. What to Download

### Minimum (for Prepare-Doc IQA)

| Priority | Type | ZIP Count | Est. Size | Justification |
|----------|------|-----------|-----------|---------------|
| **MUST** | `img` | 21 ZIPs | ~15-25 GB (est.) | Document images - primary training data |
| SHOULD | `dmap` | 21 ZIPs | ~15-25 GB (est.) | Depth maps for warping severity labels |
| COULD | `bm` (remaining) | 13 ZIPs | ~100 GB | Backward mapping for dewarping GT |

### Full Dataset (if disk allows)

All 7 ground truth types: `img`, `dmap`, `uv`, `bm`, `wc`, `norm`, `recon`, `alb` (148 total ZIPs, ~400+ GB extracted).

## 4. Download Instructions

### Option A: HuggingFace (Recommended)

Requires HuggingFace account with dataset access approved.

**Step 1: Request access**

1. Go to: <https://huggingface.co/datasets/StonyBrook-CVLab/doc3D-dataset>
2. Click "Request access to this dataset"
3. Wait for approval (typically 1-2 days)

**Step 2: Download images only**

```python
from huggingface_hub import hf_hub_download, login
import os

login(token='YOUR_HF_TOKEN')  # or set HF_TOKEN env var

OUTPUT_DIR = '/mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/doc3d'

# Download just the image ZIPs (21 files)
for i in range(1, 22):
    print(f"Downloading img_{i}.zip...")
    hf_hub_download(
        repo_id='StonyBrook-CVLab/doc3D-dataset',
        repo_type='dataset',
        filename=f'doc3d/img_{i}.zip',
        local_dir=OUTPUT_DIR,
    )

# Optional: Download depth maps (21 files)
for i in range(1, 22):
    print(f"Downloading dmap_{i}.zip...")
    hf_hub_download(
        repo_id='StonyBrook-CVLab/doc3D-dataset',
        repo_type='dataset',
        filename=f'doc3d/dmap_{i}.zip',
        local_dir=OUTPUT_DIR,
    )
```

### Option B: Legacy Download Scripts (Backup)

The Stony Brook server requires credentials. The Google Form access method is deprecated as of Dec 31, 2025 but may still work.

```bash
cd /mnt/e/image_detection/01_base_data/camera_captured/doc3d_repo/

# Edit download_img.sh - replace **** with credentials:
#   local uname=YOUR_USERNAME
#   local pass=YOUR_PASSWORD

# Download images only
bash download_img.sh /mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/

# Download depth maps only
bash download_dmap.sh /mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/
```

**Credential sources**:

- Google Form (may still work): <https://forms.gle/RTfi7LUSrt891VuN8>
- Email authors: Sagnik Das, Ke Ma (Stony Brook CVLab)

## 5. Extraction Instructions

After downloading, extract the ZIPs into their expected directory structure.

```bash
DATASET_DIR="/mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/doc3d"

# Extract images
echo "Extracting image ZIPs..."
for f in ${DATASET_DIR}/img_*.zip; do
    echo "  Extracting $(basename $f)..."
    unzip -q -o "$f" -d "${DATASET_DIR}"
done

# Extract depth maps (if downloaded)
echo "Extracting depth map ZIPs..."
for f in ${DATASET_DIR}/dmap_*.zip; do
    echo "  Extracting $(basename $f)..."
    unzip -q -o "$f" -d "${DATASET_DIR}"
done

echo "Done."
```

### Expected Directory Structure After Extraction

```
doc3d/data/doc3d/
├── img/                  # 100,000 PNG document images
│   ├── 1/               # Grouped by mesh ID (or flat)
│   │   ├── 1_1.png
│   │   ├── 1_2.png
│   │   └── ...
│   └── .../
├── dmap/                 # 100,000 NPY depth maps (optional)
│   └── .../
├── alb_1.zip - alb_8.zip    # Already present (keep or extract)
├── bm_1.zip, bm_10-16.zip   # Already present (keep or extract)
└── img_1.zip - img_21.zip   # DELETE after successful extraction
```

**Note**: The exact internal structure of the ZIPs needs verification after extraction. Files may be flat or grouped by mesh ID. Document what you find.

## 6. Verification Checklist

After extraction, verify:

```bash
DATASET_DIR="/mnt/e/image_detection/01_base_data/camera_captured/doc3d/data/doc3d"

# 1. Count extracted images (should be ~100,000)
echo "Image count:"
find ${DATASET_DIR}/img/ -name "*.png" -type f | wc -l

# 2. Check image format
echo "Sample image info:"
file $(find ${DATASET_DIR}/img/ -name "*.png" -type f | head -1)

# 3. Check image dimensions (sample 5)
python3 -c "
from PIL import Image
import glob
files = sorted(glob.glob('${DATASET_DIR}/img/**/*.png', recursive=True))[:5]
for f in files:
    img = Image.open(f)
    print(f'{f}: {img.size} {img.mode}')
"

# 4. Count depth maps (if extracted, should be ~100,000)
echo "Depth map count:"
find ${DATASET_DIR}/dmap/ -name "*.npy" -type f 2>/dev/null | wc -l

# 5. Verify no corrupt ZIPs remain
echo "ZIP integrity check:"
for f in ${DATASET_DIR}/img_*.zip; do
    unzip -t "$f" > /dev/null 2>&1 && echo "OK: $(basename $f)" || echo "CORRUPT: $(basename $f)"
done
```

### Expected Results

| Check | Expected Value |
|-------|----------------|
| PNG image count | ~100,000 |
| Image format | PNG, RGB |
| Resolution | Variable (rendered, not fixed) |
| Depth map count | ~100,000 (NPY files) |
| ZIP integrity | All OK |

## 7. Post-Extraction Cleanup

```bash
# ONLY after verification passes:

# Option A: Delete ZIPs to save ~40 GB
rm ${DATASET_DIR}/img_*.zip
rm ${DATASET_DIR}/dmap_*.zip

# Option B: Keep ZIPs (safer, costs disk space)
# No action needed
```

## 8. What to Report Back

After completing extraction, update these files:

1. **Update** `docs/datasets/source/doc3d.md` section 2.2 (Split Locations):
   - Change status from "Downloaded (as ZIPs)" to "Extracted"
   - Add actual image count
   - Document the internal directory structure found

2. **Add Data Locations table** to `docs/datasets/source/doc3d.md`:

   ```markdown
   | Data Type | Path | Status | Notes |
   |-----------|------|--------|-------|
   | **Images** | `01_base_data/camera_captured/doc3d/data/doc3d/img/` | ✅ Available | {actual_count} PNG files |
   | **Depth Maps** | `01_base_data/camera_captured/doc3d/data/doc3d/dmap/` | ✅ Available | {actual_count} NPY files |
   ```

3. **Report** the following to the team:
   - Actual image count (expected: ~100,000)
   - Image dimensions/resolution range
   - Internal directory structure (flat vs. grouped by mesh ID)
   - File naming convention observed
   - Total extracted size on disk

## 9. Reference Information

| Resource | Link |
|----------|------|
| Paper | DewarpNet: Single-Image Document Unwarping (ICCV 2019) |
| HuggingFace | <https://huggingface.co/datasets/StonyBrook-CVLab/doc3D-dataset> |
| GitHub | <https://github.com/cvlab-stonybrook/doc3D-dataset> |
| Project Page | <https://www3.cs.stonybrook.edu/~cvl/projects/DocUnwarp/index.html> |
| License | CC-BY-NC-SA-4.0 (research only, no commercial use) |
| Existing Documentation | `docs/datasets/source/doc3d.md` |
| Local README | `/mnt/e/image_detection/01_base_data/camera_captured/doc3d/README.md` |

## 10. Important Notes

- **License**: CC-BY-NC-SA-4.0 - Research use only, no commercial use
- **Split strategy**: Train/test splits must be by mesh ID (not random) to prevent data leakage. See GitHub issue #8.
- **GCS**: This dataset is intentionally excluded from GCS replication due to size (~209 GB compressed, ~400+ GB extracted)
- **Not blocking**: Prepare-Doc current phases do not require doc3d. This is P3 priority for future warping detection work.
- **Disk budget**: E: drive has 828 GB free. Downloading img + dmap will use ~50-70 GB additional. Full extraction could use ~200 GB more. Monitor space.
