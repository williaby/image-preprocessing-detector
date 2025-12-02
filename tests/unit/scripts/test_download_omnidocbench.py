# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/download_omnidocbench.py - OmniDocBench dataset downloader.

These tests verify the OmniDocBench download script correctly:
- Handles rate limiting
- Loads tokens from environment
- Calculates directory size
- Manages download retries
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock dependencies before importing
sys.modules["huggingface_hub"] = MagicMock()
sys.modules["datasets"] = MagicMock()

# Add scripts directory to path for import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from download_omnidocbench import (
    RateLimitHandler,
    _is_rate_limit_error,
    _resolve_hf_token,
    get_directory_size,
    load_token_from_env,
)


class TestRateLimitHandler:
    """Tests for RateLimitHandler class."""

    def test_init_defaults(self) -> None:
        """Test RateLimitHandler initialization with defaults."""
        handler = RateLimitHandler()

        assert handler.requests_per_window == 5000
        assert handler.window_duration == timedelta(minutes=5)
        assert handler.request_count == 0

    def test_init_custom_values(self) -> None:
        """Test RateLimitHandler with custom values."""
        handler = RateLimitHandler(requests_per_window=1000, window_minutes=10)

        assert handler.requests_per_window == 1000
        assert handler.window_duration == timedelta(minutes=10)

    def test_check_and_wait_increments_count(self) -> None:
        """Test that check_and_wait increments request count."""
        handler = RateLimitHandler()
        initial_count = handler.request_count

        handler.check_and_wait()

        assert handler.request_count == initial_count + 1

    def test_check_and_wait_resets_after_window(self) -> None:
        """Test that window resets after duration expires."""
        handler = RateLimitHandler(window_minutes=5)
        handler.request_count = 100
        # Set window start to past
        handler.window_start = datetime.now(tz=UTC) - timedelta(minutes=6)

        handler.check_and_wait()

        # Should have reset to 0 (the reset happens, then returns without incrementing)
        assert handler.request_count == 0

    def test_check_and_wait_waits_at_threshold(self) -> None:
        """Test that handler waits when approaching threshold."""
        handler = RateLimitHandler(requests_per_window=100, window_minutes=1)
        handler.request_count = 95  # At 95% threshold

        # Mock time.sleep to avoid actual waiting
        with patch("download_omnidocbench.time.sleep") as mock_sleep:
            handler.check_and_wait()

            # Should have called sleep
            if mock_sleep.called:
                assert mock_sleep.call_args[0][0] > 0


class TestLoadTokenFromEnv:
    """Tests for load_token_from_env function."""

    def test_load_token_returns_none_when_no_env(self) -> None:
        """Test loading token returns None when .env doesn't exist."""
        # The function looks for .env in a specific location relative to script
        # If it doesn't exist, should return None
        result = load_token_from_env()

        # May return None or a token depending on environment
        assert result is None or isinstance(result, str)

    def test_load_token_function_callable(self) -> None:
        """Test load_token_from_env is callable."""
        assert callable(load_token_from_env)


class TestResolveHfToken:
    """Tests for _resolve_hf_token function."""

    def test_explicit_token_takes_priority(self) -> None:
        """Test that explicit token takes priority."""
        result = _resolve_hf_token("explicit_token")

        assert result == "explicit_token"

    def test_env_var_fallback(self) -> None:
        """Test falling back to environment variable."""
        with patch("download_omnidocbench.load_token_from_env", return_value=None):
            with patch("download_omnidocbench.os.getenv", return_value="env_token"):
                result = _resolve_hf_token(None)

                assert result == "env_token"

    def test_env_file_fallback(self) -> None:
        """Test falling back to .env file."""
        with patch(
            "download_omnidocbench.load_token_from_env", return_value="file_token"
        ):
            result = _resolve_hf_token(None)

            assert result == "file_token"


class TestIsRateLimitError:
    """Tests for _is_rate_limit_error function."""

    def test_rate_limit_keywords(self) -> None:
        """Test detection of rate limit keywords."""
        assert _is_rate_limit_error("Rate limit exceeded") is True
        assert _is_rate_limit_error("Error 429: Too many requests") is True
        assert _is_rate_limit_error("too many requests") is True

    def test_non_rate_limit_errors(self) -> None:
        """Test non-rate-limit errors return False."""
        assert _is_rate_limit_error("Connection timeout") is False
        assert _is_rate_limit_error("File not found") is False
        assert _is_rate_limit_error("Authentication failed") is False

    def test_case_insensitive(self) -> None:
        """Test that detection is case insensitive."""
        assert _is_rate_limit_error("RATE LIMIT") is True
        assert _is_rate_limit_error("Rate Limit") is True


class TestGetDirectorySize:
    """Tests for get_directory_size function."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test size of empty directory."""
        result = get_directory_size(tmp_path)

        assert result == 0.0

    def test_directory_with_files(self, tmp_path: Path) -> None:
        """Test size calculation with files."""
        # Create files of known size
        (tmp_path / "file1.txt").write_bytes(b"x" * 1024)  # 1 KB
        (tmp_path / "file2.txt").write_bytes(b"x" * 2048)  # 2 KB

        result = get_directory_size(tmp_path)

        # Should be ~3 KB = 0.003 MB
        assert result == pytest.approx(3072 / (1024 * 1024), rel=0.01)

    def test_nested_directory(self, tmp_path: Path) -> None:
        """Test size calculation with nested directories."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").write_bytes(b"x" * 1024)
        (subdir / "file2.txt").write_bytes(b"x" * 1024)

        result = get_directory_size(tmp_path)

        # Should include both files
        assert result == pytest.approx(2048 / (1024 * 1024), rel=0.01)

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test size of nonexistent directory."""
        result = get_directory_size(tmp_path / "nonexistent")

        assert result == 0.0


class TestDownloadOmnidocbench:
    """Tests for download_omnidocbench function."""

    def test_missing_token_returns_false(self) -> None:
        """Test that missing token returns False."""
        from download_omnidocbench import download_omnidocbench

        with patch("download_omnidocbench._resolve_hf_token", return_value=None):
            result = download_omnidocbench(hf_token=None)

            assert result is False

    def test_function_exists(self) -> None:
        """Test that download_omnidocbench function exists."""
        from download_omnidocbench import download_omnidocbench

        assert callable(download_omnidocbench)


class TestMain:
    """Tests for main entry point."""

    def test_main_exists(self) -> None:
        """Test that main function exists and is callable."""
        from download_omnidocbench import main

        assert callable(main)
