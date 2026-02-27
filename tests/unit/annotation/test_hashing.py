"""Unit tests for integrity hashing utilities.

Tests the P0-1 fix (full-file SHA256) and P1-3 fix (deterministic sample IDs).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from image_preprocessing_detector.annotation.integrity import (
    DEFAULT_CHUNK_SIZE,
    compute_content_hash,
    compute_full_sha256,
    compute_sample_id,
    compute_string_hash,
    verify_file_hash,
)


class TestComputeFullSHA256:
    """Test full-file SHA256 hashing (P0-1 fix)."""

    def test_hash_small_file(self, tmp_path: Path) -> None:
        """Test hashing a small file."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello, World!")

        file_hash = compute_full_sha256(test_file)

        # SHA256 of "Hello, World!" is known
        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert file_hash == expected
        assert len(file_hash) == 64  # SHA256 produces 64 hex chars

    def test_hash_empty_file(self, tmp_path: Path) -> None:
        """Test hashing an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")

        file_hash = compute_full_sha256(test_file)

        # SHA256 of empty string is known
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert file_hash == expected

    def test_hash_large_file(self, tmp_path: Path) -> None:
        """Test hashing a file larger than chunk size."""
        test_file = tmp_path / "large.bin"

        # Create a file larger than DEFAULT_CHUNK_SIZE (64KB)
        content = b"A" * (DEFAULT_CHUNK_SIZE * 2 + 1000)
        test_file.write_bytes(content)

        file_hash = compute_full_sha256(test_file)

        # Verify it's a valid SHA256 hash
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_hash_binary_file(self, tmp_path: Path) -> None:
        """Test hashing a binary file."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(bytes(range(256)))

        file_hash = compute_full_sha256(test_file)

        assert len(file_hash) == 64

    def test_hash_file_not_found(self, tmp_path: Path) -> None:
        """Test hashing non-existent file raises error."""
        test_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            compute_full_sha256(test_file)

    def test_hash_is_deterministic(self, tmp_path: Path) -> None:
        """Test that same content always produces same hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Deterministic content")

        hash1 = compute_full_sha256(test_file)
        hash2 = compute_full_sha256(test_file)
        hash3 = compute_full_sha256(test_file)

        assert hash1 == hash2 == hash3

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        hash1 = compute_full_sha256(file1)
        hash2 = compute_full_sha256(file2)

        assert hash1 != hash2

    def test_full_file_hash_vs_partial(self, tmp_path: Path) -> None:
        """Test that we hash the FULL file, not just first 64KB (P0-1 fix)."""
        test_file = tmp_path / "partial_test.bin"

        # First 64KB is all A's, rest is B's
        content = b"A" * DEFAULT_CHUNK_SIZE + b"B" * DEFAULT_CHUNK_SIZE
        test_file.write_bytes(content)

        full_hash = compute_full_sha256(test_file)

        # If we only hashed first 64KB, we'd get hash of just A's
        partial_content = b"A" * DEFAULT_CHUNK_SIZE
        partial_hash = compute_content_hash(partial_content)

        # Full hash should be different from partial
        assert full_hash != partial_hash


class TestComputeSampleId:
    """Test deterministic sample ID generation (P1-3 fix)."""

    def test_generate_sample_id(self) -> None:
        """Test generating a sample ID."""
        sample_id = compute_sample_id(
            dataset_name="diqa-5000",
            relative_path="train/img001.png",
            file_hash="abc123def456" * 5,
        )

        assert len(sample_id) == 32
        assert all(c in "0123456789abcdef" for c in sample_id)

    def test_sample_id_is_deterministic(self) -> None:
        """Test that same inputs always produce same sample ID."""
        args = {
            "dataset_name": "diqa-5000",
            "relative_path": "train/img001.png",
            "file_hash": "abc123def456" * 5,
        }

        id1 = compute_sample_id(**args)
        id2 = compute_sample_id(**args)
        id3 = compute_sample_id(**args)

        assert id1 == id2 == id3

    def test_different_dataset_different_id(self) -> None:
        """Test that different dataset name produces different ID."""
        common_args = {
            "relative_path": "train/img001.png",
            "file_hash": "abc123def456" * 5,
        }

        id1 = compute_sample_id(dataset_name="diqa-5000", **common_args)
        id2 = compute_sample_id(dataset_name="smartdoc-qa", **common_args)

        assert id1 != id2

    def test_different_path_different_id(self) -> None:
        """Test that different relative path produces different ID."""
        common_args = {
            "dataset_name": "diqa-5000",
            "file_hash": "abc123def456" * 5,
        }

        id1 = compute_sample_id(relative_path="train/img001.png", **common_args)
        id2 = compute_sample_id(relative_path="train/img002.png", **common_args)

        assert id1 != id2

    def test_different_hash_different_id(self) -> None:
        """Test that different file hash produces different ID."""
        common_args = {
            "dataset_name": "diqa-5000",
            "relative_path": "train/img001.png",
        }

        id1 = compute_sample_id(file_hash="a" * 64, **common_args)
        id2 = compute_sample_id(file_hash="b" * 64, **common_args)

        assert id1 != id2

    def test_no_collision_with_prefix_suffix(self) -> None:
        """Test that separator prevents prefix/suffix collisions."""
        # These could collide without proper separation
        id1 = compute_sample_id(
            dataset_name="dataset",
            relative_path="path",
            file_hash="hash",
        )

        id2 = compute_sample_id(
            dataset_name="dataset:path",
            relative_path="",
            file_hash="hash",
        )

        assert id1 != id2


class TestComputeContentHash:
    """Test in-memory content hashing."""

    def test_hash_bytes(self) -> None:
        """Test hashing byte content."""
        content_hash = compute_content_hash(b"Hello, World!")

        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert content_hash == expected

    def test_hash_empty_bytes(self) -> None:
        """Test hashing empty bytes."""
        content_hash = compute_content_hash(b"")

        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert content_hash == expected


class TestComputeStringHash:
    """Test string content hashing."""

    def test_hash_string(self) -> None:
        """Test hashing string content."""
        string_hash = compute_string_hash("Hello, World!")

        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert string_hash == expected

    def test_hash_empty_string(self) -> None:
        """Test hashing empty string."""
        string_hash = compute_string_hash("")

        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert string_hash == expected

    def test_hash_unicode_string(self) -> None:
        """Test hashing unicode string."""
        string_hash = compute_string_hash("Hello, 世界!")

        assert len(string_hash) == 64


class TestVerifyFileHash:
    """Test file hash verification."""

    def test_verify_correct_hash(self, tmp_path: Path) -> None:
        """Test verifying correct hash returns True."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"

        assert verify_file_hash(test_file, expected) is True

    def test_verify_incorrect_hash(self, tmp_path: Path) -> None:
        """Test verifying incorrect hash returns False."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        assert verify_file_hash(test_file, wrong_hash) is False

    def test_verify_case_insensitive(self, tmp_path: Path) -> None:
        """Test that verification is case-insensitive."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        lower_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        upper_hash = "DFFD6021BB2BD5B0AF676290809EC3A53191DD81C7F70A4B28688A362182986F"

        assert verify_file_hash(test_file, lower_hash) is True
        assert verify_file_hash(test_file, upper_hash) is True

    def test_verify_nonexistent_file(self, tmp_path: Path) -> None:
        """Test verifying nonexistent file raises error."""
        test_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            verify_file_hash(test_file, "somehash")
