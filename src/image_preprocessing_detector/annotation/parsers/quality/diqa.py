"""Parser for DIQA-5000 quality assessment dataset.

DIQA-5000 provides 3-dimension quality scores (overall, sharpness, color_fidelity)
from CSV files organized in train/val/test splits. Each CSV contains restored/original
image pairs with Mean Opinion Score (MOS) values on a 1-5 scale (higher is better).

Dataset Structure:
    DIQA-5000/
        train/
            train.csv
            ori/           (original images - real scanned documents)
            res/           (restored images - synthetically degraded versions)
        val/
            val.csv
            ori/
            res/
        test/
            test.csv
            ori/
            res/

Image Origin Tracking (from DocIQ paper arXiv:2509.17012):
    - Base: Born-digital PDFs printed at 300 DPI
    - ori/ folder: Camera-captured (mobile phone) with real distortions
                   (shadow, blur, creases, moiré, occlusion)
                   capture_method: camera_smartphone
    - res/ folder: Synthetically enhanced versions (dewarp, demoiré, deblur,
                   deshadow, appearance enhancement applied)
                   capture_method: synthetic

    The parser detects which folder the image comes from and stores:
    - is_synthetic_degradation: True for res/, False for ori/
    - capture_method: "camera_smartphone" for ori/, "synthetic" for res/
    - base_document_origin: "born_digital" (PDFs printed then photographed)
    - distortion_source: "real_world" for ori/, "algorithmic_enhancement" for res/
    - paired_image: Reference to the corresponding ori/res image

CSV Format:
    - res: restored/enhanced image filename
    - ori: original image filename
    - overall: overall quality MOS (1-5 scale, higher is better)
    - sharpness: sharpness quality MOS (1-5 scale)
    - color_fidelity: color fidelity MOS (1-5 scale)

Example:
    >>> parser = DIQAParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/diqa-5000"),
    ...     image_path=Path("/data/diqa-5000/train/ori/img001.jpg"),
    ...     config={},
    ... )
    >>> print(labels.diqa_overall)
    4.2
    >>> print(labels.raw_labels["is_synthetic_degradation"])
    False
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "diqa-5000"
__l4_workstream__ = "WS3"
__l4_task__ = "quality"
__l4_l2_file__ = "diqa_metadata.json"
__l4_integrate__ = "scripts/integrate_diqa_enrichments.py"


import csv
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class DIQAParser(BaseParser):
    """Parser for DIQA-5000 quality assessment dataset.

    Extracts 3-dimension MOS scores (overall, sharpness, color_fidelity)
    from CSV files in train/val/test splits. Maintains backward compatibility
    by setting both diqa_overall and diqa_mos to the same value.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["diqa-5000"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse DIQA labels from CSV files.

        Detects whether image is from ori/ (original) or res/ (synthetic degradation)
        folder and stores appropriate metadata for layer 2 enrichment.

        Args:
            dataset_path (Path): Root path of the DIQA-5000 dataset.
            image_path (Path): Absolute path to the image file being processed.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with diqa_overall, diqa_sharpness,
                diqa_color_fidelity, diqa_mos, diqa_original_image; and raw_labels
                with is_synthetic_degradation, base_capture_method, paired_image.
                Returns empty OriginalLabels if parsing fails.
        """
        labels = OriginalLabels()

        # Determine which split based on image path
        image_name = image_path.name
        image_path_str = str(image_path)
        split = None
        for s in ["train", "val", "test"]:
            if f"/{s}/" in image_path_str:
                split = s
                break

        # Detect if image is from ori/ (original) or res/ (restored/synthetic)
        is_from_ori = "/ori/" in image_path_str
        is_from_res = "/res/" in image_path_str

        # Determine which CSV column to match against
        match_column = "ori" if is_from_ori else "res"
        paired_column = "res" if is_from_ori else "ori"

        # Initialize raw_labels with origin tracking
        # Per DocIQ paper (arXiv:2509.17012):
        # - ori/: Camera-captured (mobile phone) with real distortions
        # - res/: Synthetically enhanced versions of ori/ images
        if is_from_ori:
            image_folder: str | None = "ori"
        elif is_from_res:
            image_folder = "res"
        else:
            image_folder = None
        labels.raw_labels = {
            "is_synthetic_degradation": is_from_res,
            "capture_method": "camera_smartphone" if is_from_ori else "synthetic",
            "base_document_origin": "born_digital",  # PDFs printed then photographed
            "image_folder": image_folder,
            "paired_image": None,  # Will be populated if found in CSV
            "distortion_source": "real_world"
            if is_from_ori
            else "algorithmic_enhancement",
        }

        # Try to find and parse the appropriate CSV file
        csv_files = ["train/train.csv", "val/val.csv", "test/test.csv"]
        if split:
            # Prioritize the matching split
            csv_files = [f"{split}/{split}.csv"] + [
                f for f in csv_files if split not in f
            ]

        for csv_file in csv_files:
            csv_path = dataset_path / csv_file
            if csv_path.exists():
                try:
                    with open(csv_path, newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Match by appropriate column based on folder
                            if row.get(match_column) == image_name:
                                # 3-dimension quality scores
                                if "overall" in row:
                                    labels.diqa_overall = float(row["overall"])
                                    labels.diqa_mos = float(
                                        row["overall"]
                                    )  # Backward compat
                                if "sharpness" in row:
                                    labels.diqa_sharpness = float(row["sharpness"])
                                if "color_fidelity" in row:
                                    labels.diqa_color_fidelity = float(
                                        row["color_fidelity"]
                                    )

                                # Store paired image reference
                                paired_image = row.get(paired_column)
                                if paired_image:
                                    labels.diqa_original_image = row.get("ori")
                                    labels.raw_labels["paired_image"] = paired_image

                                return labels  # Found match, return early
                except Exception as e:
                    logger.debug(f"Failed to parse DIQA labels from {csv_path}: {e}")

        return labels


__all__ = ["DIQAParser"]
