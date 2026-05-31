"""Parser for MIDV-2020 ID document dataset.

MIDV-2020 provides 1000 scanned images and 1000 photos of 1000 unique mock
identity documents across 10 document types from 9 countries.

Capture modes (this parser handles photo + scan; video is excluded):
  - **photo**: Smartphone camera stills (100 per doc type x 10 types = 1000 total)
  - **scan_upright**: Flatbed scanner, document upright
  - **scan_rotated**: Flatbed scanner, document rotated
  - **templates**: Reference template images

Document types and scripts::

    alb_id             Albania ID card       Latin
    aze_passport       Azerbaijan Passport   Latin
    esp_id             Spain ID card         Latin
    est_id             Estonia ID card       Latin
    fin_id             Finland ID card       Latin
    grc_passport       Greece Passport       Greek  (Ελληνικό)
    lva_passport       Latvia Passport       Latin
    rus_internalpassport Russia Internal Passport  Cyrillic
    srb_passport       Serbia Passport       Cyrillic
    svk_id             Slovakia ID card      Latin

Camera capture conditions (photo.tar image numbering):
    00-09 iPhone / 10-19 Samsung — projective distortions
    20-24 iPhone / 25-29 Samsung — text documents background
    30-34 iPhone / 35-39 Samsung — keyboard background
    40-44 iPhone / 45-49 Samsung — outdoors natural lighting
    50-54 iPhone / 55-59 Samsung — table background
    60-64 iPhone / 65-69 Samsung — highlight present
    70-79 iPhone / 80-89 Samsung — low lighting
    90-94 iPhone / 95-99 Samsung — cloth background

Annotation format (VIA — VGG Image Annotator v2):
    Each annotations/<CODE>.json file covers all 100 images for that doc type.
    Structure::

        {
          "_via_settings": {...},
          "_via_img_metadata": {
            "00.jpg<size>": {
              "filename": "00.jpg",
              "size": 123456,
              "regions": [
                {
                  "shape_attributes": {
                    "name": "polygon",
                    "all_points_x": [x0, x1, x2, x3],
                    "all_points_y": [y0, y1, y2, y3]
                  },
                  "region_attributes": {
                    "type": "document_quad"  (or field name)
                  }
                }
              ]
            }
          }
        }

License:
    Creative Commons Attribution-ShareAlike 2.5 Generic (CC BY-SA 2.5)
    Face images courtesy of Generated Photos (attribution required in derivatives).

Example::

    >>> parser = Midv2020Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/midv2020/photo"),
    ...     image_path=Path("/data/midv2020/photo/images/rus_internalpassport/05.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["doc_type_code"])
    "rus_internalpassport"
    >>> print(labels.raw_labels["capture_mode"])
    "photo"
    >>> print(labels.script_name)
    "Cyrillic"
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "midv2020"
__l4_workstream__ = "WS3"
__l4_task__ = "document"
__l4_l2_file__ = "midv2020_metadata.json"
__l4_integrate__ = "scripts/integrate_midv2020_enrichments.py"


import contextlib
import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document type metadata
# ---------------------------------------------------------------------------

# iso3166_country, iso15924_script, iso639_language, country_name
_DOC_TYPE_META: dict[str, tuple[str, str, str, str]] = {
    "alb_id": ("ALB", "Latn", "sqi", "Albania"),
    "aze_passport": ("AZE", "Latn", "aze", "Azerbaijan"),
    "esp_id": ("ESP", "Latn", "spa", "Spain"),
    "est_id": ("EST", "Latn", "est", "Estonia"),
    "fin_id": ("FIN", "Latn", "fin", "Finland"),
    "grc_passport": ("GRC", "Grek", "ell", "Greece"),
    "lva_passport": ("LVA", "Latn", "lav", "Latvia"),
    "rus_internalpassport": ("RUS", "Cyrl", "rus", "Russia"),
    "srb_passport": ("SRB", "Cyrl", "srp", "Serbia"),
    "svk_id": ("SVK", "Latn", "slk", "Slovakia"),
}

# Human-readable script names for non-Latin scripts
_SCRIPT_NAME_MAP: dict[str, str] = {
    "Cyrl": "Cyrillic",
    "Grek": "Greek",
    "Latn": "Latin",
}

# Capture mode detection from directory path fragment
_CAPTURE_MODE_MAP: dict[str, str] = {
    "photo": "photo",
    "scan_upright": "scan_upright",
    "scan_rotated": "scan_rotated",
    "templates": "template",
    "template": "template",
}

# L2 capture_method vocabulary
_CAPTURE_TO_L2: dict[str, str] = {
    "photo": "camera_smartphone",
    "scan_upright": "scanner",
    "scan_rotated": "scanner",
    "template": "scanner",  # template images are scans
}

# iPhone vs Samsung detection by image number range (photo only)
_SAMSUNG_RANGES: list[tuple[int, int]] = [
    (10, 19),
    (25, 29),
    (35, 39),
    (45, 49),
    (55, 59),
    (65, 69),
    (80, 89),
    (95, 99),
]

# Capture condition by image number (phone-agnostic lowest bound)
_CAPTURE_CONDITIONS: list[tuple[range, str]] = [
    (range(20), "projective_distortions"),
    (range(20, 30), "text_documents_background"),
    (range(30, 40), "keyboard_background"),
    (range(40, 50), "outdoors_natural_lighting"),
    (range(50, 60), "table_background"),
    (range(60, 70), "highlight_present"),
    (range(70, 90), "low_lighting"),
    (range(90, 100), "cloth_background"),
]


def _get_capture_condition(image_num: int) -> str:
    """Map image number (0-99) to its capture condition label.

    Args:
        image_num (int): Integer image number (0-99).

    Returns:
        str: Capture condition string.
    """
    for r, label in _CAPTURE_CONDITIONS:
        if image_num in r:
            return label
    return "unknown"


def _is_samsung(image_num: int) -> bool | None:
    """Return True if the image number is a Samsung capture, False for iPhone.

    Args:
        image_num (int): Integer image number (0-99).

    Returns:
        bool | None: True for Samsung, False for iPhone, None if indeterminate.
    """
    for lo, hi in _SAMSUNG_RANGES:
        if lo <= image_num <= hi:
            return True
    if (
        0 <= image_num <= 9
        or image_num in range(20, 25)
        or image_num in range(30, 35)
        or image_num in range(40, 45)
        or image_num in range(50, 55)
        or image_num in range(60, 65)
        or image_num in range(70, 80)
        or image_num in range(90, 95)
    ):
        return False
    return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class Midv2020Parser(BaseParser):
    """Parser for MIDV-2020 ID document dataset.

    Extracts:
      - doc_type_code and capture_mode from directory structure
      - country code, ISO 15924 script, and language from doc type lookup
      - Capture condition metadata for photo images
      - Document quad and field quads from VIA annotation JSON
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["midv2020"]

    # ------------------------------------------------------------------
    # Path analysis
    # ------------------------------------------------------------------

    def _analyse_path(
        self, image_path: Path
    ) -> tuple[str | None, str | None, int | None]:
        """Extract doc type code, capture mode, and image number from path.

        Expected path patterns::

            {root} / images / {doc_type_code} / {NN}.jpg  # photo / scan
            {root} / {capture_mode} / images / {doc_type_code} / {NN}.jpg

        Args:
            image_path (Path): Absolute or relative path to image file.

        Returns:
            tuple[str | None, str | None, int | None]: Tuple of (doc_type_code, capture_mode, image_number).
                Any element may be None if not determinable.
        """
        parts = list(image_path.parts)
        doc_code: str | None = None
        capture_mode: str | None = None

        # Detect doc type code — must be in _DOC_TYPE_META
        for part in parts:
            if part in _DOC_TYPE_META:
                doc_code = part
                break

        # Detect capture mode from any path segment
        for part in parts:
            lower = part.lower()
            for key, mode in _CAPTURE_MODE_MAP.items():
                if key == lower:
                    capture_mode = mode
                    break
            if capture_mode:
                break

        # Detect image number from filename stem (e.g. "05" -> 5)
        image_num: int | None = None
        with contextlib.suppress(ValueError):
            image_num = int(image_path.stem)

        return doc_code, capture_mode, image_num

    def _find_via_annotation_file(
        self, dataset_path: Path, doc_code: str
    ) -> Path | None:
        """Locate the VIA annotation JSON for a document type code.

        The annotation file covers all 100 images for the given doc type.
        Tries several layout conventions:

            {dataset_path}/annotations/{doc_code}.json
            {dataset_path}/../annotations/{doc_code}.json
            {dataset_path}/../../annotations/{doc_code}.json

        Args:
            dataset_path (Path): Root dataset path (may be the extracted tar root).
            doc_code (str): Document type code (e.g. "rus_internalpassport").

        Returns:
            Path | None: Path to annotation JSON, or None if not found.
        """
        candidates = [
            dataset_path / "annotations" / f"{doc_code}.json",
            dataset_path.parent / "annotations" / f"{doc_code}.json",
            dataset_path.parent.parent / "annotations" / f"{doc_code}.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    # ------------------------------------------------------------------
    # VIA annotation parsing
    # ------------------------------------------------------------------

    def _load_via_annotation(self, annotation_path: Path) -> dict[str, Any] | None:
        """Load VIA JSON annotation file.

        Args:
            annotation_path (Path): Path to the VIA .json file.

        Returns:
            dict[str, Any] | None: Parsed JSON dict, or None on failure.
        """
        try:
            with open(annotation_path, encoding="utf-8") as fh:
                result: dict[str, Any] = json.load(fh)
                return result
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load annotation %s: %s", annotation_path, exc)
            return None

    def _find_image_record(
        self, via_data: dict[str, Any], filename: str
    ) -> dict[str, Any] | None:
        """Find the VIA metadata record for a specific image filename.

        VIA keys images as "{filename}{size}", so we search by filename prefix.

        Args:
            via_data (dict[str, Any]): Parsed VIA JSON.
            filename (str): Bare filename to look up (e.g. "05.jpg").

        Returns:
            dict[str, Any] | None: VIA image record dict, or None if not found.
        """
        img_meta: dict[str, Any] = via_data.get("_via_img_metadata", {})
        # Exact key match or prefix match (key = filename + size)
        for record in img_meta.values():
            if isinstance(record, dict) and record.get("filename") == filename:
                return record
        return None

    def _via_region_to_coco(
        self, region: dict[str, Any], source_tag: str
    ) -> dict[str, Any] | None:
        """Convert a VIA polygon region to a COCO layout detection.

        Args:
            region (dict[str, Any]): A VIA region dict with shape_attributes and region_attributes.
            source_tag (str): Provenance tag string.

        Returns:
            dict[str, Any] | None: COCO layout detection dict, or None if the region is invalid.
        """
        shape = region.get("shape_attributes", {})
        if shape.get("name") not in ("polygon", "polyline"):
            return None

        xs = shape.get("all_points_x", [])
        ys = shape.get("all_points_y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            return None

        try:
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            coco_bbox = [
                float(x_min),
                float(y_min),
                float(x_max - x_min),
                float(y_max - y_min),
            ]
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid polygon coords in region: %s", exc)
            return None

        attrs = region.get("region_attributes", {})
        region_type = attrs.get("type", "") or attrs.get("label", "") or ""
        class_name = "Picture" if "photo" in region_type.lower() else "Text"
        if "document" in region_type.lower() or region_type == "":
            class_name = "Document"

        quad = [[xs[i], ys[i]] for i in range(len(xs))]

        return {
            "class_name": class_name,
            "bbox": coco_bbox,
            "bbox_original": quad,
            "bbox_source_format": "via_polygon",
            "confidence": 1.0,
            "source": source_tag,
            "region_type": region_type,
        }

    def _extract_detections(
        self,
        via_data: dict[str, Any],
        filename: str,
        source_tag: str,
    ) -> list[dict[str, Any]]:
        """Extract all layout detections for one image from VIA annotation.

        Args:
            via_data (dict[str, Any]): Parsed VIA JSON dict.
            filename (str): Image filename to look up (e.g. "05.jpg").
            source_tag (str): Provenance label.

        Returns:
            list[dict[str, Any]]: List of COCO layout detection dicts.
        """
        record = self._find_image_record(via_data, filename)
        if not record:
            return []

        detections = []
        for region in record.get("regions", []):
            det = self._via_region_to_coco(region, source_tag)
            if det:
                detections.append(det)
        return detections

    # ------------------------------------------------------------------
    # BaseParser interface
    # ------------------------------------------------------------------

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse MIDV-2020 labels from path structure and VIA annotation JSON.

        Args:
            dataset_path (Path): Root path of the extracted MIDV-2020 archive.
            image_path (Path): Absolute path to the image file being processed.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with raw_labels containing doc_type_code,
                country_code, capture_mode, capture_method, image_num, capture_condition,
                device_model; layout_detections as COCO bboxes; and script_name set.
        """
        labels = OriginalLabels()
        if labels.raw_labels is None:
            labels.raw_labels = {}

        doc_code, capture_mode, image_num = self._analyse_path(image_path)

        # Document type metadata
        if doc_code:
            labels.raw_labels["doc_type_code"] = doc_code
            meta = _DOC_TYPE_META.get(doc_code)
            if meta:
                country, script, lang, country_name = meta
                labels.raw_labels["country_code"] = country
                labels.raw_labels["country_name"] = country_name
                labels.raw_labels["iso15924_script"] = script
                labels.raw_labels["iso639_language"] = lang
                labels.script_name = _SCRIPT_NAME_MAP.get(script, script)

        # Capture mode
        if capture_mode:
            labels.raw_labels["capture_mode"] = capture_mode
            labels.raw_labels["capture_method"] = _CAPTURE_TO_L2.get(
                capture_mode, "scanner"
            )

        # Per-image metadata for photo captures
        if capture_mode == "photo" and image_num is not None:
            labels.raw_labels["image_num"] = image_num
            labels.raw_labels["capture_condition"] = _get_capture_condition(image_num)
            samsung = _is_samsung(image_num)
            if samsung is not None:
                labels.raw_labels["device_model"] = (
                    "Samsung Galaxy S10" if samsung else "Apple iPhone XR"
                )

        # VIA annotation (per-doc-type JSON covering all 100 images)
        if doc_code:
            ann_path = self._find_via_annotation_file(dataset_path, doc_code)
            if ann_path:
                via_data = self._load_via_annotation(ann_path)
                if via_data:
                    source_tag = f"midv2020_{capture_mode or 'unknown'}"
                    detections = self._extract_detections(
                        via_data, image_path.name, source_tag
                    )
                    if detections:
                        labels.raw_labels["layout_detections"] = detections

        return labels


__all__ = ["Midv2020Parser"]
