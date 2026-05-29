"""Parser for CASIA-HWDB2 page-level Chinese handwriting dataset (DGRL binary format).

CASIA-HWDB2 contains 5,091 full-page handwritten Chinese document images
collected from 1,019 writers. Pages are stored in the proprietary DGRL
(Document Ground-truth Representation Language) binary format, which embeds
both the page scan bitmaps and per-line text annotations.

Sub-datasets: HWDB2.0, HWDB2.1, HWDB2.2 (offline page-level scans).
License: Academic Research Only -- no commercial use.

DGRL Binary Format (one page per .dgrl file):
    File Header (variable length):
        [4 bytes]             header_size  : uint32 LE -- total header bytes including this field
        [header_size-4 bytes] header_body  : variable content
            bytes [-4:-2] of header_body   : code_length (uint16 LE), typically 4

    Image Meta (12 bytes, immediately after header):
        [4 bytes]  height    : uint32 LE -- page height in pixels
        [4 bytes]  width     : uint32 LE -- page width in pixels
        [4 bytes]  line_num  : uint32 LE -- number of text lines

    Line Records (repeated line_num times):
        [4 bytes]                 char_num  : uint32 LE -- characters in this line
        [code_length x char_num]  labels    : each char stored as code_length LE bytes;
                                              assembled to uint32, decoded via struct.pack+GBK
        [4 bytes]                 y         : uint32 LE -- line top edge on page
        [4 bytes]                 x         : uint32 LE -- line left edge on page
        [4 bytes]                 h         : uint32 LE -- line height in pixels
        [4 bytes]                 w         : uint32 LE -- line width in pixels
        [h x w bytes]             bitmap    : grayscale 8-bit, row-major (seeked past)

Format source: read_dgrl.py from luozhongze/HWDB2 (HuggingFace), confirmed against
CASIA-HWDB2 community parsers.

Dataset Structure (after ZIP extraction):
    casia-hwdb2/
        HWDB2.0Train/
            *.dgrl          -- page scan + annotations, one page per file
        HWDB2.0Test/
            *.dgrl
        HWDB2.1Train/ HWDB2.1Test/ HWDB2.2Train/ HWDB2.2Test/  (similar)

Labels Extracted:
    - language_code: "zh"
    - script_name: "Hans"
    - iso15924_script_code: "Hans"
    - transcription: full-page text (lines concatenated, no newline separator)
    - writer_id: extracted from filename if identifiable
    - raw_labels: {sub_dataset, split, page_height, page_width, line_count, char_count, lines[...]}

Example:
    >>> parser = CasiaHwdb2Parser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../casia-hwdb2"),
    ...     image_path=Path("/mnt/e/.../casia-hwdb2/HWDB/HWDB2.0Train/006-P16.dgrl"),
    ...     config={},
    ... )
    >>> print(labels.language_code)
    'zh'
    >>> print(labels.iso15924_script_code)
    'Hans'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "casia-hwdb2"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "casia-hwdb2_metadata.json"
__l4_integrate__ = "scripts/integrate_casia_hwdb2_enrichments.py"


import logging
import re
import struct
from pathlib import Path
from typing import Any, cast

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Bytes for image meta block immediately after the file header
_IMAGE_META_BYTES = 12  # height(4) + width(4) + line_num(4)

# Bytes for per-line position block (y, x, h, w)
_LINE_POSITION_BYTES = 16  # 4 x uint32 LE

# Minimum header body bytes needed to extract code_length (need last 4 bytes)
_HEADER_BODY_MIN = 4

# Struct for image meta: height, width, line_num (all uint32 LE)
_STRUCT_IMAGE_META = struct.Struct("<III")

# Struct for line position: y, x, h, w (all uint32 LE)
_STRUCT_LINE_POSITION = struct.Struct("<IIII")

# Pattern for extracting writer ID from CASIA HWDB2 filenames:
# e.g. "1001-c.dgrl", "001_P01.dgrl" -> writer part before first "-" or "_"
_WRITER_ID_RE = re.compile(r"^(\d+)")

# Sub-directory name fragments for split/sub-dataset detection
_SUBDATASET_NAMES = {"HWDB2.0", "HWDB2.1", "HWDB2.2", "hwdb2.0", "hwdb2.1", "hwdb2.2"}
_TRAIN_MARKERS = {"train", "Train", "TRAIN"}
_TEST_MARKERS = {"test", "Test", "TEST"}

# Default code_length if header is malformed (GBK is 2 bytes; files may pad to 4)
_DEFAULT_CODE_LENGTH = 4


class CasiaHwdb2Parser(BaseParser):
    """Parser for CASIA-HWDB2 page-level Chinese handwriting (DGRL format).

    Reads line-level text annotations from DGRL binary files.  Returns
    full-page transcription and per-line bounding-box data in raw_labels.

    Notes:
        - Each .dgrl file contains exactly one page.
        - Bitmap pixel data is seeked past to avoid loading large image arrays.
        - Writer ID is extracted from the filename leading digit sequence.
        - Sub-dataset (2.0/2.1/2.2) and split (train/test) are inferred
          from directory path components.
        - Character encoding: each char stored as ``code_length`` LE bytes
          assembled to a uint32, then decoded via struct.pack+GBK trick.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["casia-hwdb2", "casia_hwdb2", "hwdb2", "hwdb2-pages"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse CASIA-HWDB2 labels for a single DGRL page file.

        Args:
            dataset_path: Root path of the casia-hwdb2 dataset (unused for DGRL).
            image_path: Absolute path to a DGRL binary file (e.g. ``1001-c.dgrl``).
            config: Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels with Chinese transcription, Hans script metadata,
            and per-line bounding-box annotations in raw_labels.
        """
        labels = OriginalLabels()

        labels.language_code = "zh"
        labels.script_name = "Hans"
        labels.iso15924_script_code = "Hans"

        writer_id = _extract_writer_id(image_path.name)
        if writer_id:
            labels.writer_id = writer_id

        sub_dataset, split = _detect_sub_dataset_and_split(image_path)

        labels.raw_labels = {
            "dataset": "casia-hwdb2",
            "sub_dataset": sub_dataset,
            "split": split,
            "production": "handwritten",
            "writing_system": "simplified-chinese",
        }

        if not image_path.exists():
            logger.debug("DGRL file not found: %s", image_path)
            return labels

        if image_path.suffix.lower() != ".dgrl":
            logger.debug("Unexpected extension for DGRL parser: %s", image_path.name)

        try:
            page = _parse_dgrl_page(image_path)
        except OSError as exc:
            logger.error("Cannot read DGRL file %s: %s", image_path.name, exc)  # noqa: TRY400
            return labels

        if page is None:
            return labels

        lines = page["lines"]
        line_texts = [ln["text"] for ln in lines if ln.get("text")]
        if line_texts:
            labels.transcription = "".join(line_texts)

        total_chars = sum(ln.get("char_count", 0) for ln in lines)
        labels.raw_labels.update(
            {
                "page_height": page["height"],
                "page_width": page["width"],
                "line_count": len(lines),
                "char_count": total_chars,
                "lines": lines,
            }
        )

        return labels


# ---------------------------------------------------------------------------
# Module-level helpers (not part of the public API)
# ---------------------------------------------------------------------------


def _extract_writer_id(filename: str) -> str | None:
    """Extract writer ID from a CASIA HWDB2 filename.

    CASIA files are named ``{writer_id}-P{page_num}.dgrl``
    (e.g. ``006-P16.dgrl``).  We extract the leading digit sequence.

    Args:
        filename: Base filename (e.g. ``1001-c.dgrl``).

    Returns:
        Writer ID string, or None if not determinable.
    """
    match = _WRITER_ID_RE.match(Path(filename).stem)
    return match.group(1) if match else None


def _detect_sub_dataset_and_split(image_path: Path) -> tuple[str, str]:
    """Infer HWDB2 sub-dataset and split from the directory path.

    Args:
        image_path: Full path to the DGRL file.

    Returns:
        Tuple of (sub_dataset, split), each either a detected value or "unknown".
    """
    sub_dataset = "unknown"
    for part in image_path.parts:
        for name in _SUBDATASET_NAMES:
            if name in part:
                sub_dataset = name.upper()
                break

    split = "unknown"
    for part in image_path.parts:
        if any(m in part for m in _TRAIN_MARKERS):
            split = "train"
            break
        if any(m in part for m in _TEST_MARKERS):
            split = "test"
            break

    return sub_dataset, split


def _parse_dgrl_page(path: Path) -> dict[str, Any] | None:
    """Parse a single DGRL page file.

    Args:
        path: Path to the .dgrl file.

    Returns:
        Dict with ``height``, ``width``, ``line_num``, and ``lines`` list,
        or None if the file header is malformed.

    Raises:
        OSError: If the file cannot be opened or read.
    """
    with path.open("rb") as fh:
        code_length = _read_file_header(fh, path.name)
        if code_length is None:
            return None

        image_meta_raw = fh.read(_IMAGE_META_BYTES)
        if len(image_meta_raw) < _IMAGE_META_BYTES:
            logger.warning("Truncated image meta in %s", path.name)
            return None

        height, width, line_num = _STRUCT_IMAGE_META.unpack(image_meta_raw)

        lines: list[dict[str, Any]] = []
        for _ in range(line_num):
            record = _read_line_record(fh, code_length, path.name)
            if record is None:
                break
            lines.append(record)

    logger.debug(
        "Parsed %d/%d lines from %s (page %dx%d)",
        len(lines),
        line_num,
        path.name,
        width,
        height,
    )
    return {"height": height, "width": width, "line_num": line_num, "lines": lines}


def _read_file_header(fh: Any, filename: str) -> int | None:
    """Read the variable-length DGRL file header and return code_length.

    Args:
        fh: Open binary file handle at position 0.
        filename: Filename used only for log messages.

    Returns:
        ``code_length`` (bytes per character in label blocks), or None on error.
    """
    size_raw = fh.read(4)
    if len(size_raw) < 4:
        logger.warning("DGRL header too short in %s", filename)
        return None

    (header_size,) = struct.unpack("<I", size_raw)
    body_len = header_size - 4

    if body_len < _HEADER_BODY_MIN:
        logger.debug(
            "Header body too short (%d bytes) in %s; using default code_length",
            body_len,
            filename,
        )
        if body_len > 0:
            fh.seek(body_len, 1)
        return _DEFAULT_CODE_LENGTH

    header_body = fh.read(body_len)
    if len(header_body) < body_len:
        logger.warning("Truncated header body in %s", filename)
        return None

    # code_length is stored at bytes [-4:-2] of the header body
    code_length_raw = header_body[-4:-2]
    (code_length,) = cast("tuple[int]", struct.unpack("<H", bytes(code_length_raw)))

    if code_length not in {2, 4}:
        logger.debug(
            "Unusual code_length=%d in %s; clamping to %d",
            code_length,
            filename,
            _DEFAULT_CODE_LENGTH,
        )
        code_length = _DEFAULT_CODE_LENGTH

    return code_length


def _read_line_record(
    fh: Any,
    code_length: int,
    filename: str,
) -> dict[str, Any] | None:
    """Read and decode one line record from an open DGRL file handle.

    Args:
        fh: Open binary file handle positioned at the start of a line record.
        code_length: Bytes per character in the label block (typically 4).
        filename: Filename used only for log messages.

    Returns:
        Dict with ``bbox`` ([x, y, w, h] page-relative), ``char_count``,
        and ``text``, or None on EOF or corrupt data.
    """
    char_num_raw = fh.read(4)
    if not char_num_raw or len(char_num_raw) < 4:
        return None  # EOF

    (char_num,) = struct.unpack("<I", char_num_raw)

    label_block_size = code_length * char_num
    label_raw = fh.read(label_block_size)
    if len(label_raw) < label_block_size:
        logger.debug(
            "Truncated label block in %s (expected %d bytes)",
            filename,
            label_block_size,
        )
        return None

    text = _decode_labels(label_raw, char_num, code_length)

    pos_raw = fh.read(_LINE_POSITION_BYTES)
    if len(pos_raw) < _LINE_POSITION_BYTES:
        logger.debug("Truncated line position in %s", filename)
        return None

    y, x, h, w = _STRUCT_LINE_POSITION.unpack(pos_raw)

    bitmap_size = h * w
    if bitmap_size > 0:
        fh.seek(bitmap_size, 1)  # SEEK_CUR - skip grayscale bitmap

    return {
        "bbox": [x, y, w, h],
        "char_count": char_num,
        "text": text,
    }


def _decode_labels(label_raw: bytes, char_num: int, code_length: int) -> str:
    """Decode a label block into a Unicode string.

    Each character is stored as ``code_length`` bytes in little-endian order.
    The bytes are assembled into a uint32, packed back as a 4-byte LE int,
    then decoded as GBK.  This matches the struct.pack+GBK trick used in the
    official CASIA ``read_dgrl.py`` reference script.

    Args:
        label_raw: Raw bytes containing all character labels.
        char_num: Number of characters.
        code_length: Bytes per character (2 or 4).

    Returns:
        Decoded Unicode string with null bytes stripped.
    """
    text_parts: list[str] = []
    for idx in range(char_num):
        chunk = label_raw[idx * code_length : (idx + 1) * code_length]
        code = int.from_bytes(chunk, byteorder="little")
        try:
            char = struct.pack("<I", code).decode("gbk", errors="ignore")
            if char:
                text_parts.append(char[0])
        except (struct.error, UnicodeDecodeError):
            text_parts.append("\ufffd")

    return "".join(text_parts).replace("\x00", "")


__all__ = ["CasiaHwdb2Parser"]
