"""Safe loading of PyTorch training checkpoints.

``torch.load(weights_only=True)`` refuses every pickled global that is not on
PyTorch's built-in allowlist. The repo's own trainers store validation metrics
(for example ``scipy.stats.spearmanr`` output) in the checkpoint, and those are
``numpy`` scalars, so a plain ``weights_only=True`` load rejects checkpoints we
wrote ourselves.

Rather than falling back to ``weights_only=False`` (arbitrary code execution
through pickle, CVE-2025-32434 class), this module allowlists only the narrow
set of globals needed to rebuild *numeric* numpy scalars. Anything else in the
file, including ``object``-dtype scalars, arrays, callables and arbitrary
classes, is still rejected by the weights-only unpickler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

# Numeric and boolean scalar types the trainers can emit in metric dicts.
# Object, string and structured dtypes are deliberately excluded.
_NUMERIC_SCALAR_TYPES: tuple[type, ...] = (
    np.bool_,
    np.int8,
    np.int16,
    np.int32,
    np.int64,
    np.uint8,
    np.uint16,
    np.uint32,
    np.uint64,
    np.float16,
    np.float32,
    np.float64,
)


def numpy_scalar_safe_globals() -> list[Any]:
    """Return the minimal pickle globals needed to load numpy numeric scalars.

    The scalar reconstructor lives at ``numpy._core.multiarray.scalar`` on
    numpy 2.x and ``numpy.core.multiarray.scalar`` on numpy 1.x. It is read off
    a scalar's ``__reduce__`` result so the allowlist always matches the
    installed numpy, whichever module path it pickles under.

    Returns:
        Objects suitable for ``torch.serialization.safe_globals``.
    """
    reconstructor: Any = np.float64(0).__reduce__()[0]
    dtype_classes = {
        type(np.dtype(scalar_type)) for scalar_type in _NUMERIC_SCALAR_TYPES
    }
    return [reconstructor, np.dtype, *sorted(dtype_classes, key=repr)]


def load_checkpoint_weights_only(
    path: str | Path,
    map_location: Any = "cpu",
) -> Any:
    """Load a trainer checkpoint with ``weights_only=True`` plus numpy scalars.

    #CRITICAL: Never relax this to ``weights_only=False``. Deserializing an
    untrusted checkpoint with full pickle executes arbitrary code.
    #ASSUME: weights_only=True is a complete mitigation only on torch>=2.6.0
    (CVE-2025-32434); pyproject.toml pins torch>=2.10.0 for this reason.
    #VERIFY: ``uv run python -c "import torch; print(torch.__version__)"``
    reports >=2.6.0 in every environment that calls this function.

    Args:
        path: Checkpoint file path.
        map_location: Passed through to ``torch.load``.

    Returns:
        The deserialized checkpoint object.

    Raises:
        Exception: Whatever ``torch.load`` raises (typically
            ``pickle.UnpicklingError``) when the file contains a global that
            is not allowlisted.
    """
    import torch

    with torch.serialization.safe_globals(numpy_scalar_safe_globals()):
        return torch.load(path, map_location=map_location, weights_only=True)
