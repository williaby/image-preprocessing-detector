#!/bin/bash -eu
# ClusterFuzzLite build script for Image Preprocessing Detector
# Uses OSS-Fuzz compile_python_fuzzer to create proper fuzz target executables

echo "=== ClusterFuzzLite Build Debug ==="
echo "SRC: $SRC"
echo "OUT: $OUT"
echo "WORK: $WORK"
echo "===================================="

# Install Poetry
pip3 install poetry

# Install project dependencies (without dev dependencies)
cd $SRC/image-preprocessing-detector
poetry config virtualenvs.create false
poetry install --without dev --no-interaction

# Use OSS-Fuzz helper to compile Python fuzz targets
# This creates proper executables that ClusterFuzzLite recognizes
echo "Compiling Python fuzz targets with compile_python_fuzzer..."

compile_python_fuzzer fuzz fuzz_pdf_loader
compile_python_fuzzer fuzz fuzz_image_loader
compile_python_fuzzer fuzz fuzz_text_gate

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
