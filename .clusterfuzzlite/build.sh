#!/bin/bash -eu
# ClusterFuzzLite build script for Image Preprocessing Detector
# Installs dependencies and prepares fuzzing harnesses

# Install Poetry
pip3 install poetry

# Install project dependencies (without dev dependencies)
cd $SRC/image-preprocessing-detector
poetry config virtualenvs.create false
poetry install --without dev --no-interaction

# Install Atheris fuzzing engine
pip3 install atheris

# Copy fuzzing harnesses to output directory
cp fuzz/*.py $OUT/

echo "Fuzzing build complete!"
echo "Fuzzing harnesses in $OUT:"
ls -la $OUT/*.py
