# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Doc3D synthetic document dewarping dataset.

Doc3D provides 102,064 synthetically rendered document images produced via
BlenderProc 3D mesh rendering.  Real document textures are projected onto
curved/folded mesh models and rendered under diverse lighting conditions,
creating paired (distorted, flat) training data for dewarping models.

Dataset Structure:
    doc3d/
        data/
            doc3d/
                img/
                    1/        # warp-condition bucket (1-22)
                        {docID}_{viewID}-{warpType}_Page_{pageID}-{docCode}.png
                    2/
                    ...
                    22/

Filename Pattern:
    ``{docID}_{viewID}-{warpType}_Page_{pageID}-{docCode}.png``

    - docID:    numeric document identifier (e.g. ``1000``)
    - viewID:   render viewpoint index (e.g. ``4``)
    - warpType: render mode — ``pp`` plain photo, ``tc`` color checker,
                ``pr`` projected rainbow stripes
    - pageID:   source page number within the document (e.g. ``847``)
    - docCode:  document class code + frame index (e.g. ``Pwi0001``)

Capture Method:
    HARD-CODED as ``synthetic`` — BlenderProc 3D rendering is *NOT* camera
    capture even though textures originate from real photographs.  The dataset
    root directory is named ``camera_captured/`` for historical reasons; that
    directory label MUST NOT override the correct synthetic classification.

Warp Type Codes:
    pp  — plain photo   : clean synthetic render, primary training images
    tc  — color checker : includes calibration target, use for colour normalisation
    pr  — projected rainbow : rainbow stripe projection, used for shape estimation

Primary Training Use:
    warping_reg head (SIG-G5-3) — regression target for warp severity estimation.
    pp images are the primary source; tc/pr provide geometric diversity.

License: Research use only (see dataset README). Not for commercial use.

Example:
    >>> parser = Doc3DParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../doc3d"),
    ...     image_path=Path(
    ...         "/mnt/e/.../doc3d/data/doc3d/img/1/1000_4-pp_Page_847-Pwi0001.png"
    ...     ),
    ...     config={},
    ... )
    >>> labels.raw_labels["warp_type"]
    'pp'
    >>> labels.raw_labels["capture_method"]
    'synthetic'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "doc3d"
__l4_workstream__ = "WS5c"
__l4_task__ = "correction"
__l4_l2_file__ = "doc3d_metadata.json"
__l4_integrate__ = "scripts/integrate_doc3d_enrichments.py"


import re
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

# Regex for Doc3D filename: {docID}_{viewID}-{warpType}_Page_{pageID}-{docCode}.ext
# Some filenames have an additional leading N_ prefix: N_{docID}_{viewID}-{warpType}_...
_FILENAME_RE = re.compile(
    r"^(?:\d+_)?(?P<doc_id>\d+)_(?P<view_id>\d+)-(?P<warp_type>pp|tc|pr)"
    r"_Page_(?P<page_id>\d+)-(?P<doc_code>[A-Za-z0-9]+)$"
)

# Human-readable warp type descriptions
_WARP_TYPE_LABELS: dict[str, str] = {
    "pp": "plain_photo",
    "tc": "color_checker",
    "pr": "projected_rainbow",
}

# Primary warp types suitable for warping_reg training
_PRIMARY_WARP_TYPES: frozenset[str] = frozenset({"pp"})


class Doc3DParser(BaseParser):
    """Parser for Doc3D synthetic document dewarping dataset.

    Extracts document ID, view index, warp type, page ID, and document class
    from the structured filename.  ``capture_method`` is always ``synthetic``
    regardless of parent directory name.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["doc3d"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Doc3D labels from filename pattern.

        Args:
            dataset_path: Root path of the Doc3D dataset.
            image_path: Absolute path to the image file being processed.
            config: Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels with synthetic dewarping metadata in raw_labels.
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Hard-coded: BlenderProc rendering is synthetic regardless of dir name
        labels.raw_labels["capture_method"] = "synthetic"
        labels.raw_labels["correction_task"] = "dewarping"
        labels.raw_labels["is_synthetic"] = True

        # Warp condition bucket: numbered subdirectory under img/ (1-22)
        bucket_dir = image_path.parent
        bucket_name = bucket_dir.name
        if bucket_name.isdigit():
            labels.raw_labels["warp_bucket"] = int(bucket_name)

        # Parse structured filename
        stem = image_path.stem
        match = _FILENAME_RE.match(stem)
        if match:
            warp_type = match.group("warp_type")
            labels.raw_labels["doc_id"] = int(match.group("doc_id"))
            labels.raw_labels["view_id"] = int(match.group("view_id"))
            labels.raw_labels["warp_type"] = warp_type
            labels.raw_labels["warp_type_label"] = _WARP_TYPE_LABELS.get(
                warp_type, warp_type
            )
            labels.raw_labels["page_id"] = int(match.group("page_id"))
            labels.raw_labels["doc_code"] = match.group("doc_code")
            labels.raw_labels["is_primary_warp_type"] = warp_type in _PRIMARY_WARP_TYPES
        else:
            # Unrecognised filename — still mark as synthetic dewarping
            labels.raw_labels["warp_type"] = "unknown"
            labels.raw_labels["warp_type_label"] = "unknown"
            labels.raw_labels["is_primary_warp_type"] = False

        labels.raw_labels["base_filename"] = stem

        return labels


__all__ = ["Doc3DParser"]
