"""Parser for Kuzushiji datasets (K-MNIST / K-49 / K-Kanji).

Kuzushiji is a set of three datasets containing pre-modern Japanese cursive
character crops from historical manuscripts (Edo period and earlier). Released
by ROIS-DS Center for Open Data in the Humanities (CODH). License: CC BY-SA 4.0.

Sub-Datasets:
    K-MNIST:  70,000 images, 10 Hiragana classes, 28x28 px, IDX binary format
    K-49:    270,912 images, 49 Hiragana classes, 28x28 px, NumPy .npz/.npy format
    K-Kanji: 140,424 images, 3,832 Kanji classes, 64x64 px, per-class PNG directories

All images are single character crops of pre-modern (Kuzushiji-style) cursive
Japanese. Hiragana in K-MNIST/K-49 uses heavily connected flowing strokes;
Kanji in K-Kanji uses archaic variant forms from historical dictionaries.

Dataset Structure (after extraction):
    kuzushiji/
        kmnist/
            data/
                train-images-idx3-ubyte.gz   -- IDX binary (raw HF download)
                train-labels-idx1-ubyte.gz
                test-images-idx3-ubyte.gz
                test-labels-idx1-ubyte.gz
            kmnist_classmap.csv              -- int label → Unicode Hiragana
            images/
                train/                       -- materialized PNG files
                    00000001.png
                    ...
                test/
                    ...
            train_index.jsonl                -- sidecar: {filename, label_int, char_unicode}
            test_index.jsonl
        k49/
            data/
                k49-train-imgs.npz           -- NumPy arrays
                k49-train-labels.npy
                k49-test-imgs.npz
                k49-test-labels.npy
            k49_classmap.csv                 -- int label → Unicode Hiragana
            images/
                train/
                    ...
                test/
                    ...
            train_index.jsonl
            test_index.jsonl
        kkanji/
            kkanji2/                         -- extracted from kkanji2.tar
                亡/                          -- directory name = Unicode char
                    001.png
                    002.png
                一/
                    001.png
                    ...

Sidecar JSONL format (produced by scripts/materialize_kuzushiji.py):
    {"filename": "00000001.png", "label_int": 0, "char_unicode": "お", "split": "train"}

Labels Extracted:
    - language_code: "ja"
    - script_name: "Jpan"
    - iso15924_script_code: "Jpan"
    - transcription: Unicode character string (single character)
    - raw_labels: {sub_dataset, split, label_int, char, script_type, historical, resolution_px}

Resolution Warning:
    28x28 (K-MNIST / K-49) and 64x64 (K-Kanji) are very small for modern models.
    Upscale to ≥224 px using cv2.resize(INTER_LANCZOS4) before SigLIP2 inference.

Example:
    >>> parser = KuzushijiParser()
    >>> # K-Kanji — character inferred from parent directory
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../kuzushiji"),
    ...     image_path=Path("/mnt/e/.../kuzushiji/kkanji/kkanji2/亡/001.png"),
    ...     config={},
    ... )
    >>> print(labels.transcription)
    '亡'
    >>> # K-49 — character from sidecar JSONL
    >>> labels = parser.parse(
    ...     dataset_path=Path("/mnt/e/.../kuzushiji"),
    ...     image_path=Path("/mnt/e/.../kuzushiji/k49/images/train/00000001.png"),
    ...     config={},
    ... )
    >>> print(labels.iso15924_script_code)
    'Jpan'
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "kuzushiji"
__l4_workstream__ = "WS3"
__l4_task__ = "handwriting"
__l4_l2_file__ = "kuzushiji_metadata.json"
__l4_integrate__ = "scripts/integrate_kuzushiji_enrichments.py"


import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)

# Valid split directory names
_VALID_SPLITS = frozenset({"train", "test"})

# Sub-dataset identifiers (matched against path components)
_KKANJI_MARKERS = frozenset({"kkanji", "kkanji2"})

# Native resolutions per sub-dataset (px, square)
_RESOLUTION_MAP = {
    "kmnist": 28,
    "k49": 28,
    "kkanji": 64,
}


class KuzushijiParser(BaseParser):
    """Parser for Kuzushiji pre-modern Japanese handwriting datasets.

    Handles all three sub-datasets (K-MNIST, K-49, K-Kanji) using a
    unified interface:

    - **K-Kanji**: the Unicode character is the parent directory name
      (``kkanji2/<char>/<image>.png``); no sidecar needed.
    - **K-MNIST / K-49**: the Unicode character is read from a sidecar
      JSONL index produced by ``scripts/materialize_kuzushiji.py``.
      Sidecar loading is cached per (dataset_path, sub_dataset, split).
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["kuzushiji", "kmnist", "k-mnist", "k49", "k-49", "kkanji", "k-kanji"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse Kuzushiji labels for a single character image.

        Args:
            dataset_path (Path): Root path of the kuzushiji dataset directory.
            image_path (Path): Absolute path to a single character crop PNG.
            config (dict[str, Any]): Dataset configuration dictionary (unused).

        Returns:
            OriginalLabels: OriginalLabels with Japanese script metadata and (where available)
            the Unicode character transcription.
        """
        labels = OriginalLabels()

        # All Kuzushiji data is Japanese historical cursive
        labels.language_code = "ja"
        labels.script_name = "Jpan"
        labels.iso15924_script_code = "Jpan"

        sub_dataset = _detect_sub_dataset(image_path)
        split = _detect_split(image_path)

        labels.raw_labels = {
            "dataset": "kuzushiji",
            "sub_dataset": sub_dataset,
            "split": split,
            "production": "handwritten-historical",
            "writing_system": "classical-japanese",
            "historical": True,
            "resolution_px": _RESOLUTION_MAP.get(sub_dataset, 0),
        }

        if sub_dataset == "kkanji":
            self._populate_kkanji_labels(image_path, labels)
        else:
            self._populate_indexed_labels(
                dataset_path, image_path, sub_dataset, split, labels
            )

        return labels

    def _populate_kkanji_labels(
        self,
        image_path: Path,
        labels: OriginalLabels,
    ) -> None:
        """Populate labels for K-Kanji images using directory-name character class.

        K-Kanji stores images in per-class subdirectories where the directory
        name is the Unicode character itself (e.g. ``kkanji2/亡/001.png``).

        Args:
            image_path (Path): Path to the PNG file.
            labels (OriginalLabels): OriginalLabels instance to populate in-place.
        """
        char = image_path.parent.name
        if not char or char in _KKANJI_MARKERS:
            logger.debug(
                "K-Kanji: cannot determine char from parent dir '%s' for %s",
                image_path.parent.name,
                image_path.name,
            )
            return

        labels.transcription = char
        if labels.raw_labels is not None:
            labels.raw_labels.update(
                {
                    "char": char,
                    "script_type": "kanji-historical",
                    "class_dir": str(image_path.parent.name),
                }
            )

    def _populate_indexed_labels(
        self,
        dataset_path: Path,
        image_path: Path,
        sub_dataset: str,
        split: str,
        labels: OriginalLabels,
    ) -> None:
        """Populate labels for K-MNIST / K-49 images via sidecar JSONL index.

        Args:
            dataset_path (Path): Root kuzushiji dataset path.
            image_path (Path): Path to the materialized PNG image.
            sub_dataset (str): Sub-dataset name (``"kmnist"`` or ``"k49"``).
            split (str): Split name (``"train"`` or ``"test"``).
            labels (OriginalLabels): OriginalLabels instance to populate in-place.
        """
        sub_root = dataset_path / sub_dataset
        entry = _lookup_entry(sub_root, sub_dataset, split, image_path.name)
        if entry is None:
            logger.debug(
                "No sidecar entry for %s in %s/%s — run materialize_kuzushiji.py",
                image_path.name,
                sub_dataset,
                split,
            )
            return

        char_unicode = entry.get("char_unicode", "")
        label_int = entry.get("label_int")

        if char_unicode:
            labels.transcription = char_unicode

        if labels.raw_labels is not None:
            labels.raw_labels.update(
                {
                    "char": char_unicode,
                    "label_int": label_int,
                    "script_type": "hiragana-historical",
                }
            )


# ---------------------------------------------------------------------------
# Module-level helpers (not part of the public API)
# ---------------------------------------------------------------------------


def _detect_sub_dataset(image_path: Path) -> str:
    """Detect Kuzushiji sub-dataset from path components.

    Args:
        image_path (Path): Path to the image file.

    Returns:
        str: One of ``"kmnist"``, ``"k49"``, ``"kkanji"``, or ``"unknown"``.
    """
    for part in image_path.parts:
        part_lower = part.lower()
        if part_lower in {"kkanji", "kkanji2"}:
            return "kkanji"
        if part_lower in {"kmnist", "k-mnist"}:
            return "kmnist"
        if part_lower in {"k49", "k-49"}:
            return "k49"
    return "unknown"


def _detect_split(image_path: Path) -> str:
    """Detect split name from path components.

    Args:
        image_path (Path): Path to the image file.

    Returns:
        str: ``"train"``, ``"test"``, or ``"unknown"``.
    """
    for part in reversed(image_path.parts):
        if part in _VALID_SPLITS:
            return part
    return "unknown"


def _lookup_entry(
    sub_root: Path,
    sub_dataset: str,
    split: str,
    filename: str,
) -> dict[str, Any] | None:
    """Look up a sidecar JSONL entry for a K-MNIST or K-49 image.

    Args:
        sub_root (Path): Root path for the sub-dataset (e.g. ``kuzushiji/kmnist/``).
        sub_dataset (str): Sub-dataset name for cache keying.
        split (str): Split name (``"train"`` or ``"test"``).
        filename (str): Base filename of the image.

    Returns:
        dict[str, Any] | None: Dict with ``filename``, ``label_int``, ``char_unicode`` keys,
        or None if not found.
    """
    index = _load_sidecar_index(sub_root, sub_dataset, split)
    if index is None:
        return None
    return index.get(filename)


@lru_cache(maxsize=12)
def _load_sidecar_index(
    sub_root: Path,
    sub_dataset: str,
    split: str,
) -> dict[str, dict[str, Any]] | None:
    """Load and cache a Kuzushiji sidecar JSONL index.

    Cached per (sub_root, sub_dataset, split) — loaded once per process.

    The sidecar JSONL format is:
    ``{"filename": "00000001.png", "label_int": 0, "char_unicode": "お"}``

    Args:
        sub_root (Path): Root path for the sub-dataset.
        sub_dataset (str): Sub-dataset name (used only for log messages).
        split (str): Split name (``"train"`` or ``"test"``).

    Returns:
        dict[str, dict[str, Any]] | None: Dict mapping filename → record dict, or None if index not found.
    """
    index_path = sub_root / f"{split}_index.jsonl"

    if not index_path.exists():
        logger.warning(
            "Kuzushiji %s/%s sidecar index not found: %s — "
            "run scripts/materialize_kuzushiji.py first",
            sub_dataset,
            split,
            index_path,
        )
        return None

    index: dict[str, dict[str, Any]] = {}
    try:
        with index_path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    fname = record.get("filename", "")
                    if fname:
                        index[fname] = record
                except json.JSONDecodeError:
                    logger.debug(
                        "Skipping malformed line %d in %s", line_num, index_path
                    )
    except OSError as exc:
        logger.error("Failed to read sidecar index %s: %s", index_path, exc)  # noqa: TRY400
        return None

    logger.debug(
        "Loaded %d entries from %s/%s sidecar index",
        len(index),
        sub_dataset,
        split,
    )
    return index


__all__ = ["KuzushijiParser"]
