"""Task plugins for benchmarking framework.

Task plugins orchestrate detection modules, metrics, and scoring.

SPDX-License-Identifier: Apache-2.0
"""

from benchmarks.tasks.iqa import run_iqa_benchmark

__all__ = ["run_iqa_benchmark"]
