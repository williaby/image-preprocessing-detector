"""ISO 216 Paper Size Detection.

Provides paper size detection for scanned documents based on dimensions and DPI.
Useful for layout analysis and OCR scaling decisions.

Standards:
- ISO 216: A-series and B-series paper sizes
- ANSI: North American paper sizes (Letter, Legal, Tabloid)
- JIS P 0138: Japanese B-series (slightly different from ISO)

References:
- ISO 216: https://www.iso.org/standard/36631.html
- ANSI paper sizes: ANSI/ASME Y14.1
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict


class PaperSizeStandard(StrEnum):
    """Paper size standard/region."""

    ISO = "iso"  # International (A4, A3, etc.)
    ANSI = "ansi"  # North American (Letter, Legal)
    JIS = "jis"  # Japanese B-series
    CUSTOM = "custom"  # Non-standard size


class PaperSize(StrEnum):
    """Common paper sizes with standard names."""

    # ISO A-series (most common internationally)
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    A6 = "A6"

    # ISO B-series
    B4 = "B4"
    B5 = "B5"

    # North American (ANSI)
    LETTER = "Letter"  # 8.5 x 11 in
    LEGAL = "Legal"  # 8.5 x 14 in
    TABLOID = "Tabloid"  # 11 x 17 in (ANSI B)
    LEDGER = "Ledger"  # 17 x 11 in (Tabloid rotated)
    EXECUTIVE = "Executive"  # 7.25 x 10.5 in

    # Other common
    HALF_LETTER = "Half-Letter"  # 5.5 x 8.5 in
    STATEMENT = "Statement"  # 5.5 x 8.5 in (same as half-letter)

    # Special
    CUSTOM = "Custom"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class PaperSizeSpec:
    """Paper size specification with dimensions."""

    name: PaperSize
    standard: PaperSizeStandard
    width_mm: float
    height_mm: float
    aspect_ratio: float  # height / width

    @property
    def width_inches(self) -> float:
        """Return width in inches."""
        return self.width_mm / 25.4

    @property
    def height_inches(self) -> float:
        """Return height in inches."""
        return self.height_mm / 25.4

    def pixels_at_dpi(self, dpi: int) -> tuple[int, int]:
        """Calculate pixel dimensions at given DPI."""
        width_px = int(self.width_inches * dpi)
        height_px = int(self.height_inches * dpi)
        return (width_px, height_px)


# Standard paper size definitions
PAPER_SIZE_SPECS: dict[PaperSize, PaperSizeSpec] = {
    # ISO A-series (width x height in mm)
    PaperSize.A0: PaperSizeSpec(PaperSize.A0, PaperSizeStandard.ISO, 841, 1189, 1.414),
    PaperSize.A1: PaperSizeSpec(PaperSize.A1, PaperSizeStandard.ISO, 594, 841, 1.414),
    PaperSize.A2: PaperSizeSpec(PaperSize.A2, PaperSizeStandard.ISO, 420, 594, 1.414),
    PaperSize.A3: PaperSizeSpec(PaperSize.A3, PaperSizeStandard.ISO, 297, 420, 1.414),
    PaperSize.A4: PaperSizeSpec(PaperSize.A4, PaperSizeStandard.ISO, 210, 297, 1.414),
    PaperSize.A5: PaperSizeSpec(PaperSize.A5, PaperSizeStandard.ISO, 148, 210, 1.419),
    PaperSize.A6: PaperSizeSpec(PaperSize.A6, PaperSizeStandard.ISO, 105, 148, 1.410),
    # ISO B-series
    PaperSize.B4: PaperSizeSpec(PaperSize.B4, PaperSizeStandard.ISO, 250, 353, 1.412),
    PaperSize.B5: PaperSizeSpec(PaperSize.B5, PaperSizeStandard.ISO, 176, 250, 1.420),
    # North American (width x height in mm, converted from inches)
    PaperSize.LETTER: PaperSizeSpec(
        PaperSize.LETTER, PaperSizeStandard.ANSI, 215.9, 279.4, 1.294
    ),
    PaperSize.LEGAL: PaperSizeSpec(
        PaperSize.LEGAL, PaperSizeStandard.ANSI, 215.9, 355.6, 1.647
    ),
    PaperSize.TABLOID: PaperSizeSpec(
        PaperSize.TABLOID, PaperSizeStandard.ANSI, 279.4, 431.8, 1.545
    ),
    PaperSize.LEDGER: PaperSizeSpec(
        PaperSize.LEDGER, PaperSizeStandard.ANSI, 431.8, 279.4, 0.647
    ),
    PaperSize.EXECUTIVE: PaperSizeSpec(
        PaperSize.EXECUTIVE, PaperSizeStandard.ANSI, 184.2, 266.7, 1.448
    ),
    PaperSize.HALF_LETTER: PaperSizeSpec(
        PaperSize.HALF_LETTER, PaperSizeStandard.ANSI, 139.7, 215.9, 1.545
    ),
}


class PaperSizeInfo(TypedDict):
    """Paper size detection result for schema integration."""

    detected_size: str  # PaperSize enum value
    standard: str  # PaperSizeStandard enum value
    width_mm: float
    height_mm: float
    orientation: str  # "portrait" or "landscape"
    confidence: float  # Detection confidence
    is_exact_match: bool  # True if exact size match


def detect_paper_size(
    width_px: int,
    height_px: int,
    dpi: int = 300,
    tolerance_percent: float = 3.0,
) -> PaperSizeInfo:
    """Detect paper size from pixel dimensions and DPI.

    Args:
        width_px: Image width in pixels
        height_px: Image height in pixels
        dpi: Dots per inch (default 300)
        tolerance_percent: Allowed deviation from standard size (default 3%)

    Returns:
        PaperSizeInfo with detected size and confidence

    Example:
        >>> info = detect_paper_size(2480, 3508, dpi=300)
        >>> print(info["detected_size"])  # "A4"
        >>> print(info["orientation"])  # "portrait"
    """
    # Convert pixels to mm
    width_mm = (width_px / dpi) * 25.4
    height_mm = (height_px / dpi) * 25.4

    # Determine orientation
    if width_mm > height_mm:
        orientation = "landscape"
        # Swap for comparison (standard sizes are portrait)
        compare_width = height_mm
        compare_height = width_mm
    else:
        orientation = "portrait"
        compare_width = width_mm
        compare_height = height_mm

    best_match: PaperSize = PaperSize.UNKNOWN
    best_confidence: float = 0.0
    is_exact: bool = False

    for size, spec in PAPER_SIZE_SPECS.items():
        # Calculate deviation percentage
        width_dev = abs(compare_width - spec.width_mm) / spec.width_mm * 100
        height_dev = abs(compare_height - spec.height_mm) / spec.height_mm * 100
        max_dev = max(width_dev, height_dev)

        if max_dev <= tolerance_percent:
            confidence = 1.0 - (max_dev / tolerance_percent) * 0.5
            if confidence > best_confidence:
                best_match = size
                best_confidence = confidence
                is_exact = max_dev < 0.5  # Less than 0.5% deviation

    # If no match found, return CUSTOM with low confidence
    if best_match == PaperSize.UNKNOWN:
        best_match = PaperSize.CUSTOM
        best_confidence = 0.0

    return PaperSizeInfo(
        detected_size=best_match.value,
        standard=PAPER_SIZE_SPECS.get(
            best_match,
            PaperSizeSpec(
                PaperSize.CUSTOM,
                PaperSizeStandard.CUSTOM,
                width_mm,
                height_mm,
                height_mm / width_mm,
            ),
        ).standard.value,
        width_mm=round(width_mm, 1),
        height_mm=round(height_mm, 1),
        orientation=orientation,
        confidence=round(best_confidence, 3),
        is_exact_match=is_exact,
    )


def get_expected_pixels(
    paper_size: PaperSize,
    dpi: int,
    orientation: str = "portrait",
) -> tuple[int, int]:
    """Get expected pixel dimensions for a paper size at given DPI.

    Args:
        paper_size: Paper size enum value
        dpi: Target DPI
        orientation: "portrait" or "landscape"

    Returns:
        (width_px, height_px) tuple
    """
    if paper_size not in PAPER_SIZE_SPECS:
        raise ValueError(f"Unknown paper size: {paper_size}")

    spec = PAPER_SIZE_SPECS[paper_size]
    width_px, height_px = spec.pixels_at_dpi(dpi)

    if orientation == "landscape":
        return (height_px, width_px)
    return (width_px, height_px)


# Common DPI-to-size lookup for quick reference
A4_PIXELS_BY_DPI: dict[int, tuple[int, int]] = {
    72: (595, 842),
    96: (794, 1123),
    150: (1240, 1754),
    200: (1654, 2339),
    300: (2480, 3508),
    600: (4961, 7016),
}

LETTER_PIXELS_BY_DPI: dict[int, tuple[int, int]] = {
    72: (612, 792),
    96: (816, 1056),
    150: (1275, 1650),
    200: (1700, 2200),
    300: (2550, 3300),
    600: (5100, 6600),
}
