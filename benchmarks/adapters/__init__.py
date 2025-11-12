"""Dataset adapters for benchmarking framework.

SPDX-License-Identifier: Apache-2.0
"""

# Import adapters to register them
from benchmarks.adapters import doclaynet_adapter, synthetic_iqa_adapter
from benchmarks.adapters.base import (
    BaseAdapter,
    DatasetRegistry,
    PageSample,
    load_adapter,
)

__all__ = [
    "BaseAdapter",
    "DatasetRegistry",
    "PageSample",
    "doclaynet_adapter",
    "load_adapter",
    "synthetic_iqa_adapter",
]
