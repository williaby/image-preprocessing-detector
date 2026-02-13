# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Document renderer for synthetic multi-script document generation.

This module provides document rendering capabilities for generating
synthetic training images with proper multi-script text layout.

Key Features:
    - 11 layout types (single_column, two_column, newspaper, etc.)
    - Complex script shaping via HarfBuzz/libraqm
    - RTL and TTB text direction support
    - Character-based wrapping for CJK/Thai scripts
    - COCO-format bounding box generation

Example:
    >>> from image_preprocessing_detector.synthetic.renderer import DocumentRenderer
    >>> from image_preprocessing_detector.synthetic.fonts import FontManager
    >>> font_mgr = FontManager()
    >>> font_mgr.scan_fonts()
    >>> renderer = DocumentRenderer(font_mgr)
    >>> image, blocks = renderer.render_document(text, "Arab", LayoutType.SINGLE_COLUMN)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont

from image_preprocessing_detector.synthetic.config import (
    LayoutType,
    TextDensity,
    get_script_config,
)
from image_preprocessing_detector.synthetic.schema_adapter import TextBlock

if TYPE_CHECKING:
    from image_preprocessing_detector.synthetic.fonts import FontManager

logger = logging.getLogger(__name__)

# Default rendering parameters
DEFAULT_DPI = 300
DEFAULT_PAGE_SIZE = (2480, 3508)  # A4 at 300 DPI
DEFAULT_MARGINS = (150, 150, 150, 150)  # top, right, bottom, left

# Font size ranges for different text roles
FONT_SIZES: dict[str, tuple[int, int]] = {
    "title": (48, 72),
    "header": (32, 48),
    "body": (16, 24),
    "caption": (12, 16),
    "footnote": (10, 14),
}

# Layout configurations for different layout types
# Maps to LayoutType enum values from config.py
LAYOUT_CONFIGS: dict[LayoutType, dict[str, Any]] = {
    LayoutType.STACKED: {
        "columns": 1,
        "gutter": 0,
        "has_header": True,
        "has_footer": False,
    },
    LayoutType.COLUMNS: {
        "columns": 2,
        "gutter": 60,
        "has_header": True,
        "has_footer": False,
    },
    LayoutType.HEADER_BODY: {
        "columns": 1,
        "gutter": 0,
        "has_header": True,
        "has_footer": False,
    },
    LayoutType.HEADER_BODY_FOOTER: {
        "columns": 1,
        "gutter": 0,
        "has_header": True,
        "has_footer": True,
    },
    LayoutType.INTERLEAVED: {
        "columns": 1,
        "gutter": 0,
        "has_header": False,
        "has_footer": False,
        "interleave": True,
    },
    LayoutType.FORM: {
        "columns": 1,
        "gutter": 0,
        "has_fields": True,
        "field_count": (5, 15),
    },
    LayoutType.SIDEBAR: {
        "columns": 2,
        "gutter": 50,
        "has_header": True,
        "has_footer": False,
        "has_sidebar": True,
    },
    LayoutType.CAPTIONED: {
        "columns": 1,
        "gutter": 0,
        "has_header": False,
        "has_caption": True,
    },
    LayoutType.SINGLE_LINE: {
        "columns": 1,
        "gutter": 0,
        "line_spacing": 2.0,
        "paragraph_spacing": 40,
    },
    LayoutType.SHORT_BLOCKS: {
        "columns": 1,
        "gutter": 0,
        "line_spacing": 2.0,
        "paragraph_spacing": 40,
    },
    LayoutType.DENSE_TEXT: {
        "columns": 1,
        "gutter": 0,
        "line_spacing": 1.0,
        "paragraph_spacing": 10,
    },
}

# Scripts that require character-based wrapping (no word boundaries)
CHAR_WRAP_SCRIPTS = {
    "Hans",
    "Hant",
    "Jpan",
    "Kore",
    "Thai",
    "Khmr",
    "Mymr",
    "Tibt",
    "Laoo",
}


@dataclass
class RenderRegion:
    """A rectangular region for text rendering.

    Attributes:
        x: Left edge x coordinate
        y: Top edge y coordinate
        width: Region width in pixels
        height: Region height in pixels
        is_rtl: Whether text flows right-to-left
    """

    x: int
    y: int
    width: int
    height: int
    is_rtl: bool = False


@dataclass
class RenderState:
    """Tracks current rendering state.

    Attributes:
        current_y: Current vertical position
        current_column: Current column index (0-based)
        text_blocks: Accumulated TextBlock objects
        used_height: Total height used in current column
    """

    current_y: int = 0
    current_column: int = 0
    text_blocks: list[TextBlock] = field(default_factory=list)
    used_height: int = 0


class DocumentRenderer:
    """Renders synthetic documents with multi-script text.

    Handles text layout, font selection, and bounding box generation
    for synthetic document images.
    """

    def __init__(
        self,
        font_manager: FontManager,
        page_size: tuple[int, int] = DEFAULT_PAGE_SIZE,
        margins: tuple[int, int, int, int] = DEFAULT_MARGINS,
        dpi: int = DEFAULT_DPI,
        background_color: tuple[int, int, int] = (255, 255, 255),
        text_color: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """Initialize the document renderer.

        Args:
            font_manager: FontManager instance for font lookup
            page_size: Page dimensions (width, height) in pixels
            margins: Margins (top, right, bottom, left) in pixels
            dpi: Resolution for the output image
            background_color: RGB background color
            text_color: RGB text color
        """
        self.font_manager = font_manager
        self.page_size = page_size
        self.margins = margins
        self.dpi = dpi
        self.background_color = background_color
        self.text_color = text_color

    def _get_content_area(self) -> tuple[int, int, int, int]:
        """Get the content area after margins.

        Returns:
            Tuple of (x, y, width, height) for content area
        """
        top, right, bottom, left = self.margins
        width, height = self.page_size
        return (
            left,
            top,
            width - left - right,
            height - top - bottom,
        )

    def _get_column_regions(
        self,
        layout_type: LayoutType,
        is_rtl: bool = False,
    ) -> list[RenderRegion]:
        """Calculate column regions for layout type.

        Args:
            layout_type: The layout type to use
            is_rtl: Whether text is right-to-left

        Returns:
            List of RenderRegion objects for columns
        """
        config = LAYOUT_CONFIGS.get(layout_type, LAYOUT_CONFIGS[LayoutType.STACKED])
        num_columns = config.get("columns", 1)
        gutter = config.get("gutter", 0)

        x, y, total_width, total_height = self._get_content_area()

        # Reserve space for header/footer if needed
        header_height = 100 if config.get("has_header") else 0
        footer_height = 80 if config.get("has_footer") else 0
        y += header_height
        total_height -= header_height + footer_height

        # Calculate column widths
        total_gutter = gutter * (num_columns - 1)
        column_width = (total_width - total_gutter) // num_columns

        regions: list[RenderRegion] = []
        current_x = x

        for _ in range(num_columns):
            region = RenderRegion(
                x=current_x,
                y=y,
                width=column_width,
                height=total_height,
                is_rtl=is_rtl,
            )
            regions.append(region)
            current_x += column_width + gutter

        # Reverse regions for RTL layouts
        if is_rtl:
            regions.reverse()

        return regions

    def _load_font(
        self,
        script_code: str,
        size: int,
        role: str = "body",  # noqa: ARG002
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load appropriate font for script and size.

        Args:
            script_code: ISO 15924 script code
            size: Font size in points
            role: Text role (title, header, body, etc.)

        Returns:
            PIL ImageFont object
        """
        # Get fonts for this script using FontManager API
        font_cache = self.font_manager.get_font_info(script_code)

        if not font_cache or not font_cache.fonts:
            logger.warning("No fonts found for script %s, using default", script_code)
            return ImageFont.load_default()

        # Select the default font or first available
        font_info = font_cache.default_font or font_cache.fonts[0]

        try:
            return ImageFont.truetype(str(font_info.path), size)
        except OSError as e:
            logger.warning("Failed to load font %s: %s", font_info.path, e)
            return ImageFont.load_default()

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
        script_code: str,
    ) -> list[str]:
        """Wrap text to fit within max_width.

        Uses character-based wrapping for scripts without word boundaries.

        Args:
            text: Text to wrap
            font: Font to use for measurement
            max_width: Maximum line width in pixels
            script_code: ISO 15924 script code

        Returns:
            List of wrapped lines
        """
        if script_code in CHAR_WRAP_SCRIPTS:
            return self._wrap_text_by_char(text, font, max_width)
        return self._wrap_text_by_word(text, font, max_width)

    def _wrap_text_by_word(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        """Wrap text by word boundaries.

        Args:
            text: Text to wrap
            font: Font for measurement
            max_width: Maximum line width

        Returns:
            List of wrapped lines
        """
        # Split into paragraphs first
        paragraphs = text.split("\n")
        all_lines: list[str] = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                all_lines.append("")
                continue

            words = paragraph.split()
            current_line: list[str] = []
            current_width: float = 0

            for word in words:
                word_bbox = font.getbbox(word + " ")
                word_width = word_bbox[2] - word_bbox[0]

                if current_width + word_width <= max_width:
                    current_line.append(word)
                    current_width += word_width
                else:
                    if current_line:
                        all_lines.append(" ".join(current_line))
                    current_line = [word]
                    current_width = word_width

            if current_line:
                all_lines.append(" ".join(current_line))

        return all_lines

    def _wrap_text_by_char(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        """Wrap text by character for CJK and similar scripts.

        Args:
            text: Text to wrap
            font: Font for measurement
            max_width: Maximum line width

        Returns:
            List of wrapped lines
        """
        lines: list[str] = []
        current_line = ""
        current_width: float = 0

        for char in text:
            if char == "\n":
                lines.append(current_line)
                current_line = ""
                current_width = 0
                continue

            char_bbox = font.getbbox(char)
            char_width = char_bbox[2] - char_bbox[0]

            if current_width + char_width <= max_width:
                current_line += char
                current_width += char_width
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
                current_width = char_width

        if current_line:
            lines.append(current_line)

        return lines

    @staticmethod
    def _get_cjk_char_dimensions(
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> tuple[int, int]:
        """Get character width and height from a sample CJK character."""
        sample_bbox = font.getbbox("\u4e00")  # "一" (CJK unified ideograph)
        char_width: int = int(sample_bbox[2] - sample_bbox[0])
        char_height: int = int(sample_bbox[3] - sample_bbox[1])
        if char_width == 0:
            char_width = int(getattr(font, "size", 16))
        if char_height == 0:
            char_height = int(getattr(font, "size", 16))
        return char_width, char_height

    def _flush_vertical_column(
        self,
        draw: ImageDraw.ImageDraw,
        col_chars: list[str],
        x_offset: int,
        col_start_y: int,
        char_height: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        script_code: str,
        language_code: str,
        state: RenderState,
        is_header: bool,
        is_caption: bool,
    ) -> None:
        """Render a column of characters if non-empty and within bounds."""
        if col_chars:
            self._draw_vertical_column(
                draw,
                col_chars,
                x_offset,
                col_start_y,
                char_height,
                font,
                script_code,
                language_code,
                state,
                is_header,
                is_caption,
            )

    def _render_vertical_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        region: RenderRegion,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        script_code: str,
        language_code: str,
        state: RenderState,
        is_header: bool = False,
        is_caption: bool = False,
        column_spacing: float = 1.5,
    ) -> int:
        """Render a vertical (top-to-bottom) text block for CJK tategaki.

        Characters are placed top-to-bottom in columns that flow right-to-left.
        This is the traditional East Asian vertical writing style used in
        Japanese novels, newspapers, and Chinese calligraphy.

        Args:
            draw: ImageDraw object
            text: Text to render
            region: Region to render into
            font: Font to use
            script_code: ISO 15924 script code
            language_code: ISO 639-1/3 language code
            state: Current render state
            is_header: Whether this is a header
            is_caption: Whether this is a caption
            column_spacing: Column spacing multiplier

        Returns:
            Height used in pixels (full region height for vertical text)
        """
        if not text.strip():
            return 0

        char_width, char_height = self._get_cjk_char_dimensions(font)
        col_width = int(char_width * column_spacing)
        max_chars_per_column = max(1, region.height // char_height)

        # Strip whitespace and split into characters
        chars = [c for c in text if not c.isspace() or c == "\n"]

        # Columns flow right-to-left
        x_offset = region.x + region.width - col_width
        col_start_y = region.y
        col_chars: list[str] = []
        total_width_used = 0

        for char in chars:
            if char != "\n" and len(col_chars) < max_chars_per_column:
                col_chars.append(char)
                continue

            # Render current column and advance
            if x_offset >= region.x:
                self._flush_vertical_column(
                    draw,
                    col_chars,
                    x_offset,
                    col_start_y,
                    char_height,
                    font,
                    script_code,
                    language_code,
                    state,
                    is_header,
                    is_caption,
                )
                if col_chars:
                    total_width_used += col_width
            col_chars = []
            x_offset -= col_width
            if x_offset < region.x:
                break
            if char != "\n":
                col_chars.append(char)

        # Render remaining characters
        if col_chars and x_offset >= region.x:
            self._flush_vertical_column(
                draw,
                col_chars,
                x_offset,
                col_start_y,
                char_height,
                font,
                script_code,
                language_code,
                state,
                is_header,
                is_caption,
            )
            total_width_used += col_width

        return region.height if total_width_used > 0 else 0

    def _draw_vertical_column(
        self,
        draw: ImageDraw.ImageDraw,
        chars: list[str],
        x: int,
        start_y: int,
        char_height: int,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        script_code: str,
        language_code: str,
        state: RenderState,
        is_header: bool,
        is_caption: bool,
    ) -> None:
        """Draw a single vertical column of characters.

        Args:
            draw: ImageDraw object
            chars: Characters to render in this column
            x: X position for column
            start_y: Starting Y position
            char_height: Height per character cell
            font: Font to use
            script_code: ISO 15924 script code
            language_code: Language code
            state: Render state for tracking blocks
            is_header: Header flag
            is_caption: Caption flag
        """
        y = start_y
        column_text = "".join(chars)
        column_height = len(chars) * char_height

        for char in chars:
            # Center each character horizontally within the column
            char_bbox = font.getbbox(char)
            cw = char_bbox[2] - char_bbox[0]
            x_centered = x + (char_height - cw) // 2  # Approximate centering

            draw.text(
                (x_centered, y),
                char,
                font=font,
                fill=self.text_color,
            )
            y += char_height

        # Record the entire column as one text block
        block = TextBlock(
            text=column_text,
            script_code=script_code,
            language_code=language_code,
            bbox=(x, start_y, char_height, column_height),
            font_size=getattr(font, "size", 16),
            is_header=is_header,
            is_caption=is_caption,
        )
        state.text_blocks.append(block)

    def _render_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        region: RenderRegion,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        script_code: str,
        language_code: str,
        state: RenderState,
        is_header: bool = False,
        is_caption: bool = False,
        line_spacing: float = 1.5,
        direction: str | None = None,
    ) -> int:
        """Render a text block and return height used.

        Args:
            draw: ImageDraw object
            text: Text to render
            region: Region to render into
            font: Font to use
            script_code: ISO 15924 script code
            language_code: ISO 639-1/3 language code
            state: Current render state
            is_header: Whether this is a header
            is_caption: Whether this is a caption
            line_spacing: Line spacing multiplier
            direction: Text direction override ("ltr", "rtl", "ttb")

        Returns:
            Height used in pixels
        """
        # Route to vertical renderer for TTB direction
        if direction == "ttb":
            return self._render_vertical_text_block(
                draw,
                text,
                region,
                font,
                script_code,
                language_code,
                state,
                is_header=is_header,
                is_caption=is_caption,
                column_spacing=line_spacing,
            )

        lines = self._wrap_text(text, font, region.width, script_code)
        if not lines:
            return 0

        # Get font metrics
        if hasattr(font, "getmetrics"):
            ascent, descent = font.getmetrics()
        else:
            ascent, descent = 16, 4
        line_height = int((ascent + descent) * line_spacing)

        y_offset = state.current_y
        total_height = 0

        for line in lines:
            if y_offset + line_height > region.y + region.height:
                break  # Out of space

            # Calculate x position
            line_bbox = font.getbbox(line)
            line_width = line_bbox[2] - line_bbox[0]

            x = region.x + region.width - line_width if region.is_rtl else region.x

            # Draw text
            draw.text(
                (x, y_offset),
                line,
                font=font,
                fill=self.text_color,
            )

            # Record text block
            block = TextBlock(
                text=line,
                script_code=script_code,
                language_code=language_code,
                bbox=(int(x), y_offset, int(line_width), line_height),
                font_size=getattr(font, "size", 16),
                is_header=is_header,
                is_caption=is_caption,
            )
            state.text_blocks.append(block)

            y_offset += line_height
            total_height += line_height

        return total_height

    def render_document(
        self,
        text: str,
        script_code: str,
        language_code: str,
        layout_type: LayoutType = LayoutType.STACKED,
        _text_density: TextDensity = TextDensity.MEDIUM,
        include_header: bool = True,
        header_text: str | None = None,
    ) -> tuple[Image.Image, list[TextBlock]]:
        """Render a document with the given text and layout.

        Args:
            text: Main body text
            script_code: ISO 15924 script code
            language_code: ISO 639-1/3 language code
            layout_type: Layout type to use
            _text_density: Text density level (reserved for future use)
            include_header: Whether to include a header
            header_text: Custom header text (optional)

        Returns:
            Tuple of (PIL Image, list of TextBlock objects)
        """
        # Create image
        image = Image.new("RGB", self.page_size, self.background_color)
        draw = ImageDraw.Draw(image)

        # Get script config
        script_config = get_script_config(script_code)
        is_rtl = script_config.is_rtl if script_config else False

        # Get column regions
        regions = self._get_column_regions(layout_type, is_rtl)

        # Initialize state
        state = RenderState(current_y=regions[0].y if regions else self.margins[0])

        # Load fonts
        body_size = random.randint(*FONT_SIZES["body"])  # nosec B311  # nosemgrep: gitlab.bandit.B311
        body_font = self._load_font(script_code, body_size, "body")

        header_size = random.randint(*FONT_SIZES["header"])  # nosec B311  # nosemgrep: gitlab.bandit.B311
        header_font = self._load_font(script_code, header_size, "header")

        # Render header if requested
        if include_header and regions:
            config = LAYOUT_CONFIGS.get(layout_type, {})
            if config.get("has_header", False):
                header = header_text or text[:50].split("\n")[0]
                state.current_y = self.margins[0]  # Start at top margin
                self._render_text_block(
                    draw,
                    header,
                    RenderRegion(
                        x=regions[0].x,
                        y=state.current_y,
                        width=sum(r.width for r in regions),
                        height=100,
                        is_rtl=is_rtl,
                    ),
                    header_font,
                    script_code,
                    language_code,
                    state,
                    is_header=True,
                )
                state.current_y = regions[0].y  # Reset to column start

        # Get line spacing based on layout
        config = LAYOUT_CONFIGS.get(layout_type, {})
        line_spacing = config.get("line_spacing", 1.5)

        # Render body text across columns
        remaining_text = text
        for region in regions:
            if not remaining_text:
                break

            state.current_y = region.y
            self._render_text_block(
                draw,
                remaining_text,
                region,
                body_font,
                script_code,
                language_code,
                state,
                line_spacing=line_spacing,
            )

            # Calculate how much text was rendered
            rendered_chars = sum(len(block.text) for block in state.text_blocks)
            remaining_text = text[rendered_chars:] if rendered_chars < len(text) else ""

        return image, state.text_blocks

    def render_header_body_multi_script(
        self,
        header_data: tuple[str, str, str],
        body_data: list[tuple[str, str, str]],
    ) -> tuple[Image.Image, list[TextBlock]]:
        """Render a document with header in one script and body in another.

        This implements proper HEADER_BODY semantics for multi-script documents:
        - Header is rendered at top in header_data's script
        - Body is rendered below in body_data's script(s)

        Args:
            header_data: Tuple of (text, script_code, language_code) for header
            body_data: List of (text, script_code, language_code) for body

        Returns:
            Tuple of (PIL Image, list of TextBlock objects)
        """
        # Create image
        image = Image.new("RGB", self.page_size, self.background_color)
        draw = ImageDraw.Draw(image)

        x, y, content_width, content_height = self._get_content_area()
        state = RenderState(current_y=y)

        # Unpack header data
        header_text, header_script, header_lang = header_data
        header_config = get_script_config(header_script)
        header_rtl = header_config.is_rtl if header_config else False

        # Render header (larger font, at top)
        header_size = random.randint(*FONT_SIZES["header"])  # nosec B311  # nosemgrep: gitlab.bandit.B311
        header_font = self._load_font(header_script, header_size, "header")

        header_region = RenderRegion(
            x=x,
            y=y,
            width=content_width,
            height=150,  # Reserve 150px for header
            is_rtl=header_rtl,
        )

        header_height = self._render_text_block(
            draw,
            header_text[:100],  # Limit header length
            header_region,
            header_font,
            header_script,
            header_lang,
            state,
            is_header=True,
        )

        # Add spacing after header
        body_start_y = y + max(header_height, 100) + 40

        # Render body text (can be multiple scripts)
        state.current_y = body_start_y
        body_height = content_height - (body_start_y - y)

        for body_text, body_script, body_lang in body_data:
            if state.current_y >= y + content_height - 50:
                break  # No more space

            body_config = get_script_config(body_script)
            body_rtl = body_config.is_rtl if body_config else False

            body_size = random.randint(*FONT_SIZES["body"])  # nosec B311  # nosemgrep: gitlab.bandit.B311
            body_font = self._load_font(body_script, body_size, "body")

            body_region = RenderRegion(
                x=x,
                y=state.current_y,
                width=content_width,
                height=body_height,
                is_rtl=body_rtl,
            )

            height_used = self._render_text_block(
                draw,
                body_text,
                body_region,
                body_font,
                body_script,
                body_lang,
                state,
            )

            state.current_y += height_used + 30  # Paragraph spacing

        return image, state.text_blocks

    def render_multi_script_document(
        self,
        text_blocks_data: list[tuple[str, str, str]],
        layout_type: LayoutType = LayoutType.COLUMNS,
    ) -> tuple[Image.Image, list[TextBlock]]:
        """Render a document with multiple scripts.

        Args:
            text_blocks_data: List of (text, script_code, language_code) tuples
            layout_type: Layout type to use

        Returns:
            Tuple of (PIL Image, list of TextBlock objects)
        """
        # Create image
        image = Image.new("RGB", self.page_size, self.background_color)
        draw = ImageDraw.Draw(image)

        # Get regions - use mixed layout for multi-script
        regions = self._get_column_regions(layout_type, is_rtl=False)

        state = RenderState(current_y=regions[0].y if regions else self.margins[0])
        current_region_idx = 0

        for text, script_code, language_code in text_blocks_data:
            if current_region_idx >= len(regions):
                break

            region = regions[current_region_idx]
            script_config = get_script_config(script_code)
            is_rtl = script_config.is_rtl if script_config else False

            # Update region RTL setting
            region.is_rtl = is_rtl

            # Load font for this script
            body_size = random.randint(*FONT_SIZES["body"])  # nosec B311  # nosemgrep: gitlab.bandit.B311
            font = self._load_font(script_code, body_size, "body")

            # Render text
            height_used = self._render_text_block(
                draw,
                text,
                region,
                font,
                script_code,
                language_code,
                state,
            )

            state.current_y += height_used + 20  # Add paragraph spacing

            # Move to next region if current is full
            if state.current_y > region.y + region.height - 100:
                current_region_idx += 1
                if current_region_idx < len(regions):
                    state.current_y = regions[current_region_idx].y

        return image, state.text_blocks


__all__ = [
    "DEFAULT_DPI",
    "DEFAULT_MARGINS",
    "DEFAULT_PAGE_SIZE",
    "FONT_SIZES",
    "LAYOUT_CONFIGS",
    "DocumentRenderer",
    "RenderRegion",
    "RenderState",
]
