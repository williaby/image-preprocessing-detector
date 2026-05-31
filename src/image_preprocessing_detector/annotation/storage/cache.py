"""LRU-bounded caches for annotation data.

This module provides memory-efficient caching for large-scale annotation
processing. Key features:

1. **BoundedCache**: Count-based LRU cache that prevents OOM on large datasets
2. **StreamingJSONLReader**: Index-based random access for large JSONL files

Phase 5 Task 5.1.1-5.1.2: Memory Management for P1-5 fix.

Example:
    >>> from image_preprocessing_detector.annotation.storage.cache import (
    ...     BoundedCache,
    ...     StreamingJSONLReader,
    ... )
    >>>
    >>> # Simple LRU cache
    >>> cache: BoundedCache[dict] = BoundedCache(max_size=10_000)
    >>> cache.put("sample_001", {"label": "text", "score": 0.95})
    >>> result = cache.get("sample_001")
    >>>
    >>> # Streaming JSONL reader for PubTabNet (500K+ entries)
    >>> reader = StreamingJSONLReader(Path("annotations.jsonl"))
    >>> entry = reader.get("PMC123456_001.png")
"""

from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default configuration
DEFAULT_CACHE_SIZE = 10_000  # 10K entries
DEFAULT_INDEX_CACHE_SIZE = 1_000  # 1K entries for JSONL reader


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring.

    Attributes:
        size (int): Current number of items in cache.
        max_size (int): Maximum allowed items.
        hits (int): Number of cache hits.
        misses (int): Number of cache misses.
        evictions (int): Number of items evicted due to size limit.
    """

    size: int = 0
    max_size: int = DEFAULT_CACHE_SIZE
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0-1)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def utilization(self) -> float:
        """Calculate cache utilization (0-1)."""
        return self.size / self.max_size if self.max_size > 0 else 0.0

    def to_dict(self) -> dict[str, int | float]:
        """Convert to dictionary for logging/metrics."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 4),
            "utilization": round(self.utilization, 4),
        }


class BoundedCache(Generic[T]):  # noqa: UP046
    """LRU-bounded cache for annotations.

    Prevents OOM on large datasets (500K+ samples) by limiting the
    number of cached entries and evicting least recently used items.

    Thread-safe implementation using RLock for concurrent access.

    Args:
        max_size (int): Maximum number of entries to cache (default 10,000).

    Raises:
        ValueError: If max_size is not positive.

    Example:
        >>> cache: BoundedCache[dict] = BoundedCache(max_size=10_000)
        >>> cache.put("key1", {"label": "text"})
        >>> value = cache.get("key1")
        >>> print(cache.stats)
    """

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")

        self.max_size = max_size
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        logger.debug(
            "bounded_cache_initialized",
            extra={"max_size": max_size},
        )

    def get(self, key: str) -> T | None:
        """Get item from cache, updating LRU order.

        Args:
            key (str): Cache key to retrieve.

        Returns:
            T | None: Cached value or None if not found.
        """
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]

            self._misses += 1
            return None

    def put(self, key: str, value: T) -> None:
        """Put item in cache, evicting oldest if at capacity.

        Args:
            key (str): Cache key.
            value (T): Value to cache.
        """
        with self._lock:
            if key in self._cache:
                # Update existing - move to end
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                # Evict if at capacity
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                    self._evictions += 1

                self._cache[key] = value

    def remove(self, key: str) -> bool:
        """Remove item from cache.

        Args:
            key (str): Cache key to remove.

        Returns:
            bool: True if item was removed, False if not found.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.debug("bounded_cache_cleared")

    def contains(self, key: str) -> bool:
        """Check if key exists (without affecting LRU order).

        Args:
            key (str): Cache key to check.

        Returns:
            bool: True if key exists in cache.
        """
        with self._lock:
            return key in self._cache

    def keys(self) -> list[str]:
        """Get all cache keys (ordered by access, oldest first).

        Returns:
            list[str]: List of cache keys.
        """
        with self._lock:
            return list(self._cache.keys())

    @property
    def stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            return CacheStats(
                size=len(self._cache),
                max_size=self.max_size,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )

    def reset_stats(self) -> None:
        """Reset hit/miss/eviction counters (preserves cache contents)."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def __len__(self) -> int:
        """Return number of items in cache."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return self.contains(key)


@dataclass
class JSONLIndexEntry:
    """Index entry for JSONL random access.

    Attributes:
        offset (int): Byte offset to start of line in file.
        length (int): Length of the line in bytes.
    """

    offset: int
    length: int = 0


class StreamingJSONLReader:
    """Streaming reader for large JSONL files.

    Used for PubTabNet (500K+ entries) and similar large annotation
    files to avoid OOM from loading entire file into memory.

    Features:
    - Builds index on first access (filename → byte offset)
    - LRU cache for recently accessed entries
    - Thread-safe for concurrent reads

    Args:
        file_path (Path): Path to JSONL file.
        cache_size (int): Number of entries to cache (default 1,000).
        filename_key (str | None): Key to use for filename lookup. If None, tries
            'filename', 'file_name', 'image_id' in order.

    Raises:
        FileNotFoundError: If the JSONL file does not exist.

    Example:
        >>> reader = StreamingJSONLReader(Path("pubtabnet.jsonl"))
        >>> entry = reader.get("PMC123456_001.png")
        >>> print(entry["html"])
    """

    def __init__(
        self,
        file_path: Path,
        cache_size: int = DEFAULT_INDEX_CACHE_SIZE,
        filename_key: str | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.cache: BoundedCache[dict] = BoundedCache(max_size=cache_size)
        self.filename_key = filename_key

        self._index: dict[str, JSONLIndexEntry] = {}
        self._indexed = False
        self._lock = threading.RLock()
        self._line_count = 0

        if not self.file_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {file_path}")

        logger.debug(
            "streaming_jsonl_reader_initialized",
            extra={
                "file_path": str(file_path),
                "cache_size": cache_size,
            },
        )

    def _extract_filename(self, data: dict) -> str | None:
        """Extract filename from JSON entry.

        Args:
            data (dict): Parsed JSON entry.

        Returns:
            str | None: Filename string or None if not found.
        """
        if self.filename_key:
            return data.get(self.filename_key)

        # Try common keys in order of preference
        for key in ("filename", "file_name", "image_id", "img", "image"):
            if key in data:
                value = data[key]
                if isinstance(value, str):
                    return value
        return None

    def build_index(self) -> int:
        """Build filename → offset index for random access.

        This reads through the entire file once to build an index.
        Subsequent lookups use seek() for O(1) access.

        Returns:
            int: Number of entries indexed.
        """
        with self._lock:
            if self._indexed:
                return len(self._index)

            self._index.clear()
            self._line_count = 0

            logger.info(
                "building_jsonl_index",
                extra={"file_path": str(self.file_path)},
            )

            # Use readline() instead of iteration to allow tell()
            with open(self.file_path, encoding="utf-8") as f:
                line_num = 0
                while True:
                    offset = f.tell()
                    line = f.readline()

                    if not line:
                        break

                    line = line.strip()
                    if not line:
                        line_num += 1
                        continue

                    try:
                        data = json.loads(line)
                        filename = self._extract_filename(data)

                        if filename:
                            self._index[filename] = JSONLIndexEntry(
                                offset=offset,
                                length=len(line.encode("utf-8")),
                            )
                            self._line_count += 1

                    except json.JSONDecodeError as e:
                        logger.warning(
                            "jsonl_parse_error",
                            extra={
                                "line_num": line_num,
                                "error": str(e),
                            },
                        )

                    line_num += 1

            self._indexed = True

            logger.info(
                "jsonl_index_built",
                extra={
                    "indexed_entries": len(self._index),
                    "total_lines": self._line_count,
                },
            )

            return len(self._index)

    def get(self, filename: str) -> dict[str, Any] | None:
        """Get annotation for filename with caching.

        Args:
            filename (str): Filename to look up.

        Returns:
            dict[str, Any] | None: Parsed JSON entry or None if not found.
        """
        # Check cache first
        cached = self.cache.get(filename)
        if cached is not None:
            return cached

        with self._lock:
            # Build index if needed
            if not self._indexed:
                self.build_index()

            # Look up in index
            entry = self._index.get(filename)
            if entry is None:
                return None

            # Seek to offset and read
            try:
                with open(self.file_path, encoding="utf-8") as f:
                    f.seek(entry.offset)
                    line = f.readline()
                    data: dict[str, Any] = json.loads(line)

                    # Cache the result
                    self.cache.put(filename, data)
                    return data

            except (OSError, json.JSONDecodeError) as e:
                logger.warning(
                    "jsonl_read_error",
                    extra={
                        "filename": filename,
                        "offset": entry.offset,
                        "error": str(e),
                    },
                )
                return None

    def get_batch(self, filenames: list[str]) -> dict[str, dict]:
        """Get multiple annotations efficiently.

        Args:
            filenames (list[str]): List of filenames to look up.

        Returns:
            dict[str, dict]: Dictionary mapping filename to annotation (missing entries omitted).
        """
        results: dict[str, dict] = {}

        for filename in filenames:
            entry = self.get(filename)
            if entry is not None:
                results[filename] = entry

        return results

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        """Iterate over all entries (streaming, no full load).

        Yields:
            tuple[str, dict]: Tuples of (filename, annotation_dict).
        """
        with open(self.file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    filename = self._extract_filename(data)
                    if filename:
                        yield filename, data
                except json.JSONDecodeError:
                    continue

    def __len__(self) -> int:
        """Return number of indexed entries."""
        if not self._indexed:
            self.build_index()
        return len(self._index)

    def __contains__(self, filename: str) -> bool:
        """Check if filename exists in index."""
        if not self._indexed:
            self.build_index()
        return filename in self._index

    @property
    def is_indexed(self) -> bool:
        """Check if index has been built."""
        return self._indexed

    @property
    def indexed_count(self) -> int:
        """Get number of indexed entries."""
        return len(self._index)

    def clear_cache(self) -> None:
        """Clear the entry cache (preserves index)."""
        self.cache.clear()

    def get_stats(self) -> dict[str, int | float]:
        """Get combined statistics.

        Returns:
            dict[str, int | float]: Dictionary with index and cache stats.
        """
        cache_stats = self.cache.stats.to_dict()
        return {
            "indexed_entries": len(self._index),
            "is_indexed": self._indexed,
            "cache_hits": cache_stats["hits"],
            "cache_misses": cache_stats["misses"],
            "cache_hit_rate": cache_stats["hit_rate"],
            "cache_size": cache_stats["size"],
            "cache_max_size": cache_stats["max_size"],
        }


@dataclass
class AnnotationCacheConfig:
    """Configuration for annotation caching.

    Attributes:
        sample_cache_size (int): Max entries for sample metadata cache.
        jsonl_cache_size (int): Max entries for JSONL reader cache.
        enable_caching (bool): Global flag to enable/disable caching.
    """

    sample_cache_size: int = DEFAULT_CACHE_SIZE
    jsonl_cache_size: int = DEFAULT_INDEX_CACHE_SIZE
    enable_caching: bool = True


# Factory functions for creating caches with standard configurations


def create_sample_cache(
    max_size: int = DEFAULT_CACHE_SIZE,
) -> BoundedCache[dict]:
    """Create a cache for sample metadata.

    Args:
        max_size (int): Maximum entries (default 10,000).

    Returns:
        BoundedCache[dict]: Configured BoundedCache instance.
    """
    return BoundedCache[dict](max_size=max_size)


def create_jsonl_reader(
    file_path: Path,
    cache_size: int = DEFAULT_INDEX_CACHE_SIZE,
) -> StreamingJSONLReader:
    """Create a streaming JSONL reader.

    Args:
        file_path (Path): Path to JSONL file.
        cache_size (int): Cache size for entries (default 1,000).

    Returns:
        StreamingJSONLReader: Configured StreamingJSONLReader instance.
    """
    return StreamingJSONLReader(file_path=file_path, cache_size=cache_size)


__all__ = [
    "DEFAULT_CACHE_SIZE",
    "DEFAULT_INDEX_CACHE_SIZE",
    "AnnotationCacheConfig",
    "BoundedCache",
    "CacheStats",
    "JSONLIndexEntry",
    "StreamingJSONLReader",
    "create_jsonl_reader",
    "create_sample_cache",
]
