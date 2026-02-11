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

# Install UV (replaces Poetry for this project)
pip3 install uv

# Install project dependencies (minimal set for fuzzing)
cd "$SRC/image-preprocessing-detector"

# Install ONLY the fuzz extra which includes minimal deps
# This avoids ~4GB of CUDA/PyTorch dependencies that cause disk space issues
echo "Installing minimal fuzz dependencies (no CUDA/PyTorch)..."

# Install core dependencies manually (excluding heavy ML deps)
# These are the only deps needed for the fuzz targets
# NumPy is pinned to <2.0 in the SAME install command to prevent pip from
# upgrading it when resolving other packages (e.g., opencv-python-headless).
# NumPy 2.x has _core module issues with PyInstaller used by compile_python_fuzzer.
pip3 install \
    "numpy>=1.26.0,<2.0.0" \
    "pillow>=10.0.0" \
    "pymupdf>=1.23.0" \
    "opencv-python-headless>=4.8.0,<5.0.0" \
    "pydantic>=2.0.0" \
    "structlog>=23.1.0" \
    "rich>=13.0.0" \
    "atheris>=2.3.0"

# Install project in editable mode without dependencies
# (we installed them manually above)
pip3 install -e . --no-deps

# Store project directory for absolute paths
PROJECT_DIR="$SRC/image-preprocessing-detector"

# Use OSS-Fuzz helper to compile Python fuzz targets
# This creates proper executables that ClusterFuzzLite recognizes
echo "Compiling Python fuzz targets with compile_python_fuzzer..."
echo "PROJECT_DIR: $PROJECT_DIR"
echo "Fuzz targets to compile:"
ls -la "$PROJECT_DIR/fuzz/"

# Check if compile_python_fuzzer exists
if command -v compile_python_fuzzer &> /dev/null; then
    # Use absolute paths to avoid working directory issues with pyinstaller
    compile_python_fuzzer "$PROJECT_DIR/fuzz/fuzz_pdf_loader.py"
    compile_python_fuzzer "$PROJECT_DIR/fuzz/fuzz_image_loader.py"
    compile_python_fuzzer "$PROJECT_DIR/fuzz/fuzz_text_gate.py"
else
    echo "WARNING: compile_python_fuzzer not found, using alternative approach"
    # Alternative: directly copy and make executable
    cp "$PROJECT_DIR/fuzz/fuzz_pdf_loader.py" "$OUT/fuzz_pdf_loader"
    cp "$PROJECT_DIR/fuzz/fuzz_image_loader.py" "$OUT/fuzz_image_loader"
    cp "$PROJECT_DIR/fuzz/fuzz_text_gate.py" "$OUT/fuzz_text_gate"
    chmod +x "$OUT"/fuzz_*
fi

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
for f in "$OUT"/fuzz_*; do
    [ -e "$f" ] && ls -la "$f"
done
echo "================================"
