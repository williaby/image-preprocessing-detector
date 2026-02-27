"""Unit tests for atomic file operations (P2-2 fix).

Tests atomic writes, failure scenarios, and convenience functions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.integrity import (
    atomic_json_write,
    atomic_write,
    safe_write_bytes,
    safe_write_text,
)


class TestAtomicWrite:
    """Test the atomic_write context manager."""

    def test_atomic_write_success(self, tmp_path: Path) -> None:
        """Test successful atomic write."""
        target = tmp_path / "output.txt"

        with atomic_write(target) as temp_path:
            temp_path.write_text("Hello, World!")

        assert target.exists()
        assert target.read_text() == "Hello, World!"
        # Temp file should be cleaned up
        assert not temp_path.exists()

    def test_atomic_write_to_new_file(self, tmp_path: Path) -> None:
        """Test atomic write creates new file."""
        target = tmp_path / "new_file.txt"

        assert not target.exists()

        with atomic_write(target) as temp_path:
            temp_path.write_text("New content")

        assert target.exists()
        assert target.read_text() == "New content"

    def test_atomic_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Test atomic write overwrites existing file."""
        target = tmp_path / "existing.txt"
        target.write_text("Old content")

        with atomic_write(target) as temp_path:
            temp_path.write_text("New content")

        assert target.read_text() == "New content"

    def test_atomic_write_failure_preserves_original(self, tmp_path: Path) -> None:
        """Test that failure during write preserves original file."""
        target = tmp_path / "protected.txt"
        target.write_text("Original content")

        def _write_and_fail() -> None:
            with atomic_write(target) as temp_path:
                temp_path.write_text("Partial content")
                raise ValueError("Simulated failure")

        with pytest.raises(ValueError, match="Simulated failure"):
            _write_and_fail()

        # Original should be unchanged
        assert target.read_text() == "Original content"

    def test_atomic_write_failure_cleans_temp(self, tmp_path: Path) -> None:
        """Test that failure cleans up temp file."""
        target = tmp_path / "output.txt"
        temp_path_ref: Path | None = None

        def _write_and_fail() -> None:
            nonlocal temp_path_ref
            with atomic_write(target) as temp_path:
                temp_path_ref = temp_path
                temp_path.write_text("Content")
                raise ValueError("Simulated failure")

        with pytest.raises(ValueError):
            _write_and_fail()

        # Temp file should be cleaned up (nonlocal was assigned before the exception)
        assert isinstance(temp_path_ref, Path)
        assert not temp_path_ref.exists()
        # Target should not exist (was never created)
        assert not target.exists()

    def test_atomic_write_binary(self, tmp_path: Path) -> None:
        """Test atomic write with binary content."""
        target = tmp_path / "binary.bin"
        content = bytes(range(256))

        with atomic_write(target) as temp_path:
            temp_path.write_bytes(content)

        assert target.read_bytes() == content

    def test_atomic_write_with_fsync(self, tmp_path: Path) -> None:
        """Test atomic write with fsync enabled."""
        target = tmp_path / "synced.txt"

        with atomic_write(target, fsync=True) as temp_path:
            temp_path.write_text("Synced content")

        assert target.read_text() == "Synced content"

    def test_atomic_write_custom_suffix(self, tmp_path: Path) -> None:
        """Test atomic write with custom temp suffix."""
        target = tmp_path / "output.txt"

        with atomic_write(target, suffix=".temp") as temp_path:
            # Temp file should have unique name (PID_UUID) + custom suffix
            assert str(temp_path).endswith(".temp")
            assert "output." in str(temp_path)
            temp_path.write_text("Content")

        assert target.exists()


class TestSafeWriteText:
    """Test the safe_write_text convenience function."""

    def test_safe_write_text_success(self, tmp_path: Path) -> None:
        """Test successful text write."""
        target = tmp_path / "text.txt"

        safe_write_text(target, "Hello, World!")

        assert target.read_text() == "Hello, World!"

    def test_safe_write_text_unicode(self, tmp_path: Path) -> None:
        """Test writing unicode text."""
        target = tmp_path / "unicode.txt"

        safe_write_text(target, "Hello, 世界! 🌍")

        assert target.read_text() == "Hello, 世界! 🌍"

    def test_safe_write_text_overwrite(self, tmp_path: Path) -> None:
        """Test overwriting existing file."""
        target = tmp_path / "text.txt"
        target.write_text("Old")

        safe_write_text(target, "New")

        assert target.read_text() == "New"

    def test_safe_write_text_custom_encoding(self, tmp_path: Path) -> None:
        """Test writing with custom encoding."""
        target = tmp_path / "latin1.txt"

        safe_write_text(target, "café", encoding="latin-1")

        assert target.read_text(encoding="latin-1") == "café"


class TestSafeWriteBytes:
    """Test the safe_write_bytes convenience function."""

    def test_safe_write_bytes_success(self, tmp_path: Path) -> None:
        """Test successful bytes write."""
        target = tmp_path / "binary.bin"
        content = b"\x00\x01\x02\x03"

        safe_write_bytes(target, content)

        assert target.read_bytes() == content

    def test_safe_write_bytes_large(self, tmp_path: Path) -> None:
        """Test writing large binary content."""
        target = tmp_path / "large.bin"
        content = b"A" * 1_000_000

        safe_write_bytes(target, content)

        assert target.read_bytes() == content


class TestAtomicJsonWrite:
    """Test the atomic_json_write convenience function."""

    def test_atomic_json_write_dict(self, tmp_path: Path) -> None:
        """Test writing JSON dict."""
        target = tmp_path / "data.json"
        data = {"key": "value", "number": 42}

        atomic_json_write(target, data)

        assert target.exists()
        loaded = json.loads(target.read_text())
        assert loaded == data

    def test_atomic_json_write_list(self, tmp_path: Path) -> None:
        """Test writing JSON list."""
        target = tmp_path / "data.json"
        data = [1, 2, 3, "four", {"nested": True}]

        atomic_json_write(target, data)

        loaded = json.loads(target.read_text())
        assert loaded == data

    def test_atomic_json_write_indent(self, tmp_path: Path) -> None:
        """Test writing JSON with indentation."""
        target = tmp_path / "pretty.json"
        data = {"key": "value"}

        atomic_json_write(target, data, indent=2)

        content = target.read_text()
        assert "  " in content  # Has indentation

    def test_atomic_json_write_compact(self, tmp_path: Path) -> None:
        """Test writing compact JSON."""
        target = tmp_path / "compact.json"
        data = {"key": "value", "number": 42}

        atomic_json_write(target, data, indent=None)

        content = target.read_text()
        assert "\n" not in content  # No newlines in compact

    def test_atomic_json_write_unicode(self, tmp_path: Path) -> None:
        """Test writing JSON with unicode."""
        target = tmp_path / "unicode.json"
        data = {"message": "Hello, 世界!"}

        atomic_json_write(target, data)

        loaded = json.loads(target.read_text())
        assert loaded["message"] == "Hello, 世界!"

    def test_atomic_json_write_with_fsync(self, tmp_path: Path) -> None:
        """Test writing JSON with fsync."""
        target = tmp_path / "synced.json"
        data = {"synced": True}

        atomic_json_write(target, data, fsync=True)

        loaded = json.loads(target.read_text())
        assert loaded == data

    def test_atomic_json_write_nested(self, tmp_path: Path) -> None:
        """Test writing deeply nested JSON."""
        target = tmp_path / "nested.json"
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": [1, 2, 3],
                    },
                },
            },
        }

        atomic_json_write(target, data)

        loaded = json.loads(target.read_text())
        assert loaded["level1"]["level2"]["level3"]["value"] == [1, 2, 3]
