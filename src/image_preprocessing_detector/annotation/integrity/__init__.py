# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Data integrity utilities for the annotation system.

Modules:
    - hashing.py: Full-file SHA256 hashing and deterministic sample IDs
    - atomic.py: Atomic file operations using os.replace()
    - checkpointing.py: Intra-dataset checkpoint management (Phase 2+)

Critical Fixes Implemented:
    - P0-1: Full-file SHA256 (not 64KB partial)
    - P1-3: Deterministic sample IDs (not random UUIDs)
    - P2-2: Atomic file writes (not direct overwrites)

Breaking Change Notice:
    The fix for P0-1 changes all existing sample IDs. A full re-processing
    of all datasets is required upon migration.

Example:
    >>> from image_preprocessing_detector.annotation.integrity import (
    ...     compute_full_sha256,
    ...     compute_sample_id,
    ...     atomic_write,
    ... )
    >>>
    >>> # Compute file hash
    >>> file_hash = compute_full_sha256(Path("image.png"))
    >>>
    >>> # Generate deterministic sample ID
    >>> sample_id = compute_sample_id("diqa-5000", "train/img001.png", file_hash)
    >>>
    >>> # Atomic file write
    >>> with atomic_write(Path("output.json"), fsync=True) as temp_path:
    ...     temp_path.write_text(json.dumps(data))
"""

from __future__ import annotations

# Phase 1.3.3-1.3.4: Atomic operations
from .atomic import (
    atomic_json_write,
    atomic_write,
    safe_write_bytes,
    safe_write_text,
)

# Phase 2.3 + Phase 3.3: Checkpointing
from .checkpointing import (
    BatchCheckpointInfo,
    BatchCheckpointManager,
    CheckpointInfo,
    CheckpointManager,
    CheckpointValidationResult,
    ValidationResult,  # Backward compatibility alias
)

# Phase 1.3.1-1.3.2: Hashing
from .hashing import (
    DEFAULT_CHUNK_SIZE,
    compute_content_hash,
    compute_full_sha256,
    compute_sample_id,
    compute_string_hash,
    verify_file_hash,
)

__all__: list[str] = [
    # Hashing (Phase 1.3.1-1.3.2)
    "DEFAULT_CHUNK_SIZE",
    # Checkpointing (Phase 2.3 + Phase 3.3)
    "BatchCheckpointInfo",
    "BatchCheckpointManager",
    "CheckpointInfo",
    "CheckpointManager",
    "CheckpointValidationResult",
    "ValidationResult",  # Backward compatibility alias
    "atomic_json_write",
    # Atomic operations (Phase 1.3.3-1.3.4)
    "atomic_write",
    "compute_content_hash",
    "compute_full_sha256",
    "compute_sample_id",
    "compute_string_hash",
    "safe_write_bytes",
    "safe_write_text",
    "verify_file_hash",
]
