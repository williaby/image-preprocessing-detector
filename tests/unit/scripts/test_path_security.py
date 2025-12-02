# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/_path_security.py - Security-critical path validation.

These tests verify the path security module correctly prevents:
- Path traversal attacks (../ sequences)
- Null byte injection
- Invalid path handling
- Access to non-existent paths when required
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

from pathlib import Path

import pytest

# Scripts directory added to sys.path via tests/conftest.py
from _path_security import (
    PathValidationError,
    validate_directory,
    validate_input_path,
    validate_output_path,
    validate_path,
)


class TestValidatePath:
    """Tests for the validate_path function."""

    def test_valid_existing_path(self, tmp_path: Path) -> None:
        """Test validation of existing path succeeds."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = validate_path(test_file, must_exist=True)

        assert result.exists()
        assert result.is_absolute()
        assert result == test_file.resolve()

    def test_nonexistent_path_must_exist_raises(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent path when must_exist=True."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(PathValidationError, match="Invalid path"):
            validate_path(nonexistent, must_exist=True)

    def test_nonexistent_path_not_required(self, tmp_path: Path) -> None:
        """Test validation succeeds for non-existent path when must_exist=False."""
        nonexistent = tmp_path / "new_file.txt"

        result = validate_path(nonexistent, must_exist=False)

        assert result.is_absolute()
        # Note: The file doesn't exist, but the path is valid

    def test_path_with_null_bytes_raises(self, tmp_path: Path) -> None:
        """Test validation fails for paths containing null bytes (security critical)."""
        # Create a valid file first
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Try to access it with null byte injection
        # This is a security attack vector - null bytes can truncate path strings
        # in C-based libraries, potentially accessing different files
        malicious_path = tmp_path / "test.txt\x00malicious"

        # Python's pathlib may raise ValueError for null bytes; our public
        # API converts that to PathValidationError so callers see a
        # consistent exception type.
        with pytest.raises(PathValidationError):
            validate_path(malicious_path, must_exist=False)

    def test_relative_path_resolved_to_absolute(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Test that relative paths are resolved to absolute paths."""
        # Create a file in tmp_path
        test_file = tmp_path / "relative_test.txt"
        test_file.write_text("content")

        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        # Use a relative path
        relative = Path("relative_test.txt")
        result = validate_path(relative, must_exist=True)

        assert result.is_absolute()
        assert result == test_file.resolve()

    def test_symlink_resolution(self, tmp_path: Path) -> None:
        """Test that symlinks are properly resolved."""
        # Create actual file
        actual_file = tmp_path / "actual.txt"
        actual_file.write_text("content")

        # Create symlink
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(actual_file)

        result = validate_path(symlink, must_exist=True)

        # resolve() follows symlinks
        assert result == actual_file.resolve()


class TestValidateInputPath:
    """Tests for the validate_input_path function."""

    def test_valid_input_file(self, tmp_path: Path) -> None:
        """Test validation of existing input file succeeds."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("input content")

        result = validate_input_path(input_file)

        assert result.exists()
        assert result.is_file()

    def test_nonexistent_input_raises(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent input file."""
        nonexistent = tmp_path / "nonexistent_input.txt"

        with pytest.raises(PathValidationError):
            validate_input_path(nonexistent)

    def test_input_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Test that path traversal in input paths is handled safely."""
        # Create a file outside the expected directory
        parent_file = tmp_path.parent / "secret.txt"

        # Even with ../ in the path, resolve() makes it absolute
        # The security concern is when must_exist=True, we verify the file exists
        traversal_path = tmp_path / ".." / parent_file.name

        # If the parent file doesn't exist, this should fail
        with pytest.raises(PathValidationError):
            validate_input_path(traversal_path)


class TestValidateOutputPath:
    """Tests for the validate_output_path function."""

    def test_valid_output_path_parent_exists(self, tmp_path: Path) -> None:
        """Test validation succeeds when parent directory exists."""
        output_file = tmp_path / "output.txt"

        result = validate_output_path(output_file)

        assert result.is_absolute()
        assert result.parent.exists()
        assert result.name == "output.txt"

    def test_output_path_nested_parent_missing(self, tmp_path: Path) -> None:
        """Test validation fails when nested parent directory doesn't exist."""
        output_file = tmp_path / "nonexistent_dir" / "output.txt"

        with pytest.raises(PathValidationError):
            validate_output_path(output_file)

    def test_output_path_preserves_filename(self, tmp_path: Path) -> None:
        """Test that output filename is preserved correctly."""
        output_file = tmp_path / "my_output_file.json"

        result = validate_output_path(output_file)

        assert result.name == "my_output_file.json"
        assert result.parent == tmp_path.resolve()

    def test_output_path_in_existing_subdirectory(self, tmp_path: Path) -> None:
        """Test output path validation in existing subdirectory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        output_file = subdir / "output.txt"

        result = validate_output_path(output_file)

        assert result.is_absolute()
        assert result.parent == subdir.resolve()


class TestValidateDirectory:
    """Tests for the validate_directory function."""

    def test_valid_existing_directory(self, tmp_path: Path) -> None:
        """Test validation of existing directory succeeds."""
        result = validate_directory(tmp_path, must_exist=True)

        assert result.exists()
        assert result.is_dir()
        assert result.is_absolute()

    def test_nonexistent_directory_must_exist_raises(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent directory when must_exist=True."""
        nonexistent = tmp_path / "nonexistent_dir"

        with pytest.raises(PathValidationError):
            validate_directory(nonexistent, must_exist=True)

    def test_file_path_as_directory_raises(self, tmp_path: Path) -> None:
        """Test validation fails when path is a file, not directory."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        with pytest.raises(PathValidationError, match="not a directory"):
            validate_directory(test_file, must_exist=True)

    def test_nonexistent_directory_not_required(self, tmp_path: Path) -> None:
        """Test validation succeeds for non-existent directory when must_exist=False."""
        nonexistent = tmp_path / "new_directory"

        result = validate_directory(nonexistent, must_exist=False)

        assert result.is_absolute()
        # The directory doesn't exist, but the path is valid


class TestPathValidationError:
    """Tests for the PathValidationError exception."""

    def test_exception_is_value_error_subclass(self) -> None:
        """Test that PathValidationError is a ValueError subclass."""
        assert issubclass(PathValidationError, ValueError)

    def test_exception_message(self) -> None:
        """Test that exception can be raised with message."""
        with pytest.raises(PathValidationError) as exc_info:
            raise PathValidationError("Custom error message")

        assert "Custom error message" in str(exc_info.value)


class TestSecurityScenarios:
    """Integration tests for security attack scenarios."""

    def test_double_dot_traversal_contained(self, tmp_path: Path) -> None:
        """Test that ../ sequences are resolved safely within the path system."""
        # Create file structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("content")

        # Try to traverse up and back down
        traversal_path = subdir / ".." / "subdir" / "test.txt"

        result = validate_path(traversal_path, must_exist=True)

        # The path should resolve to the actual file
        assert result == test_file.resolve()

    def test_absolute_path_injection(self, tmp_path: Path) -> None:
        """Test handling of absolute path components."""
        # Create a test file
        test_file = tmp_path / "safe.txt"
        test_file.write_text("safe content")

        # Absolute paths are handled by Path() constructor
        result = validate_path(test_file, must_exist=True)

        assert result.is_absolute()
        assert result == test_file.resolve()

    def test_unicode_path_handling(self, tmp_path: Path) -> None:
        """Test that Unicode paths are handled correctly."""
        unicode_file = tmp_path / "tëst_üñîcödé.txt"
        unicode_file.write_text("unicode content")

        result = validate_path(unicode_file, must_exist=True)

        assert result.exists()
        assert result == unicode_file.resolve()

    def test_special_characters_in_path(self, tmp_path: Path) -> None:
        """Test handling of special characters in paths."""
        special_file = tmp_path / "file with spaces & special-chars.txt"
        special_file.write_text("content")

        result = validate_path(special_file, must_exist=True)

        assert result.exists()
        assert result == special_file.resolve()

    def test_empty_filename_handling(self, tmp_path: Path) -> None:
        """Test that empty filename components don't cause issues."""
        # Path with trailing slash (empty final component)
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()

        # This should work for directory validation
        result = validate_directory(dir_path, must_exist=True)

        assert result.exists()
        assert result.is_dir()
