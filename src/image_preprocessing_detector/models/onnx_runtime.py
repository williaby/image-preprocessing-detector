"""ONNX Runtime CPU inference wrapper for document preprocessing models.

Provides a lightweight, zero-VRAM inference engine using ONNX Runtime's
CPUExecutionProvider. Designed for the deskew pipeline's MobileNetV4-Conv-S
model but generic enough for any single-input ONNX model.

Key design decisions (4-model consensus):
- CPU-only inference via ONNX Runtime (no VRAM requirement)
- INT8 quantized models via QAT (not PTQ) for regression accuracy
- Thread configuration exposed for deployment tuning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import onnxruntime as ort
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ONNXSessionConfig:
    """Configuration for ONNX Runtime inference session.

    Attributes:
        provider (str): Execution provider name (default: CPUExecutionProvider).
        num_threads (int): Intra-op thread count. 0 means auto-detect.
        graph_optimization (str): Optimization level (none/basic/extended/all).
        log_severity (int): ONNX Runtime log severity (0=verbose, 4=fatal).
    """

    provider: str = "CPUExecutionProvider"
    num_threads: int = 0
    graph_optimization: str = "all"
    log_severity: int = 3

    def to_session_options(self) -> ort.SessionOptions:
        """Convert to ONNX Runtime SessionOptions.

        Returns:
            ort.SessionOptions: Configured SessionOptions instance."""
        import onnxruntime as ort

        options = ort.SessionOptions()

        if self.num_threads > 0:
            options.intra_op_num_threads = self.num_threads

        opt_map = {
            "none": ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
            "basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
            "extended": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
            "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
        }
        options.graph_optimization_level = opt_map.get(
            self.graph_optimization,
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
        )

        options.log_severity_level = self.log_severity

        return options


@dataclass
class ONNXModelRunner:
    """Generic ONNX Runtime model runner for CPU inference.

    Lazily loads the ONNX model on first inference call.
    Thread-safe for concurrent reads (ONNX Runtime sessions are thread-safe).

    Attributes:
        model_path (Path): Path to the ONNX model file.
        config (ONNXSessionConfig): Session configuration.
    """

    model_path: Path
    config: ONNXSessionConfig = field(default_factory=ONNXSessionConfig)
    _session: object | None = field(default=None, init=False, repr=False)

    def _ensure_session(self) -> ort.InferenceSession:
        """Load ONNX model if not already loaded.

        Returns:
            ort.InferenceSession: Active ONNX Runtime InferenceSession.

        Raises:
            FileNotFoundError: If model file does not exist.
            RuntimeError: If ONNX Runtime fails to load the model.
        """
        if self._session is not None:
            return self._session

        import onnxruntime as ort

        if not self.model_path.exists():
            msg = f"ONNX model not found: {self.model_path}"
            raise FileNotFoundError(msg)

        session_options = self.config.to_session_options()
        providers = [self.config.provider]

        try:
            self._session = ort.InferenceSession(
                str(self.model_path),
                sess_options=session_options,
                providers=providers,
            )
        except Exception as exc:
            msg = f"Failed to load ONNX model from {self.model_path}: {exc}"
            raise RuntimeError(msg) from exc

        session = self._session
        assert isinstance(session, ort.InferenceSession)
        input_names = [inp.name for inp in session.get_inputs()]
        output_names = [out.name for out in session.get_outputs()]
        logger.info(
            "ONNX model loaded",
            extra={
                "model_path": str(self.model_path),
                "provider": self.config.provider,
                "inputs": input_names,
                "outputs": output_names,
            },
        )

        return session

    def run(
        self,
        input_array: NDArray[np.float32],
        input_name: str | None = None,
    ) -> list[NDArray[np.float32]]:
        """Run inference on a single input tensor.

        Args:
            input_array (NDArray[np.float32]): Input tensor (e.g., [B, C, H, W] for images).
            input_name (str | None): Name of the input node. If None, uses first input.

        Returns:
            list[NDArray[np.float32]]: List of output arrays, one per model output head."""
        session = self._ensure_session()

        if input_name is None:
            input_name = session.get_inputs()[0].name

        output_names = [out.name for out in session.get_outputs()]

        results: list[NDArray[np.float32]] = session.run(
            output_names,
            {input_name: input_array},
        )

        return results

    def get_input_shape(self) -> list[int | str]:
        """Get the expected input shape from the model.

        Returns:
            list[int | str]: Input shape as list (may contain string dims for dynamic axes)."""
        session = self._ensure_session()
        return list(session.get_inputs()[0].shape)

    def get_output_names(self) -> list[str]:
        """Get names of all output tensors.

        Returns:
            list[str]: List of output tensor names."""
        session = self._ensure_session()
        return [out.name for out in session.get_outputs()]

    @property
    def is_loaded(self) -> bool:
        """Check if the model session is loaded."""
        return self._session is not None

    def close(self) -> None:
        """Release the ONNX Runtime session."""
        self._session = None
