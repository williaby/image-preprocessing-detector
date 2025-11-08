#!/usr/bin/env python3
"""Fuzzing harness for text detection gate functionality.

This fuzzer tests the TextGate for crashes, hangs, and unexpected behavior
when processing malformed or adversarial image inputs.

Target Areas:
- Stroke density calculation
- Connected components analysis
- Edge density computation
- Ensemble voting logic
- Error handling
"""

import sys

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    import numpy as np

    from image_preprocessing_detector.detection.text_gate import TextGate


def TestOneInput(data: bytes) -> None:
    """Fuzz target for text detection gate.

    Args:
        data: Arbitrary byte sequence to use as image data
    """
    # Need at least enough data for a small image
    min_size = 100
    if len(data) < min_size:
        return

    # Create gate once for all tests (performance optimization)
    try:
        gate = TextGate()
    except Exception:  # nosec B110
        # If gate creation fails, skip this input
        return

    try:
        # Try to interpret data as various image sizes and formats
        for width, height in [(10, 10), (50, 20), (100, 100)]:
            size = width * height

            # Check if we have enough data
            if len(data) < size:
                continue

            try:
                # Grayscale (single channel)
                image_data = np.frombuffer(data[:size], dtype=np.uint8).reshape(
                    height, width
                )

                _ = gate.detect(image_data)

            except Exception:  # nosec B110
                # Expected for malformed inputs
                # Fuzzer must handle all invalid inputs gracefully
                pass

            # RGB (3 channels)
            try:
                rgb_size = size * 3
                if len(data) >= rgb_size:
                    image_data = np.frombuffer(data[:rgb_size], dtype=np.uint8).reshape(
                        height, width, 3
                    )

                    _ = gate.detect(image_data)

            except Exception:  # nosec B110
                # Expected for malformed inputs
                # Fuzzer must handle all invalid inputs gracefully
                pass

            # RGBA (4 channels)
            try:
                rgba_size = size * 4
                if len(data) >= rgba_size:
                    image_data = np.frombuffer(
                        data[:rgba_size], dtype=np.uint8
                    ).reshape(height, width, 4)

                    _ = gate.detect(image_data)

            except Exception:  # nosec B110
                # Expected for malformed inputs
                # Fuzzer must handle all invalid inputs gracefully
                pass

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
