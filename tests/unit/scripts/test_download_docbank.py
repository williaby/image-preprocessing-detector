"""Tests for scripts/download_docbank.py - DocBank dataset downloader.

These tests verify the DocBank download script correctly:
- Creates output directory
- Calls HuggingFace snapshot_download
- Handles errors appropriately
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Scripts directory added to sys.path via tests/conftest.py. huggingface_hub is a
# real installed dependency, so import the script directly; tests patch
# download_docbank.snapshot_download. (A previous module-level
# sys.modules["huggingface_hub"] = MagicMock() leaked into collection of other
# test modules and broke datasets' huggingface_hub import.)
from download_docbank import download_docbank


class TestDownloadDocbank:
    """Tests for download_docbank function."""

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        """Test that download creates output directory."""
        output_dir = tmp_path / "docbank"

        with patch("download_docbank.snapshot_download"):
            download_docbank(output_dir)

        assert output_dir.exists()

    def test_calls_snapshot_download(self, tmp_path: Path) -> None:
        """Test that HuggingFace snapshot_download is called."""
        output_dir = tmp_path / "docbank"

        with patch("download_docbank.snapshot_download") as mock_download:
            download_docbank(output_dir)

            mock_download.assert_called_once()
            call_kwargs = mock_download.call_args[1]
            assert call_kwargs["repo_id"] == "liminghao1630/DocBank"
            assert call_kwargs["repo_type"] == "dataset"
            assert call_kwargs["local_dir"] == str(output_dir)

    def test_handles_download_error(self, tmp_path: Path) -> None:
        """Test that download errors are raised."""
        output_dir = tmp_path / "docbank"

        with patch("download_docbank.snapshot_download") as mock_download:
            mock_download.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                download_docbank(output_dir)

    def test_use_cache_parameter(self, tmp_path: Path) -> None:
        """Test use_cache parameter is accepted."""
        output_dir = tmp_path / "docbank"

        with patch("download_docbank.snapshot_download"):
            # Should not raise
            download_docbank(output_dir, use_cache=False)
            download_docbank(output_dir, use_cache=True)


class TestMain:
    """Tests for main entry point."""

    def test_default_output_dir(self) -> None:
        """Test default output directory path."""
        # The default is data/training/layout/docbank
        # We just verify the module can be imported and has main
        from download_docbank import main

        assert callable(main)
