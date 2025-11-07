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

# Create wrapper scripts without .py extension (required for ClusterFuzzLite target detection)
# OSS-Fuzz/ClusterFuzzLite looks for executable files without .py extension
for fuzzer in fuzz_pdf_loader fuzz_image_loader fuzz_text_gate; do
    echo "Creating wrapper for $fuzzer"
    cat > $OUT/$fuzzer <<EOF
#!/usr/bin/env python3
# ClusterFuzzLite wrapper for ${fuzzer}.py
import sys
import os

# Add project to Python path
sys.path.insert(0, '/src/image-preprocessing-detector/src')

# Import and run the fuzzing harness
exec(open('$OUT/${fuzzer}.py').read())
EOF
    chmod +x $OUT/$fuzzer
done

echo "=== Fuzzing Build Complete ==="
echo "Fuzzing targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
