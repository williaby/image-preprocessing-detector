#!/usr/bin/env python3
"""
Download and explore VidOre V3 Finance dataset.

Usage:
    poetry run python scripts/download_vidore_finance.py
"""

import logging
from pathlib import Path

from datasets import load_dataset

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Download VidOre V3 Finance dataset."""
    output_dir = Path("data/raw/vidore_v3_finance")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading VidOre V3 Finance dataset...")

    # Download corpus (document pages with images)
    logger.info("Loading corpus config (2,940 pages)...")
    corpus = load_dataset(
        "vidore/vidore_v3_finance_en", "corpus", split="test", streaming=False
    )
    logger.info(f"✓ Corpus loaded: {len(corpus)} pages")

    # Download documents metadata
    logger.info("Loading documents_metadata config...")
    metadata = load_dataset(
        "vidore/vidore_v3_finance_en",
        "documents_metadata",
        split="test",
        streaming=False,
    )
    logger.info(f"✓ Metadata loaded: {len(metadata)} documents")

    # Download qrels (has bounding boxes!)
    logger.info("Loading qrels config (with bounding boxes)...")
    qrels = load_dataset(
        "vidore/vidore_v3_finance_en", "qrels", split="test", streaming=False
    )
    logger.info(f"✓ Qrels loaded: {len(qrels)} relevance judgments")

    # Save to disk for offline access
    logger.info(f"Saving datasets to {output_dir}...")

    corpus.save_to_disk(str(output_dir / "corpus"))
    metadata.save_to_disk(str(output_dir / "documents_metadata"))
    qrels.save_to_disk(str(output_dir / "qrels"))

    logger.info("✓ Download complete!")

    # Print summary
    print("\n" + "=" * 60)
    print("VidOre V3 Finance Dataset Summary")
    print("=" * 60)
    print(f"Corpus pages: {len(corpus)}")
    print(f"Documents: {len(metadata)}")
    print(f"Relevance judgments: {len(qrels)}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    # Show first corpus sample
    print("\nFirst corpus sample:")
    sample = corpus[0]
    print(f"  doc_id: {sample['doc_id']}")
    print(f"  page_number_in_doc: {sample['page_number_in_doc']}")
    print(f"  markdown (first 100 chars): {sample['markdown'][:100]}...")
    print(f"  image: {sample['image'].size if sample['image'] else 'None'}")

    # Show document metadata
    print("\nDocument metadata:")
    doc_meta = metadata[0]
    print(f"  file_name: {doc_meta['file_name']}")
    print(f"  total_pages: {doc_meta['page_number']}")
    print(f"  license: {doc_meta['license']}")

    # Show qrels with bounding boxes
    print("\nQrels (with bounding boxes):")
    qrel_sample = qrels[0]
    print(f"  query_id: {qrel_sample['query_id']}")
    print(f"  corpus_id: {qrel_sample['corpus_id']}")
    print(f"  bounding_boxes: {qrel_sample['bounding_boxes']}")

    print("\n✓ Dataset ready for FR-4.4 parasitic content extraction!")


if __name__ == "__main__":
    main()
