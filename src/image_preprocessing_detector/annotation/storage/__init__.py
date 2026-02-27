"""Storage layer for the annotation system.

This package provides storage implementations for annotation metadata:

Modules:
    - parquet_writer.py: Partitioned Parquet storage (P0-2 fix)
    - cache.py: LRU-bounded caches for memory management (P1-5 fix)

Design Principles:
    1. No Read-Modify-Write: Partitioned storage enables O(1) dataset writes
    2. Atomic Operations: Per-dataset replacement without corrupting others
    3. Unified View: pyarrow.dataset provides efficient cross-partition queries
    4. Scalability: Supports millions of samples without memory issues
    5. Memory Efficiency: Bounded caches prevent OOM on large datasets

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
    ...     BoundedCache,
    ...     StreamingJSONLReader,
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
    >>>
    >>> # Use bounded cache for sample metadata
    >>> cache: BoundedCache[dict] = BoundedCache(max_size=10_000)
    >>> cache.put("sample_001", {"label": "text"})
    >>>
    >>> # Stream large JSONL files (PubTabNet 500K+)
    >>> reader = StreamingJSONLReader(Path("annotations.jsonl"))
    >>> entry = reader.get("PMC123456_001.png")
"""

from __future__ import annotations

from .cache import (
    AnnotationCacheConfig,
    BoundedCache,
    CacheStats,
    StreamingJSONLReader,
    create_jsonl_reader,
    create_sample_cache,
)
from .parquet_writer import (
    ParquetSchema,
    PartitionedParquetWriter,
)

__all__: list[str] = [
    # Caching (Phase 5)
    "AnnotationCacheConfig",
    "BoundedCache",
    "CacheStats",
    # Parquet storage
    "ParquetSchema",
    "PartitionedParquetWriter",
    "StreamingJSONLReader",
    "create_jsonl_reader",
    "create_sample_cache",
]
