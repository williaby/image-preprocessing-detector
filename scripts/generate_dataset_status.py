#!/usr/bin/env python3

"""
Generate comprehensive dataset status report.

Scans all datasets in NFS storage and generates:
1. File counts per dataset
2. Total sizes
3. GCS upload status
4. Data for documentation updates
"""

import json
import subprocess  # nosec B404 - subprocess used only for du/find/gsutil with hardcoded commands
import tempfile
from pathlib import Path

NFS_ROOT = Path("/mnt/unraid/training_data/image_detection")
GCS_BUCKET = "gs://image_detection_b/image-preprocessing-detector/datasets"
GCS_CREDENTIALS = Path(__file__).parent.parent / ".gcp/service-account.json"


def get_dataset_size(dataset_path: Path) -> tuple[str, int]:
    """Get size of dataset in human-readable and bytes."""
    try:
        # Security: subprocess used only with hardcoded commands, no user input
        result = subprocess.run(  # nosec B603, B607
            ["du", "-sb", str(dataset_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        bytes_size = int(result.stdout.split()[0])
        size_for_display = float(bytes_size)

        # Convert to human readable
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_for_display < 1024:
                return f"{size_for_display:.1f} {unit}", bytes_size
            size_for_display /= 1024
        return f"{size_for_display:.1f} PB", bytes_size
    except Exception:
        return "Unknown", 0


def count_files(dataset_path: Path, extensions: list[str] = None) -> dict[str, int]:
    """Count files by type in dataset."""
    if not dataset_path.exists():
        return {}

    counts = {}

    if extensions is None:
        extensions = [".jpg", ".png", ".pdf", ".json", ".txt", ".xml"]

    for ext in extensions:
        try:
            # Security: subprocess used only with hardcoded commands, no user input
            result = subprocess.run(  # nosec B603, B607
                ["find", str(dataset_path), "-type", "f", "-name", f"*{ext}"],
                capture_output=True,
                text=True,
            )
            count = len([line for line in result.stdout.strip().split("\n") if line])
            if count > 0:
                counts[ext] = count
        except Exception as exc:
            print(f"Warning: failed counting *{ext} files in {dataset_path}: {exc}")

    # Total files
    try:
        # Security: subprocess used only with hardcoded commands, no user input
        result = subprocess.run(  # nosec B603, B607
            ["find", str(dataset_path), "-type", "f"],
            capture_output=True,
            text=True,
        )
        total = len([line for line in result.stdout.strip().split("\n") if line])
        counts["total"] = total
    except Exception:
        counts["total"] = 0

    return counts


def check_gcs_status(dataset_name: str) -> tuple[bool, str]:
    """Check if dataset exists in GCS."""
    gcs_path = f"{GCS_BUCKET}/{dataset_name}/"

    try:
        env = {"GOOGLE_APPLICATION_CREDENTIALS": str(GCS_CREDENTIALS)}
        # Security: subprocess used only with gsutil for GCS operations, no user input
        result = subprocess.run(  # nosec B603, B607
            ["gsutil", "ls", "-d", gcs_path],
            capture_output=True,
            text=True,
            env={**subprocess.os.environ, **env},
        )
        exists = result.returncode == 0

        if exists:
            # Get size from GCS
            # Security: subprocess used only with gsutil for GCS operations, no user input
            result = subprocess.run(  # nosec B603, B607
                ["gsutil", "du", "-sh", gcs_path],
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env},
            )
            size = result.stdout.split()[0] if result.returncode == 0 else "Unknown"
            return True, size
        return False, "Not uploaded"
    except Exception:
        return False, "Unknown"


def main():
    print("=" * 80)
    print("Dataset Status Report")
    print("=" * 80)
    print()

    # Scan benchmarks
    benchmarks_dir = NFS_ROOT / "benchmarks"
    datasets = {}

    if benchmarks_dir.exists():
        for dataset_path in sorted(benchmarks_dir.iterdir()):
            if dataset_path.is_dir():
                dataset_name = dataset_path.name
                print(f"Scanning {dataset_name}...")

                size_human, size_bytes = get_dataset_size(dataset_path)
                file_counts = count_files(dataset_path)
                gcs_exists, gcs_size = check_gcs_status(dataset_name)

                datasets[dataset_name] = {
                    "path": str(dataset_path),
                    "size_human": size_human,
                    "size_bytes": size_bytes,
                    "file_counts": file_counts,
                    "gcs_exists": gcs_exists,
                    "gcs_size": gcs_size,
                }

    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()

    print(f"{'Dataset':<20} {'Size':<15} {'Files':<10} {'GCS Status':<20}")
    print("-" * 80)

    total_size_bytes = 0
    total_files = 0

    for name in sorted(datasets.keys()):
        data = datasets[name]
        size = data["size_human"]
        files = data["file_counts"].get("total", 0)
        gcs_status = (
            f"✅ {data['gcs_size']}" if data["gcs_exists"] else "❌ Not uploaded"
        )

        print(f"{name:<20} {size:<15} {files:<10} {gcs_status:<20}")

        total_size_bytes += data["size_bytes"]
        total_files += files

    print("-" * 80)

    # Convert total size
    total_size = total_size_bytes
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if total_size < 1024:
            total_size_human = f"{total_size:.1f} {unit}"
            break
        total_size /= 1024

    print(f"{'TOTAL':<20} {total_size_human:<15} {total_files:<10}")
    print()

    # Save JSON report to system temp directory
    temp_dir = Path(tempfile.gettempdir())
    output_file = temp_dir / "dataset_status_report.json"
    with open(output_file, "w") as f:
        json.dump(datasets, f, indent=2)

    print(f"📊 Full report saved to: {output_file}")
    print()

    return datasets


if __name__ == "__main__":
    main()
