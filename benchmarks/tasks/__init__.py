"""Task plugins for benchmarking framework.

Task plugins orchestrate detection modules, metrics, and scoring.

"""

from benchmarks.tasks.iqa import run_iqa_benchmark

__all__ = ["run_iqa_benchmark"]
