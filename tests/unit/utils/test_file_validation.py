"""Unit tests for magic-byte file validation utility."""

from __future__ import annotations

import pytest

from image_preprocessing_detector.utils.file_validation import (
    FileTypeMismatchError,
    detect_file_type,
    validate_file_content,
)

# Minimal valid headers padded out to satisfy the min_bytes check (>=18 bytes).
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\nIHDR\x00\x00\x00\x10\x00\x00\x00\x10"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x00\x00"
JPEG_EXIF_BYTES = b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00MM\x00*\x00\x00\x00\x00\x00"
TIFF_LE_BYTES = b"II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
TIFF_BE_BYTES = b"MM\x00*\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 \x00\x00\x00\x00"
# BMP needs "BM" at offset 0 + a recognised DIB header size at offset 14.
# 0x28000000 = BITMAPINFOHEADER (40 bytes).
BMP_BYTES = b"BM\x46\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00"


class TestDetectFileType:
    def test_detects_pdf(self) -> None:
        assert detect_file_type(PDF_BYTES) == "pdf"

    def test_detects_png(self) -> None:
        assert detect_file_type(PNG_BYTES) == "png"

    def test_detects_jpeg_jfif(self) -> None:
        assert detect_file_type(JPEG_BYTES) == "jpeg"

    def test_detects_jpeg_exif(self) -> None:
        assert detect_file_type(JPEG_EXIF_BYTES) == "jpeg"

    @pytest.mark.parametrize(
        "marker_byte",
        [b"\xe0", b"\xe1", b"\xe2", b"\xe5", b"\xe9", b"\xef"],
    )
    def test_detects_jpeg_full_app_marker_range(self, marker_byte: bytes) -> None:
        # Full APPn range \xe0-\xef should be accepted, not just JFIF/EXIF.
        content = b"\xff\xd8\xff" + marker_byte + b"\x00" * 14
        assert detect_file_type(content) == "jpeg"

    def test_detects_jpeg_with_dqt_after_soi(self) -> None:
        # Valid JPEG with raw DQT marker right after SOI (some encoders emit this)
        content = b"\xff\xd8\xff\xdb" + b"\x00" * 14
        assert detect_file_type(content) == "jpeg"

    def test_detects_tiff_little_endian(self) -> None:
        assert detect_file_type(TIFF_LE_BYTES) == "tiff"

    def test_detects_tiff_big_endian(self) -> None:
        assert detect_file_type(TIFF_BE_BYTES) == "tiff"

    def test_detects_webp(self) -> None:
        assert detect_file_type(WEBP_BYTES) == "webp"

    def test_detects_bmp(self) -> None:
        assert detect_file_type(BMP_BYTES) == "bmp"

    def test_returns_none_for_empty(self) -> None:
        assert detect_file_type(b"") is None

    def test_returns_none_for_random_bytes(self) -> None:
        # Generic binary not matching any signature
        assert detect_file_type(b"NOTAREALFILEFORMAT") is None

    def test_rejects_bm_prefix_without_dib_header(self) -> None:
        # "BM" at offset 0 alone is no longer enough — the DIB header
        # size at offset 14 must also match a known BMP variant.
        bm_only = b"BM" + b"\x00" * 16
        assert detect_file_type(bm_only) is None


class TestValidateFileContent:
    @pytest.mark.parametrize(
        ("content", "ext", "expected"),
        [
            (PDF_BYTES, ".pdf", "pdf"),
            (PNG_BYTES, ".png", "png"),
            (JPEG_BYTES, ".jpg", "jpeg"),
            (JPEG_BYTES, ".jpeg", "jpeg"),
            (TIFF_LE_BYTES, ".tiff", "tiff"),
            (TIFF_BE_BYTES, ".tif", "tiff"),
            (WEBP_BYTES, ".webp", "webp"),
            (BMP_BYTES, ".bmp", "bmp"),
        ],
    )
    def test_valid_content_for_extension(
        self, content: bytes, ext: str, expected: str
    ) -> None:
        assert validate_file_content(content, ext) == expected

    def test_extension_case_insensitive(self) -> None:
        assert validate_file_content(PDF_BYTES, ".PDF") == "pdf"

    def test_extension_without_leading_dot(self) -> None:
        assert validate_file_content(PDF_BYTES, "pdf") == "pdf"

    def test_rejects_extension_spoofing_png_as_pdf(self) -> None:
        with pytest.raises(FileTypeMismatchError, match="does not match"):
            validate_file_content(PNG_BYTES, ".pdf")

    def test_rejects_extension_spoofing_arbitrary_bytes_as_png(self) -> None:
        with pytest.raises(FileTypeMismatchError, match="does not match"):
            validate_file_content(b"\x00" * 64, ".png")

    def test_rejects_unsupported_extension(self) -> None:
        with pytest.raises(FileTypeMismatchError, match="Unsupported"):
            validate_file_content(PNG_BYTES, ".exe")

    def test_rejects_unsupported_extension_even_for_tiny_content(self) -> None:
        # Extension check must run BEFORE the too-short fast path so
        # a 0-byte or near-empty `.exe` upload doesn't slip through as
        # "too short to assess".
        with pytest.raises(FileTypeMismatchError, match="Unsupported"):
            validate_file_content(b"", ".exe")
        with pytest.raises(FileTypeMismatchError, match="Unsupported"):
            validate_file_content(b"abc", ".zip")

    def test_raises_for_too_small_nonempty_content(self) -> None:
        # 4-byte content is too short to be a legitimate PDF/PNG/etc.
        # We raise FileTypeMismatchError so a crafted sub-header
        # payload cannot reach the parser libraries.
        with pytest.raises(FileTypeMismatchError, match="too small"):
            validate_file_content(b"%PDF", ".pdf")

    def test_returns_none_for_empty_content(self) -> None:
        # Truly empty content defers to the caller's EMPTY_FILE check.
        assert validate_file_content(b"", ".pdf") is None

    def test_partial_webp_rejected(self) -> None:
        # WebP requires both RIFF (offset 0) and WEBP (offset 8). A
        # RIFF container with a different format (here "ABCD") must
        # not be accepted as WebP.
        partial = b"RIFF\x00\x00\x00\x00ABCD" + b"\x00" * 8
        with pytest.raises(FileTypeMismatchError, match="does not match"):
            validate_file_content(partial, ".webp")

    def test_bmp_with_unknown_dib_header_rejected(self) -> None:
        # "BM" prefix but DIB header size is non-standard: must be rejected.
        # 0xFF000000 isn't a recognised BMP variant.
        bogus_bmp = b"BM" + b"\x00" * 12 + b"\xff\x00\x00\x00"
        with pytest.raises(FileTypeMismatchError, match="does not match"):
            validate_file_content(bogus_bmp, ".bmp")
