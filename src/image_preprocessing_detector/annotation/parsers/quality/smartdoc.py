# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for SmartDoc-QA quality assessment dataset.

SmartDoc-QA evaluates camera-captured document quality through filename encoding
and OCR accuracy measurements. The dataset captures documents under various
conditions (lighting, rotation, blur) with different phone models.

Dataset Structure:
    SmartDoc-QA/
        Captured_Images/
            {phone_model}/
                Images/
                    {S|M}_Img_{Android|WP}_D{doc}_L{light}_r{rot}_a{angle}_b{blur}[_Mb#|_Ob#].jpg
                OCR_Accuracy_Finereader/
                    {filename}.cacc.txt    (character accuracy)
                    {filename}.wacc.txt    (word accuracy)

Filename Format:
    {S|M}_Img_{Android|WP}_D{doc}_L{light}_r{rot}_a{angle}_b{blur}[_Mb#|_Ob#].jpg
    Where:
        - S/M: Phone model identifier
        - Android/WP: Operating system (Android or Windows Phone)
        - D{1-30}: Document number
        - L{1-2}: Lighting condition (1=normal, 2=challenging)
        - r{angle}: Rotation angle in degrees
        - a{angle}: Viewing angle
        - b{blur}: Blur level (-5 to 5, negative = blur, positive = sharp)
        - _Mb#: Motion blur variant
        - _Ob#: Out-of-focus blur variant

OCR Accuracy Format (UNLV-ISRI):
    Lines ending with "Accuracy" contain percentage values.
    Character accuracy is converted to 1-5 MOS scale.

Example:
    >>> parser = SmartDocParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/smartdoc-qa"),
    ...     image_path=Path(
    ...         "/data/smartdoc-qa/Captured_Images/Galaxy_S4/Images/S_Img_Android_D1_L1_r0_a0_b0.jpg"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.smartdoc_mos)
    4.5
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "smartdoc-qa"
__l4_workstream__ = "WS3"
__l4_task__ = "quality"
__l4_l2_file__ = "smartdoc_qa_metadata.json"
__l4_integrate__ = "scripts/integrate_smartdoc_qa_enrichments.py"


import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class SmartDocParser(BaseParser):
    """Parser for SmartDoc-QA quality assessment dataset.

    Extracts capture parameters from filename encoding and converts
    OCR character accuracy to MOS scores (1-5 scale).
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["smartdoc-qa"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse SmartDoc labels from filename and OCR accuracy files.

        Args:
            dataset_path: Root path of the SmartDoc-QA dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with smartdoc_mos, smartdoc_capture_device,
            smartdoc_lighting, and raw_labels populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        # Extract phone/device from parent folder structure
        # Structure: Captured_Images/{phone}/Images/{filename}
        image_parts = image_path.parts
        for i, part in enumerate(image_parts):
            if part == "Images" and i > 0:
                labels.smartdoc_capture_device = image_parts[i - 1]
                break

        # Parse filename to extract capture parameters
        filename = image_path.stem  # Without extension

        # Pattern: {S|M}_Img_{Android|WP}_D{doc}_L{light}_r{rot}_a{angle}_b{blur}[_Mb#|_Ob#]
        pattern = r"^([SM])_Img_(Android|WP)_D(\d+)_L([12])_r(-?\d+)_a(-?\d+)_b(-?\d+)(?:_(Mb|Ob)(\d+))?$"
        match = re.match(pattern, filename)

        if match:
            (
                phone_id,
                os_type,
                doc_num,
                lighting,
                rotation,
                angle,
                blur,
                blur_type,
                blur_level,
            ) = match.groups()

            # Store lighting condition (1=normal, 2=challenging)
            labels.smartdoc_lighting = "normal" if lighting == "1" else "challenging"

            # Store raw capture parameters in raw_labels for reference
            labels.raw_labels = {
                "phone_id": phone_id,
                "os_type": os_type,
                "document_number": int(doc_num),
                "lighting_code": lighting,
                "rotation_degrees": int(rotation),
                "viewing_angle": int(angle),
                "blur_level": int(blur),
                "blur_type": blur_type,  # Mb=motion blur, Ob=out-of-focus blur
                "blur_variant": int(blur_level) if blur_level else None,
            }

        # Look for OCR accuracy files
        # OCR accuracy files are in: Captured_Images/{phone}/OCR_Accuracy_Finereader/{filename}.cacc.txt
        phone_folder = image_path.parent.parent  # Go up from Images/ to phone folder
        ocr_folder = phone_folder / "OCR_Accuracy_Finereader"

        # Try to find character accuracy file
        cacc_path = ocr_folder / f"{filename}.cacc.txt"
        wacc_path = ocr_folder / f"{filename}.wacc.txt"

        if cacc_path.exists():
            try:
                with open(cacc_path) as f:
                    content = f.read()
                    # Parse UNLV-ISRI format: Look for accuracy percentage
                    # Line format: "   99.56%  Accuracy"
                    acc_match = re.search(
                        r"^\s*(\d+\.\d+)%\s+Accuracy$", content, re.MULTILINE
                    )
                    if acc_match:
                        char_accuracy = float(acc_match.group(1))
                        # Convert character accuracy to 1-5 MOS scale
                        # 100% -> 5.0, 90% -> 4.0, 80% -> 3.0, 70% -> 2.0, <70% -> 1.0
                        if char_accuracy >= 99:
                            labels.smartdoc_mos = 5.0
                        elif char_accuracy >= 95:
                            labels.smartdoc_mos = 4.5
                        elif char_accuracy >= 90:
                            labels.smartdoc_mos = 4.0
                        elif char_accuracy >= 85:
                            labels.smartdoc_mos = 3.5
                        elif char_accuracy >= 80:
                            labels.smartdoc_mos = 3.0
                        elif char_accuracy >= 75:
                            labels.smartdoc_mos = 2.5
                        elif char_accuracy >= 70:
                            labels.smartdoc_mos = 2.0
                        else:
                            labels.smartdoc_mos = 1.0 + (char_accuracy / 70.0)

                        # Store raw accuracy in raw_labels
                        if labels.raw_labels is None:
                            labels.raw_labels = {}
                        labels.raw_labels["character_accuracy_percent"] = char_accuracy
            except Exception as e:
                logger.debug(
                    f"Failed to parse SmartDoc character accuracy from {cacc_path}: {e}"
                )

        if wacc_path.exists():
            try:
                with open(wacc_path) as f:
                    content = f.read()
                    # Parse UNLV-ISRI format: Look for word accuracy
                    acc_match = re.search(
                        r"^\s*(\d+\.\d+)%\s+Accuracy$", content, re.MULTILINE
                    )
                    if acc_match:
                        word_accuracy = float(acc_match.group(1))
                        if labels.raw_labels is None:
                            labels.raw_labels = {}
                        labels.raw_labels["word_accuracy_percent"] = word_accuracy
            except Exception as e:
                logger.debug(
                    f"Failed to parse SmartDoc word accuracy from {wacc_path}: {e}"
                )

        return labels


__all__ = ["SmartDocParser"]
