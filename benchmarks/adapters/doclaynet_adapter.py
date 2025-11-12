"""DocLayNet dataset adapter for layout detection benchmarking.

DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis
Paper: https://arxiv.org/abs/2206.01062
License: CDLA-Permissive-2.0
Dataset: https://github.com/DS4SD/DocLayNet

11-class taxonomy:
- Caption, Footnote, Formula, List-item, Page-footer, Page-header,
  Picture, Section-header, Table, Text, Title

IMPORTANT: Always use doc-wise splits (not page-wise) for benchmarking.
Page-wise metrics inflate scores by ~10-15 points.

SPDX-License-Identifier: Apache-2.0
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from benchmarks.adapters.base import BaseAdapter, DatasetRegistry, PageSample


@DatasetRegistry.register("doclaynet")
class DocLayNetAdapter(BaseAdapter):
    """Adapter for DocLayNet dataset.

    Supports both doc-wise and page-wise splits (doc-wise recommended).
    """

    # DocLayNet 11-class taxonomy
    CLASSES = [
        "Caption",
        "Footnote",
        "Formula",
        "List-item",
        "Page-footer",
        "Page-header",
        "Picture",
        "Section-header",
        "Table",
        "Text",
        "Title",
    ]

    def __init__(
        self,
        data_dir: Path,
        split: str = "val_docwise",
        cache_dir: Path | None = None,
        download: bool = False,
    ) -> None:
        """Initialize DocLayNet adapter.

        Args:
            data_dir: Root directory containing DocLayNet dataset
            split: Dataset split (train, val_docwise, val_pagewise, test)
            cache_dir: Optional cache directory
            download: Whether to download if not present
        """
        super().__init__(data_dir, split, cache_dir, download)

        # Validate split
        valid_splits = ["train", "val_docwise", "val_pagewise", "test"]
        if split not in valid_splits:
            raise ValueError(f"Invalid split: {split}. Must be one of {valid_splits}")

        # Warn if using page-wise split
        if "pagewise" in split:
            import warnings

            warnings.warn(
                "Page-wise splits inflate metrics by ~10-15 points. "
                "Use doc-wise splits for benchmarking.",
                UserWarning,
                stacklevel=2,
            )

        # Load annotations
        self._load_annotations()

    def _load_annotations(self) -> None:
        """Load DocLayNet COCO-format annotations."""
        # DocLayNet uses COCO format
        ann_path = self.data_dir / "COCO" / f"{self.split}.json"

        if not ann_path.exists():
            if self.download:
                self.download_dataset()
            else:
                raise FileNotFoundError(
                    f"Annotations not found: {ann_path}\n"
                    "Set download=True to download automatically, or download from:\n"
                    "https://github.com/DS4SD/DocLayNet"
                )

        with open(ann_path) as f:
            self.coco_data = json.load(f)

        # Build sample index
        self._build_index()

    def _build_index(self) -> None:
        """Build index of images and annotations."""
        # Create image ID to info mapping
        self.image_info = {img["id"]: img for img in self.coco_data["images"]}

        # Group annotations by image ID
        self.image_annotations: dict[int, list[dict]] = {}
        for ann in self.coco_data["annotations"]:
            img_id = ann["image_id"]
            if img_id not in self.image_annotations:
                self.image_annotations[img_id] = []
            self.image_annotations[img_id].append(ann)

        # Extract sample IDs
        self._sample_ids = [str(img_id) for img_id in self.image_info]

        # Build category ID to name mapping
        self.category_names = {
            cat["id"]: cat["name"] for cat in self.coco_data["categories"]
        }

    def __iter__(self) -> Iterator[PageSample]:
        """Iterate over DocLayNet samples."""
        for sample_id in self._sample_ids:
            yield self.get_sample(sample_id)

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self._sample_ids)

    def get_sample(self, sample_id: str) -> PageSample:
        """Get a specific sample by ID.

        Args:
            sample_id: Image ID (as string)

        Returns:
            PageSample with COCO-format annotations
        """
        img_id = int(sample_id)
        if img_id not in self.image_info:
            raise KeyError(f"Sample {sample_id} not found")

        img_info = self.image_info[img_id]
        annotations = self.image_annotations.get(img_id, [])

        # Construct image path
        image_path = self.data_dir / "PNG" / img_info["file_name"]

        # Convert annotations to include category names
        enriched_annotations = []
        for ann in annotations:
            enriched_ann = ann.copy()
            enriched_ann["category_name"] = self.category_names[ann["category_id"]]
            enriched_annotations.append(enriched_ann)

        # Extract doc_id from file name (format: {doc_id}_{page_num}.png)
        file_stem = Path(img_info["file_name"]).stem
        parts = file_stem.split("_")
        doc_id = "_".join(parts[:-1])  # Everything except last part
        page_num = int(parts[-1]) if parts[-1].isdigit() else None

        return PageSample(
            image_path=image_path,
            annotations=enriched_annotations,
            metadata={
                "sample_id": sample_id,
                "image_id": img_id,
                "doc_id": doc_id,
                "page_num": page_num,
                "width": img_info["width"],
                "height": img_info["height"],
                "split": self.split,
            },
        )

    @property
    def license(self) -> str:
        """DocLayNet license."""
        return "CDLA-Permissive-2.0"

    @property
    def split_info(self) -> dict[str, Any]:
        """Information about dataset splits."""
        return {
            "train": 69375,  # images
            "val_docwise": 7059,
            "val_pagewise": 7059,
            "test": 7110,
            "documents": {
                "train": 6988,
                "val": 1000,
                "test": 999,
            },
            "classes": 11,
            "annotations": {
                "train": 1009970,
                "val": 142674,
                "test": 143312,
            },
        }

    @property
    def classes(self) -> list[str]:
        """Return list of class names."""
        return self.CLASSES

    def download_dataset(self) -> None:
        """Download DocLayNet dataset.

        Note: DocLayNet is large (~36 GB). Manual download recommended.
        """
        raise NotImplementedError(
            "DocLayNet automatic download not implemented.\n"
            "Please download manually from:\n"
            "https://github.com/DS4SD/DocLayNet\n"
            "or use Hugging Face datasets:\n"
            "https://huggingface.co/datasets/ds4sd/DocLayNet"
        )

    def get_doc_pages(self, doc_id: str) -> list[PageSample]:
        """Get all pages for a specific document.

        Useful for doc-wise evaluation.

        Args:
            doc_id: Document identifier

        Returns:
            List of PageSample instances for this document
        """
        pages = []
        for sample_id in self._sample_ids:
            sample = self.get_sample(sample_id)
            if sample.doc_id == doc_id:
                pages.append(sample)

        # Sort by page number
        pages.sort(key=lambda p: p.page_num or 0)
        return pages

    def get_doc_ids(self) -> list[str]:
        """Get list of unique document IDs in this split."""
        doc_ids = set()
        for sample_id in self._sample_ids:
            sample = self.get_sample(sample_id)
            if sample.doc_id:
                doc_ids.add(sample.doc_id)
        return sorted(doc_ids)

    def verify_integrity(self) -> bool:
        """Verify DocLayNet dataset integrity."""
        # Check annotation format
        required_keys = ["images", "annotations", "categories"]
        for key in required_keys:
            if key not in self.coco_data:
                raise RuntimeError(f"Missing key in COCO data: {key}")

        # Verify category count
        if len(self.coco_data["categories"]) != 11:
            raise RuntimeError(
                f"Expected 11 categories, got {len(self.coco_data['categories'])}"
            )

        # Verify category names
        category_names = {cat["name"] for cat in self.coco_data["categories"]}
        expected_names = set(self.CLASSES)
        if category_names != expected_names:
            raise RuntimeError(
                f"Category mismatch. Expected: {expected_names}, got: {category_names}"
            )

        # Check that images exist (sample first 10)
        return super().verify_integrity()
