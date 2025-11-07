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
echo "Copying Python fuzzing harnesses from fuzz/ to $OUT/"
cp -v fuzz/fuzz_pdf_loader.py $OUT/
cp -v fuzz/fuzz_image_loader.py $OUT/
cp -v fuzz/fuzz_text_gate.py $OUT/

# Create shell wrapper scripts for ClusterFuzzLite (without .py extension)
# ClusterFuzzLite expects fuzz targets without extensions
echo "Creating fuzz target wrappers in $OUT/"
for target in fuzz_pdf_loader fuzz_image_loader fuzz_text_gate; do
  cat > $OUT/$target <<WRAPPER_EOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="/src/image-preprocessing-detector/src:\${PYTHONPATH}"
exec python3 "\${SCRIPT_DIR}/${target}.py" "\$@"
WRAPPER_EOF

  chmod +x $OUT/$target
  echo "Created wrapper: $OUT/$target"
done

echo "=== Fuzzing Build Complete ==="
echo "Fuzz targets in $OUT:"
ls -la $OUT/ | grep -E "(fuzz_|^total|^d)"
echo "================================"
