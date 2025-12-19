#!/bin/bash
# Setup script for DeQA-Doc inference environment
#
# This creates a dedicated virtual environment for DeQA-Doc inference
# with the correct dependencies (PyTorch 2.0.1, transformers 4.36.1)

set -e

DEQA_DOC_DIR="/home/byron/dev/DeQA-Doc/DeQA-Score"
VENV_DIR="/home/byron/dev/DeQA-Doc/.venv"

echo "============================================"
echo "Setting up DeQA-Doc environment"
echo "============================================"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/bin/activate"

echo "Installing DeQA-Score package..."
cd "$DEQA_DOC_DIR"

# Install dependencies
pip install --upgrade pip
pip install -e .

# Additional dependencies for 4-bit quantization
pip install bitsandbytes accelerate

echo ""
echo "============================================"
echo "Setup complete!"
echo "============================================"
echo ""
echo "To activate the environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run inference:"
echo "  cd $DEQA_DOC_DIR"
echo "  export PYTHONPATH=./:\$PYTHONPATH"
echo "  python src/evaluate/iqa_eval.py --help"
echo ""
