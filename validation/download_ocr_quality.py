"""Download OCR-Quality dataset from Hugging Face."""

from pathlib import Path

from datasets import load_dataset

# Create output directory
output_dir = Path("validation/datasets/ocr_quality")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("DOWNLOADING OCR-QUALITY DATASET FROM HUGGING FACE")
print("=" * 80)
print()
print("Dataset: Aslan-mingye/OCR-Quality")
print("Size: ~1.1 GB (1,000 images with quality scores)")
print("Source: https://huggingface.co/datasets/Aslan-mingye/OCR-Quality")
print()

# Download dataset
print("Downloading dataset (this may take a few minutes)...")
dataset = load_dataset("Aslan-mingye/OCR-Quality", split="train")

# Save to disk
print(f"\nSaving to {output_dir}...")
dataset.save_to_disk(str(output_dir))

# Also save as parquet for easy analysis
parquet_file = output_dir / "ocr_quality.parquet"
dataset.to_parquet(str(parquet_file))

print()
print("=" * 80)
print("DOWNLOAD COMPLETE")
print("=" * 80)
print(f"✓ Downloaded {len(dataset)} images")
print(f"  Location: {output_dir}")
print(f"  Parquet file: {parquet_file}")
print()
print("Dataset Structure:")
print(f"  - index: Sample ID (0-{len(dataset)-1})")
print("  - human_score: Quality rating (1=Excellent, 2=Good, 3=Fair, 4=Poor)")
print("  - ocr_text: Extracted text")
print("  - source: Document category")
print("  - image: PNG image data @ 300 DPI")
print("  - image_width, image_height: Dimensions")
print()
print("Next step: Run validation script")
print("  poetry run python validation/validate_ocr_quality.py")
print("=" * 80)
