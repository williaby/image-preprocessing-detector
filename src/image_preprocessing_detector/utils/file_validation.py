"""File content validation via magic-byte signatures.

Defends against extension spoofing where a caller uploads a malicious
file (executable, polyglot, archive bomb) with a benign-looking
extension. Validation here is a hard gate run before the bytes ever
reach PyMuPDF, OpenCV, or PIL — libraries with their own history of
parser CVEs that should not be exposed to arbitrary untrusted input.

Stdlib-only (no libmagic dependency).

Data model
----------
Each canonical type maps to a list of *alternatives*. An alternative is
a list of (offset, expected_bytes) parts; an alternative matches when
ALL its parts match (e.g. WebP requires both `RIFF` at offset 0 AND
`WEBP` at offset 8). A type matches when ANY of its alternatives
matches. This makes the OR/AND semantics explicit so a new format
with a multi-part header (e.g. ISO BMFF, Matroska) can be added
without subtle bugs.
"""

from __future__ import annotations

# offset -> expected bytes that must equal content[offset : offset+len]
_Part = tuple[int, bytes]
# A type matches if ANY alternative (outer list element) matches, where
# an alternative matches when ALL of its parts (inner list) match.
_Signature = list[list[_Part]]

_SIGNATURES: dict[str, _Signature] = {
    "pdf": [[(0, b"%PDF-")]],
    "png": [[(0, b"\x89PNG\r\n\x1a\n")]],
    # JPEG variants: SOI marker followed by various APP/marker bytes.
    "jpeg": [
        [(0, b"\xff\xd8\xff\xe0")],  # JFIF
        [(0, b"\xff\xd8\xff\xe1")],  # EXIF
        [(0, b"\xff\xd8\xff\xe2")],  # ICC
        [(0, b"\xff\xd8\xff\xe3")],
        [(0, b"\xff\xd8\xff\xe8")],  # SPIFF
        [(0, b"\xff\xd8\xff\xdb")],  # raw quantization table (Samsung etc.)
        [(0, b"\xff\xd8\xff\xee")],  # Adobe
    ],
    "tiff": [
        [(0, b"II*\x00")],  # little-endian
        [(0, b"MM\x00*")],  # big-endian
    ],
    # WebP: "RIFF" at offset 0 AND "WEBP" at offset 8 (the 4 bytes
    # between are a little-endian length field). Both parts required.
    "webp": [[(0, b"RIFF"), (8, b"WEBP")]],
    # BMP intentionally listed last: its 2-byte "BM" prefix is the
    # shortest signature in the table and could collide with malformed
    # inputs if checked too eagerly. Iteration order in Python dicts
    # is insertion order, so keep this entry at the bottom.
    "bmp": [[(0, b"BM")]],
}

# Map common file extensions to the canonical type they MUST match.
# Multiple extensions can map to the same type (e.g. .jpg/.jpeg).
_EXTENSION_TO_TYPE: dict[str, str] = {
    ".pdf": "pdf",
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".webp": "webp",
    ".bmp": "bmp",
}


class FileTypeMismatchError(ValueError):
    """Raised when a file's magic bytes do not match its declared extension."""


def _alternative_matches(content: bytes, parts: list[_Part]) -> bool:
    """Return True iff every (offset, expected) part matches `content`."""
    return all(content[offset : offset + len(sig)] == sig for offset, sig in parts)


def detect_file_type(content: bytes) -> str | None:
    """Return the canonical file type detected from magic bytes, or None.

    Args:
        content: Raw file bytes (typically the first 64+ bytes are enough).

    Returns:
        One of the keys in _SIGNATURES (e.g., "pdf", "png") if any
        alternative for that type matches; otherwise None.
    """
    if not content:
        return None
    for type_name, alternatives in _SIGNATURES.items():
        if any(_alternative_matches(content, parts) for parts in alternatives):
            return type_name
    return None


def validate_file_content(
    content: bytes,
    declared_extension: str,
    *,
    min_bytes: int = 12,
) -> str:
    """Validate that `content` matches the file type implied by `declared_extension`.

    Args:
        content: Raw file bytes (must include at least the first 12 bytes).
        declared_extension: File extension claimed by the upload (e.g. ".pdf").
            Case-insensitive; leading dot optional.
        min_bytes: Minimum number of bytes required to perform validation.

    Returns:
        The canonical type name detected (e.g., "pdf").

    Raises:
        FileTypeMismatchError: If content is too short, the extension is
            unsupported, or the magic bytes do not match the extension.
    """
    if len(content) < min_bytes:
        msg = f"File too small to validate ({len(content)} < {min_bytes} bytes)"
        raise FileTypeMismatchError(msg)

    ext = declared_extension.lower()
    if not ext.startswith("."):
        ext = "." + ext

    expected_type = _EXTENSION_TO_TYPE.get(ext)
    if expected_type is None:
        msg = f"Unsupported file extension for content validation: {ext}"
        raise FileTypeMismatchError(msg)

    detected_type = detect_file_type(content)
    if detected_type != expected_type:
        msg = (
            f"File content does not match declared extension {ext}: "
            f"expected magic bytes for {expected_type}, "
            f"detected {detected_type or 'unknown'}"
        )
        raise FileTypeMismatchError(msg)

    return expected_type
