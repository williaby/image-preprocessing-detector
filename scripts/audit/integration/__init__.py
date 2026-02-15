"""Integration framework for dataset enrichment scripts.

Provides a mixin-based architecture for consolidating 52 copy-pasted
integration scripts into a shared framework with per-field confidence
tracking, KI mitigation methods, and declarative field resolution.
"""

from __future__ import annotations
