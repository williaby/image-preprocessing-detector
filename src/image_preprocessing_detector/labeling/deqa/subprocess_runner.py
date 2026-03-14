"""Subprocess-isolated DeQA-Doc inference runner.

Runs mPLUG-Owl2-7B models in the DeQA-Doc venv via subprocess,
communicating over stdin/stdout JSONL protocol. This avoids the
transformers version conflict (DeQA needs 4.36.1, project uses >=4.40).

Example:
    >>> from image_preprocessing_detector.labeling.deqa.subprocess_runner import (
    ...     DeQASubprocessRunner,
    ...     DeQARunnerConfig,
    ... )
    >>> config = DeQARunnerConfig(
    ...     deqa_venv="/home/user/DeQA-Doc/DeQA-Score/.venv",
    ...     deqa_root="/home/user/DeQA-Doc/DeQA-Score",
    ...     model_paths={
    ...         "overall": "/models/deqa_overall",
    ...         "sharpness": "/models/deqa_sharpness",
    ...         "color_fidelity": "/models/deqa_color",
    ...     },
    ... )
    >>> runner = DeQASubprocessRunner(config)
    >>> results = runner.score_images(["/path/to/img1.jpg", "/path/to/img2.jpg"])
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 — subprocess isolation is by design for DeQA venv bridge
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

DIMENSIONS: tuple[str, ...] = ("overall", "sharpness", "color_fidelity")
BRIDGE_SCRIPT_NAME: str = "bridge_script.py"


@dataclass(frozen=True)
class DeQARunnerConfig:
    """Configuration for DeQA subprocess runner.

    Attributes:
        deqa_venv: Path to DeQA-Doc venv (e.g., /home/user/DeQA-Doc/DeQA-Score/.venv)
        deqa_root: Path to DeQA-Score root (for PYTHONPATH)
        model_paths: Mapping of dimension name to model checkpoint path
        device: CUDA device string
        batch_size: Images per inference batch
        timeout_per_image_s: Max seconds per image before killing subprocess
        preprocessor_path: Optional path to image preprocessor config
        load_8bit: Use 8-bit quantization
        load_4bit: Use 4-bit quantization
    """

    deqa_venv: str
    deqa_root: str
    model_paths: dict[str, str]
    device: str = "cuda:0"
    batch_size: int = 4
    timeout_per_image_s: float = 30.0
    preprocessor_path: str | None = None
    load_8bit: bool = False
    load_4bit: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        for dim in DIMENSIONS:
            if dim not in self.model_paths:
                msg = (
                    f"Missing model path for dimension '{dim}'. Required: {DIMENSIONS}"
                )
                raise ValueError(msg)

        venv_python = Path(self.deqa_venv) / "bin" / "python"
        if not venv_python.exists():
            msg = f"DeQA venv python not found: {venv_python}"
            raise FileNotFoundError(msg)


@dataclass
class DimensionScore:
    """Score for a single dimension of a single image.

    Attributes:
        level_probs: Probability distribution over 5 levels
            [excellent, good, fair, poor, bad]
        expected_mos: Expected MOS (1-5 scale)
        score_normalized: MOS normalized to [0, 1]
    """

    level_probs: list[float]
    expected_mos: float
    score_normalized: float


@dataclass
class DeQAPrediction:
    """Complete DeQA-Doc prediction for a single image.

    Attributes:
        image_path: Absolute path to scored image
        overall: Overall quality dimension score
        sharpness: Sharpness dimension score
        color_fidelity: Color fidelity dimension score
        inference_time_ms: Total inference time across all dimensions
        errors: List of error messages (empty if successful)
    """

    image_path: str
    overall: DimensionScore | None = None
    sharpness: DimensionScore | None = None
    color_fidelity: DimensionScore | None = None
    inference_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Whether all 3 dimensions were scored successfully."""
        return (
            self.overall is not None
            and self.sharpness is not None
            and self.color_fidelity is not None
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSONL output."""
        result: dict[str, Any] = {"image_path": self.image_path}
        for dim in DIMENSIONS:
            score = getattr(self, dim)
            if score is not None:
                result[dim] = {
                    "level_probs": score.level_probs,
                    "expected_mos": score.expected_mos,
                    "score_normalized": score.score_normalized,
                }
            else:
                result[dim] = None
        result["inference_time_ms"] = self.inference_time_ms
        if self.errors:
            result["errors"] = self.errors
        return result


class DeQASubprocessRunner:
    """Runs DeQA-Doc inference via subprocess isolation.

    Launches a bridge script inside the DeQA-Doc venv for each
    dimension, passing image paths over stdin and reading predictions
    from stdout.
    """

    def __init__(self, config: DeQARunnerConfig) -> None:
        """Initialize runner with configuration.

        Args:
            config: Runner configuration with venv paths and model locations.
        """
        self._config = config
        self._bridge_script = str(Path(__file__).parent / BRIDGE_SCRIPT_NAME)

    def score_images(
        self, image_paths: list[str], *, progress_callback: Any | None = None
    ) -> list[DeQAPrediction]:
        """Score a list of images across all 3 dimensions.

        Args:
            image_paths: Absolute paths to images to score.
            progress_callback: Optional callable(dimension, processed, total)
                for progress reporting.

        Returns:
            List of DeQAPrediction, one per input image. Images that
            failed on some dimensions will have None for those scores.
        """
        predictions: dict[str, DeQAPrediction] = {
            path: DeQAPrediction(image_path=path) for path in image_paths
        }

        start = time.monotonic()

        for dimension in DIMENSIONS:
            dim_results = self._run_dimension(image_paths, dimension, progress_callback)
            for result in dim_results:
                path = result["image_path"]
                if path not in predictions:
                    continue

                pred = predictions[path]
                if result["status"] == "ok":
                    score = DimensionScore(
                        level_probs=result["level_probs"],
                        expected_mos=result["expected_mos"],
                        score_normalized=result["score_normalized"],
                    )
                    setattr(pred, dimension, score)
                else:
                    pred.errors.append(
                        f"{dimension}: {result.get('error', 'unknown error')}"
                    )

        elapsed_ms = (time.monotonic() - start) * 1000
        per_image_ms = elapsed_ms / max(len(image_paths), 1)
        for pred in predictions.values():
            pred.inference_time_ms = per_image_ms

        return list(predictions.values())

    def _run_dimension(
        self,
        image_paths: list[str],
        dimension: str,
        progress_callback: Any | None,
    ) -> list[dict[str, Any]]:
        """Run inference for a single dimension via subprocess.

        Args:
            image_paths: Images to score.
            dimension: One of "overall", "sharpness", "color_fidelity".
            progress_callback: Optional progress reporter.

        Returns:
            List of result dicts from bridge script.
        """
        python_bin = str(Path(self._config.deqa_venv) / "bin" / "python")
        model_path = self._config.model_paths[dimension]

        cmd = [
            python_bin,
            self._bridge_script,
            "--model-path",
            model_path,
            "--dimension",
            dimension,
            "--device",
            self._config.device,
            "--batch-size",
            str(self._config.batch_size),
        ]
        if self._config.preprocessor_path:
            cmd.extend(["--preprocessor-path", self._config.preprocessor_path])
        if self._config.load_8bit:
            cmd.append("--load-8bit")
        if self._config.load_4bit:
            cmd.append("--load-4bit")

        env = {
            "PYTHONPATH": self._config.deqa_root,
            "PATH": str(Path(self._config.deqa_venv) / "bin")
            + ":"
            + (os.environ.get("PATH", "")),
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "HOME": os.environ.get("HOME", ""),
        }

        # Propagate CUDA-related env vars
        for key in ("LD_LIBRARY_PATH", "CUDA_HOME", "TORCH_HOME", "HF_HOME"):
            val = os.environ.get(key)
            if val:
                env[key] = val

        logger.info(
            "Starting bridge subprocess",
            dimension=dimension,
            model_path=model_path,
            num_images=len(image_paths),
        )

        total_timeout = (
            self._config.timeout_per_image_s * len(image_paths) + 120
        )  # +120s for model load

        try:
            proc = subprocess.Popen(  # noqa: S603  # nosec B603 — trusted cmd from DeQA config
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                cwd=self._config.deqa_root,
            )
        except OSError as exc:
            logger.exception("Failed to start bridge subprocess", error=str(exc))
            return [
                {
                    "image_path": p,
                    "dimension": dimension,
                    "status": "error",
                    "error": str(exc),
                }
                for p in image_paths
            ]

        # Write all image paths to stdin
        if proc.stdin is None:
            raise RuntimeError("subprocess stdin not available (PIPE not configured)")
        for path in image_paths:
            proc.stdin.write(json.dumps({"image_path": path}) + "\n")
        proc.stdin.close()

        # Read results from stdout
        results: list[dict[str, Any]] = []
        if proc.stdout is None:
            raise RuntimeError("subprocess stdout not available (PIPE not configured)")
        processed = 0
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Non-JSON output from bridge", line=line)
                continue

            if record.get("status") == "done":
                logger.info(
                    "Bridge completed",
                    dimension=dimension,
                    processed=record.get("processed"),
                    errors=record.get("errors"),
                )
                break

            results.append(record)
            processed += 1
            if progress_callback:
                progress_callback(dimension, processed, len(image_paths))

        # Wait for process to finish
        try:
            proc.wait(timeout=total_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.warning("Bridge subprocess timed out", dimension=dimension)

        # Log any stderr
        if proc.stderr is None:
            raise RuntimeError("subprocess stderr not available (PIPE not configured)")
        stderr_output = proc.stderr.read()
        if stderr_output:
            for stderr_line in stderr_output.strip().split("\n")[-5:]:
                logger.debug("Bridge stderr", dimension=dimension, line=stderr_line)

        if proc.returncode and proc.returncode != 0:
            logger.warning(
                "Bridge exited with non-zero code",
                dimension=dimension,
                returncode=proc.returncode,
            )

        return results

    def score_single(self, image_path: str) -> DeQAPrediction:
        """Score a single image across all 3 dimensions.

        Args:
            image_path: Absolute path to image.

        Returns:
            DeQAPrediction with scores for all dimensions.
        """
        results = self.score_images([image_path])
        return results[0]
