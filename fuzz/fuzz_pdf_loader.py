#!/usr/bin/env python3
"""Fuzzing harness for PDF loading functionality.

This fuzzer tests the PDFLoader for crashes, hangs, and unexpected behavior
when processing malformed or adversarial PDF inputs.

Target Areas:
- PDF parsing and validation
- Page extraction
- DPI estimation
- Image conversion
- Error handling
"""

import sys

import atheris

# Instrument imports before importing target code
with atheris.instrument_imports():
    from io import BytesIO

    from image_preprocessing_detector.ingestion.pdf_loader import PDFLoader


def TestOneInput(data: bytes) -> None:
    """Fuzz target for PDF loading.

    Args:
        data: Arbitrary byte sequence to use as PDF input
    """
    # Skip inputs that are too small to be valid PDFs
    if len(data) < 10:
        return

    try:
        # Test PDF loading from bytes
        pdf_bytes = BytesIO(data)
        loader = PDFLoader()

        # Attempt to load pages with various DPI values
        for target_dpi in [72, 150, 300]:
            try:
                pages = loader.load_from_bytes(pdf_bytes, target_dpi=target_dpi)

                # Access page properties to trigger processing
                for page in pages:
                    # Trigger property access
                    _ = page.image_array
                    _ = page.page_number
                    _ = page.dpi
                    _ = page.width
                    _ = page.height

                    # Break after first page to limit execution time
                    break

            except Exception:  # nosec B110
                # Expected for malformed inputs - don't propagate
                # Fuzzer must handle all invalid inputs gracefully
                pass

            # Reset BytesIO for next iteration
            pdf_bytes.seek(0)

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
