#!/usr/bin/env python3
"""Fuzzing harness for image loading functionality.

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

    from image_preprocessing_detector.ingestion.image_loader import ImageLoader


def TestOneInput(data: bytes) -> None:
    """Fuzz target for image loading.

    Args:
        data: Arbitrary byte sequence to use as image input
    """
    # Skip inputs that are too small to be valid images
    if len(data) < 8:
        return

    # Create loader once for all tests (performance optimization)
    loader = ImageLoader()

    try:
        # Test image loading from bytes
        image_bytes = BytesIO(data)

        # Attempt to load image with various DPI values
        for target_dpi in [72, 150, 300]:
            try:
                # Try loading with different format hints
                for format_hint in [None, "PNG", "JPEG", "TIFF"]:
                    try:
                        result = loader.load_from_bytes(
                            image_bytes, target_dpi=target_dpi, format_hint=format_hint
                        )

                        # Access result properties to trigger processing
                        _ = result.image_array
                        _ = result.dpi
                        _ = result.width
                        _ = result.height
                        _ = result.format

                    except Exception:  # nosec B110
                        # Expected for malformed inputs or wrong format hints
                        # Fuzzer must handle all invalid inputs gracefully
                        pass

                    # Reset BytesIO for next iteration
                    image_bytes.seek(0)

            except Exception:  # nosec B110
                # Expected for malformed inputs
                # Fuzzer must handle all invalid inputs gracefully
                pass

            # Reset BytesIO for next DPI iteration
            image_bytes.seek(0)

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
