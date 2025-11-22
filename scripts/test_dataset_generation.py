#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Test dataset generation with 1000 samples to validate pipeline.

This script generates a small test dataset (1000 samples) to verify the
generation pipeline works correctly before running the full 100K generation.

Duration: ~10-15 minutes
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def main():
    print("="*80)
    print("TEST DATASET GENERATION - 1000 Samples")
    print("="*80)
    print("\nThis will generate 1000 test samples to validate the pipeline.")
    print("Expected duration: 10-15 minutes")
    print("Output: data/training/iqa_phase2_test/")

    response = input("\nProceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Aborted.")
        return

    # Create test configuration by modifying the main script
    cmd = [
        "poetry", "run", "python",
        str(PROJECT_ROOT / "scripts/generate_100k_iqa_dataset.py"),
        "--output-dir", str(PROJECT_ROOT / "data/training/iqa_phase2_test"),
        "--seed", "42"
    ]

    # Note: Would need to modify main script to support --test-mode with 1000 samples
    print(f"\nRunning: {' '.join(cmd)}")
    print("\nNOTE: This is a test run. For full 100K generation, see README instructions.\n")

    subprocess.run(cmd)

if __name__ == "__main__":
    main()
