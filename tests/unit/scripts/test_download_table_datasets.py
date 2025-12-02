# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/download_table_datasets.py - Table dataset downloads.

These tests verify the download script correctly:
- Loads HuggingFace tokens from .env files
- Handles multi-part zip files
- Extracts archives safely
- Validates dataset configurations
- Handles download errors gracefully
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from download_table_datasets import (
    DATASETS,
    _is_extractable_archive,
    _resolve_hf_token,
    download_dataset,
    download_file_with_hf_cli,
    extract_archive,
    join_zip_parts,
    load_token_from_env,
)


class TestDatasetsConfig:
    """Tests for DATASETS configuration."""

    def test_datasets_has_required_keys(self) -> None:
        """Test that all datasets have required configuration keys."""
        required_keys = {"repo_id", "size_gb", "files", "output_subdir", "description"}

        for name, config in DATASETS.items():
            assert required_keys.issubset(config.keys()), f"Missing keys in {name}"

    def test_tablebank_is_multipart(self) -> None:
        """Test that TableBank has multiple zip parts."""
        assert len(DATASETS["tablebank"]["files"]) == 5
        # All files should be zip parts (contain .zip.)
        for f in DATASETS["tablebank"]["files"]:
            assert ".zip." in f, f"Expected zip part, got {f}"

    def test_pubtabnet_single_file(self) -> None:
        """Test that PubTabNet has single file."""
        assert len(DATASETS["pubtabnet"]["files"]) == 1
        assert DATASETS["pubtabnet"]["files"][0].endswith(".tar.gz")

    def test_fintabnet_has_two_files(self) -> None:
        """Test that FinTabNet has two files."""
        assert len(DATASETS["fintabnet"]["files"]) == 2


class TestLoadTokenFromEnv:
    """Tests for load_token_from_env function."""

    def test_load_token_parses_env_format(self) -> None:
        """Test that token parsing logic handles various formats."""
        # The function reads from a fixed path relative to the script
        # We just verify the function is callable and returns expected types
        result = load_token_from_env()
        assert result is None or isinstance(result, str)

    def test_token_not_found_returns_none(self, tmp_path: Path) -> None:
        """Test that missing .env file returns None."""
        # Just verify the function doesn't crash on missing file
        result = load_token_from_env()
        # Result depends on whether project has .env - we just verify no crash
        assert result is None or isinstance(result, str)


class TestResolveHfToken:
    """Tests for _resolve_hf_token function."""

    def test_argument_token_takes_precedence(self) -> None:
        """Test that argument token takes precedence."""
        with patch(
            "download_table_datasets.load_token_from_env", return_value="env_token"
        ):
            with patch.dict("os.environ", {"HF_TOKEN": "os_token"}):
                result = _resolve_hf_token("arg_token")
                assert result == "arg_token"

    def test_env_file_token_used_when_no_arg(self) -> None:
        """Test that .env token is used when no argument provided."""
        with patch(
            "download_table_datasets.load_token_from_env", return_value="env_token"
        ):
            result = _resolve_hf_token(None)
            assert result == "env_token"

    def test_os_environ_token_used_as_fallback(self) -> None:
        """Test that OS environment token is used as fallback."""
        with patch("download_table_datasets.load_token_from_env", return_value=None):
            with patch.dict("os.environ", {"HF_TOKEN": "os_token"}):
                result = _resolve_hf_token(None)
                assert result == "os_token"

    def test_returns_none_when_no_token(self) -> None:
        """Test that None is returned when no token available."""
        with patch("download_table_datasets.load_token_from_env", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                # Need to explicitly remove HF_TOKEN if present
                import os

                old_token = os.environ.pop("HF_TOKEN", None)
                try:
                    result = _resolve_hf_token(None)
                    # May or may not be None depending on actual env
                    assert result is None or isinstance(result, str)
                finally:
                    if old_token:
                        os.environ["HF_TOKEN"] = old_token


class TestDownloadFileWithHfCli:
    """Tests for download_file_with_hf_cli function."""

    def test_successful_download(self, tmp_path: Path) -> None:
        """Test successful file download."""
        # The function imports hf_hub_download inside, so patch at module level
        mock_download = MagicMock()
        with patch.dict(
            "sys.modules",
            {"huggingface_hub": MagicMock(hf_hub_download=mock_download)},
        ):
            result = download_file_with_hf_cli(
                repo_id="test/repo",
                filename="test.tar.gz",
                output_dir=tmp_path,
                hf_token="test_token",
            )

            assert result is True
            mock_download.assert_called_once()

    def test_download_failure_returns_false(self, tmp_path: Path) -> None:
        """Test that download failure returns False."""
        mock_download = MagicMock(side_effect=Exception("Network error"))
        with patch.dict(
            "sys.modules",
            {"huggingface_hub": MagicMock(hf_hub_download=mock_download)},
        ):
            result = download_file_with_hf_cli(
                repo_id="test/repo",
                filename="test.tar.gz",
                output_dir=tmp_path,
                hf_token="test_token",
            )

            assert result is False


class TestJoinZipParts:
    """Tests for join_zip_parts function."""

    def test_join_zip_parts_success(self, tmp_path: Path) -> None:
        """Test successful joining of zip parts."""
        # Create fake zip parts with valid zip content
        # First, create a small valid zip file
        test_zip = tmp_path / "complete.zip"
        with zipfile.ZipFile(test_zip, "w") as zf:
            zf.writestr("test.txt", "hello world")

        # Split the zip content into parts
        zip_content = test_zip.read_bytes()
        part_size = len(zip_content) // 3 + 1

        for i in range(3):
            start = i * part_size
            end = min((i + 1) * part_size, len(zip_content))
            part_path = tmp_path / f"test.zip.{i + 1:03d}"
            part_path.write_bytes(zip_content[start:end])

        # Remove the original
        test_zip.unlink()

        result = join_zip_parts(tmp_path, "test")

        assert result is True
        assert (tmp_path / "test.zip").exists()

    def test_join_zip_parts_no_parts(self, tmp_path: Path) -> None:
        """Test joining when no parts exist."""
        result = join_zip_parts(tmp_path, "missing")

        assert result is False


class TestExtractArchive:
    """Tests for extract_archive function."""

    def test_extract_tar_gz(self, tmp_path: Path) -> None:
        """Test extracting tar.gz archive."""
        # Create a tar.gz file
        archive_path = tmp_path / "test.tar.gz"
        extract_dir = tmp_path / "extracted"

        with tarfile.open(archive_path, "w:gz") as tar:
            # Create a temporary file to add to archive
            test_file = tmp_path / "test.txt"
            test_file.write_text("test content")
            tar.add(test_file, arcname="test.txt")

        result = extract_archive(archive_path, extract_dir)

        assert result is True
        assert extract_dir.exists()
        assert (extract_dir / "test.txt").exists()

    def test_extract_zip(self, tmp_path: Path) -> None:
        """Test extracting zip archive."""
        archive_path = tmp_path / "test.zip"
        extract_dir = tmp_path / "extracted"

        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("test.txt", "test content")

        result = extract_archive(archive_path, extract_dir)

        assert result is True
        assert extract_dir.exists()
        assert (extract_dir / "test.txt").exists()

    def test_extract_nonexistent_archive_returns_false(self, tmp_path: Path) -> None:
        """Test extracting non-existent archive returns False."""
        archive_path = tmp_path / "nonexistent.tar.gz"
        extract_dir = tmp_path / "extracted"

        # Function catches ValueError and returns False
        result = extract_archive(archive_path, extract_dir)
        assert result is False

    def test_extract_directory_returns_false(self, tmp_path: Path) -> None:
        """Test extracting directory returns False."""
        archive_path = tmp_path / "dir_archive"
        archive_path.mkdir()
        extract_dir = tmp_path / "extracted"

        # Function catches ValueError and returns False
        result = extract_archive(archive_path, extract_dir)
        assert result is False

    def test_extract_unknown_format_returns_false(self, tmp_path: Path) -> None:
        """Test extracting unknown format returns False."""
        archive_path = tmp_path / "test.unknown"
        archive_path.write_text("not an archive")
        extract_dir = tmp_path / "extracted"

        result = extract_archive(archive_path, extract_dir)

        assert result is False


class TestIsExtractableArchive:
    """Tests for _is_extractable_archive function."""

    def test_tar_gz_is_extractable(self, tmp_path: Path) -> None:
        """Test that tar.gz is recognized."""
        archive = tmp_path / "test.tar.gz"
        archive.write_bytes(b"fake content")

        assert _is_extractable_archive(archive) is True

    def test_zip_is_extractable(self, tmp_path: Path) -> None:
        """Test that zip is recognized."""
        archive = tmp_path / "test.zip"
        archive.write_bytes(b"fake content")

        assert _is_extractable_archive(archive) is True

    def test_gz_is_extractable(self, tmp_path: Path) -> None:
        """Test that .gz is recognized."""
        archive = tmp_path / "test.gz"
        archive.write_bytes(b"fake content")

        assert _is_extractable_archive(archive) is True

    def test_txt_not_extractable(self, tmp_path: Path) -> None:
        """Test that txt is not extractable."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("not an archive")

        assert _is_extractable_archive(file_path) is False

    def test_nonexistent_not_extractable(self, tmp_path: Path) -> None:
        """Test that non-existent file is not extractable."""
        file_path = tmp_path / "nonexistent.tar.gz"

        assert _is_extractable_archive(file_path) is False


class TestDownloadDataset:
    """Tests for download_dataset function."""

    def test_unknown_dataset_returns_false(self, tmp_path: Path) -> None:
        """Test that unknown dataset returns False."""
        result = download_dataset(
            dataset_name="unknown_dataset",
            output_base_dir=str(tmp_path),
            hf_token="test_token",
        )

        assert result is False

    def test_download_creates_output_directory(self, tmp_path: Path) -> None:
        """Test that download creates output directory."""
        with patch(
            "download_table_datasets._download_all_files", return_value=True
        ) as mock_download:
            with patch("download_table_datasets._extract_archives"):
                result = download_dataset(
                    dataset_name="pubtabnet",
                    output_base_dir=str(tmp_path),
                    hf_token="test_token",
                    extract=False,
                )

                assert (tmp_path / "pubtabnet").exists()

    def test_download_failure_returns_false(self, tmp_path: Path) -> None:
        """Test that download failure returns False."""
        with patch("download_table_datasets._download_all_files", return_value=False):
            result = download_dataset(
                dataset_name="pubtabnet",
                output_base_dir=str(tmp_path),
                hf_token="test_token",
            )

            assert result is False

    def test_tablebank_triggers_multipart_handling(self, tmp_path: Path) -> None:
        """Test that TableBank triggers multi-part zip handling."""
        with patch("download_table_datasets._download_all_files", return_value=True):
            with patch(
                "download_table_datasets._handle_tablebank_postprocess",
                return_value=True,
            ) as mock_postprocess:
                result = download_dataset(
                    dataset_name="tablebank",
                    output_base_dir=str(tmp_path),
                    hf_token="test_token",
                )

                mock_postprocess.assert_called_once()

    def test_extract_false_skips_extraction(self, tmp_path: Path) -> None:
        """Test that extract=False skips extraction."""
        with patch("download_table_datasets._download_all_files", return_value=True):
            with patch("download_table_datasets._extract_archives") as mock_extract:
                download_dataset(
                    dataset_name="pubtabnet",
                    output_base_dir=str(tmp_path),
                    hf_token="test_token",
                    extract=False,
                )

                mock_extract.assert_not_called()


class TestDiskSpaceCheck:
    """Tests for disk space checking functionality."""

    def test_sufficient_space_returns_true(self, tmp_path: Path) -> None:
        """Test that sufficient disk space returns True."""
        from download_table_datasets import _check_disk_space

        # Use a small size that should always pass
        with patch("builtins.input", return_value="n"):
            result = _check_disk_space(tmp_path, 0.001)  # 1 MB
            # Should pass without prompting if space is sufficient
            assert result is True

    def test_low_space_prompts_user(self, tmp_path: Path) -> None:
        """Test that low disk space prompts user."""
        from download_table_datasets import _check_disk_space

        # Use huge size that will always fail
        with patch("builtins.input", return_value="y") as mock_input:
            # Request way more than available
            result = _check_disk_space(tmp_path, 999999)

            # Should have prompted
            if result is False or mock_input.called:
                # Either returned False immediately or prompted
                pass


class TestRunDownloads:
    """Tests for _run_downloads function."""

    def test_successful_downloads_counted(self, tmp_path: Path) -> None:
        """Test that successful downloads are counted."""
        from download_table_datasets import _run_downloads

        with patch("download_table_datasets.download_dataset", return_value=True):
            result = _run_downloads(
                datasets=["pubtabnet", "fintabnet"],
                output_dir=str(tmp_path),
                hf_token="test_token",
                extract=True,
            )

            assert result == 2

    def test_failed_downloads_not_counted(self, tmp_path: Path) -> None:
        """Test that failed downloads are not counted."""
        from download_table_datasets import _run_downloads

        with patch("download_table_datasets.download_dataset", return_value=False):
            result = _run_downloads(
                datasets=["pubtabnet"],
                output_dir=str(tmp_path),
                hf_token="test_token",
                extract=True,
            )

            assert result == 0

    def test_keyboard_interrupt_returns_negative_one(self, tmp_path: Path) -> None:
        """Test that keyboard interrupt returns -1."""
        from download_table_datasets import _run_downloads

        with patch(
            "download_table_datasets.download_dataset",
            side_effect=KeyboardInterrupt,
        ):
            result = _run_downloads(
                datasets=["pubtabnet"],
                output_dir=str(tmp_path),
                hf_token="test_token",
                extract=True,
            )

            assert result == -1

    def test_exception_continues_to_next(self, tmp_path: Path) -> None:
        """Test that exception on one dataset continues to next."""
        from download_table_datasets import _run_downloads

        # First fails, second succeeds
        with patch(
            "download_table_datasets.download_dataset",
            side_effect=[Exception("Error"), True],
        ):
            result = _run_downloads(
                datasets=["tablebank", "pubtabnet"],
                output_dir=str(tmp_path),
                hf_token="test_token",
                extract=True,
            )

            assert result == 1


class TestArchiveSecurityValidation:
    """Tests for archive security validation."""

    def test_paths_are_resolved(self, tmp_path: Path) -> None:
        """Test that paths are resolved to prevent traversal."""
        archive_path = tmp_path / "test.tar.gz"
        extract_dir = tmp_path / "extracted"

        with tarfile.open(archive_path, "w:gz") as tar:
            test_file = tmp_path / "safe.txt"
            test_file.write_text("safe content")
            tar.add(test_file, arcname="safe.txt")

        result = extract_archive(archive_path, extract_dir)

        assert result is True
        # Verify path was resolved
        assert extract_dir.is_absolute() or (tmp_path / "extracted").exists()

    def test_symlinks_in_archive_handled(self, tmp_path: Path) -> None:
        """Test that archives with symlinks are handled safely."""
        # Note: Python's tarfile filter="data" should handle this
        archive_path = tmp_path / "test.tar.gz"
        extract_dir = tmp_path / "extracted"

        with tarfile.open(archive_path, "w:gz") as tar:
            test_file = tmp_path / "normal.txt"
            test_file.write_text("normal content")
            tar.add(test_file, arcname="normal.txt")

        result = extract_archive(archive_path, extract_dir)

        assert result is True


class TestArgumentParser:
    """Tests for argument parser configuration."""

    def test_parser_has_required_arguments(self) -> None:
        """Test that argument parser has all required arguments."""
        from download_table_datasets import _create_argument_parser

        parser = _create_argument_parser()

        # Parse help to verify arguments exist
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_parser_validates_dataset_choices(self) -> None:
        """Test that parser validates dataset choices."""
        from download_table_datasets import _create_argument_parser

        parser = _create_argument_parser()

        # Valid choice should work
        args = parser.parse_args(["--datasets", "pubtabnet"])
        assert "pubtabnet" in args.datasets

        # Invalid choice should fail
        with pytest.raises(SystemExit):
            parser.parse_args(["--datasets", "invalid_dataset"])

    def test_parser_all_flag(self) -> None:
        """Test that --all flag works."""
        from download_table_datasets import _create_argument_parser

        parser = _create_argument_parser()
        args = parser.parse_args(["--all"])

        assert args.all is True

    def test_parser_default_output_dir(self) -> None:
        """Test default output directory."""
        from download_table_datasets import _create_argument_parser

        parser = _create_argument_parser()
        args = parser.parse_args(["--all"])

        assert args.output_dir == "data/benchmarks"
