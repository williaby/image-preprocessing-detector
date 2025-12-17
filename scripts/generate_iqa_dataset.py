#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

"""
Generate IQA Training Dataset with 13-Dimensional Distribution Tracking.

This script generates a comprehensive IQA training dataset with balanced distributions
across 13 dimensions including defect types, severity, DPI, color mode, orientation,
combined defects, JPEG quality, layout type, text density, and more.

IMPORTANT (Consensus Review 2025-12-14):
- Target reduced to 25K samples (saturation point per multi-model consensus)
- DIQA-5000 REMOVED from training (evaluation-only to prevent data leakage)
- See docs/planning/PHASE7_CRITICAL_EVALUATION.md Section 12.14 for rationale

Output: data/training/iqa_phase2_25k/
Size: ~10-12GB
Duration: 2-3 hours (local CPU)
"""

import argparse
import json
import random  # nosec B311 - used for non-cryptographic dataset shuffling/sampling
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from tqdm import tqdm

try:
    from datasets import load_from_disk
except ImportError:
    print("Error: datasets library not installed. Run: uv sync --extra ml")
    sys.exit(1)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import albumentations as A  # noqa: N812 - standard ML convention
except ImportError:
    print("Error: albumentations not installed. Run: uv sync --extra ml")
    sys.exit(1)


class DatasetConfig:
    """Configuration for 25K dataset generation with 13-dimensional tracking.

    Updated 2025-12-15 per multi-model consensus review and MVP plan v2:
    - Target reduced from 100K to 25K (saturation point identified)
    - DIQA-5000 TRAIN SPLIT included (val/test reserved for evaluation)
    - See PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 3.3
    - See PHASE7_CRITICAL_EVALUATION.md Section 12.14
    """

    # Target dataset size - REDUCED per multi-model consensus (saturation at ~25K)
    # See docs/planning/PHASE7_CRITICAL_EVALUATION.md Section 12.14
    TOTAL_SAMPLES = 25_000

    # Dataset composition (samples per source) - 14 SOURCES for domain diversity
    # Updated 2025-12-15 per MVP v2.1 plan to reduce domain bias
    # NOTE: DIQA-5000 uses TRAIN SPLIT ONLY to prevent data leakage
    # Val/test splits are reserved for evaluation (human MOS scores)
    # See docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 3.3
    COMPOSITION = {
        # Real degradation anchor sources (21.5% total)
        "diqa_5000_train": 3_500,  # TRAIN SPLIT ONLY - real degradation with human MOS
        "tobacco_800": 1_285,  # Historical scans - real degradation
        "dibco": 600,  # Document binarization competition - real degradation
        # Multi-category diversity
        "rvl_cdip": 3_500,  # 16 document categories - needs download
        # Structured forms
        "nist_db2_sd6": 2_500,  # Check/tax forms - needs download
        "funsd_plus": 1_300,  # Form understanding
        # Mobile capture proxy
        "sroie": 1_500,  # Receipts - needs download
        # Born-digital tables (reduced from 70% to 18%)
        "tablebank": 2_500,  # LaTeX/Word tables
        "pubtabnet": 2_000,  # Scientific paper tables
        # Mixed layouts
        "doclaynet": 2_500,  # Needs PDF→image conversion
        # Handwriting
        "nist_sd19": 1_500,  # Handwriting in forms context - needs download
        # Math/formulas
        "im2latex": 1_200,  # Mathematical formulas - needs download
        "mathverse": 500,  # Math diagrams - needs download
        # Educational content
        "multimodal_textbook": 1_113,  # Sample from 6.5M keyframes
        # CRITICAL: DIQA val/test splits are EVALUATION ONLY (not included here)
    }

    # 13-Dimensional Distribution Targets
    DISTRIBUTIONS = {
        # 1. Defect types
        "defect_type": {
            "blur": 0.29,
            "noise": 0.24,
            "skew": 0.19,
            "illumination": 0.24,
            "artifacts": 0.15,
        },
        # 2. Severity levels
        "severity": {"mild": 0.30, "moderate": 0.50, "severe": 0.20},
        # 3. Document types (from source datasets)
        "document_type": {
            "born_digital": 0.86,
            "hybrid": 0.03,
            "image_only": 0.11,
        },
        # 4. Document categories (from source datasets)
        "category": {
            "scientific": 0.40,
            "tables": 0.30,
            "mixed_layout": 0.18,
            "handwriting": 0.13,
            "forms": 0.001,
        },
        # 5. DPI ranges
        "dpi_range": {
            "<100": 0.10,
            "100-149": 0.15,
            "150-199": 0.18,
            "200-249": 0.20,
            "250-299": 0.22,
            ">=300": 0.15,
        },
        # 6. Color modes (NEW)
        "color_mode": {"RGB": 0.60, "L": 0.35, "1": 0.05},
        # 7. Orientation (NEW)
        "orientation": {"portrait": 0.75, "landscape": 0.20, "square": 0.05},
        # 8. Combined defects (NEW)
        "combined_defects": {0: 0.20, 1: 0.40, 2: 0.25, 3: 0.15},
        # 9. JPEG quality (NEW)
        "jpeg_quality": {
            "high": 0.30,  # 90-100
            "medium": 0.40,  # 70-89
            "low": 0.20,  # 50-69
            "very_low": 0.10,  # <50
        },
        # 10. Layout complexity
        "layout_type": {
            "single_column": 0.50,
            "multi_column": 0.30,
            "three_column": 0.10,
            "complex": 0.10,
        },
        # 11. Text density
        "text_density": {
            "none": 0.05,
            "sparse": 0.15,
            "medium": 0.50,
            "dense": 0.30,
        },
        # 12. Background complexity
        "background": {
            "plain": 0.70,
            "textured": 0.15,
            "watermark": 0.10,
            "dark": 0.05,
        },
        # 13. Language/Script (check dataset diversity)
        "language": {
            "english": 0.70,
            "other_latin": 0.15,
            "cjk": 0.10,
            "arabic": 0.03,
            "other": 0.02,
        },
    }

    # Dataset-specific augmentation strategies
    AUGMENTATION_STRATEGY = {
        "diqa_5000": {
            "clean": 0.0,
            "light": 0.0,
            "medium": 0.0,
            "heavy": 0.0,
        },  # Use as-is
        "doclaynet": {"clean": 0.20, "light": 0.20, "medium": 0.40, "heavy": 0.20},
        "tablebank": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "pubtabnet": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "docbank": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "iam": {"clean": 0.50, "light": 0.50, "medium": 0.0, "heavy": 0.0},
        "funsd_plus": {
            "clean": 0.20,
            "light": 0.30,
            "medium": 0.35,
            "heavy": 0.15,
        },  # Varied augmentation for 5x multiplier
    }

    # DPI upsampling targets per dataset
    DPI_STRATEGY = {
        "diqa_5000": None,  # Already ~260 DPI
        "doclaynet": None,  # Already 150-300 DPI
        "tablebank": {"150": 0.50, "200": 0.30, "300": 0.20},  # Upsample from 72 DPI
        "pubtabnet": {"150": 0.50, "200": 0.30, "300": 0.20},
        "docbank": {"150": 0.40, "200": 0.30, "300": 0.30},
        "iam": None,  # Already 300 DPI
        "funsd_plus": None,  # Already 200-300 DPI
    }


class AugmentationPipeline:
    """Multi-dimensional augmentation with defect tracking."""

    def __init__(self):
        # Define augmentation transforms for each defect type
        self.defect_transforms = {
            "blur": A.OneOf(
                [
                    A.GaussianBlur(blur_limit=(3, 15), p=1.0),
                    A.MotionBlur(blur_limit=(3, 15), p=1.0),
                    A.MedianBlur(blur_limit=(3, 9), p=1.0),
                ],
                p=1.0,
            ),
            "noise": A.OneOf(
                [
                    A.GaussNoise(p=1.0),  # Use defaults
                    A.ISONoise(
                        color_shift=(0.01, 0.1), p=1.0
                    ),  # Removed intensity parameter
                    A.MultiplicativeNoise(multiplier=(0.9, 1.1), p=1.0),
                ],
                p=1.0,
            ),
            "skew": A.Rotate(
                limit=15, border_mode=0, p=1.0
            ),  # Use constant border fill
            "illumination": A.OneOf(
                [
                    A.RandomBrightnessContrast(
                        brightness_limit=0.3, contrast_limit=0.3, p=1.0
                    ),
                    A.RandomGamma(
                        gamma_limit=(50, 150), p=1.0
                    ),  # Keep as-is (percentage values)
                    A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=1.0),
                ],
                p=1.0,
            ),
            "artifacts": A.ImageCompression(quality_range=(10, 90), p=1.0),
        }

    def apply_defects(
        self, image: np.ndarray, num_defects: int
    ) -> tuple[np.ndarray, list[str]]:
        """Apply random combination of defects."""
        if num_defects == 0:
            return image, []

        # Select defects to apply (avoid conflicting combinations)
        defect_pool = list(self.defect_transforms.keys())
        # Avoid skew + artifacts (skew should be detected, not masked by compression)
        if num_defects > 1 and random.random() < 0.5:  # nosec B311
            defect_pool = [d for d in defect_pool if d != "artifacts"]

        applied_defects = random.sample(  # nosec B311
            defect_pool, min(num_defects, len(defect_pool))
        )

        # Apply each defect sequentially
        for defect in applied_defects:
            transform = self.defect_transforms[defect]
            image = transform(image=image)["image"]

        return image, applied_defects


class DatasetGenerator:
    """Generate 100K IQA dataset with 13-dimensional tracking."""

    def __init__(self, output_dir: Path, config: DatasetConfig):
        self.output_dir = output_dir
        self.config = config
        self.augmentor = AugmentationPipeline()

        # Track actual distributions
        self.actual_distributions = {
            key: defaultdict(int) for key in config.DISTRIBUTIONS.keys()
        }

        # Create output structure
        self.setup_output_directories()

    def setup_output_directories(self):
        """Create output directory structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "metadata").mkdir(exist_ok=True)

        print(f"Output directory: {self.output_dir}")

    def load_source_datasets(self) -> dict[str, list[Path]]:
        """Load file paths from source datasets.

        Updated 2025-12-15 for 14-source MVP v2.1 distribution.
        See docs/planning/PHASE7_IDEAL_STATE_PROJECT_PLAN_v2.md Section 3.3
        """
        datasets = {}

        # === REAL DEGRADATION ANCHOR SOURCES (21.5%) ===

        # DIQA-5000 TRAIN SPLIT ONLY - val/test reserved for evaluation
        # This prevents data leakage while still using real degraded images with MOS labels
        diqa_train_path = PROJECT_ROOT / "data/benchmarks/diqa-5000/train/res"
        if diqa_train_path.exists():
            all_files = sorted(diqa_train_path.glob("*.jpg"))
            target = self.config.COMPOSITION.get("diqa_5000_train", 0)
            if target > 0:
                datasets["diqa_5000_train"] = all_files[:target]
                print(
                    f"  DIQA-5000 (TRAIN ONLY): Found {len(all_files)} samples, using {len(datasets['diqa_5000_train'])}"
                )
                print(
                    "    ⚠️  Val/test splits reserved for evaluation (data leakage prevention)"
                )

        # Tobacco-800 - Historical scans with real degradation
        tobacco_path = PROJECT_ROOT / "data/benchmarks/tobacco-800"
        if tobacco_path.exists():
            all_files = sorted(tobacco_path.glob("**/*.jpg")) + sorted(
                tobacco_path.glob("**/*.tif")
            )
            target = self.config.COMPOSITION.get("tobacco_800", 0)
            if target > 0 and all_files:
                datasets["tobacco_800"] = all_files[:target]
                print(
                    f"  Tobacco-800: Found {len(all_files)} samples, using {len(datasets['tobacco_800'])}"
                )

        # DIBCO - Document binarization competition (real degradation)
        dibco_path = PROJECT_ROOT / "data/benchmarks/dibco"
        if dibco_path.exists():
            all_files = sorted(dibco_path.glob("**/*.png")) + sorted(
                dibco_path.glob("**/*.bmp")
            )
            target = self.config.COMPOSITION.get("dibco", 0)
            if target > 0 and all_files:
                datasets["dibco"] = all_files[:target]
                print(
                    f"  DIBCO: Found {len(all_files)} samples, using {len(datasets['dibco'])}"
                )
        else:
            print("  DIBCO: ⚠️ Not downloaded - needs DIBCO 2009-2019 competition data")

        # === MULTI-CATEGORY DIVERSITY ===

        # RVL-CDIP - 16 document categories
        rvl_cdip_path = PROJECT_ROOT / "data/benchmarks/rvl-cdip"
        if rvl_cdip_path.exists():
            all_files = sorted(rvl_cdip_path.glob("**/*.tif"))
            target = self.config.COMPOSITION.get("rvl_cdip", 0)
            if target > 0 and all_files:
                datasets["rvl_cdip"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  RVL-CDIP: Found {len(all_files)} samples, using {len(datasets['rvl_cdip'])}"
                )
        else:
            print("  RVL-CDIP: ⚠️ Not downloaded - use HuggingFace `rvl_cdip`")

        # === STRUCTURED FORMS ===

        # NIST DB2 + SD6 - Check and tax forms
        nist_forms_path = PROJECT_ROOT / "data/benchmarks/nist-forms"
        if nist_forms_path.exists():
            all_files = sorted(nist_forms_path.glob("**/*.png"))
            target = self.config.COMPOSITION.get("nist_db2_sd6", 0)
            if target > 0 and all_files:
                datasets["nist_db2_sd6"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  NIST DB2+SD6: Found {len(all_files)} samples, using {len(datasets['nist_db2_sd6'])}"
                )
        else:
            print("  NIST DB2+SD6: ⚠️ Not downloaded - needs NIST Special Databases")

        # FUNSD+ (Enhanced - HuggingFace Datasets format)
        funsd_plus_path = PROJECT_ROOT / "data/benchmarks/funsd_plus/train"
        if funsd_plus_path.exists():
            try:
                funsd_dataset = load_from_disk(str(funsd_plus_path))
                target = self.config.COMPOSITION.get("funsd_plus", 0)
                if target > 0:
                    # Use available samples (no augmentation multiplier needed for 1,300)
                    selected_indices = list(range(min(len(funsd_dataset), target)))
                    datasets["funsd_plus"] = [
                        (funsd_dataset, idx) for idx in selected_indices
                    ]
                    print(
                        f"  FUNSD+: Found {len(funsd_dataset)} samples, using {len(datasets['funsd_plus'])}"
                    )
            except Exception as e:
                print(f"  FUNSD+: ⚠️ Could not load: {e}")

        # === MOBILE CAPTURE PROXY ===

        # SROIE - Receipts (approximates mobile capture)
        sroie_path = PROJECT_ROOT / "data/benchmarks/sroie"
        if sroie_path.exists():
            all_files = sorted(sroie_path.glob("**/*.jpg"))
            target = self.config.COMPOSITION.get("sroie", 0)
            if target > 0 and all_files:
                datasets["sroie"] = all_files[:target]
                print(
                    f"  SROIE: Found {len(all_files)} samples, using {len(datasets['sroie'])}"
                )
        else:
            print("  SROIE: ⚠️ Not downloaded - needs ICDAR 2019 SROIE")

        # === BORN-DIGITAL TABLES (reduced from 70% to 18%) ===

        # TableBank
        tablebank_path = (
            PROJECT_ROOT / "data/benchmarks/tablebank/TableBank/Detection/images"
        )
        if tablebank_path.exists():
            all_files = sorted(tablebank_path.glob("*.jpg"))
            target = self.config.COMPOSITION.get("tablebank", 0)
            if target > 0 and all_files:
                datasets["tablebank"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  TableBank: Found {len(all_files)} samples, using {len(datasets['tablebank'])}"
                )

        # PubTabNet
        pubtabnet_path = PROJECT_ROOT / "data/benchmarks/pubtabnet/pubtabnet/train"
        if pubtabnet_path.exists():
            all_files = sorted(pubtabnet_path.glob("*.png"))
            target = self.config.COMPOSITION.get("pubtabnet", 0)
            if target > 0 and all_files:
                datasets["pubtabnet"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  PubTabNet: Found {len(all_files)} samples, using {len(datasets['pubtabnet'])}"
                )

        # === MIXED LAYOUTS ===

        # DocLayNet - requires PDF->image conversion
        doclaynet_path = PROJECT_ROOT / "data/benchmarks/doclaynet/images"
        if doclaynet_path.exists():
            all_files = sorted(doclaynet_path.glob("*.png"))
            target = self.config.COMPOSITION.get("doclaynet", 0)
            if target > 0 and all_files:
                datasets["doclaynet"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  DocLayNet: Found {len(all_files)} samples, using {len(datasets['doclaynet'])}"
                )
        else:
            print("  DocLayNet: ⚠️ Needs PDF→image conversion")

        # === HANDWRITING ===

        # NIST SD19 - Handwriting in forms context
        nist_sd19_path = PROJECT_ROOT / "data/benchmarks/nist-sd19"
        if nist_sd19_path.exists():
            all_files = sorted(nist_sd19_path.glob("**/*.png"))
            target = self.config.COMPOSITION.get("nist_sd19", 0)
            if target > 0 and all_files:
                datasets["nist_sd19"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  NIST SD19: Found {len(all_files)} samples, using {len(datasets['nist_sd19'])}"
                )
        else:
            print("  NIST SD19: ⚠️ Not downloaded - needs NIST Special Database 19")

        # === MATH/FORMULAS ===

        # im2latex - Mathematical formulas
        im2latex_path = PROJECT_ROOT / "data/benchmarks/im2latex"
        if im2latex_path.exists():
            all_files = sorted(im2latex_path.glob("**/*.png"))
            target = self.config.COMPOSITION.get("im2latex", 0)
            if target > 0 and all_files:
                datasets["im2latex"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  im2latex: Found {len(all_files)} samples, using {len(datasets['im2latex'])}"
                )
        else:
            print("  im2latex: ⚠️ Not downloaded - needs im2latex-100k")

        # MathVerse - Math diagrams and equations
        mathverse_path = PROJECT_ROOT / "data/benchmarks/mathverse"
        if mathverse_path.exists():
            all_files = sorted(mathverse_path.glob("**/*.png")) + sorted(
                mathverse_path.glob("**/*.jpg")
            )
            target = self.config.COMPOSITION.get("mathverse", 0)
            if target > 0 and all_files:
                datasets["mathverse"] = random.sample(
                    all_files, min(target, len(all_files))
                )  # nosec B311
                print(
                    f"  MathVerse: Found {len(all_files)} samples, using {len(datasets['mathverse'])}"
                )
        else:
            print("  MathVerse: ⚠️ Not downloaded - use HuggingFace `MathVerse`")

        # === EDUCATIONAL CONTENT ===

        # Multimodal Textbook - Sample from educational video keyframes
        textbook_path = PROJECT_ROOT / "data/benchmarks/multimodal-textbook"
        if textbook_path.exists():
            all_files = sorted(textbook_path.glob("**/*.jpg")) + sorted(
                textbook_path.glob("**/*.png")
            )
            target = self.config.COMPOSITION.get("multimodal_textbook", 0)
            if target > 0 and all_files:
                datasets["multimodal_textbook"] = all_files[:target]
                print(
                    f"  Multimodal Textbook: Found {len(all_files)} samples, using {len(datasets['multimodal_textbook'])}"
                )
        else:
            print("  Multimodal Textbook: ⚠️ Sample not found")

        # === SUMMARY ===
        print("\n" + "=" * 60)
        print("LOADED DATASETS SUMMARY")
        print("=" * 60)
        total_loaded = 0
        for name, files in datasets.items():
            count = len(files)
            total_loaded += count
            target = self.config.COMPOSITION.get(name, 0)
            status = "✅" if count >= target * 0.9 else "⚠️"  # 90% threshold
            print(
                f"  {status} {name}: {count:,} / {target:,} ({count / target * 100:.0f}%)"
                if target > 0
                else f"  {name}: {count:,}"
            )

        print(
            f"\nTotal loaded: {total_loaded:,} / {self.config.TOTAL_SAMPLES:,} ({total_loaded / self.config.TOTAL_SAMPLES * 100:.1f}%)"
        )

        if total_loaded < self.config.TOTAL_SAMPLES * 0.5:
            print("\n⚠️  WARNING: Less than 50% of target samples available!")
            print("   Download missing datasets before generation.")

        return datasets

    def generate_dataset(self):
        """Generate complete 100K dataset."""
        print(f"\n{'=' * 80}")
        print("GENERATING 100K IQA TRAINING DATASET")
        print(f"{'=' * 80}\n")

        # Load source datasets
        source_datasets = self.load_source_datasets()

        # Generate samples
        sample_id = 0
        all_metadata = []

        for dataset_name, file_paths_or_tuples in source_datasets.items():
            print(f"\nProcessing {dataset_name}: {len(file_paths_or_tuples)} samples")

            for item in tqdm(file_paths_or_tuples, desc=dataset_name):
                try:
                    # Handle both file paths (Path objects) and HF dataset tuples
                    if isinstance(item, tuple):
                        # FUNSD+ format: (dataset, index)
                        dataset_obj, idx = item
                        # Extract image from HuggingFace Dataset
                        image = dataset_obj[idx]["image"]
                        # Generate augmented sample with image directly
                        sample_metadata = self.generate_sample(
                            image, dataset_name, sample_id, is_pil_image=True
                        )
                    else:
                        # Regular file path
                        sample_metadata = self.generate_sample(
                            item, dataset_name, sample_id, is_pil_image=False
                        )

                    all_metadata.append(sample_metadata)
                    sample_id += 1

                except Exception as e:
                    print(f"Error processing item from {dataset_name}: {e}")
                    continue

        # Save global metadata
        self.save_global_metadata(all_metadata)

        # Print final statistics
        self.print_statistics(sample_id)

    def generate_sample(
        self,
        source_path_or_image,
        dataset_name: str,
        sample_id: int,
        is_pil_image: bool = False,
    ) -> dict[str, Any]:
        """Generate single augmented sample with full metadata tracking.

        Args:
            source_path_or_image: Either a Path object (for regular datasets) or PIL Image (for HF datasets)
            dataset_name: Name of the source dataset
            sample_id: Unique sample identifier
            is_pil_image: True if source_path_or_image is already a PIL Image, False if it's a Path
        """
        # Load image and ensure RGB for augmentation
        if is_pil_image:
            # Already a PIL Image from HuggingFace Dataset
            image = source_path_or_image
        else:
            # Load from file path
            image = Image.open(source_path_or_image)

        if image.mode != "RGB":
            image = image.convert("RGB")

        # 1. DPI upsampling (if needed)
        image, target_dpi, current_dpi = self.apply_dpi_upsampling(image, dataset_name)

        # 2. Orientation (20% landscape, 5% square) - BEFORE augmentation
        orientation, image = self.apply_orientation(image)

        # 3. Combined defects (multi-defect augmentation) - Requires RGB
        num_defects = self.choose_num_defects()
        image_np = np.array(image)
        image_np, applied_defects = self.augmentor.apply_defects(image_np, num_defects)
        image = Image.fromarray(image_np)

        # 4. Color mode conversion (35% grayscale, 5% B&W) - AFTER augmentation
        color_mode, image = self.apply_color_conversion(image)

        # 5. JPEG quality (varying compression)
        jpeg_quality = self.choose_jpeg_quality()

        # 6. Save image
        output_filename = f"sample_{sample_id:06d}.jpg"
        output_path = self.output_dir / "images" / output_filename
        image.save(output_path, "JPEG", quality=jpeg_quality)

        # 7. Generate weak supervision labels (placeholder - implement actual detection)
        labels = self.generate_weak_supervision_labels(image_np, applied_defects)

        # 8. Track metadata
        # Determine source filename (Path object or HF dataset)
        source_filename = (
            str(source_path_or_image.name)
            if not is_pil_image
            else f"{dataset_name}_{sample_id}.png"
        )

        metadata = {
            "sample_id": sample_id,
            "filename": output_filename,
            "source_dataset": dataset_name,
            "source_file": source_filename,
            # Dimension tracking
            "color_mode": color_mode,
            "orientation": orientation,
            "dpi": target_dpi if target_dpi else current_dpi,
            "num_defects": num_defects,
            "applied_defects": applied_defects,
            "jpeg_quality": jpeg_quality,
            "layout_type": self.infer_layout_type(dataset_name),
            "text_density": "medium",  # Placeholder
            "background": "plain",  # Placeholder
            "language": "english",  # Placeholder
            "document_type": self.infer_document_type(dataset_name),
            "category": self.infer_category(dataset_name),
            # Labels
            "labels": labels,
        }

        # Update distribution tracking
        self.update_distributions(metadata)

        return metadata

    def apply_dpi_upsampling(
        self, image: Image.Image, dataset_name: str
    ) -> tuple[Image.Image, int | None, int]:
        """Apply DPI upsampling if needed."""
        dpi_strategy = self.config.DPI_STRATEGY.get(dataset_name)

        if dpi_strategy is None:
            return image, None, self.estimate_dpi(image)

        # Choose target DPI based on strategy
        target_dpi = random.choices(  # nosec B311
            [int(k) for k in dpi_strategy.keys()],
            weights=list(dpi_strategy.values()),
        )[0]

        current_dpi = self.estimate_dpi(image)

        if target_dpi > current_dpi:
            # Upsample
            scale_factor = target_dpi / current_dpi
            new_size = (
                int(image.size[0] * scale_factor),
                int(image.size[1] * scale_factor),
            )
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        return image, target_dpi, current_dpi

    def apply_color_conversion(self, image: Image.Image) -> tuple[str, Image.Image]:
        """Apply color mode conversion (35% grayscale, 5% B&W)."""
        rand = random.random()  # nosec B311

        if rand < 0.05:  # 5% B&W
            image = image.convert("1")
            return "1", image
        if rand < 0.40:  # 35% grayscale (0.05 + 0.35)
            image = image.convert("L")
            return "L", image
        # Remaining 60 percent stays RGB
        if image.mode != "RGB":
            image = image.convert("RGB")
        return "RGB", image

    def apply_orientation(self, image: Image.Image) -> tuple[str, Image.Image]:
        """Apply orientation transformation (20% landscape, 5% square)."""
        current_orientation = (
            "portrait" if image.size[0] < image.size[1] else "landscape"
        )

        rand = random.random()  # nosec B311

        if rand < 0.05:
            # Center crop to square
            min_side = min(image.size)
            left = (image.width - min_side) // 2
            top = (image.height - min_side) // 2
            image = image.crop((left, top, left + min_side, top + min_side))
            return "square", image

        if rand < 0.25 and current_orientation == "portrait":
            # Rotate to landscape
            image = image.rotate(90, expand=True)
            return "landscape", image

        return current_orientation, image

    def choose_num_defects(self) -> int:
        """Choose number of defects based on target distribution."""
        return random.choices([0, 1, 2, 3], weights=[0.20, 0.40, 0.25, 0.15])[0]  # nosec B311

    def choose_jpeg_quality(self) -> int:
        """Choose JPEG quality based on target distribution."""
        quality_ranges = {
            "high": (90, 100),
            "medium": (70, 89),
            "low": (50, 69),
            "very_low": (30, 49),
        }

        quality_level = random.choices(  # nosec B311
            list(quality_ranges.keys()), weights=[0.30, 0.40, 0.20, 0.10]
        )[0]

        return random.randint(*quality_ranges[quality_level])  # nosec B311

    def generate_weak_supervision_labels(
        self, _image: np.ndarray, applied_defects: list[str]
    ) -> dict[str, float]:
        """Generate weak supervision labels using classical IQA detectors.

        Args:
            _image: Input image (reserved for future classical IQA implementation)
            applied_defects: List of applied defect types
        """
        labels = {
            "blur": 1.0 if "blur" in applied_defects else 0.0,
            "noise": 1.0 if "noise" in applied_defects else 0.0,
            "skew": 1.0 if "skew" in applied_defects else 0.0,
            "illumination": 1.0 if "illumination" in applied_defects else 0.0,
            "artifacts": 1.0 if "artifacts" in applied_defects else 0.0,
        }

        return labels

    def estimate_dpi(self, image: Image.Image) -> int:
        """Estimate effective DPI."""
        # Assume portrait 8.5x11 page
        width_inches = 8.5 if image.size[0] <= image.size[1] else 11.0
        return int(image.size[0] / width_inches)

    def infer_layout_type(self, dataset_name: str) -> str:
        """Infer layout type from dataset."""
        layout_map = {
            # Real degradation anchors
            "diqa_5000_train": "single_column",
            "tobacco_800": random.choice(["single_column", "multi_column"]),  # nosec B311
            "dibco": "single_column",
            # Multi-category
            "rvl_cdip": random.choice(["single_column", "multi_column", "complex"]),  # nosec B311
            # Forms
            "nist_db2_sd6": "single_column",
            "funsd_plus": "single_column",
            # Mobile proxy
            "sroie": "single_column",
            # Tables
            "tablebank": "single_column",
            "pubtabnet": "single_column",
            # Mixed layouts
            "doclaynet": random.choice(["single_column", "multi_column", "complex"]),  # nosec B311
            # Handwriting
            "nist_sd19": "single_column",
            # Math
            "im2latex": "single_column",
            "mathverse": random.choice(["single_column", "complex"]),  # nosec B311
            # Educational
            "multimodal_textbook": random.choice(["single_column", "multi_column"]),  # nosec B311
        }
        return layout_map.get(dataset_name, "single_column")

    def infer_document_type(self, dataset_name: str) -> str:
        """Infer PDF document type (born_digital, image_only, hybrid)."""
        type_map = {
            # Real degradation anchors - all scanned
            "diqa_5000_train": "image_only",
            "tobacco_800": "image_only",
            "dibco": "image_only",
            # Multi-category - mixed
            "rvl_cdip": random.choice(["image_only", "hybrid"]),  # nosec B311
            # Forms - mostly scanned
            "nist_db2_sd6": "image_only",
            "funsd_plus": "image_only",
            # Mobile proxy - image capture
            "sroie": "image_only",
            # Tables - born digital
            "tablebank": "born_digital",
            "pubtabnet": "born_digital",
            # Mixed layouts
            "doclaynet": "hybrid",
            # Handwriting - scanned
            "nist_sd19": "image_only",
            # Math - born digital
            "im2latex": "born_digital",
            "mathverse": "born_digital",
            # Educational - video keyframes
            "multimodal_textbook": "image_only",
        }
        return type_map.get(dataset_name, "born_digital")

    def infer_category(self, dataset_name: str) -> str:
        """Infer document category."""
        category_map = {
            # Real degradation anchors
            "diqa_5000_train": "mixed_layout",
            "tobacco_800": "mixed_layout",
            "dibco": "mixed_layout",
            # Multi-category - diverse
            "rvl_cdip": random.choice(["scientific", "mixed_layout", "forms"]),  # nosec B311
            # Forms
            "nist_db2_sd6": "forms",
            "funsd_plus": "forms",
            # Mobile proxy
            "sroie": "forms",  # receipts are form-like
            # Tables
            "tablebank": "tables",
            "pubtabnet": "tables",
            # Mixed layouts
            "doclaynet": "mixed_layout",
            # Handwriting
            "nist_sd19": "handwriting",
            # Math
            "im2latex": "scientific",
            "mathverse": "scientific",
            # Educational
            "multimodal_textbook": "scientific",
        }
        return category_map.get(dataset_name, "mixed_layout")

    def update_distributions(self, metadata: dict[str, Any]):
        """Update distribution tracking."""
        self.actual_distributions["color_mode"][metadata["color_mode"]] += 1
        self.actual_distributions["orientation"][metadata["orientation"]] += 1
        self.actual_distributions["combined_defects"][metadata["num_defects"]] += 1
        # Additional dimensions tracked via metadata during generation

    def save_global_metadata(self, all_metadata: list[dict[str, Any]]):
        """Save global metadata file."""
        metadata_path = self.output_dir / "metadata.json"

        global_metadata = {
            "total_samples": len(all_metadata),
            "generation_timestamp": datetime.now().isoformat(),
            "config": {
                "composition": self.config.COMPOSITION,
                "target_distributions": self.config.DISTRIBUTIONS,
            },
            "actual_distributions": {
                k: dict(v) for k, v in self.actual_distributions.items()
            },
            "samples": all_metadata,
        }

        with open(metadata_path, "w") as f:
            json.dump(global_metadata, f, indent=2)

        print(f"\nMetadata saved to: {metadata_path}")

    def print_statistics(self, total_samples: int):
        """Print final dataset statistics."""
        print(f"\n{'=' * 80}")
        print("DATASET GENERATION COMPLETE")
        print(f"{'=' * 80}")
        print(f"Total samples generated: {total_samples:,}")
        print(f"Output directory: {self.output_dir}")
        print(f"Estimated size: ~{total_samples * 0.5 / 1000:.1f} GB")


def main():
    parser = argparse.ArgumentParser(description="Generate 25K IQA training dataset")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/training/iqa_phase2_25k",
        help="Output directory for dataset",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Generate dataset
    config = DatasetConfig()
    generator = DatasetGenerator(args.output_dir, config)
    generator.generate_dataset()


if __name__ == "__main__":
    main()
