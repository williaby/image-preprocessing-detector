#!/bin/bash -eu
# ClusterFuzzLite build script for Image Preprocessing Detector
# Installs dependencies and prepares Python fuzzing harnesses

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

# Install Atheris fuzzing engine
pip3 install atheris

# Copy Python fuzzing harnesses and wrappers to output directory
echo "Copying Python fuzzing harnesses from fuzz/ to $OUT/"
cp -v fuzz/fuzz_*.py $OUT/
cp -v fuzz/fuzz_pdf_loader fuzz/fuzz_image_loader fuzz/fuzz_text_gate $OUT/

# Ensure wrappers are executable
chmod +x $OUT/fuzz_pdf_loader $OUT/fuzz_image_loader $OUT/fuzz_text_gate

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
