"""Base adapter interface for benchmark datasets.

All dataset adapters must implement the BaseAdapter interface to ensure
consistent integration with the benchmarking framework.

SPDX-License-Identifier: Apache-2.0
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class PageSample:
    """Standardized page sample for benchmarking.

    All adapters must return PageSample instances to ensure uniform
    processing across different datasets.

    Attributes:
        image_path: Path to the page image file
        annotations: List of annotation dictionaries (COCO format preferred)
        metadata: Additional metadata (page_num, doc_id, split, etc.)
    """

    image_path: Path
    annotations: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate PageSample after initialization."""
        if not isinstance(self.image_path, Path):
            self.image_path = Path(self.image_path)

        if not self.image_path.exists():
            raise FileNotFoundError(f"Image not found: {self.image_path}")

    @property
    def sample_id(self) -> str:
        """Unique identifier for this sample."""
        return self.metadata.get("sample_id", self.image_path.stem)

    @property
    def doc_id(self) -> str | None:
        """Document identifier (for doc-wise evaluation)."""
        return self.metadata.get("doc_id")

    @property
    def page_num(self) -> int | None:
        """Page number within document."""
        return self.metadata.get("page_num")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON output."""
        return {
            "image_path": str(self.image_path),
            "annotations": self.annotations,
            "metadata": self.metadata,
        }


class BaseAdapter(ABC):
    """Abstract base class for dataset adapters.

    All dataset adapters must inherit from this class and implement
    the required methods.
    """

    def __init__(
        self,
        data_dir: Path,
        split: str = "val",
        cache_dir: Path | None = None,
        download: bool = False,
    ) -> None:
        """Initialize the adapter.

        Args:
            data_dir: Root directory containing the dataset
            split: Dataset split (train, val, test)
            cache_dir: Optional cache directory for processed data
            download: Whether to download the dataset if not present
        """
        self.data_dir = Path(data_dir)
        self.split = split
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.download = download

        # Validate dataset presence
        if not self.data_dir.exists() and not download:
            raise FileNotFoundError(
                f"Dataset not found at {self.data_dir}. "
                "Set download=True to download automatically."
            )

        # Create cache directory if needed
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Subclasses should populate this in __init__
        self._sample_ids: list[str] = []

    @abstractmethod
    def __iter__(self) -> Iterator[PageSample]:
        """Iterate over dataset samples.

        Yields:
            PageSample instances
        """

    @abstractmethod
    def __len__(self) -> int:
        """Return number of samples in the dataset."""

    @abstractmethod
    def get_sample(self, sample_id: str) -> PageSample:
        """Retrieve a specific sample by ID.

        Args:
            sample_id: Unique sample identifier

        Returns:
            PageSample instance

        Raises:
            KeyError: If sample_id not found
        """

    @property
    @abstractmethod
    def license(self) -> str:
        """Dataset license (e.g., 'CC-BY-4.0', 'CDLA-Permissive-2.0')."""

    @property
    @abstractmethod
    def split_info(self) -> dict[str, Any]:
        """Information about available splits and their sizes."""

    @property
    def sample_ids(self) -> list[str]:
        """List of all sample IDs in this split."""
        return self._sample_ids

    @property
    def classes(self) -> list[str]:
        """List of class names (for classification/detection tasks).

        Returns:
            Empty list if not applicable
        """
        return []

    @property
    def num_classes(self) -> int:
        """Number of classes in the dataset."""
        return len(self.classes)

    def get_subset(self, n: int, seed: int = 42) -> "BaseAdapter":
        """Create a subset adapter for smoke testing.

        Args:
            n: Number of samples in subset
            seed: Random seed for reproducibility

        Returns:
            New adapter instance with subset of samples
        """
        import random

        random.seed(seed)
        subset_ids = random.sample(self._sample_ids, min(n, len(self._sample_ids)))

        # Create a shallow copy with subset IDs
        adapter = self.__class__(
            data_dir=self.data_dir,
            split=self.split,
            cache_dir=self.cache_dir,
            download=False,
        )
        adapter._sample_ids = subset_ids
        return adapter

    def verify_integrity(self) -> bool:
        """Verify dataset integrity (checksums, file counts, etc.).

        Returns:
            True if integrity checks pass

        Raises:
            RuntimeError: If integrity checks fail
        """
        # Base implementation: check that all sample images exist
        missing = []
        for sample_id in self._sample_ids[:10]:  # Check first 10
            try:
                sample = self.get_sample(sample_id)
                if not sample.image_path.exists():
                    missing.append(str(sample.image_path))
            except Exception as e:
                raise RuntimeError(f"Integrity check failed for {sample_id}: {e}") from e

        if missing:
            raise RuntimeError(f"Missing images: {missing}")

        return True

    def download_dataset(self) -> None:
        """Download the dataset if not present.

        Subclasses should implement this method if they support downloads.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support automatic downloads"
        )

    def __repr__(self) -> str:
        """String representation of the adapter."""
        return (
            f"{self.__class__.__name__}("
            f"split={self.split!r}, "
            f"samples={len(self)}, "
            f"classes={self.num_classes})"
        )


class DatasetRegistry:
    """Registry for dataset adapters.

    Allows registering and retrieving adapter classes by name.
    """

    _adapters: ClassVar[dict[str, type[BaseAdapter]]] = {}

    @classmethod
    def register(cls, name: str) -> Any:
        """Decorator to register an adapter class.

        Usage:
            @DatasetRegistry.register("doclaynet")
            class DocLayNetAdapter(BaseAdapter):
                ...
        """

        def decorator(adapter_class: type[BaseAdapter]) -> type[BaseAdapter]:
            cls._adapters[name] = adapter_class
            return adapter_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[BaseAdapter]:
        """Retrieve an adapter class by name.

        Args:
            name: Registered adapter name

        Returns:
            Adapter class

        Raises:
            KeyError: If adapter not registered
        """
        if name not in cls._adapters:
            raise KeyError(
                f"Adapter '{name}' not registered. "
                f"Available: {list(cls._adapters.keys())}"
            )
        return cls._adapters[name]

    @classmethod
    def list_adapters(cls) -> list[str]:
        """List all registered adapter names."""
        return list(cls._adapters.keys())


# Convenience function for loading adapters
def load_adapter(
    name: str,
    data_dir: Path,
    split: str = "val",
    cache_dir: Path | None = None,
    download: bool = False,
) -> BaseAdapter:
    """Load a dataset adapter by name.

    Args:
        name: Registered adapter name (e.g., "doclaynet")
        data_dir: Root directory containing the dataset
        split: Dataset split (train, val, test)
        cache_dir: Optional cache directory
        download: Whether to download if not present

    Returns:
        Initialized adapter instance

    Example:
        >>> adapter = load_adapter(
        ...     "doclaynet", data_dir="/data/doclaynet", split="val_docwise"
        ... )
        >>> for sample in adapter:
        ...     print(sample.image_path, len(sample.annotations))
    """
    adapter_class = DatasetRegistry.get(name)
    return adapter_class(
        data_dir=data_dir,
        split=split,
        cache_dir=cache_dir,
        download=download,
    )
