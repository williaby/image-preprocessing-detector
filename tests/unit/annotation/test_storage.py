# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Tests for partitioned Parquet storage.

Test Coverage:
    - ParquetSchema definition
    - PartitionedParquetWriter operations
    - Partition management
    - Dataset queries
"""

from __future__ import annotations

import pyarrow as pa
import pyarrow.dataset as ds
import pytest

from image_preprocessing_detector.annotation.schemas.immutable import (
    OriginalFileMetadata,
    OriginalLabels,
)
from image_preprocessing_detector.annotation.schemas.sample import (
    SampleMetadata,
)
from image_preprocessing_detector.annotation.storage.parquet_writer import (
    ParquetSchema,
    PartitionedParquetWriter,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_metadata() -> SampleMetadata:
    """Create a sample SampleMetadata instance."""
    return SampleMetadata(
        id="test123",
        file_hash="sha256:abc123",
        dataset_name="test-dataset",
        dataset_version="1.0",
        original_path="train/img001.png",
        original_filename="img001.png",
        download_date="2025-01-26",
        original_labels=OriginalLabels(
            diqa_overall=4.2,
            diqa_sharpness=4.0,
        ),
        original_file=OriginalFileMetadata(
            format="png",
            width_px=640,
            height_px=480,
            channels=3,
            bit_depth=8,
            file_size_bytes=50000,
            dpi=300,
        ),
    )


@pytest.fixture
def multiple_samples() -> list[SampleMetadata]:
    """Create multiple sample instances."""
    samples = []
    for i in range(5):
        sample = SampleMetadata(
            id=f"test{i:03d}",
            file_hash=f"sha256:hash{i}",
            dataset_name="test-dataset",
            dataset_version="1.0",
            original_path=f"train/img{i:03d}.png",
            original_filename=f"img{i:03d}.png",
            download_date="2025-01-26",
            original_labels=OriginalLabels(
                diqa_overall=4.0 + (i * 0.1),
            ),
            original_file=OriginalFileMetadata(
                format="png",
                width_px=640 + i,
                height_px=480 + i,
                channels=3,
                bit_depth=8,
                file_size_bytes=50000 + (i * 1000),
            ),
        )
        samples.append(sample)
    return samples


@pytest.fixture
def writer(tmp_path) -> PartitionedParquetWriter:
    """Create a PartitionedParquetWriter with temp directory."""
    return PartitionedParquetWriter(tmp_path / "parquet")


# ============================================================================
# Schema Tests
# ============================================================================


class TestParquetSchema:
    """Test ParquetSchema definition."""

    def test_get_schema(self):
        """Test schema has expected fields."""
        schema = ParquetSchema.get_schema()

        assert isinstance(schema, pa.Schema)
        assert "id" in schema.names
        assert "file_hash" in schema.names
        assert "dataset_name" in schema.names
        assert "original_labels_json" in schema.names
        assert "enrichments_json" in schema.names

    def test_schema_field_types(self):
        """Test schema field types are correct."""
        schema = ParquetSchema.get_schema()

        assert schema.field("id").type == pa.string()
        assert schema.field("width_px").type == pa.int32()
        assert schema.field("file_size_bytes").type == pa.int64()
        assert schema.field("quality_overall").type == pa.float32()


# ============================================================================
# Writer Initialization Tests
# ============================================================================


class TestWriterInitialization:
    """Test PartitionedParquetWriter initialization."""

    def test_creates_directory(self, tmp_path):
        """Test writer creates parquet root directory."""
        parquet_root = tmp_path / "new_parquet_dir"
        assert not parquet_root.exists()

        writer = PartitionedParquetWriter(parquet_root)

        assert parquet_root.exists()

    def test_compression_setting(self, tmp_path):
        """Test compression setting is stored."""
        writer = PartitionedParquetWriter(tmp_path, compression="zstd")
        assert writer.compression == "zstd"


# ============================================================================
# Write Operations Tests
# ============================================================================


class TestWriteOperations:
    """Test write operations."""

    def test_write_single_sample(self, writer, sample_metadata):
        """Test writing a single sample."""
        count = writer.write_dataset("test-dataset", [sample_metadata])

        assert count == 1
        assert "test-dataset" in writer.list_datasets()

    def test_write_multiple_samples(self, writer, multiple_samples):
        """Test writing multiple samples."""
        count = writer.write_dataset("test-dataset", multiple_samples)

        assert count == 5

    def test_write_empty_list(self, writer):
        """Test writing empty list returns 0."""
        count = writer.write_dataset("test-dataset", [])

        assert count == 0
        assert "test-dataset" not in writer.list_datasets()

    def test_write_creates_partition(self, writer, sample_metadata, tmp_path):
        """Test write creates partition directory."""
        writer.write_dataset("my-dataset", [sample_metadata])

        partition_dir = tmp_path / "parquet" / "dataset_name=my-dataset"
        assert partition_dir.exists()
        assert (partition_dir / "part-0000.parquet").exists()

    def test_write_replaces_existing(self, writer, multiple_samples):
        """Test write replaces existing data."""
        # Write initial data
        writer.write_dataset("test-dataset", multiple_samples)

        # Write new data (should replace)
        new_sample = multiple_samples[0]
        writer.write_dataset("test-dataset", [new_sample])

        # Should only have 1 sample now
        table = writer.read_dataset("test-dataset")
        assert len(table) == 1


# ============================================================================
# Append Operations Tests
# ============================================================================


class TestAppendOperations:
    """Test append operations."""

    def test_append_creates_new_part(self, writer, multiple_samples):
        """Test append creates new part file."""
        # Initial write
        writer.write_dataset("test-dataset", multiple_samples[:2])

        # Append
        count = writer.append_to_dataset("test-dataset", multiple_samples[2:])

        assert count == 3

        # Read all should have 5 samples
        table = writer.read_dataset("test-dataset")
        assert len(table) == 5

    def test_append_to_nonexistent(self, writer, sample_metadata):
        """Test append to nonexistent dataset."""
        count = writer.append_to_dataset("new-dataset", [sample_metadata])

        assert count == 1
        assert "new-dataset" in writer.list_datasets()


# ============================================================================
# Read Operations Tests
# ============================================================================


class TestReadOperations:
    """Test read operations."""

    def test_read_single_dataset(self, writer, multiple_samples):
        """Test reading a single dataset."""
        writer.write_dataset("test-dataset", multiple_samples)

        table = writer.read_dataset("test-dataset")

        assert len(table) == 5
        assert "id" in table.column_names

    def test_read_nonexistent_dataset(self, writer):
        """Test reading nonexistent dataset returns empty table."""
        table = writer.read_dataset("nonexistent")

        assert len(table) == 0

    def test_read_all_datasets(self, writer, multiple_samples):
        """Test reading all datasets."""
        # Write to multiple datasets
        writer.write_dataset("dataset-a", multiple_samples[:2])
        writer.write_dataset("dataset-b", multiple_samples[2:])

        table = writer.read_all()

        assert len(table) == 5

    def test_get_dataset_returns_dataset(self, writer, multiple_samples):
        """Test get_dataset returns pyarrow Dataset."""
        writer.write_dataset("test-dataset", multiple_samples)

        dataset = writer.get_dataset()

        assert isinstance(dataset, ds.Dataset)

    def test_empty_dataset(self, writer):
        """Test get_dataset on empty storage."""
        dataset = writer.get_dataset()

        assert isinstance(dataset, ds.Dataset)
        table = dataset.to_table()
        assert len(table) == 0


# ============================================================================
# Delete Operations Tests
# ============================================================================


class TestDeleteOperations:
    """Test delete operations."""

    def test_delete_existing_dataset(self, writer, sample_metadata):
        """Test deleting existing dataset."""
        writer.write_dataset("test-dataset", [sample_metadata])
        assert "test-dataset" in writer.list_datasets()

        result = writer.delete_dataset("test-dataset")

        assert result is True
        assert "test-dataset" not in writer.list_datasets()

    def test_delete_nonexistent_dataset(self, writer):
        """Test deleting nonexistent dataset returns False."""
        result = writer.delete_dataset("nonexistent")

        assert result is False


# ============================================================================
# List and Stats Tests
# ============================================================================


class TestListAndStats:
    """Test listing and statistics."""

    def test_list_datasets_empty(self, writer):
        """Test listing datasets when empty."""
        datasets = writer.list_datasets()

        assert datasets == []

    def test_list_datasets_multiple(self, writer, sample_metadata):
        """Test listing multiple datasets."""
        writer.write_dataset("dataset-a", [sample_metadata])
        writer.write_dataset("dataset-b", [sample_metadata])
        writer.write_dataset("dataset-c", [sample_metadata])

        datasets = writer.list_datasets()

        assert len(datasets) == 3
        assert datasets == sorted(datasets)  # Should be sorted

    def test_get_stats(self, writer, multiple_samples):
        """Test getting storage statistics."""
        writer.write_dataset("test-dataset", multiple_samples)

        stats = writer.get_stats()

        assert stats["dataset_count"] == 1
        assert stats["total_files"] == 1
        assert stats["total_size_bytes"] > 0
        assert stats["compression"] == "snappy"


# ============================================================================
# Compact Operations Tests
# ============================================================================


class TestCompactOperations:
    """Test compact operations."""

    def test_compact_multiple_parts(self, writer, multiple_samples):
        """Test compacting multiple part files."""
        # Create multiple parts via append
        writer.write_dataset("test-dataset", multiple_samples[:2])
        writer.append_to_dataset("test-dataset", multiple_samples[2:4])
        writer.append_to_dataset("test-dataset", multiple_samples[4:])

        # Compact
        count = writer.compact_dataset("test-dataset")

        assert count == 5

        # Should have only one part file now
        partition_dir = writer._get_partition_dir("test-dataset")
        parts = list(partition_dir.glob("part-*.parquet"))
        assert len(parts) == 1

    def test_compact_nonexistent(self, writer):
        """Test compacting nonexistent dataset."""
        count = writer.compact_dataset("nonexistent")

        assert count == 0


# ============================================================================
# Data Integrity Tests
# ============================================================================


class TestDataIntegrity:
    """Test data integrity after round-trip."""

    def test_roundtrip_preserves_data(self, writer, sample_metadata):
        """Test data is preserved after write/read cycle."""
        writer.write_dataset("test-dataset", [sample_metadata])

        table = writer.read_dataset("test-dataset")

        # Check key fields
        assert table.column("id").to_pylist()[0] == "test123"
        assert table.column("file_hash").to_pylist()[0] == "sha256:abc123"
        assert table.column("width_px").to_pylist()[0] == 640
        assert table.column("diqa_overall").to_pylist()[0] == pytest.approx(4.2)

    def test_json_fields_are_valid(self, writer, sample_metadata):
        """Test JSON fields contain valid JSON."""
        import json

        writer.write_dataset("test-dataset", [sample_metadata])
        table = writer.read_dataset("test-dataset")

        labels_json = table.column("original_labels_json").to_pylist()[0]
        labels = json.loads(labels_json)

        assert labels["diqa_overall"] == 4.2
        assert labels["diqa_sharpness"] == 4.0


# ============================================================================
# Integration Tests
# ============================================================================


class TestStorageIntegration:
    """Integration tests for storage workflows."""

    def test_multi_dataset_workflow(self, writer, multiple_samples):
        """Test complete multi-dataset workflow."""
        # Write multiple datasets
        writer.write_dataset("dataset-a", multiple_samples[:2])
        writer.write_dataset("dataset-b", multiple_samples[2:4])
        writer.write_dataset("dataset-c", multiple_samples[4:])

        # Verify counts
        assert len(writer.list_datasets()) == 3

        # Read individual datasets
        assert len(writer.read_dataset("dataset-a")) == 2
        assert len(writer.read_dataset("dataset-b")) == 2
        assert len(writer.read_dataset("dataset-c")) == 1

        # Read all
        assert len(writer.read_all()) == 5

        # Delete one
        writer.delete_dataset("dataset-b")
        assert len(writer.list_datasets()) == 2
        assert len(writer.read_all()) == 3

    def test_append_and_compact_workflow(self, writer, multiple_samples):
        """Test append and compact workflow."""
        # Incremental writes via append
        for i, sample in enumerate(multiple_samples):
            writer.append_to_dataset("incremental", [sample])

        # Should have 5 part files
        partition_dir = writer._get_partition_dir("incremental")
        assert len(list(partition_dir.glob("part-*.parquet"))) == 5

        # Compact
        writer.compact_dataset("incremental")

        # Should have 1 part file with all 5 samples
        assert len(list(partition_dir.glob("part-*.parquet"))) == 1
        assert len(writer.read_dataset("incremental")) == 5
