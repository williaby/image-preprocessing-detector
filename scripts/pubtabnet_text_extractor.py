#!/usr/bin/env python3
"""Extract text from PubTabNet JSONL for language detection.

PubTabNet stores table content as character-level tokens in cells.
This script extracts and reconstructs text for language detection.

JSONL Structure:
    {
        "filename": "PMC4840965_004_00.png",
        "html": {
            "cells": [
                {"tokens": ["V", "a", "r", "i", "a", "b", "l", "e"], "bbox": [...]},
                ...
            ]
        }
    }

Usage:
    # Build text lookup from JSONL
    PYTHONPATH=. uv run python scripts/pubtabnet_text_extractor.py --build-index

    # Get text for a specific image
    PYTHONPATH=. uv run python scripts/pubtabnet_text_extractor.py --image PMC4840965_004_00.png
"""

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
PUBTABNET_PATH = Path("/mnt/e/image_detection/01_base_data/tables/pubtabnet/pubtabnet")
JSONL_PATH = PUBTABNET_PATH / "PubTabNet_2.0.0.jsonl"
INDEX_PATH = Path("/mnt/e/image_detection/metadata_registry/pubtabnet_text_index.json")


def extract_text_from_tokens(tokens: list[str]) -> str:
    """Convert character tokens to text, filtering HTML tags."""
    text_chars = []
    for token in tokens:
        # Skip HTML tags
        if token.startswith("<") and token.endswith(">"):
            continue
        text_chars.append(token)
    return "".join(text_chars)


def extract_text_from_record(record: dict) -> str:
    """Extract all text from a PubTabNet record."""
    cells = record.get("html", {}).get("cells", [])
    texts = []
    for cell in cells:
        tokens = cell.get("tokens", [])
        text = extract_text_from_tokens(tokens)
        if text.strip():
            texts.append(text)
    return " ".join(texts)


def build_text_index() -> dict[str, str]:
    """Build {filename: text} index from JSONL."""
    if not JSONL_PATH.exists():
        logger.error(f"JSONL not found: {JSONL_PATH}")
        return {}

    logger.info(f"Building text index from {JSONL_PATH}")
    index: dict[str, str] = {}

    with open(JSONL_PATH) as f:
        for i, line in enumerate(f):
            if (i + 1) % 50000 == 0:
                logger.info(f"Processed {i + 1} records...")

            try:
                record = json.loads(line)
                filename = record.get("filename", "")
                text = extract_text_from_record(record)
                if filename and text:
                    index[filename] = text
            except json.JSONDecodeError:
                continue

    logger.info(f"Built index with {len(index)} entries")
    return index


def save_index(index: dict[str, str]) -> None:
    """Save index to JSON file."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f)
    logger.info(f"Saved index to {INDEX_PATH}")


def load_index() -> dict[str, str]:
    """Load index from JSON file."""
    if not INDEX_PATH.exists():
        logger.warning(f"Index not found, building: {INDEX_PATH}")
        index = build_text_index()
        save_index(index)
        return index

    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_text(filename: str, index: dict[str, str] | None = None) -> str | None:
    """Get text for a filename from the index."""
    if index is None:
        index = load_index()
    return index.get(filename)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PubTabNet")
    parser.add_argument("--build-index", action="store_true", help="Build text index")
    parser.add_argument("--image", type=str, help="Get text for specific image")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    args = parser.parse_args()

    if args.build_index:
        index = build_text_index()
        save_index(index)
        print(f"\nBuilt index with {len(index)} entries")
        print(f"Saved to: {INDEX_PATH}")

    elif args.image:
        index = load_index()
        text = get_text(args.image, index)
        if text:
            print(f"\nText for {args.image}:")
            print("-" * 60)
            print(text[:1000] + ("..." if len(text) > 1000 else ""))
        else:
            print(f"No text found for: {args.image}")

    elif args.stats:
        index = load_index()
        total = len(index)
        avg_len = sum(len(t) for t in index.values()) / total if total > 0 else 0
        print("\nPubTabNet Text Index Statistics:")
        print(f"  Total entries: {total:,}")
        print(f"  Average text length: {avg_len:.0f} chars")
        print(f"  Index file: {INDEX_PATH}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
