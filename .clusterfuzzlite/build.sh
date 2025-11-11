#!/bin/bash -eu
# ClusterFuzzLite build script for Image Preprocessing Detector
# Uses OSS-Fuzz compile_python_fuzzer to create proper fuzz target executables

echo "=== ClusterFuzzLite Build Debug ==="
echo "SRC: $SRC"
echo "OUT: $OUT"
echo "WORK: $WORK"
echo "===================================="

# Verify Python version compatibility with Atheris (3.8-3.11)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

echo "Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 8 ] || [ "$PYTHON_MINOR" -gt 11 ]; then
    echo "ERROR: Python $PYTHON_VERSION is not compatible with Atheris"
    echo "Atheris requires Python 3.8-3.11 (not 3.12+ due to PRECALL opcode changes)"
    echo "Base image should provide Python 3.11.13"
    exit 1
fi

echo "Python version $PYTHON_VERSION is compatible with Atheris"

# Install Poetry
pip3 install poetry==2.2.1

# Install project dependencies (without dev dependencies)
cd $SRC/image-preprocessing-detector
poetry config virtualenvs.create false
poetry install --without dev --no-interaction

# Install Atheris for Python fuzzing
pip3 install atheris==2.3.0

# Use OSS-Fuzz helper to compile Python fuzz targets
# This creates proper executables that ClusterFuzzLite recognizes
echo "Compiling Python fuzz targets with compile_python_fuzzer..."

# Check if compile_python_fuzzer exists
if command -v compile_python_fuzzer &> /dev/null; then
    compile_python_fuzzer fuzz/fuzz_pdf_loader.py
    compile_python_fuzzer fuzz/fuzz_image_loader.py
    compile_python_fuzzer fuzz/fuzz_text_gate.py
else
    echo "WARNING: compile_python_fuzzer not found, using alternative approach"
    # Alternative: directly copy and make executable
    cp fuzz/fuzz_pdf_loader.py $OUT/fuzz_pdf_loader
    cp fuzz/fuzz_image_loader.py $OUT/fuzz_image_loader
    cp fuzz/fuzz_text_gate.py $OUT/fuzz_text_gate
    chmod +x $OUT/fuzz_*
fi

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
