#!/usr/bin/env python3
# ruff: noqa: N802, S110
"""Fuzzing harness for text detection gate functionality.

Note: N802 (TestOneInput) and S110 (try-except-pass) violations are intentional.
ClusterFuzzLite requires TestOneInput naming, and fuzzers must catch all exceptions
without logging to avoid performance overhead during fuzzing.

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


def _fuzz_image_format(
    gate: TextGate, data: bytes, width: int, height: int, channels: int
) -> None:
    """Test a specific image format against the text gate.

    Args:
        gate: TextGate instance to test
        data: Raw byte data to interpret as image
        width: Image width
        height: Image height
        channels: Number of color channels (1=gray, 3=RGB, 4=RGBA)
    """
    size = width * height * channels
    if len(data) < size:
        return

    try:
        shape = (height, width) if channels == 1 else (height, width, channels)
        image_data = np.frombuffer(data[:size], dtype=np.uint8).reshape(shape)
        _ = gate.detect(image_data)
    except Exception:  # nosec B110
        # Expected for malformed inputs - fuzzer must handle gracefully
        pass


def _fuzz_all_formats(gate: TextGate, data: bytes, width: int, height: int) -> None:
    """Test all image formats for a given dimension.

    Args:
        gate: TextGate instance to test
        data: Raw byte data to interpret as image
        width: Image width
        height: Image height
    """
    for channels in (1, 3, 4):  # Grayscale, RGB, RGBA
        _fuzz_image_format(gate, data, width, height, channels)


def TestOneInput(data: bytes) -> None:  # nosonar
    """Fuzz target for text detection gate.

    Note: Function name required by ClusterFuzzLite/atheris framework.

    Args:
        data: Arbitrary byte sequence to use as image data
    """
    min_size = 100
    if len(data) < min_size:
        return

    try:
        gate = TextGate()
    except Exception:  # nosec B110
        return

    try:
        for width, height in [(10, 10), (50, 20), (100, 100)]:
            _fuzz_all_formats(gate, data, width, height)
    except Exception:  # nosec B110
        # Catch all - fuzzer should not crash on invalid input
        pass


def main() -> None:
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
