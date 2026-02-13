"""Download Doc3D image ZIPs from HuggingFace.

Downloads img_1.zip through img_21.zip to the local doc3d data directory.
Requires HF_TOKEN environment variable with access to StonyBrook-CVLab/doc3D-dataset.
"""

import os
import sys
import time

from huggingface_hub import hf_hub_download


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN environment variable not set")
        sys.exit(1)

    output_dir = "/mnt/e/image_detection/01_base_data/camera_captured/doc3d/data"
    repo_id = "StonyBrook-CVLab/doc3D-dataset"
    total_zips = 21

    print(f"Output directory: {output_dir}")
    print(f"Downloading {total_zips} image ZIPs from {repo_id}")
    print("=" * 60)

    for i in range(1, total_zips + 1):
        filename = f"doc3d/img_{i}.zip"
        dest = os.path.join(output_dir, "doc3d", f"img_{i}.zip")

        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(
                f"[{i}/{total_zips}] SKIP img_{i}.zip (already exists, {size_mb:.1f} MB)"
            )
            continue

        print(f"[{i}/{total_zips}] Downloading img_{i}.zip ...")
        start = time.time()
        try:
            hf_hub_download(
                repo_id=repo_id,
                repo_type="dataset",
                filename=filename,
                local_dir=output_dir,
                token=token,
            )
            elapsed = time.time() - start
            if os.path.exists(dest):
                size_mb = os.path.getsize(dest) / (1024 * 1024)
                print(f"         Done in {elapsed:.1f}s ({size_mb:.1f} MB)")
            else:
                print(f"         Done in {elapsed:.1f}s (file location may differ)")
        except Exception as e:
            print(f"         FAILED: {e}")
            sys.exit(1)

    print("=" * 60)
    print("All image ZIPs downloaded successfully.")


if __name__ == "__main__":
    main()
