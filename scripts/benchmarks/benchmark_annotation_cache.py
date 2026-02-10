#!/usr/bin/env python3
"""Benchmark memory usage for annotation caching components.

Measures memory efficiency of BoundedCache and StreamingJSONLReader
compared to unbounded dictionary caching. Critical for Phase 5 memory
management to prevent OOM on large datasets (500K+ entries).

Targets:
- BoundedCache: Constant memory regardless of dataset size
- StreamingJSONLReader: O(index_size) memory, not O(data_size)
- No OOM on 500K+ entry datasets
"""

from __future__ import annotations

import gc
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Memory measurement utilities
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import tracemalloc

    HAS_TRACEMALLOC = True
except ImportError:
    HAS_TRACEMALLOC = False

from image_preprocessing_detector.annotation.storage.cache import (
    BoundedCache,
    StreamingJSONLReader,
)


@dataclass
class MemorySnapshot:
    """Memory measurement at a point in time."""

    rss_mb: float  # Resident Set Size (actual memory used)
    tracemalloc_mb: float  # Python-tracked allocations
    timestamp: float

    @classmethod
    def capture(cls) -> MemorySnapshot:
        """Capture current memory state."""
        rss_mb = 0.0
        tracemalloc_mb = 0.0

        if HAS_PSUTIL:
            process = psutil.Process()
            rss_mb = process.memory_info().rss / (1024 * 1024)

        if HAS_TRACEMALLOC and tracemalloc.is_tracing():
            current, _peak = tracemalloc.get_traced_memory()
            tracemalloc_mb = current / (1024 * 1024)

        return cls(
            rss_mb=rss_mb,
            tracemalloc_mb=tracemalloc_mb,
            timestamp=time.time(),
        )


def generate_sample_data(size_bytes: int = 1024) -> dict[str, Any]:
    """Generate a sample annotation entry of approximate size.

    Args:
        size_bytes: Target size in bytes

    Returns:
        Dictionary simulating annotation data
    """
    # Approximate JSON overhead
    base_size = 100
    padding_size = max(0, size_bytes - base_size)

    return {
        "filename": f"image_{hash(size_bytes):08x}.png",
        "width": 1920,
        "height": 1080,
        "annotations": [
            {
                "bbox": [100, 200, 300, 400],
                "category": "text",
                "confidence": 0.95,
            }
        ],
        "metadata": {
            "source": "benchmark",
            "padding": "x" * padding_size,
        },
    }


def create_test_jsonl(
    path: Path,
    num_entries: int,
    entry_size_bytes: int = 1024,
) -> int:
    """Create a test JSONL file with specified entries.

    Args:
        path: Output file path
        num_entries: Number of entries to create
        entry_size_bytes: Approximate size per entry

    Returns:
        Actual file size in bytes
    """
    with open(path, "w", encoding="utf-8") as f:
        for i in range(num_entries):
            entry = generate_sample_data(entry_size_bytes)
            entry["filename"] = f"image_{i:08d}.png"
            f.write(json.dumps(entry) + "\n")

    return path.stat().st_size


def benchmark_bounded_cache_memory(
    cache_sizes: list[int],
    num_entries: int = 100_000,
    entry_size_bytes: int = 1024,
) -> dict[str, Any]:
    """Benchmark BoundedCache memory usage with different cache sizes.

    Args:
        cache_sizes: List of cache sizes to test
        num_entries: Total entries to process
        entry_size_bytes: Size of each entry

    Returns:
        Benchmark results dictionary
    """
    results = {
        "cache_sizes": [],
        "memory_mb": [],
        "hit_rates": [],
        "entries_processed": num_entries,
    }

    print(f"\nBenchmarking BoundedCache (processing {num_entries:,} entries):")
    print("-" * 60)

    for cache_size in cache_sizes:
        # Force garbage collection
        gc.collect()

        # Start memory tracking
        if HAS_TRACEMALLOC:
            tracemalloc.start()

        before = MemorySnapshot.capture()

        # Create cache and fill it
        cache: BoundedCache[dict] = BoundedCache(max_size=cache_size)

        # Simulate processing - write and read patterns
        for i in range(num_entries):
            key = f"image_{i:08d}.png"
            data = generate_sample_data(entry_size_bytes)

            # Write
            cache.put(key, data)

            # Simulate reads (recent entries more likely)
            if i > 0 and i % 10 == 0:
                read_idx = max(0, i - (i % cache_size))
                cache.get(f"image_{read_idx:08d}.png")

        after = MemorySnapshot.capture()

        # Get stats
        stats = cache.stats
        memory_delta = (
            after.tracemalloc_mb if HAS_TRACEMALLOC else (after.rss_mb - before.rss_mb)
        )

        results["cache_sizes"].append(cache_size)
        results["memory_mb"].append(memory_delta)
        results["hit_rates"].append(stats.hit_rate)

        print(
            f"  Cache size {cache_size:>7,}: "
            f"Memory={memory_delta:>6.1f}MB, "
            f"Hit rate={stats.hit_rate:.2%}, "
            f"Evictions={stats.evictions:,}"
        )

        # Cleanup
        del cache
        gc.collect()

        if HAS_TRACEMALLOC:
            tracemalloc.stop()

    return results


def benchmark_unbounded_dict_memory(
    num_entries_list: list[int],
    entry_size_bytes: int = 1024,
) -> dict[str, Any]:
    """Benchmark unbounded dictionary memory growth.

    Shows what happens without BoundedCache - memory grows linearly.

    Args:
        num_entries_list: List of entry counts to test
        entry_size_bytes: Size of each entry

    Returns:
        Benchmark results dictionary
    """
    results = {
        "num_entries": [],
        "memory_mb": [],
    }

    print("\nBenchmarking unbounded dict (baseline comparison):")
    print("-" * 60)

    for num_entries in num_entries_list:
        gc.collect()

        if HAS_TRACEMALLOC:
            tracemalloc.start()

        before = MemorySnapshot.capture()

        # Unbounded dictionary (the problem we're solving)
        cache: dict[str, dict] = {}

        for i in range(num_entries):
            key = f"image_{i:08d}.png"
            cache[key] = generate_sample_data(entry_size_bytes)

        after = MemorySnapshot.capture()

        memory_delta = (
            after.tracemalloc_mb if HAS_TRACEMALLOC else (after.rss_mb - before.rss_mb)
        )

        results["num_entries"].append(num_entries)
        results["memory_mb"].append(memory_delta)

        print(
            f"  {num_entries:>7,} entries: Memory={memory_delta:>6.1f}MB "
            f"({memory_delta / num_entries * 1024:.1f}KB/entry)"
        )

        del cache
        gc.collect()

        if HAS_TRACEMALLOC:
            tracemalloc.stop()

    return results


def benchmark_streaming_jsonl_reader(
    num_entries_list: list[int],
    cache_size: int = 1_000,
    entry_size_bytes: int = 1024,
) -> dict[str, Any]:
    """Benchmark StreamingJSONLReader memory efficiency.

    Args:
        num_entries_list: List of entry counts to test
        cache_size: Reader cache size
        entry_size_bytes: Size of each entry

    Returns:
        Benchmark results dictionary
    """
    results = {
        "num_entries": [],
        "file_size_mb": [],
        "memory_mb": [],
        "index_time_s": [],
        "random_access_time_ms": [],
    }

    print(f"\nBenchmarking StreamingJSONLReader (cache_size={cache_size:,}):")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        for num_entries in num_entries_list:
            gc.collect()

            # Create test file
            jsonl_path = Path(tmpdir) / f"test_{num_entries}.jsonl"
            file_size = create_test_jsonl(jsonl_path, num_entries, entry_size_bytes)
            file_size_mb = file_size / (1024 * 1024)

            if HAS_TRACEMALLOC:
                tracemalloc.start()

            before = MemorySnapshot.capture()

            # Create reader and build index
            start_index = time.perf_counter()
            reader = StreamingJSONLReader(
                file_path=jsonl_path,
                cache_size=cache_size,
            )
            reader.build_index()
            index_time = time.perf_counter() - start_index

            after = MemorySnapshot.capture()

            # Measure random access time
            access_times = []
            import random

            for _ in range(100):
                idx = random.randint(0, num_entries - 1)
                key = f"image_{idx:08d}.png"

                start_access = time.perf_counter()
                _ = reader.get(key)
                access_times.append((time.perf_counter() - start_access) * 1000)

            memory_delta = (
                after.tracemalloc_mb
                if HAS_TRACEMALLOC
                else (after.rss_mb - before.rss_mb)
            )
            avg_access_time = sum(access_times) / len(access_times)

            results["num_entries"].append(num_entries)
            results["file_size_mb"].append(file_size_mb)
            results["memory_mb"].append(memory_delta)
            results["index_time_s"].append(index_time)
            results["random_access_time_ms"].append(avg_access_time)

            print(
                f"  {num_entries:>7,} entries ({file_size_mb:>5.1f}MB file): "
                f"Memory={memory_delta:>5.1f}MB, "
                f"Index={index_time:.2f}s, "
                f"Access={avg_access_time:.2f}ms"
            )

            del reader
            gc.collect()

            if HAS_TRACEMALLOC:
                tracemalloc.stop()

    return results


def benchmark_full_load_vs_streaming(
    num_entries: int = 50_000,
    cache_size: int = 1_000,
    entry_size_bytes: int = 1024,
) -> dict[str, Any]:
    """Compare full file load vs streaming approach.

    Args:
        num_entries: Number of entries
        cache_size: Streaming reader cache size
        entry_size_bytes: Size of each entry

    Returns:
        Comparison results
    """
    results = {}

    print(f"\nFull Load vs Streaming Comparison ({num_entries:,} entries):")
    print("-" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "test.jsonl"
        file_size = create_test_jsonl(jsonl_path, num_entries, entry_size_bytes)
        file_size_mb = file_size / (1024 * 1024)

        # Method 1: Full load into memory
        gc.collect()
        if HAS_TRACEMALLOC:
            tracemalloc.start()

        before = MemorySnapshot.capture()

        start = time.perf_counter()
        full_cache: dict[str, dict] = {}
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                full_cache[data["filename"]] = data
        load_time = time.perf_counter() - start

        after = MemorySnapshot.capture()
        full_load_memory = (
            after.tracemalloc_mb if HAS_TRACEMALLOC else (after.rss_mb - before.rss_mb)
        )

        del full_cache
        gc.collect()
        if HAS_TRACEMALLOC:
            tracemalloc.stop()

        results["full_load"] = {
            "memory_mb": full_load_memory,
            "load_time_s": load_time,
        }

        print(f"  Full load:  Memory={full_load_memory:>6.1f}MB, Time={load_time:.2f}s")

        # Method 2: Streaming with index
        gc.collect()
        if HAS_TRACEMALLOC:
            tracemalloc.start()

        before = MemorySnapshot.capture()

        start = time.perf_counter()
        reader = StreamingJSONLReader(jsonl_path, cache_size=cache_size)
        reader.build_index()
        stream_time = time.perf_counter() - start

        after = MemorySnapshot.capture()
        streaming_memory = (
            after.tracemalloc_mb if HAS_TRACEMALLOC else (after.rss_mb - before.rss_mb)
        )

        del reader
        gc.collect()
        if HAS_TRACEMALLOC:
            tracemalloc.stop()

        results["streaming"] = {
            "memory_mb": streaming_memory,
            "index_time_s": stream_time,
        }

        print(
            f"  Streaming:  Memory={streaming_memory:>6.1f}MB, Time={stream_time:.2f}s"
        )

        # Calculate savings
        memory_reduction = (
            (full_load_memory - streaming_memory) / full_load_memory * 100
            if full_load_memory > 0
            else 0
        )

        results["comparison"] = {
            "file_size_mb": file_size_mb,
            "memory_reduction_pct": memory_reduction,
            "streaming_is_better": streaming_memory < full_load_memory,
        }

        print(f"\n  Memory reduction: {memory_reduction:.1f}%")
        print(f"  Streaming saves: {full_load_memory - streaming_memory:.1f}MB")

    return results


def run_benchmark() -> dict[str, Any]:
    """Run complete memory benchmark suite.

    Returns:
        Dictionary with all benchmark results
    """
    print("=" * 60)
    print("Annotation Cache Memory Benchmark")
    print("=" * 60)

    if not HAS_PSUTIL:
        print("\nWARNING: psutil not available, using basic memory measurement")
    if not HAS_TRACEMALLOC:
        print("\nWARNING: tracemalloc not available")

    results: dict[str, Any] = {
        "benchmark": "annotation_cache_memory",
        "python_version": sys.version,
        "has_psutil": HAS_PSUTIL,
        "has_tracemalloc": HAS_TRACEMALLOC,
    }

    # Test 1: BoundedCache with different sizes
    bounded_results = benchmark_bounded_cache_memory(
        cache_sizes=[1_000, 5_000, 10_000, 50_000],
        num_entries=100_000,
        entry_size_bytes=1024,
    )
    results["bounded_cache"] = bounded_results

    # Test 2: Unbounded dict baseline
    unbounded_results = benchmark_unbounded_dict_memory(
        num_entries_list=[1_000, 5_000, 10_000, 50_000, 100_000],
        entry_size_bytes=1024,
    )
    results["unbounded_dict"] = unbounded_results

    # Test 3: StreamingJSONLReader scalability
    streaming_results = benchmark_streaming_jsonl_reader(
        num_entries_list=[1_000, 10_000, 50_000, 100_000],
        cache_size=1_000,
        entry_size_bytes=1024,
    )
    results["streaming_jsonl"] = streaming_results

    # Test 4: Direct comparison
    comparison_results = benchmark_full_load_vs_streaming(
        num_entries=50_000,
        cache_size=1_000,
        entry_size_bytes=1024,
    )
    results["full_vs_streaming"] = comparison_results

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print("\nBoundedCache (10K cache processing 100K entries):")
    idx = bounded_results["cache_sizes"].index(10_000)
    bounded_10k_memory = bounded_results["memory_mb"][idx]
    print(f"  Memory used: {bounded_10k_memory:.1f}MB")
    print(f"  Hit rate: {bounded_results['hit_rates'][idx]:.2%}")

    print("\nUnbounded dict (100K entries):")
    idx = unbounded_results["num_entries"].index(100_000)
    unbounded_100k_memory = unbounded_results["memory_mb"][idx]
    print(f"  Memory used: {unbounded_100k_memory:.1f}MB")

    if unbounded_100k_memory > 0:
        savings = (
            (unbounded_100k_memory - bounded_10k_memory) / unbounded_100k_memory * 100
        )
        print(f"\n  BoundedCache saves {savings:.0f}% memory!")

    print("\nStreamingJSONLReader (100K entries):")
    if 100_000 in streaming_results["num_entries"]:
        idx = streaming_results["num_entries"].index(100_000)
        print(f"  Memory used: {streaming_results['memory_mb'][idx]:.1f}MB")
        print(
            f"  Random access: {streaming_results['random_access_time_ms'][idx]:.2f}ms"
        )

    # Validation
    print("\n" + "-" * 60)
    print("TARGET VALIDATION")
    print("-" * 60)

    # Target: BoundedCache memory is bounded by cache_size, not entries processed
    # 10K cache processing 100K entries should use ~same memory as 10K entries
    idx_10k = bounded_results["cache_sizes"].index(10_000)
    idx_unbounded_10k = unbounded_results["num_entries"].index(10_000)
    bounded_10k_mem = bounded_results["memory_mb"][idx_10k]
    unbounded_10k_mem = unbounded_results["memory_mb"][idx_unbounded_10k]
    # Bounded 10K cache should be similar to unbounded 10K dict (both hold ~10K entries)
    memory_bounded = abs(bounded_10k_mem - unbounded_10k_mem) < 10  # Within 10MB
    print(
        f"  BoundedCache memory bounded by size: {'PASS' if memory_bounded else 'FAIL'}"
    )

    # Target: Streaming should use less memory than full load
    streaming_better = comparison_results["comparison"]["streaming_is_better"]
    print(f"  Streaming uses less memory: {'PASS' if streaming_better else 'FAIL'}")

    # Target: No OOM simulation (we processed 100K entries successfully)
    print("  Processed 100K entries without OOM: PASS")

    results["validation"] = {
        "bounded_cache_memory_bounded": memory_bounded,
        "streaming_uses_less_memory": streaming_better,
        "no_oom_100k_entries": True,
    }

    # Save results
    output_path = Path("docs/benchmarks/results/annotation_cache_memory.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    try:
        results = run_benchmark()
        print("\n" + "=" * 60)
        print("Benchmark Complete!")
        print("=" * 60)
    except Exception as e:
        print(f"\n Benchmark failed: {e}")
        raise
