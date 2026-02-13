#!/usr/bin/env python3
"""Smoke test for complex script rendering with HarfBuzz/libraqm.

This script validates that Pillow is correctly configured with libraqm support
for rendering complex scripts that require text shaping (Arabic, Devanagari,
Tibetan, etc.).

Run this BEFORE implementing the synthetic document generator to ensure
the rendering infrastructure works correctly.

Usage:
    uv run python scripts/smoke_test_complex_scripts.py

Requirements:
    - System dependency: libraqm (see pyproject.toml synthetic extra for install)
    - Noto fonts installed (will attempt to locate automatically)

Expected Output:
    - Console output showing test results for each script
    - Sample images saved to tmp_cleanup/smoke_test_output/
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont, features


class ScriptTestCase(NamedTuple):
    """Test case for a complex script."""

    script_code: str
    script_name: str
    sample_text: str
    font_name: str
    expected_features: list[str]


# Test cases for complex scripts
# These scripts REQUIRE HarfBuzz text shaping for correct rendering
TEST_CASES: list[ScriptTestCase] = [
    ScriptTestCase(
        script_code="Tibt",
        script_name="Tibetan",
        sample_text="བཀྲ་ཤིས་བདེ་ལེགས།",  # "Tashi Delek" (blessing)
        font_name="NotoSerifTibetan-Regular.ttf",
        expected_features=["vertical_stacking", "conjuncts"],
    ),
    ScriptTestCase(
        script_code="Arab",
        script_name="Arabic",
        sample_text="مرحبا بالعالم",  # "Hello World"
        font_name="NotoNaskhArabic-Regular.ttf",
        expected_features=["rtl", "contextual_shaping", "ligatures"],
    ),
    ScriptTestCase(
        script_code="Deva",
        script_name="Devanagari (Hindi)",
        sample_text="नमस्ते दुनिया",  # "Hello World"
        font_name="NotoSansDevanagari-Regular.ttf",
        expected_features=["conjuncts", "matras", "nukta"],
    ),
    ScriptTestCase(
        script_code="Thai",
        script_name="Thai",
        sample_text="สวัสดีโลก",  # "Hello World"
        font_name="NotoSansThai-Regular.ttf",
        expected_features=["tone_marks", "vowel_positioning"],
    ),
    ScriptTestCase(
        script_code="Khmr",
        script_name="Khmer",
        sample_text="សួស្តី​ពិភពលោក",  # "Hello World"
        font_name="NotoSansKhmer-Regular.ttf",
        expected_features=["subscript_consonants", "vowel_positioning"],
    ),
    ScriptTestCase(
        script_code="Mymr",
        script_name="Myanmar",
        sample_text="မင်္ဂလာပါ",  # "Hello"
        font_name="NotoSansMyanmar-Regular.ttf",
        expected_features=["stacked_consonants", "medials"],
    ),
]

# Common Noto font directories
FONT_SEARCH_PATHS = [
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/noto"),
    Path("/usr/share/fonts/google-noto"),
    Path("/usr/local/share/fonts"),
    Path.home() / ".local/share/fonts",
    Path.home() / ".fonts",
    # macOS
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    # Windows
    Path("C:/Windows/Fonts"),
]


def check_libraqm_support() -> bool:
    """Check if Pillow was compiled with libraqm support."""
    # Check for raqm feature (complex text layout)
    raqm_available = features.check("raqm")

    # Also check freetype (required base)
    freetype_available = features.check("freetype2")

    print("=" * 60)
    print("PILLOW FEATURE CHECK")
    print("=" * 60)
    print(f"  FreeType2: {'✓ Available' if freetype_available else '✗ Missing'}")
    print(f"  libraqm:   {'✓ Available' if raqm_available else '✗ Missing'}")

    if not raqm_available:
        print("\n⚠️  WARNING: libraqm is NOT available!")
        print("   Complex scripts (Arabic, Devanagari, Tibetan, etc.) will NOT")
        print("   render correctly without libraqm support.")
        print("\n   To fix, install libraqm:")
        print("     Ubuntu/Debian: sudo apt-get install libraqm-dev")
        print("     macOS: brew install libraqm")
        print("     Then reinstall Pillow: pip install --force-reinstall pillow")
    print()

    return raqm_available


def find_font(font_name: str) -> Path | None:
    """Search for a font file in common locations."""
    for search_path in FONT_SEARCH_PATHS:
        if not search_path.exists():
            continue

        # Direct match
        font_path = search_path / font_name
        if font_path.exists():
            return font_path

        # Search recursively
        for found in search_path.rglob(font_name):
            return found

        # Try without extension variations
        base_name = font_name.rsplit(".", 1)[0]
        for ext in [".ttf", ".otf", ".TTF", ".OTF"]:
            for found in search_path.rglob(f"{base_name}*{ext}"):
                return found

    return None


def render_text_sample(
    text: str,
    font_path: Path,
    font_size: int = 48,
    direction: str = "ltr",
) -> Image.Image:
    """Render text sample using Pillow with optional direction."""
    # Create image
    img_width = 800
    img_height = 200
    img = Image.new("RGB", (img_width, img_height), "white")
    draw = ImageDraw.Draw(img)

    # Load font
    font = ImageFont.truetype(str(font_path), font_size)

    # Calculate text position
    x = 50
    y = 50

    # Draw text with direction parameter (requires libraqm)
    try:
        # Try with direction parameter (requires Pillow 9.2.0+ and libraqm)
        draw.text((x, y), text, font=font, fill="black", direction=direction)
    except TypeError:
        # Fallback for older Pillow without direction parameter
        draw.text((x, y), text, font=font, fill="black")

    return img


def test_script(test_case: ScriptTestCase, output_dir: Path) -> tuple[bool, str]:
    """Test rendering for a specific script.

    Returns:
        Tuple of (success, message)
    """
    print(f"\n--- Testing {test_case.script_name} ({test_case.script_code}) ---")

    # Find font
    font_path = find_font(test_case.font_name)
    if not font_path:
        return False, f"Font not found: {test_case.font_name}"

    print(f"  Font: {font_path}")
    print(f"  Sample text: {test_case.sample_text}")

    # Determine direction
    direction = "rtl" if test_case.script_code in ["Arab", "Hebr"] else "ltr"

    try:
        # Render text
        img = render_text_sample(
            test_case.sample_text,
            font_path,
            font_size=48,
            direction=direction,
        )

        # Save output
        output_path = output_dir / f"smoke_test_{test_case.script_code}.png"
        img.save(output_path)
        print(f"  Output: {output_path}")

        # Basic validation - check that the image isn't blank
        # (A very basic check; visual inspection is still recommended)
        pixels = list(img.getdata())
        non_white_pixels = sum(1 for p in pixels if p != (255, 255, 255))
        if non_white_pixels < 100:
            return False, "Rendered image appears blank - text may not have rendered"

        return True, f"Success - {non_white_pixels} non-white pixels rendered"

    except Exception as e:
        return False, f"Rendering failed: {e}"


def main() -> int:
    """Run smoke tests for complex script rendering."""
    print("\n" + "=" * 60)
    print("COMPLEX SCRIPT RENDERING SMOKE TEST")
    print("=" * 60)
    print("\nThis test validates that complex scripts can be rendered correctly.")
    print("It requires libraqm for proper text shaping.\n")

    # Check libraqm support
    has_raqm = check_libraqm_support()

    # Create output directory
    output_dir = Path("tmp_cleanup/smoke_test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir.absolute()}\n")

    # Run tests
    results: list[tuple[str, bool, str]] = []

    for test_case in TEST_CASES:
        success, message = test_script(test_case, output_dir)
        results.append((test_case.script_name, success, message))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0

    for script_name, success, message in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {script_name}")
        if not success:
            print(f"         {message}")
            failed += 1
        else:
            passed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if not has_raqm:
        print("\n⚠️  WARNING: Tests ran WITHOUT libraqm support!")
        print("   Results may show passing but text shaping is INCORRECT.")
        print("   Install libraqm and re-run for accurate results.")

    if failed > 0:
        print("\n❌ Some tests failed. Check the output images for visual inspection.")
        return 1

    print("\n✅ All tests passed!")
    print(f"   Check rendered images in: {output_dir.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
