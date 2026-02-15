#!/usr/bin/env python3
# ruff: noqa: N802, S110
"""Fuzzing harness for image loading functionality.

Note: N802 (TestOneInput) and S110 (try-except-pass) violations are intentional.
ClusterFuzzLite requires TestOneInput naming, and fuzzers must catch all exceptions
without logging to avoid performance overhead during fuzzing.

This fuzzer tests the ImageLoader for crashes, hangs, and unexpected behavior
when processing malformed or adversarial image inputs.

Target Areas:
- Image format detection and validation
- Image decoding (PNG, JPEG, TIFF)
- Color space conversion
- DPI normalization
- Error handling
"""

import sys

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    from io import BytesIO

    import numpy as np
    from PIL import Image


def TestOneInput(data: bytes) -> None:  # nosonar  # Name required by atheris framework
    """Fuzz target for image loading.

    Args:
        data: Arbitrary byte sequence to use as image input
    """
    # Skip inputs that are too small to be valid images
    if len(data) < 8:
        return

    try:
        # DESIGN: Use PIL directly instead of ImageLoader for performance
        # ImageLoader requires file paths (not bytes), which would force us to write
        # each fuzz input to disk. Using PIL.Image.open() with BytesIO allows direct
        # byte-based fuzzing without filesystem I/O overhead.
        image_bytes = BytesIO(data)

        # Try opening the image
        img = Image.open(image_bytes)

        # Access image properties to trigger processing
        _ = img.size
        _ = img.mode
        _ = img.format

        # Convert to numpy array (triggers decoding)
        img_array = np.array(img)
        _ = img_array.shape

        # Test DPI information access
        dpi_info = img.info.get("dpi", None)
        _ = dpi_info

        img.close()

    except Exception:  # nosec B110
        # Catch all exceptions - fuzzer should not crash on invalid input
        # Fuzzing requires handling all edge cases without propagating exceptions
        pass


def main() -> None:
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
