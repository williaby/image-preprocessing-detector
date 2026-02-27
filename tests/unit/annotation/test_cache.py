"""Tests for annotation storage cache module.

Phase 5 Task 5.1.1-5.1.2: Memory Management for P1-5 fix.
Tests BoundedCache and StreamingJSONLReader implementations.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from image_preprocessing_detector.annotation.storage.cache import (
    DEFAULT_CACHE_SIZE,
    DEFAULT_INDEX_CACHE_SIZE,
    AnnotationCacheConfig,
    BoundedCache,
    CacheStats,
    JSONLIndexEntry,
    StreamingJSONLReader,
    create_jsonl_reader,
    create_sample_cache,
)

if TYPE_CHECKING:
    pass  # No type-only imports needed yet; guard kept for future additions


# ============================================================================
# BoundedCache Tests
# ============================================================================


class TestBoundedCache:
    """Tests for BoundedCache class."""

    def test_init_default_size(self) -> None:
        """Test cache initialization with default size."""
        cache: BoundedCache[str] = BoundedCache()
        assert cache.max_size == DEFAULT_CACHE_SIZE
        assert len(cache) == 0

    def test_init_custom_size(self) -> None:
        """Test cache initialization with custom size."""
        cache: BoundedCache[str] = BoundedCache(max_size=100)
        assert cache.max_size == 100

    def test_init_invalid_size(self) -> None:
        """Test cache rejects invalid max_size."""
        with pytest.raises(ValueError, match="must be positive"):
            BoundedCache(max_size=0)

        with pytest.raises(ValueError, match="must be positive"):
            BoundedCache(max_size=-1)

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        cache: BoundedCache[dict] = BoundedCache(max_size=10)

        cache.put("key1", {"value": 1})
        cache.put("key2", {"value": 2})

        assert cache.get("key1") == {"value": 1}
        assert cache.get("key2") == {"value": 2}
        assert cache.get("nonexistent") is None

    def test_get_updates_lru_order(self) -> None:
        """Test that get() updates LRU order."""
        cache: BoundedCache[int] = BoundedCache(max_size=3)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        # Access 'a' to make it most recently used
        cache.get("a")

        # Add new item - should evict 'b' (least recently used)
        cache.put("d", 4)

        assert cache.get("a") == 1  # Still present
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_put_updates_existing(self) -> None:
        """Test that put() updates existing entry."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("key", 1)
        cache.put("key", 2)

        assert cache.get("key") == 2
        assert len(cache) == 1

    def test_eviction_at_capacity(self) -> None:
        """Test LRU eviction when cache is at capacity."""
        cache: BoundedCache[int] = BoundedCache(max_size=3)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        # Cache is full, adding new item should evict 'a'
        cache.put("d", 4)

        assert cache.get("a") is None  # Evicted
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4
        assert len(cache) == 3

    def test_remove(self) -> None:
        """Test remove operation."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("key", 42)
        assert cache.remove("key") is True
        assert cache.get("key") is None

        assert cache.remove("nonexistent") is False

    def test_clear(self) -> None:
        """Test clear operation."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        cache.clear()

        assert len(cache) == 0
        assert cache.get("a") is None

    def test_contains(self) -> None:
        """Test contains check."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("key", 42)

        assert cache.contains("key") is True
        assert cache.contains("nonexistent") is False
        assert "key" in cache
        assert "nonexistent" not in cache

    def test_keys(self) -> None:
        """Test keys() returns all keys in LRU order."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        keys = cache.keys()
        assert keys == ["a", "b", "c"]

        # Access 'a' to move it to end
        cache.get("a")
        keys = cache.keys()
        assert keys == ["b", "c", "a"]

    def test_stats(self) -> None:
        """Test cache statistics."""
        cache: BoundedCache[int] = BoundedCache(max_size=3)

        # Initial stats
        stats = cache.stats
        assert stats.size == 0
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.hit_rate == pytest.approx(0.0)

        # Add items and access
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # hit
        cache.get("nonexistent")  # miss

        stats = cache.stats
        assert stats.size == 2
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == pytest.approx(0.5)

        # Trigger eviction
        cache.put("c", 3)
        cache.put("d", 4)  # Evicts 'b'

        stats = cache.stats
        assert stats.evictions == 1

    def test_reset_stats(self) -> None:
        """Test reset_stats preserves cache contents."""
        cache: BoundedCache[int] = BoundedCache(max_size=10)

        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss

        cache.reset_stats()

        stats = cache.stats
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 1  # Cache contents preserved

    def test_thread_safety(self) -> None:
        """Test thread-safe concurrent access."""
        cache: BoundedCache[int] = BoundedCache(max_size=100)
        errors: list[Exception] = []

        def writer(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.put(f"key_{thread_id}_{i}", i)
            except Exception as e:
                errors.append(e)

        def reader(thread_id: int) -> None:
            try:
                for i in range(100):
                    cache.get(f"key_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == pytest.approx(0.75)

        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == pytest.approx(0.0)

    def test_utilization_calculation(self) -> None:
        """Test utilization calculation."""
        stats = CacheStats(size=50, max_size=100)
        assert stats.utilization == pytest.approx(0.5)

        stats = CacheStats(size=0, max_size=0)
        assert stats.utilization == pytest.approx(0.0)

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        stats = CacheStats(
            size=50,
            max_size=100,
            hits=75,
            misses=25,
            evictions=10,
        )
        result = stats.to_dict()

        assert result["size"] == 50
        assert result["max_size"] == 100
        assert result["hits"] == 75
        assert result["misses"] == 25
        assert result["evictions"] == 10
        assert result["hit_rate"] == pytest.approx(0.75)
        assert result["utilization"] == pytest.approx(0.5)


# ============================================================================
# StreamingJSONLReader Tests
# ============================================================================


class TestStreamingJSONLReader:
    """Tests for StreamingJSONLReader class."""

    @pytest.fixture
    def sample_jsonl_file(self, tmp_path: Path) -> Path:
        """Create a sample JSONL file for testing."""
        file_path = tmp_path / "annotations.jsonl"
        entries = [
            {"filename": "image_001.png", "label": "text", "score": 0.95},
            {"filename": "image_002.png", "label": "table", "score": 0.88},
            {"filename": "image_003.png", "label": "figure", "score": 0.92},
            {"filename": "image_004.png", "label": "text", "score": 0.97},
            {"filename": "image_005.png", "label": "header", "score": 0.85},
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)
        return file_path

    @pytest.fixture
    def large_jsonl_file(self, tmp_path: Path) -> Path:
        """Create a larger JSONL file for performance testing."""
        file_path = tmp_path / "large_annotations.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            for i in range(1000):
                entry = {
                    "filename": f"image_{i:05d}.png",
                    "label": "text" if i % 2 == 0 else "table",
                    "score": 0.5 + (i % 50) / 100,
                }
                f.write(json.dumps(entry) + "\n")
        return file_path

    def test_init(self, sample_jsonl_file: Path) -> None:
        """Test reader initialization."""
        reader = StreamingJSONLReader(sample_jsonl_file)
        assert reader.file_path == sample_jsonl_file
        assert not reader.is_indexed
        assert reader.indexed_count == 0

    def test_init_file_not_found(self, tmp_path: Path) -> None:
        """Test initialization with non-existent file."""
        with pytest.raises(FileNotFoundError):
            StreamingJSONLReader(tmp_path / "nonexistent.jsonl")

    def test_build_index(self, sample_jsonl_file: Path) -> None:
        """Test index building."""
        reader = StreamingJSONLReader(sample_jsonl_file)
        count = reader.build_index()

        assert count == 5
        assert reader.is_indexed
        assert reader.indexed_count == 5
        assert len(reader) == 5

    def test_get_single_entry(self, sample_jsonl_file: Path) -> None:
        """Test retrieving a single entry."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        entry = reader.get("image_003.png")
        assert entry is not None
        assert entry["filename"] == "image_003.png"
        assert entry["label"] == "figure"
        assert entry["score"] == pytest.approx(0.92)

    def test_get_nonexistent_entry(self, sample_jsonl_file: Path) -> None:
        """Test retrieving non-existent entry."""
        reader = StreamingJSONLReader(sample_jsonl_file)
        entry = reader.get("nonexistent.png")
        assert entry is None

    def test_get_with_caching(self, sample_jsonl_file: Path) -> None:
        """Test that entries are cached after first access."""
        reader = StreamingJSONLReader(sample_jsonl_file, cache_size=10)

        # First access - builds index and reads from file
        entry1 = reader.get("image_002.png")
        stats = reader.get_stats()
        assert stats["cache_misses"] == 1

        # Second access - should be cached
        entry2 = reader.get("image_002.png")
        stats = reader.get_stats()
        assert stats["cache_hits"] == 1

        assert entry1 == entry2

    def test_get_batch(self, sample_jsonl_file: Path) -> None:
        """Test batch retrieval."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        filenames = ["image_001.png", "image_003.png", "nonexistent.png"]
        results = reader.get_batch(filenames)

        assert len(results) == 2
        assert "image_001.png" in results
        assert "image_003.png" in results
        assert "nonexistent.png" not in results

    def test_contains(self, sample_jsonl_file: Path) -> None:
        """Test contains check."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        assert "image_001.png" in reader
        assert "nonexistent.png" not in reader

    def test_iteration(self, sample_jsonl_file: Path) -> None:
        """Test streaming iteration."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        entries = list(reader)
        assert len(entries) == 5

        filenames = [filename for filename, _ in entries]
        assert "image_001.png" in filenames
        assert "image_005.png" in filenames

    def test_custom_filename_key(self, tmp_path: Path) -> None:
        """Test reader with custom filename key."""
        file_path = tmp_path / "custom.jsonl"
        entries = [
            {"image_id": "img_001", "data": "value1"},
            {"image_id": "img_002", "data": "value2"},
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)

        reader = StreamingJSONLReader(file_path, filename_key="image_id")
        entry = reader.get("img_001")
        assert entry is not None
        assert entry["image_id"] == "img_001"

    def test_clear_cache(self, sample_jsonl_file: Path) -> None:
        """Test clearing the entry cache."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        reader.get("image_001.png")
        reader.get("image_002.png")

        stats = reader.get_stats()
        assert stats["cache_size"] == 2

        reader.clear_cache()

        stats = reader.get_stats()
        assert stats["cache_size"] == 0
        # Index should still be intact
        assert reader.is_indexed

    def test_get_stats(self, sample_jsonl_file: Path) -> None:
        """Test getting combined statistics."""
        reader = StreamingJSONLReader(sample_jsonl_file)

        reader.get("image_001.png")  # miss + cache
        reader.get("image_001.png")  # hit

        stats = reader.get_stats()
        assert stats["indexed_entries"] == 5
        assert stats["is_indexed"] is True
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_hit_rate"] == pytest.approx(0.5)

    def test_handles_empty_lines(self, tmp_path: Path) -> None:
        """Test reader handles empty lines in JSONL."""
        file_path = tmp_path / "with_empty.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"filename": "a.png", "value": 1}\n')
            f.write("\n")  # Empty line
            f.write('{"filename": "b.png", "value": 2}\n')
            f.write("   \n")  # Whitespace line
            f.write('{"filename": "c.png", "value": 3}\n')

        reader = StreamingJSONLReader(file_path)
        reader.build_index()

        assert len(reader) == 3
        assert reader.get("a.png") is not None
        assert reader.get("b.png") is not None
        assert reader.get("c.png") is not None

    def test_handles_malformed_json(self, tmp_path: Path) -> None:
        """Test reader handles malformed JSON lines gracefully."""
        file_path = tmp_path / "malformed.jsonl"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"filename": "a.png", "value": 1}\n')
            f.write("this is not json\n")  # Invalid JSON
            f.write('{"filename": "b.png", "value": 2}\n')

        reader = StreamingJSONLReader(file_path)
        reader.build_index()

        # Should still have valid entries
        assert len(reader) == 2
        assert reader.get("a.png") is not None
        assert reader.get("b.png") is not None

    def test_performance_large_file(self, large_jsonl_file: Path) -> None:
        """Test performance with larger file."""
        reader = StreamingJSONLReader(large_jsonl_file, cache_size=100)

        # Build index
        start = time.time()
        reader.build_index()
        index_time = time.time() - start

        assert reader.indexed_count == 1000
        # Index building should be reasonably fast (< 1s for 1000 entries)
        assert index_time < 1.0

        # Random access should be fast
        start = time.time()
        for i in [0, 500, 999, 123, 456]:
            entry = reader.get(f"image_{i:05d}.png")
            assert entry is not None
        access_time = time.time() - start
        assert access_time < 0.1  # 5 lookups in < 100ms


class TestJSONLIndexEntry:
    """Tests for JSONLIndexEntry dataclass."""

    def test_creation(self) -> None:
        """Test entry creation."""
        entry = JSONLIndexEntry(offset=1024, length=128)
        assert entry.offset == 1024
        assert entry.length == 128

    def test_default_length(self) -> None:
        """Test default length value."""
        entry = JSONLIndexEntry(offset=1024)
        assert entry.length == 0


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestFactoryFunctions:
    """Tests for cache factory functions."""

    def test_create_sample_cache(self) -> None:
        """Test create_sample_cache factory."""
        cache = create_sample_cache()
        assert cache.max_size == DEFAULT_CACHE_SIZE

        cache = create_sample_cache(max_size=500)
        assert cache.max_size == 500

    def test_create_jsonl_reader(self, tmp_path: Path) -> None:
        """Test create_jsonl_reader factory."""
        file_path = tmp_path / "test.jsonl"
        file_path.write_text('{"filename": "test.png"}\n')

        reader = create_jsonl_reader(file_path)
        assert reader.file_path == file_path

        reader = create_jsonl_reader(file_path, cache_size=50)
        assert reader.cache.max_size == 50


class TestAnnotationCacheConfig:
    """Tests for AnnotationCacheConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AnnotationCacheConfig()
        assert config.sample_cache_size == DEFAULT_CACHE_SIZE
        assert config.jsonl_cache_size == DEFAULT_INDEX_CACHE_SIZE
        assert config.enable_caching is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = AnnotationCacheConfig(
            sample_cache_size=5000,
            jsonl_cache_size=500,
            enable_caching=False,
        )
        assert config.sample_cache_size == 5000
        assert config.jsonl_cache_size == 500
        assert config.enable_caching is False
