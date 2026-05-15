"""File content validation via magic-byte signatures.

Defends against extension spoofing where a caller uploads a malicious
file (executable, polyglot, archive bomb) with a benign-looking
extension. Validation here is a hard gate run before the bytes ever
reach PyMuPDF, OpenCV, or PIL — libraries with their own history of
parser CVEs that should not be exposed to arbitrary untrusted input.

Stdlib-only (no libmagic dependency).
"""

from __future__ import annotations

# Mapping of canonical type → list of (offset, signature_bytes) tuples.
# A file matches a type if at least one signature matches at its offset.
_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "pdf": [(0, b"%PDF-")],
    "png": [(0, b"\x89PNG\r\n\x1a\n")],
    # JPEG variants: SOI marker followed by various APP markers.
    "jpeg": [
        (0, b"\xff\xd8\xff\xe0"),  # JFIF
        (0, b"\xff\xd8\xff\xe1"),  # EXIF
        (0, b"\xff\xd8\xff\xe2"),  # ICC
        (0, b"\xff\xd8\xff\xe3"),
        (0, b"\xff\xd8\xff\xe8"),  # SPIFF
        (0, b"\xff\xd8\xff\xdb"),  # raw quantization table (Samsung etc.)
        (0, b"\xff\xd8\xff\xee"),  # Adobe
    ],
    "tiff": [
        (0, b"II*\x00"),  # little-endian
        (0, b"MM\x00*"),  # big-endian
    ],
    # WebP: "RIFF" <4-byte size> "WEBP"
    "webp": [(0, b"RIFF"), (8, b"WEBP")],
    # BMP: 'BM' header
    "bmp": [(0, b"BM")],
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


def detect_file_type(content: bytes) -> str | None:
    """Return the canonical file type detected from magic bytes, or None.

    Args:
        content: Raw file bytes (typically the first 64+ bytes are enough).

    Returns:
        One of the keys in _SIGNATURES (e.g., "pdf", "png") if a signature
        matches, otherwise None.
    """
    if not content:
        return None
    for type_name, signatures in _SIGNATURES.items():
        if all(
            content[offset : offset + len(sig)] == sig for offset, sig in signatures
        ):
            return type_name
    # WebP needs all-of semantics; types above use first-of, so fall back
    # to per-signature any-match for the simple types.
    for type_name, signatures in _SIGNATURES.items():
        if type_name == "webp":
            continue
        for offset, sig in signatures:
            if content[offset : offset + len(sig)] == sig:
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
