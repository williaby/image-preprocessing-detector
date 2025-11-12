"""Dataset adapters for benchmarking framework.

SPDX-License-Identifier: Apache-2.0
"""

from benchmarks.adapters.base import (
    BaseAdapter,
    DatasetRegistry,
    PageSample,
    load_adapter,
)

# Import adapters to register them
from benchmarks.adapters import doclaynet_adapter, synthetic_iqa_adapter

__all__ = [
    "BaseAdapter",
    "DatasetRegistry",
    "PageSample",
    "load_adapter",
    "doclaynet_adapter",
    "synthetic_iqa_adapter",
]
