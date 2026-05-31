"""Parser for Kleister Charity dataset.

British charity annual report PDFs rendered to page images.
3,414 documents (1,729 train / 440 dev / 609 test) containing mixed
typed and handwritten content in financial/administrative context.

Dataset Structure (after rendering):
    kleister-charity/
        rendered_images/
            train/
                {md5}_p{page:03d}.png
            dev-0/
                {md5}_p{page:03d}.png
            test-A/
                {md5}_p{page:03d}.png

Labels:
    - Per-document: charity_name, charity_number, address, income,
      spending, report_date (from expected.tsv)
    - Per-image: split, doc_id, page_num (from filename)

Reference:
    - GitHub: https://github.com/applicaai/kleister-charity
    - License: MIT (code), Public domain implied for gov.uk data

Example:
    >>> parser = KleisterCharityParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/kleister-charity"),
    ...     image_path=Path(
    ...         "/data/kleister-charity/rendered_images/train/"
    ...         "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4_p001.png"
    ...     ),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["doc_id"])
    "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "kleister-charity"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "kleister_charity_metadata.json"
__l4_integrate__ = "scripts/render_kleister_charity_pdfs.py"

import json
import logging
import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class KleisterCharityParser(BaseParser):
    """Parser for Kleister Charity rendered page images.

    Extracts split membership, document ID, and page number from the
    rendered image filename.  Optionally loads per-document labels from
    JSON sidecar files produced by the rendering script.
    """

    # Filename pattern: {md5}_p{page:03d}.png
    FILENAME_PATTERN = re.compile(
        r"^(?P<doc_id>[a-f0-9]{32})_p(?P<page>\d{3})\.png$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._labels_cache: dict[str, dict[str, Any]] = {}

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["kleister-charity", "kleister_charity"]

    def _load_sidecar_labels(
        self, dataset_path: Path, split: str, doc_id: str
    ) -> dict[str, Any]:
        """Load per-document labels from JSON sidecar file.

        Args:
            dataset_path (Path): Root path of the dataset
            split (str): Split name (train, dev-0, test-A)
            doc_id (str): MD5 document identifier

        Returns:
            dict[str, Any]: Dict of label key->value, empty dict if sidecar not found
        """
        cache_key = f"{split}/{doc_id}"
        if cache_key in self._labels_cache:
            return self._labels_cache[cache_key]

        sidecar_path = (
            dataset_path / "rendered_images" / split / f"{doc_id}_labels.json"
        )
        if sidecar_path.exists():
            try:
                with open(sidecar_path, encoding="utf-8") as f:
                    data = json.load(f)
                labels: dict[str, Any] = data.get("labels", {})
                self._labels_cache[cache_key] = labels
                return labels
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not load sidecar %s: %s", sidecar_path, exc)

        self._labels_cache[cache_key] = {}
        return {}

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse labels from rendered page image filename.

        Args:
            dataset_path (Path): Root path of the Kleister Charity dataset
            image_path (Path): Absolute path to the rendered page image
            config (dict[str, Any]): Dataset configuration dictionary

        Returns:
            OriginalLabels: OriginalLabels with document metadata in raw_labels
        """
        labels = OriginalLabels()
        labels.language_code = "en"
        labels.script_name = "Latin"
        labels.iso15924_script_code = "Latn"

        if labels.raw_labels is None:
            labels.raw_labels = {}
        labels.raw_labels["dataset"] = "kleister-charity"

        # Parse filename
        match = self.FILENAME_PATTERN.match(image_path.name)
        if match:
            doc_id = match.group("doc_id")
            page_num = int(match.group("page"))
            labels.raw_labels["doc_id"] = doc_id
            labels.raw_labels["page_num"] = page_num
        else:
            logger.warning(
                "Could not parse Kleister Charity filename: %s", image_path.name
            )
            labels.raw_labels["parse_error"] = (
                f"Invalid filename format: {image_path.name}"
            )
            return labels

        # Determine split from path
        for split_name in ("train", "dev-0", "test-A"):
            if split_name in image_path.parts:
                labels.raw_labels["split"] = split_name
                break

        # Try loading sidecar labels
        split = labels.raw_labels.get("split")
        if split is None:
            logger.warning(
                "Could not determine split for %s; skipping sidecar labels",
                image_path.name,
            )
            labels.raw_labels["document_type"] = "charity_annual_report"
            return labels
        sidecar = self._load_sidecar_labels(dataset_path, split, doc_id)
        if sidecar:
            labels.raw_labels["charity_name"] = sidecar.get("charity_name")
            labels.raw_labels["charity_number"] = sidecar.get("charity_number")
            labels.raw_labels["report_date"] = sidecar.get("report_date")
            # Financial fields (preserve valid zero values)
            income = sidecar.get("income_annually_in_british_pounds")
            spending = sidecar.get("spending_annually_in_british_pounds")
            if income is not None:
                labels.raw_labels["annual_income_gbp"] = income
            if spending is not None:
                labels.raw_labels["annual_spending_gbp"] = spending
            # Address fields
            post_town = sidecar.get("address__post_town")
            postcode = sidecar.get("address__postcode")
            if post_town:
                labels.raw_labels["post_town"] = post_town
            if postcode:
                labels.raw_labels["postcode"] = postcode

        labels.raw_labels["document_type"] = "charity_annual_report"

        return labels

    def supports_batch(self) -> bool:
        """Kleister Charity supports batch parsing with cached sidecars."""
        return True


__all__ = ["KleisterCharityParser"]
