# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Partitioned Parquet writer for scalable storage.

CRITICAL: Does NOT read entire Parquet into memory.
Uses partitioned datasets: parquet_root/dataset_name=X/part-0000.parquet

This module solves P0-2 (monolithic Parquet read-modify-write) by using
Hive-style partitioning. Each dataset is stored in its own partition,
enabling O(1) writes without affecting other datasets.

Benefits:
    - O(1) per-dataset writes (no read-modify-write)
    - Atomic per-dataset replacement
    - pyarrow.dataset provides unified view
    - Efficient predicate pushdown for queries

Example:
    >>> from image_preprocessing_detector.annotation.storage.parquet_writer import (
    ...     PartitionedParquetWriter,
    ... )
    >>>
    >>> writer = PartitionedParquetWriter(Path("/data/parquet"))
    >>> writer.write_dataset("diqa-5000", samples)
    >>>
    >>> # Read single dataset
    >>> table = writer.read_dataset("diqa-5000")
    >>>
    >>> # Query across all datasets with predicate pushdown
    >>> dataset = writer.get_dataset()
    >>> high_quality = dataset.to_table(filter=ds.field("quality_overall") > 0.8)
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from ..integrity.atomic import atomic_write

if TYPE_CHECKING:
    from ..schemas.sample import SampleMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Schema Definition
# ============================================================================


@dataclass
class ParquetSchema:
    """Parquet schema for SampleMetadata storage.

    Defines the columnar schema used for storing annotation metadata.
    Includes nested fields for source, labels, file metadata, and enrichments.
    """

    @staticmethod
    def get_schema() -> pa.Schema:
        """Get PyArrow schema for SampleMetadata.

        Returns:
            PyArrow schema with all fields properly typed
        """
        return pa.schema(
            [
                # Identity
                ("id", pa.string()),
                ("file_hash", pa.string()),
                # Source information
                ("dataset_name", pa.string()),
                ("dataset_version", pa.string()),
                ("original_path", pa.string()),
                ("original_filename", pa.string()),
                ("download_date", pa.string()),
                # Original file metadata
                ("file_format", pa.string()),
                ("width_px", pa.int32()),
                ("height_px", pa.int32()),
                ("channels", pa.int32()),
                ("bit_depth", pa.int32()),
                ("file_size_bytes", pa.int64()),
                ("dpi", pa.int32()),
                ("color_space", pa.string()),
                # Quality scores
                ("quality_overall", pa.float32()),
                ("quality_sharpness", pa.float32()),
                ("diqa_overall", pa.float32()),
                ("diqa_sharpness", pa.float32()),
                ("diqa_color_fidelity", pa.float32()),
                ("ocr_quality_score", pa.int32()),
                # Enrichment metadata
                ("current_enrichment_version", pa.int32()),
                ("enrichment_count", pa.int32()),
                # Record metadata
                ("created_at", pa.string()),
                ("schema_version", pa.string()),
                # Serialized JSON for complex nested fields
                ("original_labels_json", pa.string()),
                ("enrichments_json", pa.string()),
            ]
        )


# ============================================================================
# Writer Implementation
# ============================================================================


class PartitionedParquetWriter:
    """Write samples to partitioned Parquet dataset.

    Structure:
        parquet_root/
        ├── dataset_name=diqa-5000/
        │   └── part-0000.parquet
        ├── dataset_name=smartdoc-qa/
        │   └── part-0000.parquet
        └── ...

    Attributes:
        parquet_root: Root directory for Parquet partitions
        compression: Compression algorithm (default: snappy)
    """

    def __init__(
        self,
        parquet_root: Path,
        compression: str = "snappy",
    ):
        """Initialize the Parquet writer.

        Args:
            parquet_root: Root directory for partitioned storage
            compression: Compression algorithm (snappy, zstd, gzip, none)
        """
        self.parquet_root = Path(parquet_root)
        self.compression = compression
        self.parquet_root.mkdir(parents=True, exist_ok=True)

        # Cache the schema
        self._schema = ParquetSchema.get_schema()

    def write_dataset(
        self,
        dataset_name: str,
        samples: list[SampleMetadata],
    ) -> int:
        """Write samples for a single dataset (atomic replacement).

        Replaces all existing data for this dataset partition.
        Does NOT touch other dataset partitions.

        Args:
            dataset_name: Name of the dataset
            samples: List of SampleMetadata to write

        Returns:
            Number of samples written

        Raises:
            ValueError: If samples list is empty
            IOError: If write fails
        """
        if not samples:
            logger.debug(f"No samples to write for {dataset_name}")
            return 0

        # Create partition directory
        partition_dir = self._get_partition_dir(dataset_name)
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Convert to Arrow table
        table = self._samples_to_table(samples)

        # Write atomically
        output_path = partition_dir / "part-0000.parquet"
        try:
            with atomic_write(output_path, fsync=False) as temp_path:
                pq.write_table(
                    table,
                    temp_path,
                    compression=self.compression,
                    write_statistics=True,
                )
            logger.info(f"Wrote {len(samples)} samples to {dataset_name} partition")
            return len(samples)
        except Exception:
            logger.exception(f"Failed to write {dataset_name}")
            raise

    def append_to_dataset(
        self,
        dataset_name: str,
        samples: list[SampleMetadata],
    ) -> int:
        """Append samples to existing dataset partition.

        Unlike write_dataset, this preserves existing data and adds new samples.
        Creates a new part file to avoid read-modify-write.

        Args:
            dataset_name: Name of the dataset
            samples: List of SampleMetadata to append

        Returns:
            Number of samples appended
        """
        if not samples:
            return 0

        partition_dir = self._get_partition_dir(dataset_name)
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Find next part number
        existing_parts = list(partition_dir.glob("part-*.parquet"))
        next_part = len(existing_parts)

        # Convert and write
        table = self._samples_to_table(samples)
        output_path = partition_dir / f"part-{next_part:04d}.parquet"

        with atomic_write(output_path, fsync=False) as temp_path:
            pq.write_table(
                table,
                temp_path,
                compression=self.compression,
                write_statistics=True,
            )

        logger.info(
            f"Appended {len(samples)} samples to {dataset_name} (part-{next_part:04d})"
        )
        return len(samples)

    def get_dataset(self) -> ds.Dataset:
        """Get unified view of all partitions.

        Returns pyarrow Dataset that can be queried efficiently
        with predicate pushdown.

        Returns:
            pyarrow Dataset for all partitions
        """
        if not self.parquet_root.exists():
            # Return empty dataset
            return ds.dataset([], schema=self._schema)

        # Check if any partitions exist
        partitions = list(self.parquet_root.glob("dataset_name=*/part-*.parquet"))
        if not partitions:
            return ds.dataset([], schema=self._schema)

        return ds.dataset(
            self.parquet_root,
            format="parquet",
            partitioning=ds.partitioning(
                pa.schema([("dataset_name", pa.string())]),
                flavor="hive",
            ),
        )

    def read_all(self) -> pa.Table:
        """Read all data as single table (for compatibility).

        Warning: May use significant memory for large datasets.

        Returns:
            PyArrow Table with all samples
        """
        dataset = self.get_dataset()
        return dataset.to_table()

    def read_dataset(self, dataset_name: str) -> pa.Table:
        """Read single dataset partition efficiently.

        Uses predicate pushdown to only read the relevant partition.

        Args:
            dataset_name: Name of the dataset to read

        Returns:
            PyArrow Table with samples from the specified dataset
        """
        dataset = self.get_dataset()
        return dataset.to_table(filter=ds.field("dataset_name") == dataset_name)

    def delete_dataset(self, dataset_name: str) -> bool:
        """Delete a dataset partition.

        Args:
            dataset_name: Name of the dataset to delete

        Returns:
            True if partition was deleted, False if it didn't exist
        """
        partition_dir = self._get_partition_dir(dataset_name)
        if partition_dir.exists():
            shutil.rmtree(partition_dir)
            logger.info(f"Deleted partition for {dataset_name}")
            return True
        return False

    def list_datasets(self) -> list[str]:
        """List all dataset partitions.

        Returns:
            List of dataset names with existing partitions
        """
        datasets = []
        for path in self.parquet_root.glob("dataset_name=*"):
            if path.is_dir():
                # Extract dataset name from directory name
                name = path.name.replace("dataset_name=", "")
                datasets.append(name)
        return sorted(datasets)

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        datasets = self.list_datasets()
        total_files = 0
        total_size = 0

        for dataset in datasets:
            partition_dir = self._get_partition_dir(dataset)
            for parquet_file in partition_dir.glob("*.parquet"):
                total_files += 1
                total_size += parquet_file.stat().st_size

        return {
            "parquet_root": str(self.parquet_root),
            "dataset_count": len(datasets),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "compression": self.compression,
        }

    def compact_dataset(self, dataset_name: str) -> int:
        """Compact multiple part files into a single file.

        Useful after many append operations to improve read performance.

        Args:
            dataset_name: Name of the dataset to compact

        Returns:
            Number of samples in compacted file
        """
        partition_dir = self._get_partition_dir(dataset_name)
        if not partition_dir.exists():
            return 0

        # Read all parts
        table = self.read_dataset(dataset_name)
        if len(table) == 0:
            return 0

        # Remove old parts
        for part_file in partition_dir.glob("part-*.parquet"):
            part_file.unlink()

        # Write compacted file
        output_path = partition_dir / "part-0000.parquet"
        with atomic_write(output_path, fsync=False) as temp_path:
            pq.write_table(
                table,
                temp_path,
                compression=self.compression,
                write_statistics=True,
            )

        logger.info(f"Compacted {dataset_name}: {len(table)} samples")
        return len(table)

    def _get_partition_dir(self, dataset_name: str) -> Path:
        """Get partition directory for a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Path to partition directory
        """
        # Sanitize dataset name for filesystem
        safe_name = dataset_name.replace("/", "_").replace("\\", "_")
        return self.parquet_root / f"dataset_name={safe_name}"

    def _samples_to_table(
        self,
        samples: list[SampleMetadata],
    ) -> pa.Table:
        """Convert samples to Arrow table.

        Args:
            samples: List of SampleMetadata instances

        Returns:
            PyArrow Table with columnar data
        """
        import json

        # Build column arrays
        columns: dict[str, list[Any]] = {
            "id": [],
            "file_hash": [],
            "dataset_name": [],
            "dataset_version": [],
            "original_path": [],
            "original_filename": [],
            "download_date": [],
            "file_format": [],
            "width_px": [],
            "height_px": [],
            "channels": [],
            "bit_depth": [],
            "file_size_bytes": [],
            "dpi": [],
            "color_space": [],
            "quality_overall": [],
            "quality_sharpness": [],
            "diqa_overall": [],
            "diqa_sharpness": [],
            "diqa_color_fidelity": [],
            "ocr_quality_score": [],
            "current_enrichment_version": [],
            "enrichment_count": [],
            "created_at": [],
            "schema_version": [],
            "original_labels_json": [],
            "enrichments_json": [],
        }

        for sample in samples:
            columns["id"].append(sample.id)
            columns["file_hash"].append(sample.file_hash)
            columns["dataset_name"].append(sample.dataset_name)
            columns["dataset_version"].append(sample.dataset_version)
            columns["original_path"].append(sample.original_path)
            columns["original_filename"].append(sample.original_filename)
            columns["download_date"].append(sample.download_date)

            # File metadata
            columns["file_format"].append(sample.original_file.format)
            columns["width_px"].append(sample.original_file.width_px)
            columns["height_px"].append(sample.original_file.height_px)
            columns["channels"].append(sample.original_file.channels)
            columns["bit_depth"].append(sample.original_file.bit_depth)
            columns["file_size_bytes"].append(sample.original_file.file_size_bytes)
            columns["dpi"].append(sample.original_file.dpi)
            columns["color_space"].append(sample.original_file.color_space)

            # Quality scores from labels
            labels = sample.original_labels
            columns["quality_overall"].append(None)  # From enrichment
            columns["quality_sharpness"].append(None)
            columns["diqa_overall"].append(labels.diqa_overall)
            columns["diqa_sharpness"].append(labels.diqa_sharpness)
            columns["diqa_color_fidelity"].append(labels.diqa_color_fidelity)
            columns["ocr_quality_score"].append(labels.ocr_quality_score)

            # Enrichment metadata
            columns["current_enrichment_version"].append(sample.current_version)
            columns["enrichment_count"].append(len(sample.enrichment_versions))

            # Record metadata
            columns["created_at"].append(sample.created_at)
            columns["schema_version"].append(sample.schema_version)

            # Serialize complex nested fields as JSON
            labels_dict = {
                k: v
                for k, v in sample.original_labels.__dict__.items()
                if v is not None
            }
            columns["original_labels_json"].append(json.dumps(labels_dict))

            # Serialize enrichments
            enrichments = [
                {
                    "version": v.version,
                    "created_at": v.created_at,
                    "method": v.method,
                }
                for v in sample.enrichment_versions
            ]
            columns["enrichments_json"].append(json.dumps(enrichments))

        return pa.Table.from_pydict(columns, schema=self._schema)


__all__ = [
    "ParquetSchema",
    "PartitionedParquetWriter",
]
