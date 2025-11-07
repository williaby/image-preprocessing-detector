#!/bin/bash -eu
# ClusterFuzzLite build script for Image Preprocessing Detector
# Installs dependencies and prepares fuzzing harnesses

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

# Copy fuzzing harnesses to output directory
echo "Copying fuzzing harnesses from fuzz/ to $OUT/"
cp -v fuzz/fuzz_*.py $OUT/

# Make fuzzing harnesses executable (required for ClusterFuzzLite to recognize them as targets)
chmod +x $OUT/fuzz_*.py

echo "=== Fuzzing Build Complete ==="
echo "Fuzzing harnesses in $OUT:"
ls -la $OUT/
echo "================================"
