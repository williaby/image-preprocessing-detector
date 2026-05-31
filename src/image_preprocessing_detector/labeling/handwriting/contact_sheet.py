"""Contact sheet generation for handwriting legibility scoring.

Creates labeled grid images from a list of handwriting image paths.
Each cell receives a numbered badge overlay (#1-#N) so models can
return per-image JSON scores keyed by position.

Example:
    >>> from pathlib import Path
    >>> from image_preprocessing_detector.labeling.handwriting.contact_sheet import (
    ...     create_hw_contact_sheet,
    ...     partition_into_sheets,
    ... )
    >>> image_paths = list(Path("data/iam").glob("*.png"))[:12]
    >>> sheet_path = create_hw_contact_sheet(image_paths, Path("out/sheet_001.jpg"))
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default values used when no config is passed
_DEFAULT_COLS = 4
_DEFAULT_CELL_WIDTH = 512
_DEFAULT_JPEG_QUALITY = 85
_DEFAULT_FONT_SIZE = 20

# OS-specific font search paths tried in order before falling back to PIL default
_FONT_CANDIDATE_PATHS: tuple[str, ...] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Debian/Ubuntu
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # RHEL/Fedora
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "C:/Windows/Fonts/arialbd.ttf",  # Windows
)


def create_hw_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
    cols: int = _DEFAULT_COLS,
    cell_width_px: int = _DEFAULT_CELL_WIDTH,
    jpeg_quality: int = _DEFAULT_JPEG_QUALITY,
    label_font_size: int = _DEFAULT_FONT_SIZE,
) -> Path:
    """Create a labeled contact sheet from a list of image paths.

    Images are arranged left-to-right, top-to-bottom. Each cell is
    scaled to ``cell_width_px`` wide (aspect ratio preserved) and
    receives a white "#N" badge in the top-left corner.

    Args:
        image_paths (list[Path]): Ordered list of image file paths (max 12 recommended).
        output_path (Path): Destination path for the output JPEG.
        cols (int): Number of columns in the grid.
        cell_width_px (int): Width of each cell in pixels.
        jpeg_quality (int): JPEG save quality (1-95).
        label_font_size (int): Font size for the number badge overlay.

    Returns:
        Path:         Path to the saved contact sheet image.

    Raises:
        ImportError: If Pillow is not installed.
        ValueError: If image_paths is empty.
    """
    try:
        from PIL import Image as PILImage
        from PIL import ImageDraw
    except ImportError as exc:
        msg = "Pillow required for contact sheet generation: pip install Pillow"
        raise ImportError(msg) from exc

    if not image_paths:
        msg = "image_paths must not be empty"
        raise ValueError(msg)

    n_images = len(image_paths)
    rows = math.ceil(n_images / cols)

    thumbnails = _load_thumbnails(image_paths, cell_width_px, PILImage)
    cell_h = max(t.height for t in thumbnails) if thumbnails else cell_width_px

    sheet_w = cols * cell_width_px
    sheet_h = rows * cell_h
    sheet = PILImage.new("RGB", (sheet_w, sheet_h), color=(240, 240, 240))

    font = _load_font(label_font_size)

    for position, (thumb, _source_path) in enumerate(
        zip(thumbnails, image_paths, strict=True), start=1
    ):
        col_idx = (position - 1) % cols
        row_idx = (position - 1) // cols
        x_offset = col_idx * cell_width_px
        y_offset = row_idx * cell_h

        sheet.paste(thumb, (x_offset, y_offset))
        _draw_label(sheet, f"#{position}", x_offset, y_offset, font, ImageDraw)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="JPEG", quality=jpeg_quality)

    logger.debug(
        "contact_sheet_created",
        path=str(output_path),
        n_images=n_images,
        cols=cols,
        rows=rows,
    )
    return output_path


def partition_into_sheets(
    image_paths: list[Path],
    images_per_sheet: int,
) -> list[list[Path]]:
    """Split a list of image paths into fixed-size batches for contact sheets.

    Args:
        image_paths (list[Path]): Full list of image file paths.
        images_per_sheet (int): Maximum images per sheet (e.g., 12 for 4x3 grid).

    Returns:
        list[list[Path]]: List of batches; the last batch may be smaller than images_per_sheet.

    Raises:
        ValueError: If images_per_sheet is not positive.
    """
    if images_per_sheet <= 0:
        msg = f"images_per_sheet must be positive, got {images_per_sheet}"
        raise ValueError(msg)
    return [
        image_paths[i : i + images_per_sheet]
        for i in range(0, len(image_paths), images_per_sheet)
    ]


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────


def _load_thumbnails(
    image_paths: list[Path],
    cell_width_px: int,
    pil_image: Any,
) -> list[Any]:
    """Load images and resize to cell_width_px wide (aspect preserved).

    Failed loads are replaced with a grey placeholder cell.

    Args:
        image_paths (list[Path]): Paths to load.
        cell_width_px (int): Target width for each thumbnail.
        pil_image (Any): PIL.Image module reference.

    Returns:
        list[Any]:         List of PIL Image objects in RGB mode.
    """
    thumbnails: list[Any] = []
    for path in image_paths:
        try:
            with pil_image.open(path) as img:
                img = img.convert("RGB")
                orig_w, orig_h = img.size
                ratio = cell_width_px / orig_w
                new_h = max(1, int(orig_h * ratio))
                thumb = img.resize((cell_width_px, new_h), pil_image.Resampling.LANCZOS)
                thumbnails.append(thumb)
        except Exception:
            logger.warning("contact_sheet_load_failed", path=str(path))
            placeholder = pil_image.new(
                "RGB", (cell_width_px, cell_width_px), (200, 200, 200)
            )
            thumbnails.append(placeholder)
    return thumbnails


def _load_font(font_size: int) -> Any:
    """Load a truetype font, falling back to PIL default.

    Args:
        font_size (int): Desired font size in points.

    Returns:
        Any:         PIL ImageFont object.
    """
    from PIL import ImageFont

    for path in _FONT_CANDIDATE_PATHS:
        try:
            return ImageFont.truetype(path, font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_label(
    sheet: Any,
    label: str,
    x: int,
    y: int,
    font: Any,
    image_draw_module: Any,
) -> None:
    """Draw a white background badge with black text at (x, y).

    Args:
        sheet (Any): PIL Image to draw on (modified in place).
        label (str): Text to render (e.g., "#1").
        x (int): Left edge of the cell in pixels.
        y (int): Top edge of the cell in pixels.
        font (Any): PIL ImageFont to use.
        image_draw_module (Any): PIL.ImageDraw module reference.
    """
    draw = image_draw_module.Draw(sheet)
    padding = 4
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    rect_x1 = x + padding
    rect_y1 = y + padding
    rect_x2 = rect_x1 + text_w + padding * 2
    rect_y2 = rect_y1 + text_h + padding

    draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=(255, 255, 255))
    draw.text((rect_x1 + padding, rect_y1), label, fill=(0, 0, 0), font=font)
