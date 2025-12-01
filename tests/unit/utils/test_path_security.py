"""Unit tests for path security utilities.

Tests the validate_safe_path() function for preventing directory traversal attacks.
"""

from pathlib import Path

import pytest

from image_preprocessing_detector.utils.path_security import validate_safe_path


class TestValidateSafePath:
    """Tests for validate_safe_path() function."""

    def test_valid_absolute_path(self, tmp_path: Path) -> None:
        """Test validation of valid absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.touch()

        result = validate_safe_path(test_file)

        assert result == test_file
        assert result.is_absolute()

    def test_valid_relative_path(self, tmp_path: Path) -> None:
        """Test validation of valid relative path."""
        # Create file in temp directory
        test_file = tmp_path / "relative.txt"
        test_file.touch()

        # Change to temp directory and use relative path
        import os

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = validate_safe_path("relative.txt")
            assert result.is_absolute()
            assert result.name == "relative.txt"
        finally:
            os.chdir(original_cwd)

    def test_path_object_input(self, tmp_path: Path) -> None:
        """Test that Path objects are accepted as input."""
        test_file = tmp_path / "pathobj.txt"
        test_file.touch()

        result = validate_safe_path(test_file)

        assert result == test_file
        assert isinstance(result, Path)

    def test_path_traversal_detected_dotdot(self) -> None:
        """Test that path traversal with .. is detected."""
        with pytest.raises(ValueError, match="Path traversal pattern detected"):
            validate_safe_path("../../../etc/passwd")

    def test_path_traversal_detected_relative(self) -> None:
        """Test that path traversal in relative paths is detected."""
        with pytest.raises(ValueError, match="Path traversal pattern detected"):
            validate_safe_path("data/../../../secrets.txt")

    def test_path_traversal_detected_middle(self) -> None:
        """Test that .. in middle of path is detected."""
        with pytest.raises(ValueError, match="Path traversal pattern detected"):
            validate_safe_path("/home/user/../admin/data.txt")

    def test_allowed_base_enforcement(self, tmp_path: Path) -> None:
        """Test that allowed_base directory restriction is enforced."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        allowed_file = base_dir / "allowed.txt"
        allowed_file.touch()

        # Should succeed for file within base
        result = validate_safe_path(allowed_file, allowed_base=base_dir)
        assert result == allowed_file

    def test_allowed_base_blocks_escape(self, tmp_path: Path) -> None:
        """Test that allowed_base blocks paths outside the directory."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        outside_file = tmp_path / "outside.txt"
        outside_file.touch()

        # Should fail for file outside base
        with pytest.raises(ValueError, match="outside allowed base directory"):
            validate_safe_path(outside_file, allowed_base=base_dir)

    def test_allowed_base_subdirectory(self, tmp_path: Path) -> None:
        """Test that subdirectories within allowed_base are permitted."""
        base_dir = tmp_path / "base"
        sub_dir = base_dir / "subdir"
        sub_dir.mkdir(parents=True)
        sub_file = sub_dir / "file.txt"
        sub_file.touch()

        result = validate_safe_path(sub_file, allowed_base=base_dir)
        assert result == sub_file

    def test_must_exist_true_existing_file(self, tmp_path: Path) -> None:
        """Test must_exist=True with existing file."""
        test_file = tmp_path / "exists.txt"
        test_file.touch()

        result = validate_safe_path(test_file, must_exist=True)
        assert result == test_file

    def test_must_exist_true_missing_file(self, tmp_path: Path) -> None:
        """Test must_exist=True with missing file raises FileNotFoundError."""
        missing_file = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError, match="Path does not exist"):
            validate_safe_path(missing_file, must_exist=True)

    def test_must_exist_false_missing_file(self, tmp_path: Path) -> None:
        """Test must_exist=False allows missing files."""
        missing_file = tmp_path / "missing.txt"

        result = validate_safe_path(missing_file, must_exist=False)
        assert result.is_absolute()
        assert not result.exists()

    def test_string_path_input(self, tmp_path: Path) -> None:
        """Test that string paths are converted to Path objects."""
        test_file = tmp_path / "string_path.txt"
        test_file.touch()

        result = validate_safe_path(str(test_file))

        assert isinstance(result, Path)
        assert result == test_file

    def test_combined_restrictions(self, tmp_path: Path) -> None:
        """Test combination of allowed_base and must_exist."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        test_file = base_dir / "combined.txt"
        test_file.touch()

        result = validate_safe_path(test_file, allowed_base=base_dir, must_exist=True)
        assert result == test_file

    def test_combined_restrictions_violation(self, tmp_path: Path) -> None:
        """Test that violations are caught with combined restrictions."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        outside_file = tmp_path / "outside.txt"
        # Don't create the file

        # Should fail on base directory check first
        with pytest.raises(ValueError, match="outside allowed base directory"):
            validate_safe_path(outside_file, allowed_base=base_dir, must_exist=True)

    def test_symlink_resolution(self, tmp_path: Path) -> None:
        """Test that symlinks are resolved correctly."""
        real_file = tmp_path / "real.txt"
        real_file.touch()
        link_file = tmp_path / "link.txt"
        link_file.symlink_to(real_file)

        result = validate_safe_path(link_file)

        # Should resolve to the real file
        assert result == real_file

    def test_empty_path_string(self) -> None:
        """Test handling of empty path string."""
        # Empty path resolves to current working directory
        result = validate_safe_path("")
        assert result.is_absolute()
        assert result.exists()

    def test_root_path(self) -> None:
        """Test validation of root path."""
        result = validate_safe_path("/")
        assert result == Path("/")

    def test_home_directory_expansion(self) -> None:
        """Test that ~ is expanded properly."""
        # Path.resolve() handles ~ expansion
        result = validate_safe_path(Path("~").expanduser())
        assert result.is_absolute()
        assert result.exists()
