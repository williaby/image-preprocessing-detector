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

# Copy Python fuzzing harnesses to output directory
# For Python fuzzing, the .py files themselves are the fuzz targets
echo "Copying Python fuzzing harnesses from fuzz/ to $OUT/"
cp -v fuzz/fuzz_pdf_loader.py $OUT/
cp -v fuzz/fuzz_image_loader.py $OUT/
cp -v fuzz/fuzz_text_gate.py $OUT/

# Make Python files executable (they have #!/usr/bin/env python3 shebang)
chmod +x $OUT/fuzz_pdf_loader.py $OUT/fuzz_image_loader.py $OUT/fuzz_text_gate.py

# Set PYTHONPATH for imports
export PYTHONPATH="${SRC}/image-preprocessing-detector/src:${PYTHONPATH:-}"

echo "=== Fuzzing Build Complete ==="
echo "Python fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "PYTHONPATH: $PYTHONPATH"
echo "================================"
