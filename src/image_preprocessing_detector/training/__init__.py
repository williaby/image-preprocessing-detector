"""Training utilities for deep learning models.

This module contains training loops, validation logic, and checkpointing
utilities for the teacher and student IQA models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# PyTorch is an optional dependency (installed via the `ml` extra). Provide a
# lightweight stub so base installs can import the training package without the
# heavy dependency.
# Use lowercase to avoid BasedPyright reportConstantRedefinition
_torch_import_error: ModuleNotFoundError | None = None

try:  # pragma: no cover - exercised indirectly via import checks
    from image_preprocessing_detector.training.teacher_trainer import (
        TeacherTrainer as _TeacherTrainer,
    )
except ModuleNotFoundError as _exc:  # pragma: no cover - defensive for missing torch
    if _exc.name != "torch":
        raise
    _torch_import_error = _exc
    _TeacherTrainer = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from image_preprocessing_detector.training.teacher_trainer import TeacherTrainer
else:
    if _TeacherTrainer is not None:
        TeacherTrainer = _TeacherTrainer
    else:

        class TeacherTrainer:  # type: ignore[no-redef]
            """Stub Trainer that surfaces a helpful error when torch is absent."""

            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                raise ImportError(
                    "TeacherTrainer requires the optional ML dependencies. "
                    "Install with `pip install image-preprocessing-detector[ml]` "
                    "or `poetry install --with ml`."
                ) from _torch_import_error


__all__ = ["TeacherTrainer"]
