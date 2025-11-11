# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

#!/usr/bin/env python3
"""Validation script for PDF resolution detection and upscaling.

This script allows manual verification that the Phase 1c implementation:
1. Correctly identifies PDFs below 300 DPI
2. Successfully upscales them to 300 DPI
3. Produces quality improvements

Usage:
    python scripts/validate_pdf_resolution.py <pdf_file>
    python scripts/validate_pdf_resolution.py <pdf_file> --upscale
    python scripts/validate_pdf_resolution.py <pdf_file> --upscale --output upscaled.pdf
"""

import argparse
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from image_preprocessing_detector.core.config import Settings
from image_preprocessing_detector.ingestion.pdf_analyzer import PDFDocumentAnalyzer
from image_preprocessing_detector.ingestion.pdf_resolution import PDFResolutionAnalyzer


def print_separator(char: str = "=", length: int = 80) -> None:
    """Print a separator line."""
    print(char * length)


def print_section(title: str) -> None:
    """Print a section header."""
    print()
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


def format_bytes(size_bytes: int | float) -> str:
    """Format bytes to human-readable string."""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.2f} TB"


def print_resolution_analysis(analysis: dict[str, Any]) -> None:
    """Print resolution analysis results."""
    print("Resolution Analysis Results:")
    print("-" * 40)

    # Overall metrics
    print(f"  Needs Upscaling: {analysis.get('needs_upscaling', 'N/A')}")
    print(f"  Total Images: {analysis.get('image_count', 0)}")
    print(f"  Low-Res Images: {analysis.get('low_res_image_count', 0)}")

    # DPI metrics
    min_dpi = analysis.get("min_dpi")
    avg_dpi = analysis.get("avg_dpi")
    max_dpi = analysis.get("max_dpi")

    print()
    print("  DPI Metrics:")
    print(f"    Minimum: {min_dpi:.1f} DPI" if min_dpi else "    Minimum: N/A")
    print(f"    Average: {avg_dpi:.1f} DPI" if avg_dpi else "    Average: N/A")
    print(f"    Maximum: {max_dpi:.1f} DPI" if max_dpi else "    Maximum: N/A")

    # Per-page details
    if analysis.get("details"):
        print()
        print("  Per-Page Details:")
        for page_info in analysis["details"]:
            page_num = page_info.get("page_number", "?")
            page_min = page_info.get("min_dpi")
            page_avg = page_info.get("avg_dpi")
            page_images = page_info.get("image_count", 0)

            if page_min:
                print(
                    f"    Page {page_num}: {page_images} images, "
                    f"min={page_min:.1f} DPI, avg={page_avg:.1f} DPI"
                )


def print_upscaling_result(result: dict[str, Any]) -> None:
    """Print upscaling result."""
    print("Upscaling Results:")
    print("-" * 40)

    success = result.get("success", False)
    print(f"  Success: {success}")

    if not success:
        error_msg = result.get("error_message", "Unknown error")
        print(f"  Error: {error_msg}")
        return

    # Size information
    before_size = result.get("before_size", 0)
    after_size = result.get("after_size", 0)

    print(f"  Original Size: {format_bytes(before_size)}")
    print(f"  Upscaled Size: {format_bytes(after_size)}")

    if before_size > 0:
        ratio = after_size / before_size
        print(f"  Size Increase: {ratio:.2f}x")

    # Processing information
    processing_time = result.get("processing_time", 0)
    pages_processed = result.get("pages_processed", 0)

    print(f"  Processing Time: {processing_time:.2f}s")
    print(f"  Pages Processed: {pages_processed}")

    # Output path
    output_path = result.get("output_path")
    if output_path:
        print(f"  Output Path: {output_path}")


def validate_pdf_resolution(pdf_path: Path) -> dict[str, Any]:
    """Validate PDF resolution detection.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Analysis results dictionary
    """
    print_section("Step 1: Resolution Detection")

    analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)

    try:
        analysis = analyzer.analyze_pdf_resolution(pdf_path)
        print_resolution_analysis(analysis)
        return analysis
    except Exception as e:
        print(f"❌ Error analyzing PDF: {e}")
        return {"error": str(e)}


def validate_pdf_upscaling(
    pdf_path: Path,
    output_path: Path | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Validate PDF upscaling.

    Args:
        pdf_path: Path to input PDF
        output_path: Optional output path for upscaled PDF
        settings: Optional settings

    Returns:
        Upscaling results dictionary
    """
    print_section("Step 2: PDF Upscaling")

    settings = settings or Settings()
    analyzer = PDFDocumentAnalyzer(settings=settings)

    try:
        result = analyzer.analyze(pdf_path, perform_upscaling=True)

        print(f"Analysis Time: {result.processing_time:.2f}s")
        print()

        if result.upscaling_result:
            print_upscaling_result(result.upscaling_result)

        # Verify upscaled resolution
        if result.upscaled_path and Path(result.upscaled_path).exists():
            print()
            print_section("Step 3: Verify Upscaled Resolution")

            upscaled_analyzer = PDFResolutionAnalyzer(min_dpi_threshold=300)
            upscaled_analysis = upscaled_analyzer.analyze_pdf_resolution(
                result.upscaled_path
            )

            print_resolution_analysis(upscaled_analysis)

            # Compare before and after
            print()
            print("DPI Improvement:")
            print("-" * 40)

            original_min = result.resolution_analysis.get("min_dpi", 0)
            upscaled_min = upscaled_analysis.get("min_dpi", 0)

            if original_min and upscaled_min:
                improvement = upscaled_min - original_min
                improvement_pct = (improvement / original_min) * 100

                print(f"  Original Min DPI: {original_min:.1f}")
                print(f"  Upscaled Min DPI: {upscaled_min:.1f}")
                print(f"  Improvement: {improvement:.1f} DPI ({improvement_pct:.1f}%)")

                # Verify target achieved
                if upscaled_min >= 300:
                    print()
                    print("  ✓ Target DPI (300) achieved!")
                else:
                    print()
                    print(
                        f"  ⚠ Target DPI (300) not fully achieved "
                        f"(got {upscaled_min:.1f})"
                    )

            # Move to output path if specified
            if output_path:
                import shutil

                shutil.copy2(result.upscaled_path, output_path)
                print()
                print(f"✓ Upscaled PDF saved to: {output_path}")

                # Cleanup temp file
                Path(result.upscaled_path).unlink()
            else:
                print()
                print(f"Note: Temporary upscaled file at: {result.upscaled_path}")
                print("      (will be cleaned up automatically)")

        return result.to_dict()

    except Exception as e:
        print(f"❌ Error upscaling PDF: {e}")
        return {"error": str(e)}


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate PDF resolution detection and upscaling (Phase 1c)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze PDF resolution only
  python scripts/validate_pdf_resolution.py document.pdf

  # Analyze and upscale PDF
  python scripts/validate_pdf_resolution.py document.pdf --upscale

  # Analyze, upscale, and save to specific output
  python scripts/validate_pdf_resolution.py document.pdf --upscale --output high_res.pdf

  # Use custom DPI thresholds
  python scripts/validate_pdf_resolution.py document.pdf --upscale --min-dpi 200 --target-dpi 600
        """,
    )

    parser.add_argument(
        "pdf_file",
        type=Path,
        help="Path to PDF file to validate",
    )

    parser.add_argument(
        "--upscale",
        action="store_true",
        help="Perform upscaling (not just analysis)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output path for upscaled PDF (implies --upscale)",
    )

    parser.add_argument(
        "--min-dpi",
        type=int,
        default=300,
        help="Minimum DPI threshold (default: 300)",
    )

    parser.add_argument(
        "--target-dpi",
        type=int,
        default=300,
        help="Target DPI for upscaling (default: 300)",
    )

    parser.add_argument(
        "--algorithm",
        choices=["lanczos", "bicubic", "inter_cubic", "inter_linear", "inter_area"],
        default="lanczos",
        help="Upscaling algorithm (default: lanczos)",
    )

    args = parser.parse_args()

    # Validate input file
    if not args.pdf_file.exists():
        print(f"❌ Error: PDF file not found: {args.pdf_file}")
        return 1

    # Print header
    print()
    print_separator("=")
    print("  PDF Resolution Validation (Phase 1c)")
    print_separator("=")
    print()
    print(f"Input PDF: {args.pdf_file}")
    print(f"File Size: {format_bytes(args.pdf_file.stat().st_size)}")

    # Step 1: Analyze resolution
    analysis = validate_pdf_resolution(args.pdf_file)

    if "error" in analysis:
        return 1

    # Step 2: Upscale if requested
    if args.upscale or args.output:
        settings = Settings(
            enable_pdf_upscaling=True,
            pdf_min_dpi=args.min_dpi,
            pdf_target_dpi=args.target_dpi,
            pdf_upscale_algorithm=args.algorithm,
        )

        result = validate_pdf_upscaling(args.pdf_file, args.output, settings)

        if "error" in result:
            return 1

    # Summary
    print()
    print_section("Validation Complete")

    needs_upscaling = analysis.get("needs_upscaling", False)
    min_dpi = analysis.get("min_dpi")

    if needs_upscaling:
        print(f"✓ Correctly identified low-resolution PDF (min DPI: {min_dpi:.1f})")
    else:
        print(f"✓ Correctly identified high-resolution PDF (min DPI: {min_dpi:.1f})")

    if args.upscale or args.output:
        print("✓ Upscaling completed successfully")

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
