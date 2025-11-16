# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Google Drive synchronization utilities for Colab training.

Handles dataset download/upload, model artifact management, and progress tracking
for large files stored in Google Drive.
"""

import shutil
import zipfile
from pathlib import Path

import gdown


def mount_google_drive(mount_point: str = "/content/drive") -> bool:
    """Mount Google Drive in Colab environment.

    Args:
        mount_point: Path where Drive should be mounted

    Returns:
        True if successfully mounted

    Raises:
        ImportError: If not running in Google Colab
    """
    try:
        from google.colab import drive

        print(f"📁 Mounting Google Drive at {mount_point}...")
        drive.mount(mount_point, force_remount=False)
        print("✅ Google Drive mounted successfully!")
        return True
    except ImportError:
        print("❌ Error: Not running in Google Colab environment")
        return False


def download_dataset(
    drive_path: str,
    local_path: str,
    extract_zip: bool = True,
) -> Path:
    """Download dataset from Google Drive to local Colab storage.

    Args:
        drive_path: Path in Google Drive (e.g., /content/drive/MyDrive/datasets/iqa_50k)
        local_path: Local path to copy to (e.g., /content/data)
        extract_zip: If True and file is .zip, extract it

    Returns:
        Path to downloaded/extracted dataset

    Raises:
        FileNotFoundError: If drive_path doesn't exist
    """
    drive_path_obj = Path(drive_path)
    local_path_obj = Path(local_path)

    if not drive_path_obj.exists():
        raise FileNotFoundError(f"Dataset not found in Google Drive: {drive_path}")

    print("📥 Downloading dataset from Google Drive...")
    print(f"   Source: {drive_path}")
    print(f"   Destination: {local_path}")

    # Create local directory
    local_path_obj.mkdir(parents=True, exist_ok=True)

    # Check if it's a zip file
    if drive_path_obj.is_file() and drive_path_obj.suffix == ".zip":
        print("   Detected ZIP archive")
        zip_local_path = local_path_obj / drive_path_obj.name

        # Copy zip file
        shutil.copy2(drive_path_obj, zip_local_path)
        print(f"   ✅ ZIP file copied: {zip_local_path.name}")

        # Extract if requested
        if extract_zip:
            print("   📦 Extracting ZIP archive...")
            with zipfile.ZipFile(zip_local_path, "r") as zip_ref:
                zip_ref.extractall(local_path_obj)
            print(f"   ✅ Extracted to: {local_path_obj}")

            # Remove zip file to save space
            zip_local_path.unlink()
            print("   🗑️  Removed ZIP file to save space")

        return local_path_obj

    # If it's a directory, copy recursively
    if drive_path_obj.is_dir():
        print("   Detected directory")
        shutil.copytree(drive_path_obj, local_path_obj, dirs_exist_ok=True)
        print(f"   ✅ Directory copied: {local_path_obj}")
        return local_path_obj

    # Single file
    shutil.copy2(drive_path_obj, local_path_obj / drive_path_obj.name)
    print(f"   ✅ File copied: {drive_path_obj.name}")
    return local_path_obj / drive_path_obj.name


def upload_model_artifacts(
    local_model_path: str,
    drive_output_dir: str,
    include_checkpoints: bool = False,
) -> None:
    """Upload trained model artifacts back to Google Drive.

    Args:
        local_model_path: Local path to model file or directory
        drive_output_dir: Google Drive directory to upload to
        include_checkpoints: If True, also upload checkpoint files
    """
    local_path = Path(local_model_path)
    drive_dir = Path(drive_output_dir)

    # Create Drive output directory
    drive_dir.mkdir(parents=True, exist_ok=True)

    print("📤 Uploading model artifacts to Google Drive...")
    print(f"   Source: {local_model_path}")
    print(f"   Destination: {drive_output_dir}")

    if local_path.is_file():
        # Single file (e.g., final ONNX model)
        shutil.copy2(local_path, drive_dir / local_path.name)
        print(f"   ✅ Uploaded: {local_path.name}")

    elif local_path.is_dir():
        # Directory (e.g., checkpoint directory)
        for file_path in local_path.rglob("*"):
            if file_path.is_file():
                # Skip checkpoint files unless requested
                if not include_checkpoints and "checkpoint" in file_path.name:
                    continue

                # Preserve directory structure
                relative_path = file_path.relative_to(local_path)
                dest_path = drive_dir / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(file_path, dest_path)
                print(f"   ✅ Uploaded: {relative_path}")

    print("✅ Model artifacts uploaded successfully!")


def download_from_google_drive_url(
    file_id: str,
    output_path: str,
    extract_zip: bool = True,
) -> Path:
    """Download file from Google Drive using shareable link.

    Useful for downloading pre-prepared datasets from shared Drive links.

    Args:
        file_id: Google Drive file ID from shareable link
        output_path: Local path to save file
        extract_zip: If True and file is .zip, extract it

    Returns:
        Path to downloaded/extracted file

    Example:
        # For link: https://drive.google.com/file/d/1abc123xyz/view
        download_from_google_drive_url("1abc123xyz", "/content/dataset.zip")
    """
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    print(f"📥 Downloading from Google Drive (file ID: {file_id})...")

    # Download using gdown
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, str(output_path_obj), quiet=False)

    print(f"✅ Downloaded to: {output_path_obj}")

    # Extract if it's a zip file
    if extract_zip and output_path_obj.suffix == ".zip":
        print("📦 Extracting ZIP archive...")
        extract_dir = output_path_obj.parent / output_path_obj.stem
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path_obj, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"✅ Extracted to: {extract_dir}")
        output_path_obj.unlink()  # Remove zip to save space
        return extract_dir

    return output_path_obj


def check_drive_space(mount_point: str = "/content/drive/MyDrive") -> dict:
    """Check available space in Google Drive.

    Args:
        mount_point: Google Drive mount point

    Returns:
        Dictionary with total, used, and free space in GB
    """
    mount_path = Path(mount_point)

    if not mount_path.exists():
        return {"error": "Google Drive not mounted"}

    stat = shutil.disk_usage(mount_path)

    total_gb = stat.total / (1024**3)
    used_gb = stat.used / (1024**3)
    free_gb = stat.free / (1024**3)

    print("💾 Google Drive Space:")
    print(f"   Total: {total_gb:.2f} GB")
    print(f"   Used: {used_gb:.2f} GB")
    print(f"   Free: {free_gb:.2f} GB")
    print(f"   Usage: {(used_gb / total_gb) * 100:.1f}%")

    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb,
        "usage_percent": (used_gb / total_gb) * 100,
    }


def sync_checkpoints_to_drive(
    local_checkpoint_dir: str,
    drive_checkpoint_dir: str,
    sync_mode: str = "incremental",
) -> None:
    """Sync local checkpoints to Google Drive during training.

    Args:
        local_checkpoint_dir: Local checkpoint directory
        drive_checkpoint_dir: Google Drive checkpoint directory
        sync_mode: 'incremental' (only new files) or 'full' (all files)
    """
    local_dir = Path(local_checkpoint_dir)
    drive_dir = Path(drive_checkpoint_dir)

    drive_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔄 Syncing checkpoints to Google Drive ({sync_mode} mode)...")

    synced_count = 0
    for checkpoint_file in local_dir.glob("*.pt"):
        dest_file = drive_dir / checkpoint_file.name

        # Skip if already exists in incremental mode
        if sync_mode == "incremental" and dest_file.exists():
            # Check if local is newer
            if checkpoint_file.stat().st_mtime <= dest_file.stat().st_mtime:
                continue

        shutil.copy2(checkpoint_file, dest_file)
        synced_count += 1
        print(f"   ✅ Synced: {checkpoint_file.name}")

    # Also sync JSON metadata files
    for json_file in local_dir.glob("*.json"):
        dest_file = drive_dir / json_file.name
        if sync_mode == "full" or not dest_file.exists():
            shutil.copy2(json_file, dest_file)

    print(f"✅ Synced {synced_count} checkpoint(s) to Google Drive")


def create_dataset_info_file(
    dataset_path: str,
    info: dict,
) -> None:
    """Create dataset info file for documentation.

    Args:
        dataset_path: Path to dataset directory
        info: Dictionary with dataset information (size, splits, etc.)
    """
    import json

    dataset_dir = Path(dataset_path)
    info_file = dataset_dir / "dataset_info.json"

    with open(info_file, "w") as f:
        json.dump(info, f, indent=2)

    print(f"✅ Dataset info saved: {info_file}")
