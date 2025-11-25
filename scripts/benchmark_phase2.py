#!/usr/bin/env python3
"""
Performance benchmarking script for Phase 2 integration.

Measures:
1. Phase 1 baseline latency (classical IQA pipeline)
2. Phase 2 overhead estimate (ML components when implemented)
3. Throughput metrics
4. Component-level performance breakdown

Target: <50ms overhead for Phase 2 ML components (when implemented)

Note: Phase 2 ML components are not yet implemented (~25% complete).
This script currently benchmarks Phase 1 baseline performance only.
"""

import tempfile
import time
from pathlib import Path
from typing import Any

import cv2
import fitz  # PyMuPDF
import numpy as np
from rich.console import Console
from rich.table import Table

from image_preprocessing_detector.correction.corrections import (
    correct_skew,
    enhance_contrast,
)
from image_preprocessing_detector.detection.iqa_classical import (
    detect_blur,
    detect_contrast,
    detect_skew,
)
from image_preprocessing_detector.detection.text_gate import detect_text
from image_preprocessing_detector.ingestion.image_loader import load_image
from image_preprocessing_detector.ingestion.pdf_loader import load_pdf
from image_preprocessing_detector.output.json_generator import (
    MetadataBuilder,
    generate_json,
)

console = Console()

# Status indicator constants
STATUS_PASS = "✓ Pass"  # nosec B105 - False positive: status text, not password
STATUS_FAIL = "✗ Fail"


class PerformanceBenchmark:
    """Performance benchmarking for Phase 1 and Phase 2 pipelines."""

    def __init__(self, num_iterations: int = 10) -> None:
        """
        Initialize performance benchmark.

        Args:
            num_iterations: Number of iterations for each benchmark
        """
        self.num_iterations = num_iterations
        self.results: dict[str, Any] = {}

    def benchmark_component(
        self, name: str, func: Any, *args: Any, **kwargs: Any
    ) -> dict[str, float]:
        """
        Benchmark a single component.

        Args:
            name: Component name
            func: Function to benchmark
            *args: Positional arguments to pass to function
            **kwargs: Keyword arguments to pass to function

        Returns:
            Dictionary with timing statistics
        """
        times = []

        for _ in range(self.num_iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        return {
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": sum(times) / len(times),
            "median_ms": sorted(times)[len(times) // 2],
        }

    def create_test_pdf(self, tmpdir: Path, num_pages: int = 1) -> Path:
        """
        Create test PDF for benchmarking.

        Args:
            tmpdir: Temporary directory
            num_pages: Number of pages in PDF

        Returns:
            Path to created PDF
        """
        pdf_path = tmpdir / f"benchmark_{num_pages}p.pdf"
        doc = fitz.open()

        for i in range(num_pages):
            page = doc.new_page(width=595, height=842)
            text = f"Page {i + 1}\n\nBenchmark Document\n\nLorem ipsum dolor sit amet."
            page.insert_text((50, 50), text, fontsize=12)

        doc.save(str(pdf_path))
        doc.close()

        return pdf_path

    def create_test_image(self, tmpdir: Path) -> Path:
        """
        Create test image for benchmarking.

        Args:
            tmpdir: Temporary directory

        Returns:
            Path to created image
        """
        img = np.ones((1000, 800, 3), dtype=np.uint8) * 200

        # Add text-like patterns
        for y in range(100, 900, 50):
            cv2.line(img, (100, y), (700, y), (50, 50, 50), 3)

        img_path = tmpdir / "benchmark.jpg"
        cv2.imwrite(str(img_path), img)

        return img_path

    def benchmark_phase1_components(self) -> None:
        """Benchmark Phase 1 individual components."""
        console.print("\n[bold]Phase 1 Component Benchmarks[/bold]")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test data
            pdf_path = self.create_test_pdf(tmppath)
            img_path = self.create_test_image(tmppath)

            # Load test data once
            pages = load_pdf(str(pdf_path))
            test_image = pages[0].image

            _, _ = load_image(str(img_path))

            # Benchmark components
            console.print("\n[cyan]Ingestion Components:[/cyan]")
            self.results["pdf_loader"] = self.benchmark_component(
                "PDF Loader", load_pdf, str(pdf_path)
            )
            console.print(
                f"  PDF Loader: {self.results['pdf_loader']['mean_ms']:.2f}ms (avg)"
            )

            self.results["image_loader"] = self.benchmark_component(
                "Image Loader", load_image, str(img_path)
            )
            console.print(
                f"  Image Loader: {self.results['image_loader']['mean_ms']:.2f}ms (avg)"
            )

            # Detection components
            console.print("\n[cyan]Detection Components:[/cyan]")
            self.results["text_gate"] = self.benchmark_component(
                "Text Gate", detect_text, test_image
            )
            console.print(
                f"  Text Gate: {self.results['text_gate']['mean_ms']:.2f}ms (avg)"
            )

            self.results["skew_detection"] = self.benchmark_component(
                "Skew Detection", detect_skew, test_image
            )
            console.print(
                f"  Skew Detection: {self.results['skew_detection']['mean_ms']:.2f}ms (avg)"
            )

            self.results["blur_detection"] = self.benchmark_component(
                "Blur Detection", detect_blur, test_image
            )
            console.print(
                f"  Blur Detection: {self.results['blur_detection']['mean_ms']:.2f}ms (avg)"
            )

            self.results["contrast_detection"] = self.benchmark_component(
                "Contrast Detection", detect_contrast, test_image
            )
            console.print(
                f"  Contrast Detection: {self.results['contrast_detection']['mean_ms']:.2f}ms (avg)"
            )

            # Correction components
            console.print("\n[cyan]Correction Components:[/cyan]")
            skew_result = detect_skew(test_image)
            if skew_result and skew_result.is_skewed:
                self.results["skew_correction"] = self.benchmark_component(
                    "Skew Correction",
                    correct_skew,
                    test_image,
                    skew_result.angle,
                    skew_result.confidence,
                )
                console.print(
                    f"  Skew Correction: {self.results['skew_correction']['mean_ms']:.2f}ms (avg)"
                )
            else:
                console.print("  Skew Correction: N/A (no skew detected)")

            contrast_result = detect_contrast(test_image)
            if contrast_result and contrast_result.is_low_contrast:
                self.results["contrast_enhancement"] = self.benchmark_component(
                    "Contrast Enhancement",
                    enhance_contrast,
                    test_image,
                    contrast_result.score,
                    contrast_result.severity,
                )
                console.print(
                    f"  Contrast Enhancement: {self.results['contrast_enhancement']['mean_ms']:.2f}ms (avg)"
                )
            else:
                console.print("  Contrast Enhancement: N/A (contrast OK)")

    def benchmark_phase1_end_to_end(self) -> None:
        """Benchmark Phase 1 end-to-end pipeline."""
        console.print("\n[bold]Phase 1 End-to-End Pipeline Benchmark[/bold]")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Single page
            pdf_path = self.create_test_pdf(tmppath, num_pages=1)

            def run_pipeline() -> None:
                pages = load_pdf(str(pdf_path))
                builder = MetadataBuilder(
                    document_id="bench_001", file_name="benchmark.pdf"
                )

                for page_idx, page_image in enumerate(pages):
                    text_result = detect_text(page_image.image)

                    skew_result = None
                    blur_result = None
                    contrast_result = None

                    if text_result.has_text:
                        skew_result = detect_skew(page_image.image)
                        blur_result = detect_blur(page_image.image)
                        contrast_result = detect_contrast(page_image.image)

                    builder.add_page(
                        page_number=page_idx,
                        page_data=page_image,
                        text_result=text_result,
                        skew_result=skew_result,
                        blur_result=blur_result,
                        contrast_result=contrast_result,
                    )

                metadata = builder.build()
                output_path = tmppath / "output.json"
                generate_json(metadata, output_path)

            self.results["phase1_e2e_1page"] = self.benchmark_component(
                "Phase 1 E2E (1 page)", run_pipeline
            )

            console.print(
                f"\n  Single Page: {self.results['phase1_e2e_1page']['mean_ms']:.2f}ms (avg)"
            )

            # Multi-page
            pdf_path_multi = self.create_test_pdf(tmppath, num_pages=10)

            def run_pipeline_multi() -> None:
                pages = load_pdf(str(pdf_path_multi))
                builder = MetadataBuilder(
                    document_id="bench_multi_001", file_name="benchmark_multi.pdf"
                )

                for page_idx, page_image in enumerate(pages):
                    text_result = detect_text(page_image.image)

                    skew_result = None
                    blur_result = None
                    contrast_result = None

                    if text_result.has_text:
                        skew_result = detect_skew(page_image.image)
                        blur_result = detect_blur(page_image.image)
                        contrast_result = detect_contrast(page_image.image)

                    builder.add_page(
                        page_number=page_idx,
                        page_data=page_image,
                        text_result=text_result,
                        skew_result=skew_result,
                        blur_result=blur_result,
                        contrast_result=contrast_result,
                    )

                metadata = builder.build()
                output_path = tmppath / "output_multi.json"
                generate_json(metadata, output_path)

            self.results["phase1_e2e_10page"] = self.benchmark_component(
                "Phase 1 E2E (10 pages)", run_pipeline_multi
            )

            console.print(
                f"  10 Pages: {self.results['phase1_e2e_10page']['mean_ms']:.2f}ms (avg)"
            )

            # Calculate per-page average
            per_page_ms = self.results["phase1_e2e_10page"]["mean_ms"] / 10
            console.print(f"  Per Page Average: {per_page_ms:.2f}ms")

            # Calculate throughput
            throughput = 1000 / per_page_ms  # pages/sec
            console.print(f"  Throughput: {throughput:.2f} pages/sec")

    def estimate_phase2_overhead(self) -> None:
        """
        Estimate Phase 2 ML overhead.

        Note: Phase 2 ML components not yet implemented.
        This provides target estimates based on design specs.
        """
        console.print("\n[bold]Phase 2 ML Overhead Estimates[/bold]")

        console.print(
            "\n[yellow]Note: Phase 2 ML components not yet implemented[/yellow]"
        )
        console.print("[yellow]Estimates based on design targets:[/yellow]\n")

        # Design targets from ADRs and phase plan
        targets = {
            "ML IQA Inference (MobileNetV3)": {
                "target_ms": 30,
                "confidence": "high",
                "notes": "Per-page with ONNX INT8",
            },
            "Ensemble Voting (Classical + ML)": {
                "target_ms": 5,
                "confidence": "medium",
                "notes": "Confidence-weighted combination",
            },
            "Document Quality Score (DQS)": {
                "target_ms": 10,
                "confidence": "medium",
                "notes": "Degradation + complexity calculation",
            },
            "PDF Type Classification": {
                "target_ms": 5,
                "confidence": "high",
                "notes": "Heuristic-based, fast",
            },
        }

        total_overhead = sum(t["target_ms"] for t in targets.values())

        table = Table(title="Phase 2 Component Estimates")
        table.add_column("Component", style="cyan")
        table.add_column("Target (ms)", justify="right", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Notes", style="dim")

        for component, data in targets.items():
            table.add_row(
                component,
                str(data["target_ms"]),
                data["confidence"],
                data["notes"],
            )

        console.print(table)

        console.print(f"\n[bold]Total Estimated Overhead: {total_overhead}ms[/bold]")

        if total_overhead <= 50:
            console.print(
                f"[green]✓ Within target: <50ms overhead (actual: {total_overhead}ms)[/green]"
            )
        else:
            console.print(
                f"[red]✗ Exceeds target: >50ms overhead (actual: {total_overhead}ms)[/red]"
            )

    def generate_summary_report(self) -> None:
        """Generate summary performance report."""
        console.print("\n[bold]Performance Summary Report[/bold]")

        # Phase 1 baseline
        phase1_baseline = self.results.get("phase1_e2e_1page", {}).get("mean_ms", 0)

        # Estimated Phase 2
        phase2_ml_overhead = 50  # Target estimate
        phase2_total = phase1_baseline + phase2_ml_overhead

        table = Table(title="Phase Comparison")
        table.add_column("Phase", style="cyan")
        table.add_column("Per Page (ms)", justify="right", style="green")
        table.add_column("Throughput (pages/sec)", justify="right", style="yellow")
        table.add_column("Status", style="magenta")

        if phase1_baseline > 0:
            phase1_throughput = 1000 / phase1_baseline
            table.add_row(
                "Phase 1 (Classical IQA)",
                f"{phase1_baseline:.2f}",
                f"{phase1_throughput:.2f}",
                "✓ Measured",
            )

        phase2_throughput = 1000 / phase2_total if phase2_total > 0 else 0
        table.add_row(
            "Phase 2 (Classical + ML)",
            f"{phase2_total:.2f}",
            f"{phase2_throughput:.2f}",
            "⚠ Estimate",
        )

        console.print(table)

        # Targets comparison
        console.print("\n[bold]Target Comparison[/bold]")

        targets_table = Table()
        targets_table.add_column("Metric", style="cyan")
        targets_table.add_column("Target", style="yellow")
        targets_table.add_column("Phase 2 Estimate", style="green")
        targets_table.add_column("Status", style="magenta")

        # Latency target: <150ms per page (with GPU)
        status = STATUS_PASS if phase2_total < 150 else STATUS_FAIL
        targets_table.add_row(
            "Latency (GPU)",
            "<150ms/page",
            f"{phase2_total:.2f}ms",
            status,
        )

        # Throughput target: >6 pages/sec
        status = STATUS_PASS if phase2_throughput > 6 else STATUS_FAIL
        targets_table.add_row(
            "Throughput (GPU)",
            ">6 pages/sec",
            f"{phase2_throughput:.2f}",
            status,
        )

        # Overhead target: <50ms
        overhead = phase2_total - phase1_baseline if phase1_baseline > 0 else 50
        status = STATUS_PASS if overhead <= 50 else STATUS_FAIL
        targets_table.add_row(
            "ML Overhead",
            "<50ms",
            f"{overhead:.2f}ms",
            status,
        )

        console.print(targets_table)

    def run_all_benchmarks(self) -> None:
        """Run all performance benchmarks."""
        console.print("[bold green]Phase 2 Performance Benchmarking[/bold green]")
        console.print(f"Running {self.num_iterations} iterations per benchmark...\n")

        self.benchmark_phase1_components()
        self.benchmark_phase1_end_to_end()
        self.estimate_phase2_overhead()
        self.generate_summary_report()

        console.print("\n[bold green]Benchmarking complete![/bold green]")


def main() -> None:
    """Run performance benchmarks."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2 Performance Benchmarking")
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations per benchmark (default: 10)",
    )

    args = parser.parse_args()

    benchmark = PerformanceBenchmark(num_iterations=args.iterations)
    benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()
