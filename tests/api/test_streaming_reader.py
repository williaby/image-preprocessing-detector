"""Tests for streaming upload helpers in the /process route.

Covers read_with_size_limit (streaming size cap, first-chunk magic-byte
validation, short-read accumulation, remaining-budget clamp) and
make_content_validator, which the endpoint tests do not exercise
directly.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="FastAPI required for API tests")

from image_preprocessing_detector.api.routes import process  # noqa: E402
from image_preprocessing_detector.utils.file_validation import (  # noqa: E402
    FileTypeMismatchError,
)

# Minimal valid magic-byte headers (>= MIN_VALIDATION_BYTES = 18).
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n%%EOF\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\nIHDR\x00\x00\x00\x10\x00\x00\x00\x10"


class _FakeUpload:
    """Minimal async stand-in for starlette UploadFile.

    Honours the per-call `n` argument so the remaining-budget clamp is
    exercised, like a real streaming reader.
    """

    def __init__(self, data: bytes, size: int | None = None) -> None:
        self._data = data
        self._pos = 0
        self.size = size

    async def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


class _DribbleUpload(_FakeUpload):
    """Returns at most 4 bytes per read to simulate a short-read backend."""

    async def read(self, n: int = -1) -> bytes:
        cap = 4 if (n is None or n < 0) else min(n, 4)
        return await super().read(cap)


@pytest.mark.asyncio
async def test_returns_full_content() -> None:
    payload = PDF_BYTES + b"\x00" * 1000
    content = await process.read_with_size_limit(_FakeUpload(payload), max_size_mb=10)
    assert content == payload


@pytest.mark.asyncio
async def test_aborts_oversize() -> None:
    payload = b"%PDF-1.4\n" + b"\x00" * (2 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds limit"):
        await process.read_with_size_limit(_FakeUpload(payload), max_size_mb=1)


@pytest.mark.asyncio
async def test_early_validate_rejects_spoof() -> None:
    # PNG content declared as .pdf -> magic-byte mismatch on first chunk.
    with pytest.raises(FileTypeMismatchError, match="does not match"):
        await process.read_with_size_limit(
            _FakeUpload(PNG_BYTES + b"\x00" * 100),
            max_size_mb=10,
            early_validate=process.make_content_validator(".pdf"),
        )


@pytest.mark.asyncio
async def test_early_validate_accepts_match() -> None:
    payload = PDF_BYTES + b"\x00" * 100
    content = await process.read_with_size_limit(
        _FakeUpload(payload),
        max_size_mb=10,
        early_validate=process.make_content_validator(".pdf"),
    )
    assert content == payload


@pytest.mark.asyncio
async def test_short_reads_accumulate_before_validation() -> None:
    """A reader returning < MIN_VALIDATION_BYTES per call must not
    falsely trip 'too small' - the helper accumulates first."""
    payload = PDF_BYTES + b"\x00" * 50
    content = await process.read_with_size_limit(
        _DribbleUpload(payload),
        max_size_mb=10,
        early_validate=process.make_content_validator(".pdf"),
    )
    assert content == payload


@pytest.mark.asyncio
async def test_extra_byte_limit_clamps() -> None:
    # File fits under max_size_mb but exceeds the remaining batch budget.
    payload = PDF_BYTES + b"\x00" * 10_000
    with pytest.raises(ValueError, match="remaining batch budget"):
        await process.read_with_size_limit(
            _FakeUpload(payload),
            max_size_mb=10,
            extra_byte_limit=500,
        )


def test_make_content_validator_runs_validation() -> None:
    validator = process.make_content_validator(".pdf")
    validator(PDF_BYTES)  # valid PDF head passes
    with pytest.raises(FileTypeMismatchError):
        validator(PNG_BYTES)  # PNG head under a .pdf claim fails
