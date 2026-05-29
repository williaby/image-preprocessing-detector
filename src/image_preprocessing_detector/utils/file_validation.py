"""File content validation via magic-byte signatures.

Defends against extension spoofing where a caller uploads a malicious
file (executable, polyglot, archive bomb) with a benign-looking
extension. Validation here is a hard gate run before the bytes ever
reach PyMuPDF, OpenCV, or PIL - libraries with their own history of
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

Tiny uploads
------------
For our supported types, no legitimate file exists below
``_DEFAULT_MIN_BYTES`` (18). Any non-empty upload shorter than the
threshold therefore cannot match the declared extension and is
rejected with ``FileTypeMismatchError`` - this keeps crafted
sub-header payloads (e.g. a ~15-byte JPEG fragment shaped to
exploit a PIL/OpenCV CVE) from reaching the parser.

Truly empty content (``b""``) is treated separately: the validator
returns ``None`` so the route can surface the more specific
``EMPTY_FILE`` error its post-read check provides.
"""

from __future__ import annotations

# offset -> expected bytes that must equal content[offset : offset+len]
_Part = tuple[int, bytes]
# A type matches if ANY alternative (outer list element) matches, where
# an alternative matches when ALL of its parts (inner list) match.
_Signature = list[list[_Part]]


def _jpeg_app_marker_alternatives() -> list[list[_Part]]:
    r"""Return JPEG signature alternatives.

    Covers the full APPn marker range plus the most common stand-alone
    markers seen immediately after SOI.

    A valid JPEG always starts with SOI (\xff\xd8\xff) followed by a
    one-byte marker. Most files use APP0/APP1/APPe (JFIF/EXIF/Adobe), but
    encoders are free to emit any byte in the APPn range \xe0-\xef, and
    some emit DQT/DRI/SOF/DHT/COM directly. Enumerating the full
    plausible marker set avoids rejecting legitimate JPEGs from less
    common encoders or pipelines that strip APP segments.
    """
    # Standalone markers commonly seen right after SOI in raw JPEGs
    # (DQT, DRI, COM, SOF0/2/3, DHT - strict subset of valid post-SOI
    # markers; restrictive enough that random binary noise won't pass).
    standalone_markers = [
        b"\xdb",  # DQT - Define Quantization Table
        b"\xdc",  # DNL - Define Number of Lines
        b"\xdd",  # DRI - Define Restart Interval
        b"\xc0",  # SOF0 - Start of Frame (baseline)
        b"\xc2",  # SOF2 - Start of Frame (progressive)
        b"\xc3",  # SOF3 - Start of Frame (lossless)
        b"\xc4",  # DHT - Define Huffman Table
        b"\xfe",  # COM - Comment
    ]
    # APPn markers (\xe0-\xef): all 16 alternatives
    app_markers = [bytes([0xE0 + i]) for i in range(16)]
    return [
        [(0, b"\xff\xd8\xff" + marker)] for marker in (app_markers + standalone_markers)
    ]


# BMP DIB header sizes (at offset 14, 4 bytes little-endian) for the
# standard variants we accept. Chained with the "BM" prefix so a random
# binary blob starting with "BM" cannot be misidentified as BMP. Covers
# Windows BMP (BITMAPCORE, INFO, V2..V5) plus the OS/2 short and long
# variants - operators who upload from OS/2-derived pipelines should
# not see false rejections.
#
# Design note: this is an exact-match allowlist rather than a range
# check (e.g. 12..256). A range check would accept random DIB-size
# fields that happen to fall in the plausible range, which is exactly
# the false-positive class the strengthened BMP signature was added
# to close. Adobe-extended BMP variants and other rare formats are
# intentionally rejected with INVALID_FILE_TYPE; the operator can
# add the specific header size to this list once observed.
_BMP_DIB_HEADER_SIZES = [
    b"\x0c\x00\x00\x00",  # BITMAPCOREHEADER / OS22XBITMAPHEADER short (12)
    b"\x10\x00\x00\x00",  # OS22XBITMAPHEADER short variant (16)
    b"\x28\x00\x00\x00",  # BITMAPINFOHEADER (40)
    b"\x34\x00\x00\x00",  # BITMAPV2INFOHEADER (52)
    b"\x38\x00\x00\x00",  # BITMAPV3INFOHEADER (56)
    b"\x40\x00\x00\x00",  # OS22XBITMAPHEADER long variant (64)
    b"\x6c\x00\x00\x00",  # BITMAPV4HEADER (108)
    b"\x7c\x00\x00\x00",  # BITMAPV5HEADER (124)
]

_SIGNATURES: dict[str, _Signature] = {
    "pdf": [[(0, b"%PDF-")]],
    "png": [[(0, b"\x89PNG\r\n\x1a\n")]],
    "jpeg": _jpeg_app_marker_alternatives(),
    "tiff": [
        [(0, b"II*\x00")],  # little-endian
        [(0, b"MM\x00*")],  # big-endian
    ],
    # WebP: "RIFF" at offset 0 AND "WEBP" at offset 8 (the 4 bytes
    # between are a little-endian length field). Both parts required.
    "webp": [[(0, b"RIFF"), (8, b"WEBP")]],
    # BMP requires "BM" at offset 0 AND a recognised DIB header size
    # at offset 14, both must match. The BM-only check was too weak - # many random binary blobs start with the ASCII "BM" pair.
    "bmp": [[(0, b"BM"), (14, dib_size)] for dib_size in _BMP_DIB_HEADER_SIZES],
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

# Minimum content length for meaningful magic-byte validation. Set
# to 18 so the strengthened BMP signature (which inspects bytes
# 14-17) has enough data to run. Exported as part of the public
# surface so batch handlers can pre-reject requests whose remaining
# budget cannot fund a validation read.
MIN_VALIDATION_BYTES = 18
_DEFAULT_MIN_BYTES = MIN_VALIDATION_BYTES  # alias kept for back-compat


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
    min_bytes: int = _DEFAULT_MIN_BYTES,
) -> str | None:
    """Validate that `content` matches the file type implied by `declared_extension`.

    Args:
        content: Raw file bytes (typically the first chunk of an upload).
        declared_extension: File extension claimed by the upload (e.g. ".pdf").
            Case-insensitive; leading dot optional.
        min_bytes: Minimum number of bytes required to assess. Defaults
            to 18 so the strongest signature (BMP DIB header at offset
            14-17) can run.

    Returns:
        - The canonical type name (e.g. ``"pdf"``) if magic bytes
          confirm the declared extension.
        - ``None`` only when ``content`` is empty (``b""``). The
          caller's downstream ``EMPTY_FILE`` check handles that case
          with a more specific error code.

    Raises:
        FileTypeMismatchError: If the extension is unsupported, if
            ``content`` is non-empty but shorter than ``min_bytes``
            (no legitimate file of our supported types fits in
            <18 bytes, so a short upload is presumed crafted), or if
            the magic bytes confirm a different type than declared.
    """
    ext = declared_extension.lower()
    if not ext.startswith("."):
        ext = "." + ext

    # Validate the declared extension BEFORE the short-content checks.
    # An unsupported extension is always an error, even when content
    # is empty or below `min_bytes` - otherwise a 0-byte `.exe`
    # upload would slip through as "too short to assess".
    expected_type = _EXTENSION_TO_TYPE.get(ext)
    if expected_type is None:
        msg = f"Unsupported file extension for content validation: {ext}"
        raise FileTypeMismatchError(msg)

    if not content:
        # Empty content: defer to the caller's EMPTY_FILE check.
        return None
    if len(content) < min_bytes:
        # Sub-header payload: no legitimate file of any supported
        # type fits in less than `min_bytes`. Reject as a type
        # mismatch rather than letting a crafted short payload
        # reach PyMuPDF / PIL / OpenCV where it could exercise a
        # parser CVE.
        msg = (
            f"File content too small to be a valid {expected_type}: "
            f"got {len(content)} bytes, need at least {min_bytes}"
        )
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
