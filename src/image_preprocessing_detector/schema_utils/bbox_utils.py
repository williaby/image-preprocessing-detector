"""Bounding Box Utilities for Schema Standardization.

This module provides utilities for converting between different bounding box
formats and standardizing to COCO format [x, y, width, height].

Supported Formats:
- COCO (xywh): [x, y, width, height] - top-left corner + dimensions
- XYXY: [x1, y1, x2, y2] - top-left and bottom-right corners
- YOLO Normalized: [cx, cy, w, h] - center point + dimensions (0-1 normalized)

The standard format for all Project A metadata is COCO [x, y, width, height].

References:
- Layer 2 Schema: docs/schema/layer2_enrichment.schema.json
- Output Schema: docs/schema/document_metadata.schema.json
- COCO Format: https://cocodataset.org/#format-data
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

# Type aliases for clarity (requires Python 3.10+, not 3.12+ type keyword)
COCOBox: TypeAlias = tuple[float, float, float, float]  # noqa: UP040
XYXYBox: TypeAlias = tuple[float, float, float, float]  # noqa: UP040
YOLOBox: TypeAlias = tuple[float, float, float, float]  # noqa: UP040


class BBoxFormat(str, Enum):
    """Supported bounding box formats."""

    COCO_XYWH = "coco_xywh"  # [x, y, width, height] - PROJECT STANDARD
    XYXY = "xyxy"  # [x1, y1, x2, y2]
    YOLO_NORMALIZED = "yolo_normalized"  # [cx, cy, w, h] normalized 0-1


@dataclass(frozen=True)
class BoundingBox:
    """Immutable bounding box with format tracking.

    All internal storage uses COCO format [x, y, width, height].
    Original format is preserved for audit purposes.
    """

    x: float
    y: float
    width: float
    height: float
    source_format: BBoxFormat = BBoxFormat.COCO_XYWH
    original_values: tuple[float, float, float, float] | None = None

    @classmethod
    def from_coco(
        cls,
        bbox: list[float] | tuple[float, ...],
    ) -> BoundingBox:
        """Create from COCO format [x, y, width, height]."""
        if len(bbox) != 4:
            raise ValueError(f"Expected 4 values, got {len(bbox)}")

        x, y, w, h = bbox
        return cls(
            x=float(x),
            y=float(y),
            width=float(w),
            height=float(h),
            source_format=BBoxFormat.COCO_XYWH,
            original_values=(
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            ),
        )

    @classmethod
    def from_xyxy(
        cls,
        bbox: list[float] | tuple[float, ...],
    ) -> BoundingBox:
        """Create from XYXY format [x1, y1, x2, y2]."""
        if len(bbox) != 4:
            raise ValueError(f"Expected 4 values, got {len(bbox)}")

        x1, y1, x2, y2 = bbox

        # Ensure x1 < x2 and y1 < y2
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        return cls(
            x=float(x1),
            y=float(y1),
            width=float(x2 - x1),
            height=float(y2 - y1),
            source_format=BBoxFormat.XYXY,
            original_values=(
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            ),
        )

    @classmethod
    def from_yolo_normalized(
        cls,
        bbox: list[float] | tuple[float, ...],
        image_width: int,
        image_height: int,
    ) -> BoundingBox:
        """Create from YOLO normalized format [cx, cy, w, h].

        YOLO format uses center point and dimensions, all normalized to 0-1.

        Args:
            bbox (list[float] | tuple[float, ...]): [center_x, center_y, width, height] normalized 0-1
            image_width (int): Image width in pixels for denormalization
            image_height (int): Image height in pixels for denormalization"""
        if len(bbox) != 4:
            raise ValueError(f"Expected 4 values, got {len(bbox)}")

        cx_norm, cy_norm, w_norm, h_norm = bbox

        # Validate normalized values
        for val in bbox:
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"YOLO values must be 0-1, got {val}")

        # Denormalize
        cx = cx_norm * image_width
        cy = cy_norm * image_height
        w = w_norm * image_width
        h = h_norm * image_height

        # Convert center to top-left
        x = cx - w / 2
        y = cy - h / 2

        return cls(
            x=float(x),
            y=float(y),
            width=float(w),
            height=float(h),
            source_format=BBoxFormat.YOLO_NORMALIZED,
            original_values=(
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            ),
        )

    def to_coco(self) -> list[float]:
        """Export as COCO format [x, y, width, height]."""
        return [self.x, self.y, self.width, self.height]

    def to_xyxy(self) -> list[float]:
        """Export as XYXY format [x1, y1, x2, y2]."""
        return [self.x, self.y, self.x + self.width, self.y + self.height]

    def to_yolo_normalized(
        self,
        image_width: int,
        image_height: int,
    ) -> list[float]:
        """Export as YOLO normalized format [cx, cy, w, h]."""
        cx = (self.x + self.width / 2) / image_width
        cy = (self.y + self.height / 2) / image_height
        w = self.width / image_width
        h = self.height / image_height
        return [cx, cy, w, h]

    @property
    def area(self) -> float:
        """Calculate bounding box area."""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """Get center point (cx, cy)."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def aspect_ratio(self) -> float:
        """Get aspect ratio (width / height)."""
        if self.height == 0:
            return 0.0
        return self.width / self.height

    def iou(self, other: BoundingBox) -> float:
        """Calculate Intersection over Union with another bbox."""
        # Calculate intersection
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection

        if union == 0:
            return 0.0

        return intersection / union

    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside bbox."""
        return (
            self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
        )

    def to_dict(self) -> dict:
        """Export as dictionary for JSON serialization."""
        result = {
            "bbox": self.to_coco(),
            "bbox_source_format": self.source_format.value,
            "area": self.area,
        }
        if self.original_values and self.source_format != BBoxFormat.COCO_XYWH:
            result["bbox_original"] = list(self.original_values)
        return result


def convert_bbox(
    bbox: list[float] | tuple[float, ...],
    from_format: BBoxFormat | str,
    to_format: BBoxFormat | str,
    image_width: int | None = None,
    image_height: int | None = None,
) -> list[float]:
    """Convert between bbox formats.

    Args:
        bbox (list[float] | tuple[float, ...]): Input bounding box (4 values)
        from_format (BBoxFormat | str): Source format
        to_format (BBoxFormat | str): Target format
        image_width (int | None): Required for YOLO conversion
        image_height (int | None): Required for YOLO conversion

    Returns:
        list[float]: Converted bounding box as list

    Example:
        >>> convert_bbox([100, 200, 300, 250], "xyxy", "coco_xywh")
        [100, 200, 200, 50]
    """
    # Normalize format strings
    if isinstance(from_format, str):
        from_format = BBoxFormat(from_format)
    if isinstance(to_format, str):
        to_format = BBoxFormat(to_format)

    # Create BoundingBox from source format
    if from_format == BBoxFormat.COCO_XYWH:
        bb = BoundingBox.from_coco(bbox)
    elif from_format == BBoxFormat.XYXY:
        bb = BoundingBox.from_xyxy(bbox)
    elif from_format == BBoxFormat.YOLO_NORMALIZED:
        if image_width is None or image_height is None:
            raise ValueError("YOLO conversion requires image dimensions")
        bb = BoundingBox.from_yolo_normalized(bbox, image_width, image_height)
    else:
        raise ValueError(f"Unknown source format: {from_format}")

    # Export to target format
    if to_format == BBoxFormat.COCO_XYWH:
        return bb.to_coco()
    if to_format == BBoxFormat.XYXY:
        return bb.to_xyxy()
    if to_format == BBoxFormat.YOLO_NORMALIZED:
        if image_width is None or image_height is None:
            raise ValueError("YOLO conversion requires image dimensions")
        return bb.to_yolo_normalized(image_width, image_height)
    raise ValueError(f"Unknown target format: {to_format}")


def standardize_layout_detection(
    detection: dict,
    source_format: BBoxFormat | str | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
) -> dict:
    """Standardize a layout detection dict to COCO bbox format.

    Automatically detects source format if not provided:
    - YOLO detections have normalized values (all 0-1)
    - COCO annotations have xywh where w,h are smaller than x,y typically
    - XYXY has x2 > x1 and y2 > y1 with larger absolute values

    Args:
        detection (dict): Layout detection dict with 'bbox' key
        source_format (BBoxFormat | str | None): Optional explicit source format
        image_width (int | None): Image width (required for YOLO)
        image_height (int | None): Image height (required for YOLO)

    Returns:
        dict: Detection dict with standardized COCO bbox"""
    if "bbox" not in detection:
        raise ValueError("Detection must have 'bbox' key")

    bbox = detection["bbox"]

    # Auto-detect format if not specified
    if source_format is None:
        source_format = _detect_bbox_format(bbox)

    if isinstance(source_format, str):
        source_format = BBoxFormat(source_format)

    # Create BoundingBox and standardize
    if source_format == BBoxFormat.COCO_XYWH:
        bb = BoundingBox.from_coco(bbox)
    elif source_format == BBoxFormat.XYXY:
        bb = BoundingBox.from_xyxy(bbox)
    elif source_format == BBoxFormat.YOLO_NORMALIZED:
        if image_width is None or image_height is None:
            raise ValueError("YOLO format requires image dimensions")
        bb = BoundingBox.from_yolo_normalized(bbox, image_width, image_height)
    else:
        raise ValueError(f"Unknown format: {source_format}")

    # Build standardized detection
    result = detection.copy()
    result.update(bb.to_dict())

    return result


def _detect_bbox_format(bbox: list[float] | tuple[float, ...]) -> BBoxFormat:
    """Auto-detect bbox format from values.

    Heuristics:
    - All values 0-1: YOLO normalized
    - values[2] > values[0] and values[3] > values[1]: XYXY
    - Otherwise: COCO (default)
    """
    if len(bbox) != 4:
        raise ValueError(f"Expected 4 values, got {len(bbox)}")

    x1, y1, x2, y2 = bbox

    # Check for YOLO normalized (all values 0-1)
    if all(0.0 <= v <= 1.0 for v in bbox):
        return BBoxFormat.YOLO_NORMALIZED

    # Check for XYXY (x2 > x1, y2 > y1)
    # XYXY typically has x2, y2 as absolute coordinates > x1, y1
    if x2 > x1 and y2 > y1 and x2 > 10 and y2 > 10:
        # Additional check: in XYXY, x2-x1 and y2-y1 should be reasonable
        # In COCO, x2 and y2 ARE width and height
        width_ratio = x2 / max(x1, 1)
        height_ratio = y2 / max(y1, 1)

        # If x2/x1 and y2/y1 are close to 1, it's likely XYXY
        # If x2 is much smaller relative to x1, it's likely COCO
        if width_ratio < 3 and height_ratio < 3:
            return BBoxFormat.XYXY

    # Default to COCO
    return BBoxFormat.COCO_XYWH


def batch_standardize_detections(
    detections: list[dict],
    source: str,
    image_width: int | None = None,
    image_height: int | None = None,
) -> list[dict]:
    """Batch standardize layout detections based on source.

    Args:
        detections (list[dict]): List of detection dicts
        source (str): Detection source identifier
        image_width (int | None): Image width for YOLO
        image_height (int | None): Image height for YOLO

    Returns:
        list[dict]: List of standardized detections"""
    # Determine format based on source
    source_format_map: dict[str, BBoxFormat] = {
        "doclayout_yolo": BBoxFormat.XYXY,  # YOLO outputs xyxy
        "coco_annotation": BBoxFormat.COCO_XYWH,
        "tablebank": BBoxFormat.COCO_XYWH,
        "doclaynet": BBoxFormat.COCO_XYWH,
        "funsd": BBoxFormat.COCO_XYWH,
    }

    source_format = source_format_map.get(source.lower())

    return [
        standardize_layout_detection(
            d,
            source_format=source_format,
            image_width=image_width,
            image_height=image_height,
        )
        for d in detections
    ]
