"""Base classes for benchmark datasets.

This module provides abstract base classes for dataset adapters used
in Arena benchmarking.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class DatasetSample:
    """A single sample from a benchmark dataset.

    Attributes:
        sample_id: Unique identifier for this sample.
        image: Image as numpy array (H, W, C) in RGB format.
        ground_truth: Dictionary of ground truth scores.
            For DIQA-5000: {"overall": float, "sharpness": float, "color": float}
        metadata: Additional sample metadata.
    """

    sample_id: str
    image: NDArray[np.uint8]
    ground_truth: dict[str, float]
    metadata: dict[str, str | int | float] = field(default_factory=dict)

    @property
    def pil_image(self) -> Image.Image:
        """Convert to PIL Image."""
        return Image.fromarray(self.image)

    @property
    def image_id(self) -> str:
        """Alias for sample_id for compatibility."""
        return self.sample_id

    @property
    def labels(self) -> dict[str, float]:
        """Alias for ground_truth for compatibility."""
        return self.ground_truth

    @property
    def image_path(self) -> str | None:
        """Path to the image file, if available."""
        return self.metadata.get("image_path")  # type: ignore[return-value]


class BenchmarkDataset(ABC):
    """Abstract base class for benchmark datasets.

    Subclasses must implement iteration over DatasetSample instances
    and provide dataset metadata.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Dataset name (e.g., 'diqa5000')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Dataset version."""
        ...

    @property
    @abstractmethod
    def split(self) -> str:
        """Dataset split (train/val/test)."""
        ...

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of samples in the dataset."""
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[DatasetSample]:
        """Iterate over dataset samples."""
        ...

    @abstractmethod
    def __getitem__(self, idx: int) -> DatasetSample:
        """Get a specific sample by index."""
        ...

    @property
    def dimensions(self) -> list[str]:
        """List of ground truth dimensions (e.g., ['overall', 'sharpness', 'color'])."""
        return ["overall", "sharpness", "color"]

    @property
    def current_split(self) -> str:
        """Alias for split property for compatibility."""
        return self.split

    def compute_checksum(self) -> str:
        """Compute a checksum for the dataset.

        Returns:
            SHA256 hash of dataset metadata.
        """
        import hashlib

        data = f"{self.name}:{self.version}:{self.split}:{len(self)}"
        return f"sha256:{hashlib.sha256(data.encode()).hexdigest()[:16]}"


class SyntheticDataset(BenchmarkDataset):
    """Synthetic dataset for testing purposes.

    Generates random images with synthetic ground truth labels.
    """

    def __init__(
        self,
        num_samples: int = 10,
        image_size: tuple[int, int] = (224, 224),
        seed: int = 42,
    ) -> None:
        """Initialize synthetic dataset.

        Args:
            num_samples: Number of synthetic samples to generate.
            image_size: Size of generated images (height, width).
            seed: Random seed for reproducibility.
        """
        self._num_samples = num_samples
        self._image_size = image_size
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._samples = self._generate_samples()

    def _generate_samples(self) -> list[DatasetSample]:
        """Generate synthetic samples."""
        samples = []
        for i in range(self._num_samples):
            # Generate random image
            image = self._rng.integers(0, 256, (*self._image_size, 3), dtype=np.uint8)

            # Generate random ground truth scores in [0, 1]
            ground_truth = {
                "overall": float(self._rng.uniform(0.3, 0.9)),
                "sharpness": float(self._rng.uniform(0.3, 0.9)),
                "color": float(self._rng.uniform(0.3, 0.9)),
            }

            samples.append(
                DatasetSample(
                    sample_id=f"synthetic_{i:04d}",
                    image=image,
                    ground_truth=ground_truth,
                    metadata={"synthetic": True, "seed": self._seed},
                )
            )
        return samples

    @property
    def name(self) -> str:
        """Return dataset name."""
        return "synthetic"

    @property
    def version(self) -> str:
        """Return dataset version."""
        return "1.0.0"

    @property
    def split(self) -> str:
        """Return dataset split."""
        return "test"

    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self._samples)

    def __iter__(self) -> Iterator[DatasetSample]:
        """Iterate over dataset samples."""
        return iter(self._samples)

    def __getitem__(self, idx: int) -> DatasetSample:
        """Get sample by index."""
        return self._samples[idx]


class DIQA5000Dataset(BenchmarkDataset):
    """DIQA-5000 dataset adapter.

    Loads the Document Image Quality Assessment dataset with
    overall, sharpness, and color quality annotations.

    Dataset Structure:
        diqa-5000/
        ├── train/
        │   ├── train.csv
        │   ├── ori/  (original images)
        │   └── res/  (result/degraded images)
        ├── val/
        │   ├── val.csv
        │   ├── ori/
        │   └── res/
        └── test/
            ├── test.csv
            ├── ori/
            └── res/

    CSV Format:
        res,ori,overall,sharpness,color_fidelity
        test_res_00001.jpg,test_ori_00001.jpg,3.76,3.653,3.707

    Scores are MOS (Mean Opinion Scores) on 1-5 scale, normalized to 0-1.
    """

    def __init__(
        self,
        root_dir: str | Path,
        split: str = "test",
        normalize_scores: bool = True,
    ) -> None:
        """Initialize DIQA-5000 dataset.

        Args:
            root_dir: Path to dataset root directory.
            split: Dataset split ('train', 'val', 'test').
            normalize_scores: If True, normalize 1-5 MOS scores to 0-1 range.
        """
        self._root_dir = Path(root_dir)
        self._split = split
        self._normalize_scores = normalize_scores
        self._samples: list[DatasetSample] = []
        self._load_dataset()

    def _normalize_mos(self, score: float) -> float:
        """Normalize MOS score from 1-5 to 0-1 range."""
        if self._normalize_scores:
            return (score - 1.0) / 4.0  # Map [1,5] -> [0,1]
        return score

    def _load_dataset(self) -> None:
        """Load dataset from disk."""
        import csv

        split_dir = self._root_dir / self._split
        csv_path = split_dir / f"{self._split}.csv"
        res_dir = split_dir / "res"

        # Check if dataset exists
        if not csv_path.exists():
            logger.warning(
                "DIQA-5000 CSV not found at %s, using synthetic data", csv_path
            )
            synthetic = SyntheticDataset(num_samples=100)
            self._samples = list(synthetic)
            return

        if not res_dir.exists():
            logger.warning(
                "DIQA-5000 images not found at %s, using synthetic data", res_dir
            )
            synthetic = SyntheticDataset(num_samples=100)
            self._samples = list(synthetic)
            return

        # Load CSV and create samples
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                image_filename = row["res"]
                image_path = res_dir / image_filename

                if not image_path.exists():
                    continue

                # Load image
                try:
                    img = Image.open(image_path).convert("RGB")
                    image_array = np.array(img)
                except Exception as e:
                    logger.warning("Failed to load %s: %s", image_path, e)
                    continue

                # Parse and normalize scores
                ground_truth = {
                    "overall": self._normalize_mos(float(row["overall"])),
                    "sharpness": self._normalize_mos(float(row["sharpness"])),
                    "color": self._normalize_mos(float(row["color_fidelity"])),
                }

                sample = DatasetSample(
                    sample_id=image_filename.replace(".jpg", ""),
                    image=image_array,
                    ground_truth=ground_truth,
                    metadata={
                        "image_path": str(image_path),
                        "original_image": row["ori"],
                        "raw_overall": float(row["overall"]),
                        "raw_sharpness": float(row["sharpness"]),
                        "raw_color": float(row["color_fidelity"]),
                    },
                )
                self._samples.append(sample)

        logger.info(
            "Loaded %d samples from DIQA-5000 %s split",
            len(self._samples),
            self._split,
        )

    @property
    def name(self) -> str:
        """Return dataset name."""
        return "diqa5000"

    @property
    def version(self) -> str:
        """Return dataset version."""
        return "1.0.0"

    @property
    def split(self) -> str:
        """Return dataset split."""
        return self._split

    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self._samples)

    def __iter__(self) -> Iterator[DatasetSample]:
        """Iterate over dataset samples."""
        return iter(self._samples)

    def __getitem__(self, idx: int) -> DatasetSample:
        """Get sample by index."""
        return self._samples[idx]
