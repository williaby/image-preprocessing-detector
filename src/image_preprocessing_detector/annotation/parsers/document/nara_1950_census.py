"""Parser for NARA 1950 Census dataset.

Scanned enumeration schedules from the 1950 U.S. Population Census.
Each page is a handwritten census form containing tabular data with
names, addresses, demographics, and employment information.

Dataset Structure:
    nara-1950-census/
        {StateName}/
            {census_id}-{StateName}-{serial}/
                {census_id}-{StateName}-{serial}-{page:04d}.jpg

Labels:
    - Per-image: state_name, census_id, serial_number, page_num (from filename)
    - Content type: handwritten census forms (tabular)

Reference:
    - S3 Bucket: s3://nara-1950-census/ (public, no auth)
    - License: Public Domain (U.S. Government work)
    - Agency: National Archives and Records Administration

Example:
    >>> parser = Nara1950CensusParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/nara-1950-census"),
    ...     image_path=Path(
    ...         "/data/nara-1950-census/Alabama/43290879-Alabama-005563/43290879-Alabama-005563-0001.jpg"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["state_name"])
    "Alabama"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "nara-1950-census"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "nara_1950_census_metadata.json"
__l4_integrate__ = "scripts/sample_nara_1950_census.py"

import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class Nara1950CensusParser(BaseParser):
    """Parser for NARA 1950 Census scanned enumeration schedules.

    Extracts state, census ID, serial number, and page number from
    the image filename. Directory structure provides state grouping.
    """

    def __init__(self) -> None:
        super().__init__()

    # Filename pattern: {census_id}-{StateName}-{serial}-{page:04d}.jpg
    # e.g., 43290879-Alabama-005563-0001.jpg
    FILENAME_PATTERN = re.compile(
        r"^(?P<census_id>\d+)-(?P<state_name>[A-Za-z_]+)-"
        r"(?P<serial>\d+)-(?P<page>\d{4})\.jpg$",
    )

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["nara-1950-census", "nara_1950_census"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels from NARA census image filename.

        Args:
            dataset_path (Path): Root path of the NARA 1950 Census dataset.
            image_path (Path): Absolute path to the census page image.
            config (dict[str, Any]): Dataset configuration dictionary.

        Returns:
            OriginalLabels: OriginalLabels with census metadata in raw_labels.
        """
        labels = OriginalLabels()
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.iso15924_script_code = "Latn"

        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["dataset"] = "nara-1950-census"

        # Parse filename
        match = self.FILENAME_PATTERN.match(image_path.name)
        if match:
            labels.raw_labels["census_id"] = match.group("census_id")
            labels.raw_labels["state_name"] = match.group("state_name")
            labels.raw_labels["serial_number"] = match.group("serial")
            labels.raw_labels["page_num"] = int(match.group("page"))
        else:
            logger.warning("Could not parse NARA Census filename: %s", image_path.name)
            labels.raw_labels["parse_error"] = (
                f"Invalid filename format: {image_path.name}"
            )
            return labels

        labels.raw_labels["document_type"] = "census_enumeration_schedule"
        labels.raw_labels["content_type"] = "handwritten_form"

        return labels

    def supports_batch(self) -> bool:
        """NARA Census supports batch parsing."""
        return True


__all__ = ["Nara1950CensusParser"]
