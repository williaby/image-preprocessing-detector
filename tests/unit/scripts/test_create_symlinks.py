# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""Tests for scripts/create_symlinks.py - Symlink management.

These tests verify the symlink management utilities correctly:
- Create symlinks from local paths to NFS paths
- Handle existing symlinks and directories
- Verify symlink configurations
- Manage symlink mappings
"""

# Scripts directory added to sys.path via tests/conftest.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

# Scripts directory added to sys.path via tests/conftest.py
import create_symlinks
import pytest
from create_symlinks import SYMLINK_MAPPINGS, create_symlink, verify_symlinks


class TestSymlinkMappings:
    """Tests for SYMLINK_MAPPINGS configuration."""

    def test_mappings_not_empty(self) -> None:
        """Test that mappings list is not empty."""
        assert len(SYMLINK_MAPPINGS) > 0

    def test_mappings_structure(self) -> None:
        """Test that all mappings have correct structure."""
        for mapping in SYMLINK_MAPPINGS:
            assert isinstance(mapping, tuple)
            assert len(mapping) == 2
            local_path, nfs_path = mapping
            assert isinstance(local_path, str)
            assert isinstance(nfs_path, str)

    def test_local_paths_start_with_data(self) -> None:
        """Test that local paths start with data/."""
        for local_path, _ in SYMLINK_MAPPINGS:
            assert local_path.startswith("data/"), (
                f"Path {local_path} doesn't start with data/"
            )

    def test_contains_benchmark_mappings(self) -> None:
        """Test that benchmarks mappings exist."""
        benchmark_mappings = [m for m in SYMLINK_MAPPINGS if "benchmarks" in m[0]]
        assert len(benchmark_mappings) > 0

    def test_contains_training_mappings(self) -> None:
        """Test that training mappings exist."""
        training_mappings = [m for m in SYMLINK_MAPPINGS if "training" in m[0]]
        assert len(training_mappings) > 0

    def test_nfs_paths_correspond_to_local(self) -> None:
        """Test that NFS paths correspond to local paths."""
        for local_path, nfs_path in SYMLINK_MAPPINGS:
            # Extract the dataset name from local path
            dataset_name = local_path.split("/")[-1]
            assert dataset_name in nfs_path, f"{dataset_name} not in {nfs_path}"


class TestCreateSymlink:
    """Tests for create_symlink function."""

    @pytest.fixture
    def mock_paths(self, tmp_path: Path):
        """Setup mock PROJECT_ROOT and NFS_ROOT."""
        project_root = tmp_path / "project"
        nfs_root = tmp_path / "nfs"
        project_root.mkdir()
        nfs_root.mkdir()

        with patch.object(create_symlinks, "PROJECT_ROOT", project_root):
            with patch.object(create_symlinks, "NFS_ROOT", nfs_root):
                yield project_root, nfs_root

    def test_create_symlink_success(self, mock_paths: tuple[Path, Path]) -> None:
        """Test successful symlink creation."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "benchmarks" / "test_dataset"
        nfs_target.mkdir(parents=True)

        # Create parent directory for local path
        (project_root / "data" / "benchmarks").mkdir(parents=True)

        success, message = create_symlink(
            "data/benchmarks/test_dataset", "benchmarks/test_dataset"
        )

        assert success is True
        assert "Created" in message or "correct" in message
        local_path = project_root / "data" / "benchmarks" / "test_dataset"
        assert local_path.is_symlink()

    def test_create_symlink_nfs_target_missing(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test symlink creation when NFS target doesn't exist."""
        _, _ = mock_paths

        success, message = create_symlink(
            "data/benchmarks/missing", "benchmarks/missing"
        )

        assert success is False
        assert "NFS target does not exist" in message

    def test_create_symlink_already_correct(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test when symlink already exists and is correct."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "benchmarks" / "existing"
        nfs_target.mkdir(parents=True)

        # Create local symlink
        local_path = project_root / "data" / "benchmarks" / "existing"
        local_path.parent.mkdir(parents=True)
        local_path.symlink_to(nfs_target)

        success, message = create_symlink(
            "data/benchmarks/existing", "benchmarks/existing"
        )

        assert success is True
        assert "already correct" in message

    def test_create_symlink_replaces_wrong_symlink(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test symlink replacement when pointing to wrong target."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "benchmarks" / "dataset"
        nfs_target.mkdir(parents=True)

        # Create wrong symlink
        local_path = project_root / "data" / "benchmarks" / "dataset"
        local_path.parent.mkdir(parents=True)
        wrong_target = nfs_root / "wrong"
        wrong_target.mkdir()
        local_path.symlink_to(wrong_target)

        success, _ = create_symlink("data/benchmarks/dataset", "benchmarks/dataset")

        assert success is True
        assert local_path.is_symlink()
        assert local_path.readlink() == nfs_target

    def test_create_symlink_empty_directory(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test symlink creation when empty directory exists."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "benchmarks" / "dataset"
        nfs_target.mkdir(parents=True)

        # Create empty local directory
        local_path = project_root / "data" / "benchmarks" / "dataset"
        local_path.mkdir(parents=True)

        success, _ = create_symlink("data/benchmarks/dataset", "benchmarks/dataset")

        assert success is True
        assert local_path.is_symlink()

    def test_create_symlink_non_empty_directory_fails(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test symlink creation fails when non-empty directory exists."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "benchmarks" / "dataset"
        nfs_target.mkdir(parents=True)

        # Create non-empty local directory
        local_path = project_root / "data" / "benchmarks" / "dataset"
        local_path.mkdir(parents=True)
        (local_path / "file.txt").write_text("content")

        success, message = create_symlink(
            "data/benchmarks/dataset", "benchmarks/dataset"
        )

        assert success is False
        assert "not empty" in message

    def test_create_symlink_creates_parent_directories(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test that parent directories are created."""
        project_root, nfs_root = mock_paths

        # Create NFS target
        nfs_target = nfs_root / "nested" / "path" / "dataset"
        nfs_target.mkdir(parents=True)

        # Don't create local parent directories
        success, _ = create_symlink("data/nested/path/dataset", "nested/path/dataset")

        assert success is True
        local_path = project_root / "data" / "nested" / "path" / "dataset"
        assert local_path.parent.exists()


class TestVerifySymlinks:
    """Tests for verify_symlinks function."""

    @pytest.fixture
    def mock_paths_for_verify(self, tmp_path: Path):
        """Setup mock paths with specific mappings."""
        project_root = tmp_path / "project"
        nfs_root = tmp_path / "nfs"
        project_root.mkdir()
        nfs_root.mkdir()

        # Create test mappings
        test_mappings = [
            ("data/benchmarks/valid", "benchmarks/valid"),
            ("data/benchmarks/missing_nfs", "benchmarks/missing_nfs"),
            ("data/benchmarks/missing_local", "benchmarks/missing_local"),
        ]

        with patch.object(create_symlinks, "PROJECT_ROOT", project_root):
            with patch.object(create_symlinks, "NFS_ROOT", nfs_root):
                with patch.object(create_symlinks, "SYMLINK_MAPPINGS", test_mappings):
                    yield project_root, nfs_root, test_mappings

    def test_verify_valid_symlink(
        self, mock_paths_for_verify: tuple[Path, Path, list]
    ) -> None:
        """Test verification of valid symlink."""
        project_root, nfs_root, _ = mock_paths_for_verify

        # Create valid NFS target
        nfs_target = nfs_root / "benchmarks" / "valid"
        nfs_target.mkdir(parents=True)

        # Create valid symlink
        local_path = project_root / "data" / "benchmarks" / "valid"
        local_path.parent.mkdir(parents=True)
        local_path.symlink_to(nfs_target)

        # Setup other required paths
        (nfs_root / "benchmarks" / "missing_local").mkdir(parents=True)

        results = verify_symlinks()

        # Find the valid result
        valid_result = next(r for r in results if r[0] == "data/benchmarks/valid")
        assert valid_result[2] is True
        assert "Valid" in valid_result[3]

    def test_verify_missing_nfs_target(
        self, mock_paths_for_verify: tuple[Path, Path, list]
    ) -> None:
        """Test verification when NFS target is missing."""
        project_root, nfs_root, _ = mock_paths_for_verify

        # Create only valid NFS target
        (nfs_root / "benchmarks" / "valid").mkdir(parents=True)
        (nfs_root / "benchmarks" / "missing_local").mkdir(parents=True)

        # Create symlinks for valid
        local_valid = project_root / "data" / "benchmarks" / "valid"
        local_valid.parent.mkdir(parents=True)
        local_valid.symlink_to(nfs_root / "benchmarks" / "valid")

        results = verify_symlinks()

        # Find the missing NFS result
        missing_result = next(
            r for r in results if r[0] == "data/benchmarks/missing_nfs"
        )
        assert missing_result[2] is False
        assert "NFS target missing" in missing_result[3]

    def test_verify_missing_local_symlink(
        self, mock_paths_for_verify: tuple[Path, Path, list]
    ) -> None:
        """Test verification when local symlink is missing."""
        project_root, nfs_root, _ = mock_paths_for_verify

        # Create all NFS targets
        (nfs_root / "benchmarks" / "valid").mkdir(parents=True)
        (nfs_root / "benchmarks" / "missing_local").mkdir(parents=True)

        # Create only one symlink
        local_valid = project_root / "data" / "benchmarks" / "valid"
        local_valid.parent.mkdir(parents=True)
        local_valid.symlink_to(nfs_root / "benchmarks" / "valid")

        results = verify_symlinks()

        # Find the missing local result
        missing_result = next(
            r for r in results if r[0] == "data/benchmarks/missing_local"
        )
        assert missing_result[2] is False
        assert "Local symlink missing" in missing_result[3]

    def test_verify_returns_tuple_structure(
        self, mock_paths_for_verify: tuple[Path, Path, list]
    ) -> None:
        """Test that verify_symlinks returns correct structure."""
        _, nfs_root, mappings = mock_paths_for_verify

        # Create minimal setup
        (nfs_root / "benchmarks" / "valid").mkdir(parents=True)

        results = verify_symlinks()

        assert isinstance(results, list)
        assert len(results) == len(mappings)

        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 4
            local_rel, nfs_rel, is_valid, status = result
            assert isinstance(local_rel, str)
            assert isinstance(nfs_rel, str)
            assert isinstance(is_valid, bool)
            assert isinstance(status, str)


class TestCreateSymlinkEdgeCases:
    """Edge case tests for create_symlink function."""

    @pytest.fixture
    def mock_paths(self, tmp_path: Path):
        """Setup mock PROJECT_ROOT and NFS_ROOT."""
        project_root = tmp_path / "project"
        nfs_root = tmp_path / "nfs"
        project_root.mkdir()
        nfs_root.mkdir()

        with patch.object(create_symlinks, "PROJECT_ROOT", project_root):
            with patch.object(create_symlinks, "NFS_ROOT", nfs_root):
                yield project_root, nfs_root

    def test_symlink_to_file_target(self, mock_paths: tuple[Path, Path]) -> None:
        """Test symlink creation to a file target."""
        project_root, nfs_root = mock_paths

        # Create file as NFS target (unusual but valid)
        nfs_target = nfs_root / "file.txt"
        nfs_target.write_text("content")

        success, _ = create_symlink("data/file.txt", "file.txt")

        assert success is True
        local_path = project_root / "data" / "file.txt"
        assert local_path.is_symlink()

    def test_symlink_with_special_characters_in_path(
        self, mock_paths: tuple[Path, Path]
    ) -> None:
        """Test symlink with special characters in path."""
        _, nfs_root = mock_paths

        # Create NFS target with hyphen
        nfs_target = nfs_root / "benchmarks" / "diqa-5000"
        nfs_target.mkdir(parents=True)

        success, _ = create_symlink("data/benchmarks/diqa-5000", "benchmarks/diqa-5000")

        assert success is True

    def test_symlink_deeply_nested(self, mock_paths: tuple[Path, Path]) -> None:
        """Test symlink creation for deeply nested paths."""
        project_root, nfs_root = mock_paths

        # Create deeply nested NFS target
        nfs_target = nfs_root / "a" / "b" / "c" / "d" / "dataset"
        nfs_target.mkdir(parents=True)

        success, _ = create_symlink("data/a/b/c/d/dataset", "a/b/c/d/dataset")

        assert success is True
        local_path = project_root / "data" / "a" / "b" / "c" / "d" / "dataset"
        assert local_path.is_symlink()


class TestSymlinkCategories:
    """Tests for symlink categorization."""

    def test_benchmark_paths_use_benchmarks_nfs(self) -> None:
        """Test that benchmark local paths map to benchmarks NFS."""
        for local_path, nfs_path in SYMLINK_MAPPINGS:
            if "benchmarks" in local_path:
                assert nfs_path.startswith("benchmarks/"), (
                    f"Benchmark {local_path} should map to benchmarks/"
                )

    def test_training_paths_use_training_nfs(self) -> None:
        """Test that training local paths map to training NFS."""
        for local_path, nfs_path in SYMLINK_MAPPINGS:
            if "training" in local_path:
                assert nfs_path.startswith("training/"), (
                    f"Training {local_path} should map to training/"
                )

    def test_known_datasets_present(self) -> None:
        """Test that known important datasets are in mappings."""
        dataset_names = [m[0].split("/")[-1] for m in SYMLINK_MAPPINGS]

        # Check for some expected datasets
        expected = ["tablebank", "pubtabnet", "omnidocbench", "iqa_phase2"]
        for expected_name in expected:
            assert expected_name in dataset_names, (
                f"Missing expected dataset: {expected_name}"
            )
