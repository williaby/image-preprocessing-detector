"""Tensor and page render caching for inference optimization.

This module provides LRU caching for:
- Preprocessed tensors (image arrays ready for model inference)
- Page renders (PDF pages converted to images at specific DPI)

Used by Phase 4 performance optimization to reduce redundant
preprocessing and page rendering operations.
"""

import hashlib
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Generic, TypeVar

import numpy as np

from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Default cache configuration
DEFAULT_TENSOR_CACHE_MB = 256  # 256 MB for tensor cache
DEFAULT_PAGE_CACHE_MB = 512  # 512 MB for page render cache
DEFAULT_TTL_SECONDS = 3600  # 1 hour TTL


@dataclass
class CacheMetrics:
    """Statistics for cache performance monitoring.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of items evicted due to size limit
        current_size_bytes: Current cache size in bytes
        max_size_bytes: Maximum allowed cache size in bytes
        total_items: Current number of items in cache
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size_bytes: int = 0
    max_size_bytes: int = 0
    total_items: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    @property
    def utilization(self) -> float:
        """Calculate cache utilization as percentage."""
        if self.max_size_bytes == 0:
            return 0.0
        return (self.current_size_bytes / self.max_size_bytes) * 100

    def to_dict(self) -> dict[str, int | float]:
        """Convert metrics to dictionary for logging/monitoring."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate_pct": round(self.hit_rate, 2),
            "current_size_mb": round(self.current_size_bytes / (1024 * 1024), 2),
            "max_size_mb": round(self.max_size_bytes / (1024 * 1024), 2),
            "utilization_pct": round(self.utilization, 2),
            "total_items": self.total_items,
        }


@dataclass
class CacheEntry(Generic[T]):  # noqa: UP046
    """Individual cache entry with metadata.

    Attributes:
        value: Cached value
        size_bytes: Size of the cached value in bytes
        created_at: Unix timestamp when entry was created
        last_accessed: Unix timestamp of last access
        access_count: Number of times this entry was accessed
    """

    value: T
    size_bytes: int
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 1

    def touch(self) -> None:
        """Update last access time and increment access count."""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache(Generic[T]):  # noqa: UP046
    """Thread-safe LRU cache with size-based eviction.

    This cache implementation:
    - Evicts least recently used items when size limit is exceeded
    - Supports optional TTL for cache entries
    - Provides detailed metrics for monitoring
    - Is thread-safe for concurrent access

    Example:
        >>> cache = LRUCache[np.ndarray](max_size_mb=256, name="tensor")
        >>> cache.put("key1", tensor_array, size_bytes=1024)
        >>> result = cache.get("key1")
        >>> print(cache.get_metrics().hit_rate)
    """

    def __init__(
        self,
        max_size_mb: int = DEFAULT_TENSOR_CACHE_MB,
        ttl_seconds: int | None = DEFAULT_TTL_SECONDS,
        name: str = "cache",
    ) -> None:
        """Initialize LRU cache.

        Args:
            max_size_mb: Maximum cache size in megabytes
            ttl_seconds: Time-to-live for cache entries (None for no expiry)
            name: Cache name for logging purposes
        """
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._ttl_seconds = ttl_seconds
        self._name = name
        self._metrics = CacheMetrics(max_size_bytes=self._max_size_bytes)

        logger.debug(
            f"{name}_cache_initialized",
            max_size_mb=max_size_mb,
            ttl_seconds=ttl_seconds,
        )

    def get(self, key: str) -> T | None:
        """Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._metrics.misses += 1
                return None

            # Check TTL expiration
            if self._ttl_seconds is not None:
                age = time.time() - entry.created_at
                if age > self._ttl_seconds:
                    self._remove_entry(key)
                    self._metrics.misses += 1
                    logger.debug(
                        f"{self._name}_cache_expired",
                        key=key,
                        age_seconds=round(age, 2),
                    )
                    return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._metrics.hits += 1
            return entry.value

    def put(self, key: str, value: T, size_bytes: int) -> None:
        """Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
            size_bytes: Size of the value in bytes
        """
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)

            # Evict until we have room
            while (
                self._metrics.current_size_bytes + size_bytes > self._max_size_bytes
                and self._cache
            ):
                self._evict_lru()

            # Add new entry
            entry = CacheEntry(value=value, size_bytes=size_bytes)
            self._cache[key] = entry
            self._metrics.current_size_bytes += size_bytes
            self._metrics.total_items = len(self._cache)

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache (caller must hold lock)."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._metrics.current_size_bytes -= entry.size_bytes
            self._metrics.total_items = len(self._cache)

    def _evict_lru(self) -> None:
        """Evict least recently used entry (caller must hold lock)."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._metrics.current_size_bytes -= entry.size_bytes
            self._metrics.evictions += 1
            self._metrics.total_items = len(self._cache)
            logger.debug(
                f"{self._name}_cache_eviction",
                key=key,
                size_bytes=entry.size_bytes,
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._metrics.current_size_bytes = 0
            self._metrics.total_items = 0
            logger.info(f"{self._name}_cache_cleared")

    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics."""
        with self._lock:
            return CacheMetrics(
                hits=self._metrics.hits,
                misses=self._metrics.misses,
                evictions=self._metrics.evictions,
                current_size_bytes=self._metrics.current_size_bytes,
                max_size_bytes=self._metrics.max_size_bytes,
                total_items=self._metrics.total_items,
            )

    def contains(self, key: str) -> bool:
        """Check if key exists in cache (without affecting LRU order)."""
        with self._lock:
            return key in self._cache

    def __len__(self) -> int:
        """Return number of items in cache."""
        with self._lock:
            return len(self._cache)


def compute_tensor_key(
    image_array: np.ndarray,
    model_name: str = "student",
    input_size: tuple[int, int] = (224, 224),
) -> str:
    """Compute cache key for a preprocessed tensor.

    Args:
        image_array: Input image as numpy array
        model_name: Name of the target model
        input_size: Target input size for the model

    Returns:
        Unique cache key string
    """
    # Hash the image content
    content_hash = hashlib.sha256(image_array.tobytes()).hexdigest()[:16]
    return f"tensor_{model_name}_{input_size[0]}x{input_size[1]}_{content_hash}"


def compute_page_key(
    file_hash: str,
    page_num: int,
    dpi: int = 300,
) -> str:
    """Compute cache key for a rendered page.

    Args:
        file_hash: Hash of the source file
        page_num: Page number (0-indexed)
        dpi: Render DPI

    Returns:
        Unique cache key string
    """
    return f"page_{file_hash}_{page_num}_{dpi}"


def get_array_size_bytes(array: np.ndarray) -> int:
    """Get size of numpy array in bytes."""
    size: int = array.nbytes
    return size


# Global cache instances (singleton pattern)
_tensor_cache: LRUCache[np.ndarray] | None = None
_page_cache: LRUCache[np.ndarray] | None = None
_cache_lock = threading.Lock()


def get_tensor_cache() -> LRUCache[np.ndarray]:
    """Get or create the global tensor cache instance.

    Cache size can be configured via IMGPREP_TENSOR_CACHE_MB environment variable.

    Returns:
        Global tensor cache instance
    """
    global _tensor_cache
    if _tensor_cache is None:
        with _cache_lock:
            if _tensor_cache is None:
                size_mb = int(
                    os.getenv("IMGPREP_TENSOR_CACHE_MB", str(DEFAULT_TENSOR_CACHE_MB))
                )
                ttl = int(
                    os.getenv("IMGPREP_CACHE_TTL_SECONDS", str(DEFAULT_TTL_SECONDS))
                )
                _tensor_cache = LRUCache[np.ndarray](
                    max_size_mb=size_mb,
                    ttl_seconds=ttl,
                    name="tensor",
                )
                logger.info(
                    "tensor_cache_created",
                    size_mb=size_mb,
                    ttl_seconds=ttl,
                )
    return _tensor_cache


def get_page_cache() -> LRUCache[np.ndarray]:
    """Get or create the global page render cache instance.

    Cache size can be configured via IMGPREP_PAGE_CACHE_MB environment variable.

    Returns:
        Global page cache instance
    """
    global _page_cache
    if _page_cache is None:
        with _cache_lock:
            if _page_cache is None:
                size_mb = int(
                    os.getenv("IMGPREP_PAGE_CACHE_MB", str(DEFAULT_PAGE_CACHE_MB))
                )
                ttl = int(
                    os.getenv("IMGPREP_CACHE_TTL_SECONDS", str(DEFAULT_TTL_SECONDS))
                )
                _page_cache = LRUCache[np.ndarray](
                    max_size_mb=size_mb,
                    ttl_seconds=ttl,
                    name="page",
                )
                logger.info(
                    "page_cache_created",
                    size_mb=size_mb,
                    ttl_seconds=ttl,
                )
    return _page_cache


def clear_all_caches() -> None:
    """Clear all global cache instances."""
    global _tensor_cache, _page_cache
    with _cache_lock:
        if _tensor_cache is not None:
            _tensor_cache.clear()
        if _page_cache is not None:
            _page_cache.clear()
    logger.info("all_caches_cleared")


def reset_cache_instances() -> None:
    """Reset cache instances (for testing).

    Forces re-creation of cache instances on next access.
    """
    global _tensor_cache, _page_cache
    with _cache_lock:
        _tensor_cache = None
        _page_cache = None
    logger.debug("cache_instances_reset")


def get_combined_cache_metrics() -> dict[str, dict[str, int | float]]:
    """Get combined metrics from all caches.

    Returns:
        Dictionary with metrics for each cache type
    """
    result: dict[str, dict[str, int | float]] = {}

    tensor_cache = get_tensor_cache()
    result["tensor"] = tensor_cache.get_metrics().to_dict()

    page_cache = get_page_cache()
    result["page"] = page_cache.get_metrics().to_dict()

    return result
