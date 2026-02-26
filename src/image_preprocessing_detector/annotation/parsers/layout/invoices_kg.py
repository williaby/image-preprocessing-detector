# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Parser for Kaggle High-Quality Invoice Images dataset (invoices-kg).

The invoices-kg dataset provides invoice images with structured JSON annotations
extracted from the Kaggle dataset:
https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr

Dataset Structure:
    invoices_kaggle/
        train/
            images/
                train_00000.jpg
                train_00001.jpg
                ...
            annotations.json  - Manifest with invoice data and OCR text
        val/
            images/
                val_00000.jpg
                ...
            annotations.json

Annotation Format:
    Each annotations.json is a list of dictionaries:
    [
        {
            "filename": "train_00000.jpg",
            "original_filename": "batch1-0965.jpg",
            "original_path": "data/downloads/...",
            "csv_source": "data/downloads/.../batch1_2.csv",
            "json_data": "{...structured invoice data...}",
            "ocred_text": "Invoice no: 41389063 Date of issue: ..."
        },
        ...
    ]

JSON Data Structure (within json_data field):
    {
        "invoice": {
            "client_name": "...",
            "client_address": "...",
            "seller_name": "...",
            "seller_address": "...",
            "invoice_number": "...",
            "invoice_date": "MM/DD/YYYY",
            "due_date": "..."
        },
        "items": [
            {
                "description": "...",
                "quantity": "3.00",
                "total_price": "16.14"
            }
        ],
        "subtotal": {
            "tax": "1.47",
            "discount": "",
            "total": "16.14"
        },
        "payment_instructions": {
            "due_date": "",
            "bank_name": "",
            "account_number": "",
            "payment_method": ""
        }
    }

Extracts:
    - invoice_data: Structured invoice fields (client, seller, items, totals)
    - text_content: Full OCR text
    - split: Dataset split (train/val)
    - document_type: "invoice"

Example:
    >>> parser = InvoicesKgParser()
    >>> labels = parser.parse(
    ...     dataset_path=Path("/data/invoices_kaggle"),
    ...     image_path=Path("/data/invoices_kaggle/train/images/train_00000.jpg"),
    ...     config={},
    ... )
    >>> print(labels.raw_labels["invoice_number"])
    41389063
    >>> print(labels.text_content["full_text"][:50])
    Invoice no: 41389063 Date of issue: 03/17/2021...
"""

# --- Level 4 registry metadata ---
from __future__ import annotations

__l4_category__ = "parser"
__l4_dataset__ = "invoices-kg"
__l4_workstream__ = "WS3"
__l4_task__ = "layout"
__l4_l2_file__ = "invoices_kg_metadata.json"
__l4_integrate__ = "scripts/integrate_invoices_kg_enrichments.py"


import json
import logging
from pathlib import Path
from typing import Any

from ...schemas.immutable import OriginalLabels
from ..base import BaseParser

logger = logging.getLogger(__name__)


class InvoicesKgParser(BaseParser):
    """Parser for Kaggle High-Quality Invoice Images dataset.

    Extracts structured invoice data and OCR text from JSON manifest files.
    """

    @property
    def dataset_names(self) -> list[str]:
        """Return dataset names handled by this parser."""
        return ["invoices-kg", "invoices_kaggle"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse invoices-kg labels from annotation manifest.

        Args:
            dataset_path: Root path of the invoices_kaggle dataset
            image_path: Absolute path to the image file being processed
            config: Dataset configuration dictionary (unused)

        Returns:
            OriginalLabels with invoice data and text_content populated

        Raises:
            No exceptions raised - returns empty OriginalLabels if parsing fails
        """
        labels = OriginalLabels()

        if labels.raw_labels is None:
            labels.raw_labels = {}

        # Determine split from path
        path_str = str(image_path)
        split_name = None
        if "/train/" in path_str:
            split_name = "train"
        elif "/val/" in path_str:
            split_name = "val"

        if not split_name:
            logger.warning(f"Could not determine split for {image_path}")
            return labels

        # Find annotations.json file
        annotations_path = dataset_path / split_name / "annotations.json"
        if not annotations_path.exists():
            logger.debug(f"Annotations file not found: {annotations_path}")
            return labels

        # Load annotations
        try:
            with open(annotations_path, encoding="utf-8") as f:
                annotations = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Failed to load annotations: {e}")
            return labels

        # Find matching annotation by filename
        image_filename = image_path.name
        annotation = None
        for ann in annotations:
            if ann.get("filename") == image_filename:
                annotation = ann
                break

        if not annotation:
            logger.debug(f"No annotation found for {image_filename}")
            return labels

        # Parse invoice data from json_data field
        json_data_str = annotation.get("json_data", "")
        if json_data_str:
            try:
                invoice_data = json.loads(json_data_str)

                # Extract invoice fields
                invoice_info = invoice_data.get("invoice", {})
                labels.raw_labels.update(
                    {
                        "client_name": invoice_info.get("client_name", ""),
                        "client_address": invoice_info.get("client_address", ""),
                        "seller_name": invoice_info.get("seller_name", ""),
                        "seller_address": invoice_info.get("seller_address", ""),
                        "invoice_number": invoice_info.get("invoice_number", ""),
                        "invoice_date": invoice_info.get("invoice_date", ""),
                        "due_date": invoice_info.get("due_date", ""),
                    }
                )

                # Extract line items
                items = invoice_data.get("items", [])
                labels.raw_labels["items"] = items
                labels.raw_labels["item_count"] = len(items)

                # Extract totals
                subtotal = invoice_data.get("subtotal", {})
                labels.raw_labels.update(
                    {
                        "tax": subtotal.get("tax", ""),
                        "discount": subtotal.get("discount", ""),
                        "total": subtotal.get("total", ""),
                    }
                )

                # Payment instructions
                payment = invoice_data.get("payment_instructions", {})
                labels.raw_labels["payment_account"] = payment.get("account_number", "")
                labels.raw_labels["payment_method"] = payment.get("payment_method", "")

            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse invoice json_data: {e}")

        # Extract OCR text
        ocred_text = annotation.get("ocred_text", "")
        if ocred_text:
            # Populate Layer 2 text_content schema fields
            if labels.raw_labels is None:
                labels.raw_labels = {}
            labels.raw_labels["text_content"] = {
                "full_text": ocred_text,
                "source_type": "dataset_provided",
                "source_format": "json_manifest",
                "extraction_method": "InvoicesKgParser.parse",
                "extraction_timestamp": None,
                "is_complete": True,
                "encoding": "utf-8",
            }

        # Add provenance metadata
        labels.raw_labels.update(
            {
                "split": split_name,
                "document_type": "invoice",
                "original_filename": annotation.get("original_filename", ""),
                "csv_source": annotation.get("csv_source", ""),
            }
        )

        return labels


__all__ = ["InvoicesKgParser"]
