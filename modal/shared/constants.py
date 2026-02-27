"""Shared constants for Modal applications.

Centralizes GCS configuration, volume definitions, and secrets
to eliminate duplication across benchmark and training scripts.
"""

from __future__ import annotations

import modal

# =============================================================================
# GCS Configuration
# =============================================================================

# DIQA-5000 dataset location
GCS_BUCKET = "assured-oss-457903-diqa5000"
GCS_ARCHIVE = "diqa5000-test.tar.gz"
DATASET_CACHE_DIR = "/data/diqa5000"

# =============================================================================
# Modal Volumes (shared across apps)
# =============================================================================

# Arena benchmarking volumes
arena_model_volume = modal.Volume.from_name("arena-models", create_if_missing=True)
arena_data_volume = modal.Volume.from_name("arena-data", create_if_missing=True)

# Training volumes
training_data_volume = modal.Volume.from_name(
    "stage2-training-data", create_if_missing=True
)
checkpoint_volume = modal.Volume.from_name("dociq-checkpoints", create_if_missing=True)

# =============================================================================
# Modal Secrets
# =============================================================================

gcs_secret = modal.Secret.from_name("gcs-credentials")

# =============================================================================
# IQA Prompts for VLM-based Assessment
# =============================================================================

IQA_PROMPT = """Analyze this document image and rate its quality on a scale of 1-5 for each dimension.

Rate the following:
1. Overall quality (considering all aspects): a number from 1.0 to 5.0
2. Sharpness (text clarity, edge definition): a number from 1.0 to 5.0
3. Color fidelity (color accuracy, consistency): a number from 1.0 to 5.0

Respond with ONLY three lines in this exact format:
Overall: X.X
Sharpness: X.X
Color: X.X"""
