"""Tests for tensor and page render caching."""

import time
from collections.abc import Iterator
from unittest.mock import patch

import numpy as np
import pytest

from image_preprocessing_detector.utils.tensor_cache import (
    CacheMetrics,
    LRUCache,
    clear_all_caches,
    compute_page_key,
    compute_tensor_key,
    get_array_size_bytes,
    get_combined_cache_metrics,
    get_page_cache,
    get_tensor_cache,
    reset_cache_instances,
)


@pytest.fixture(autouse=True)
def reset_caches() -> Iterator[None]:
    """Reset cache instances before each test."""
    reset_cache_instances()
    yield
    reset_cache_instances()


class TestCacheMetrics:
    """Tests for CacheMetrics dataclass."""

    def test_hit_rate_no_accesses(self) -> None:
        """Test hit rate is 0% with no accesses."""
        metrics = CacheMetrics()
        assert metrics.hit_rate == pytest.approx(0.0)

    def test_hit_rate_all_hits(self) -> None:
        """Test hit rate is 100% with all hits."""
        metrics = CacheMetrics(hits=10, misses=0)
        assert metrics.hit_rate == pytest.approx(100.0)

    def test_hit_rate_mixed(self) -> None:
        """Test hit rate calculation with mixed hits/misses."""
        metrics = CacheMetrics(hits=75, misses=25)
        assert metrics.hit_rate == pytest.approx(75.0)

    def test_utilization_empty(self) -> None:
        """Test utilization is 0% for empty cache."""
        metrics = CacheMetrics(current_size_bytes=0, max_size_bytes=1024)
        assert metrics.utilization == pytest.approx(0.0)

    def test_utilization_full(self) -> None:
        """Test utilization is 100% for full cache."""
        metrics = CacheMetrics(current_size_bytes=1024, max_size_bytes=1024)
        assert metrics.utilization == pytest.approx(100.0)

    def test_utilization_no_max_size(self) -> None:
        """Test utilization is 0% when max_size is 0."""
        metrics = CacheMetrics(current_size_bytes=100, max_size_bytes=0)
        assert metrics.utilization == pytest.approx(0.0)

    def test_to_dict(self) -> None:
        """Test metrics serialization to dictionary."""
        metrics = CacheMetrics(
            hits=100,
            misses=50,
            evictions=10,
            current_size_bytes=512 * 1024,
            max_size_bytes=1024 * 1024,
            total_items=5,
        )
        result = metrics.to_dict()

        assert result["hits"] == 100
        assert result["misses"] == 50
        assert result["evictions"] == 10
        assert result["hit_rate_pct"] == pytest.approx(66.67, rel=0.01)
        assert result["current_size_mb"] == pytest.approx(0.5)
        assert result["max_size_mb"] == pytest.approx(1.0)
        assert result["utilization_pct"] == pytest.approx(50.0)
        assert result["total_items"] == 5


class TestLRUCache:
    """Tests for LRUCache implementation."""

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        cache: LRUCache[bytes] = LRUCache(max_size_mb=1, name="test")
        cache.put("key1", b"value1", size_bytes=6)

        result = cache.get("key1")
        assert result == b"value1"

    def test_get_nonexistent(self) -> None:
        """Test getting a nonexistent key returns None."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        result = cache.get("nonexistent")
        assert result is None

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        # Small cache that can hold ~2 items
        cache: LRUCache[bytes] = LRUCache(max_size_mb=1, name="test")
        item_size = 400 * 1024  # 400 KB each

        cache.put("key1", b"a" * item_size, size_bytes=item_size)
        cache.put("key2", b"b" * item_size, size_bytes=item_size)

        # Access key1 to make it recently used
        _ = cache.get("key1")

        # Add key3, should evict key2 (LRU)
        cache.put("key3", b"c" * item_size, size_bytes=item_size)

        assert cache.get("key1") is not None  # Still present (recently used)
        assert cache.get("key2") is None  # Evicted (LRU)
        assert cache.get("key3") is not None  # Just added

    def test_update_existing_key(self) -> None:
        """Test updating an existing key replaces value."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        cache.put("key1", "old_value", size_bytes=10)
        cache.put("key1", "new_value", size_bytes=10)

        result = cache.get("key1")
        assert result == "new_value"

    def test_ttl_expiration(self) -> None:
        """Test TTL expiration of cache entries."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, ttl_seconds=1, name="test")

        cache.put("key1", "value1", size_bytes=6)

        # Immediately accessible
        assert cache.get("key1") == "value1"

        # Wait for TTL expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("key1") is None

    def test_no_ttl(self) -> None:
        """Test cache without TTL doesn't expire entries."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, ttl_seconds=None, name="test")

        cache.put("key1", "value1", size_bytes=6)

        # Should not expire
        assert cache.get("key1") == "value1"

    def test_metrics_tracking(self) -> None:
        """Test that metrics are properly tracked."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        cache.put("key1", "value1", size_bytes=100)
        cache.put("key2", "value2", size_bytes=200)

        # Generate hits and misses
        _ = cache.get("key1")  # hit
        _ = cache.get("key2")  # hit
        _ = cache.get("nonexistent")  # miss

        metrics = cache.get_metrics()
        assert metrics.hits == 2
        assert metrics.misses == 1
        assert metrics.current_size_bytes == 300
        assert metrics.total_items == 2

    def test_clear(self) -> None:
        """Test clearing the cache."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        cache.put("key1", "value1", size_bytes=100)
        cache.put("key2", "value2", size_bytes=100)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache) == 0

        metrics = cache.get_metrics()
        assert metrics.current_size_bytes == 0
        assert metrics.total_items == 0

    def test_contains(self) -> None:
        """Test contains method."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        cache.put("key1", "value1", size_bytes=6)

        assert cache.contains("key1") is True
        assert cache.contains("nonexistent") is False

    def test_len(self) -> None:
        """Test len() returns correct count."""
        cache: LRUCache[str] = LRUCache(max_size_mb=1, name="test")

        assert len(cache) == 0

        cache.put("key1", "value1", size_bytes=6)
        assert len(cache) == 1

        cache.put("key2", "value2", size_bytes=6)
        assert len(cache) == 2

    def test_eviction_count(self) -> None:
        """Test eviction count in metrics."""
        # Very small cache
        cache: LRUCache[bytes] = LRUCache(max_size_mb=1, name="test")
        item_size = 600 * 1024  # 600 KB each

        cache.put("key1", b"a" * item_size, size_bytes=item_size)
        cache.put("key2", b"b" * item_size, size_bytes=item_size)  # Evicts key1

        metrics = cache.get_metrics()
        assert metrics.evictions >= 1


class TestNumpyArrayCache:
    """Tests for caching numpy arrays."""

    def test_cache_numpy_array(self) -> None:
        """Test caching and retrieving numpy arrays."""
        cache: LRUCache[np.ndarray] = LRUCache(max_size_mb=10, name="test")

        # Create test array
        rng = np.random.default_rng(42)
        array = rng.random((224, 224, 3)).astype(np.float32)
        size = array.nbytes

        cache.put("tensor1", array, size_bytes=size)

        result = cache.get("tensor1")
        assert result is not None
        np.testing.assert_array_equal(result, array)

    def test_multiple_arrays(self) -> None:
        """Test caching multiple numpy arrays."""
        cache: LRUCache[np.ndarray] = LRUCache(max_size_mb=50, name="test")

        rng = np.random.default_rng(42)
        arrays = [rng.random((224, 224, 3)).astype(np.float32) for _ in range(5)]

        for i, arr in enumerate(arrays):
            cache.put(f"tensor{i}", arr, size_bytes=arr.nbytes)

        for i, arr in enumerate(arrays):
            result = cache.get(f"tensor{i}")
            assert result is not None
            np.testing.assert_array_equal(result, arr)


class TestKeyGeneration:
    """Tests for cache key generation functions."""

    def test_compute_tensor_key_basic(self) -> None:
        """Test basic tensor key generation."""
        rng = np.random.default_rng(42)
        array = rng.random((224, 224, 3)).astype(np.float32)

        key = compute_tensor_key(array, model_name="student", input_size=(224, 224))

        assert key.startswith("tensor_student_224x224_")
        assert len(key) > 20  # Should include hash

    def test_compute_tensor_key_different_arrays(self) -> None:
        """Test different arrays produce different keys."""
        rng = np.random.default_rng(42)
        array1 = rng.random((224, 224, 3)).astype(np.float32)
        array2 = rng.random((224, 224, 3)).astype(np.float32)

        key1 = compute_tensor_key(array1)
        key2 = compute_tensor_key(array2)

        assert key1 != key2

    def test_compute_tensor_key_same_array(self) -> None:
        """Test same array produces same key."""
        rng = np.random.default_rng(42)
        array = rng.random((224, 224, 3)).astype(np.float32)

        key1 = compute_tensor_key(array)
        key2 = compute_tensor_key(array)

        assert key1 == key2

    def test_compute_page_key(self) -> None:
        """Test page key generation."""
        key = compute_page_key(file_hash="abc123", page_num=5, dpi=300)
        assert key == "page_abc123_5_300"

    def test_compute_page_key_different_params(self) -> None:
        """Test different parameters produce different keys."""
        key1 = compute_page_key(file_hash="abc123", page_num=0, dpi=300)
        key2 = compute_page_key(file_hash="abc123", page_num=1, dpi=300)
        key3 = compute_page_key(file_hash="abc123", page_num=0, dpi=150)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_array_size_bytes(self) -> None:
        """Test array size calculation."""
        array = np.zeros((224, 224, 3), dtype=np.float32)
        expected_size = 224 * 224 * 3 * 4  # 4 bytes per float32

        size = get_array_size_bytes(array)
        assert size == expected_size

    def test_get_array_size_bytes_different_dtypes(self) -> None:
        """Test array size calculation with different dtypes."""
        shape = (100, 100)

        float32_size = get_array_size_bytes(np.zeros(shape, dtype=np.float32))
        float64_size = get_array_size_bytes(np.zeros(shape, dtype=np.float64))
        uint8_size = get_array_size_bytes(np.zeros(shape, dtype=np.uint8))

        assert float32_size == 100 * 100 * 4
        assert float64_size == 100 * 100 * 8
        assert uint8_size == 100 * 100 * 1


class TestGlobalCacheInstances:
    """Tests for global cache instance management."""

    def test_get_tensor_cache(self) -> None:
        """Test getting the global tensor cache."""
        cache = get_tensor_cache()
        assert cache is not None
        assert isinstance(cache, LRUCache)

    def test_get_tensor_cache_singleton(self) -> None:
        """Test tensor cache is singleton."""
        cache1 = get_tensor_cache()
        cache2 = get_tensor_cache()
        assert cache1 is cache2

    def test_get_page_cache(self) -> None:
        """Test getting the global page cache."""
        cache = get_page_cache()
        assert cache is not None
        assert isinstance(cache, LRUCache)

    def test_get_page_cache_singleton(self) -> None:
        """Test page cache is singleton."""
        cache1 = get_page_cache()
        cache2 = get_page_cache()
        assert cache1 is cache2

    def test_clear_all_caches(self) -> None:
        """Test clearing all caches."""
        tensor_cache = get_tensor_cache()
        page_cache = get_page_cache()

        tensor_cache.put("t1", np.array([1, 2, 3]), size_bytes=24)
        page_cache.put("p1", np.array([4, 5, 6]), size_bytes=24)

        clear_all_caches()

        assert tensor_cache.get("t1") is None
        assert page_cache.get("p1") is None

    def test_reset_cache_instances(self) -> None:
        """Test resetting cache instances creates new caches."""
        cache1 = get_tensor_cache()
        reset_cache_instances()
        cache2 = get_tensor_cache()

        # Should be different instances after reset
        assert cache1 is not cache2

    def test_get_combined_cache_metrics(self) -> None:
        """Test getting combined metrics from all caches."""
        tensor_cache = get_tensor_cache()
        page_cache = get_page_cache()

        tensor_cache.put("t1", np.array([1, 2, 3]), size_bytes=24)
        page_cache.put("p1", np.array([4, 5, 6]), size_bytes=24)

        # Generate some activity
        _ = tensor_cache.get("t1")  # hit
        _ = page_cache.get("nonexistent")  # miss

        metrics = get_combined_cache_metrics()

        assert "tensor" in metrics
        assert "page" in metrics
        assert metrics["tensor"]["hits"] == 1
        assert metrics["page"]["misses"] == 1


class TestEnvironmentConfiguration:
    """Tests for environment-based cache configuration."""

    def test_tensor_cache_size_from_env(self) -> None:
        """Test tensor cache size can be configured via environment."""
        with patch.dict("os.environ", {"IMGPREP_TENSOR_CACHE_MB": "64"}):
            reset_cache_instances()
            cache = get_tensor_cache()
            metrics = cache.get_metrics()
            assert metrics.max_size_bytes == 64 * 1024 * 1024

    def test_page_cache_size_from_env(self) -> None:
        """Test page cache size can be configured via environment."""
        with patch.dict("os.environ", {"IMGPREP_PAGE_CACHE_MB": "128"}):
            reset_cache_instances()
            cache = get_page_cache()
            metrics = cache.get_metrics()
            assert metrics.max_size_bytes == 128 * 1024 * 1024

    def test_ttl_from_env(self) -> None:
        """Test cache TTL can be configured via environment."""
        with patch.dict("os.environ", {"IMGPREP_CACHE_TTL_SECONDS": "600"}):
            reset_cache_instances()
            cache = get_tensor_cache()

            # Put an item
            cache.put("key1", np.array([1, 2, 3]), size_bytes=24)

            # Should still be accessible (TTL is 600 seconds)
            assert cache.get("key1") is not None
