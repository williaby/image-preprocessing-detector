# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Storage layer for the annotation system.

This package provides storage implementations for annotation metadata:

Modules:
    - parquet_writer.py: Partitioned Parquet storage (P0-2 fix)

Design Principles:
    1. No Read-Modify-Write: Partitioned storage enables O(1) dataset writes
    2. Atomic Operations: Per-dataset replacement without corrupting others
    3. Unified View: pyarrow.dataset provides efficient cross-partition queries
    4. Scalability: Supports millions of samples without memory issues

Storage Structure:
    parquet_root/
    ├── dataset_name=diqa-5000/
    │   └── part-0000.parquet
    ├── dataset_name=smartdoc-qa/
    │   └── part-0000.parquet
    └── ...

Example:
    >>> from image_preprocessing_detector.annotation.storage import (
    ...     PartitionedParquetWriter,
    ... )
    >>>
    >>> writer = PartitionedParquetWriter(Path("/data/parquet"))
    >>>
    >>> # Write samples for a single dataset
    >>> writer.write_dataset("diqa-5000", samples)
    >>>
    >>> # Read back efficiently
    >>> table = writer.read_dataset("diqa-5000")
    >>>
    >>> # Query across all datasets
    >>> dataset = writer.get_dataset()
    >>> filtered = dataset.to_table(filter=ds.field("quality_overall") > 0.8)
"""

from __future__ import annotations

from .parquet_writer import (
    ParquetSchema,
    PartitionedParquetWriter,
)

__all__: list[str] = [
    "ParquetSchema",
    "PartitionedParquetWriter",
]
