"""Dataset utilities for Modal applications.

Provides dataset loading functionality shared across
benchmark and training scripts.
"""

from __future__ import annotations

import csv
from pathlib import Path


def load_diqa5000_dataset(
    dataset_path: Path,
    verbose: bool = False,
) -> list[dict[str, str | dict[str, float]]]:
    """Load DIQA-5000 test samples.

    Args:
        dataset_path: Path to the extracted dataset directory.
        verbose: If True, print column information.

    Returns:
        List of sample dictionaries with sample_id, image_path, and ground_truth.
    """
    test_dir = dataset_path / "test"
    csv_path = test_dir / "test.csv"
    res_dir = test_dir / "res"

    samples: list[dict[str, str | dict[str, float]]] = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        # Print available columns on first load
        if verbose:
            print(f"CSV columns: {reader.fieldnames}")
        for row in reader:
            image_filename = row["res"]
            image_path = res_dir / image_filename

            if not image_path.exists():
                continue

            samples.append(
                {
                    "sample_id": image_filename.replace(".jpg", ""),
                    "image_path": str(image_path),
                    "ground_truth": {
                        "overall": float(row["overall"]),
                        "sharpness": float(row["sharpness"]),
                        "color": float(row["color_fidelity"]),
                    },
                }
            )

    print(f"Loaded {len(samples)} samples")
    return samples
