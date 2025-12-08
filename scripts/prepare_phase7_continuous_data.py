#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Generate 150K IQA Training Dataset with Continuous Labels for Phase 7.

Follows Phase 2/3's proven 13-dimensional cross-sectional design, enhanced with
continuous detector-driven labels for better calibration (target ECE < 0.10).

8 Source Datasets:
- DIQA-5000 (5.5K): Real degraded scans
- TableBank (60K): Clean tables
- PubTabNet (60K): Scientific papers
- FUNSD+ (3K): Generic forms
- Voxel51 (700): Mobile receipts ⭐ NEW
- NIST DB2 (5.5K): Tax forms ⭐ NEW
- IAM (8K): Handwriting ⭐ NEW
- Kaggle (1.4K): Invoices ⭐ NEW

Usage:
    # Generate full 150K dataset
    python scripts/prepare_phase7_continuous_data.py \\
        --output-dir data/training/iqa_phase7_150k_continuous

    # Test on 1K subset
    python scripts/prepare_phase7_continuous_data.py \\
        --output-dir data/training/iqa_phase7_1k_test \\
        --max-samples 1000
"""

import argparse
import json
import random  # nosec B311
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

try:
    from datasets import load_dataset, load_from_disk
except ImportError:
    print("Error: datasets library not installed. Run: uv sync --extra ml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

try:
    import albumentations as A  # noqa: N812
except ImportError:
    print("Error: albumentations not installed. Run: uv sync --extra ml")
    sys.exit(1)

from weak_supervision_labeling_continuous import ContinuousWeakSupervisionLabeler

from image_preprocessing_detector.utils import get_logger

logger = get_logger(__name__)


class Phase7DatasetConfig:
    """Configuration for Phase 7 170K dataset with complete RAG coverage."""

    TOTAL_SAMPLES = 165_000

    COMPOSITION = {
        # Phase 7.1 Base (9 sources, 132.5K)
        "diqa_5000": 4_000,  # Use train/res + val/res - degraded only
        "tablebank": 52_500,  # Increased
        "pubtabnet": 52_500,  # Increased
        "funsd_plus": 3_000,
        "voxel51_receipts": 700,
        "nist_db2": 5_500,
        "invoices_kaggle": 1_400,
        "doclaynet": 15_400,  # Phase 9 element coverage (figures)

        # RAG Enhancements (4 working sources, 25K)
        "obelics": 0,  # Deferred - URL fetching complexity
        "multimodal_textbook": 5_000,  # Working via streaming with 'default' config
        "im2latex": 8_000,  # LaTeX formulas
        "mathverse": 2_000,  # Geometry diagrams
        "iam_handwriting": 5_000,  # Pure handwriting (path fixed)

        # Total: 157,500 + buffer → 165,000
    }

    AUGMENTATION_STRATEGY = {
        # Base sources
        "diqa_5000": {"clean": 1.0, "light": 0.0, "medium": 0.0, "heavy": 0.0},
        "tablebank": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "pubtabnet": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "funsd_plus": {"clean": 0.20, "light": 0.30, "medium": 0.35, "heavy": 0.15},
        "voxel51_receipts": {"clean": 0.70, "light": 0.20, "medium": 0.10, "heavy": 0.0},
        "nist_db2": {"clean": 0.50, "light": 0.30, "medium": 0.15, "heavy": 0.05},
        "invoices_kaggle": {"clean": 0.30, "light": 0.30, "medium": 0.30, "heavy": 0.10},
        "doclaynet": {"clean": 0.40, "light": 0.30, "medium": 0.20, "heavy": 0.10},
        # RAG enhancements
        "obelics": {"clean": 0.50, "light": 0.30, "medium": 0.15, "heavy": 0.05},
        "multimodal_textbook": {"clean": 0.60, "light": 0.25, "medium": 0.10, "heavy": 0.05},
        "im2latex": {"clean": 0.40, "light": 0.35, "medium": 0.20, "heavy": 0.05},
        "mathverse": {"clean": 0.70, "light": 0.20, "medium": 0.08, "heavy": 0.02},
        "iam_handwriting": {"clean": 0.60, "light": 0.30, "medium": 0.10, "heavy": 0.0},
    }

    DPI_STRATEGY = {
        # Base sources
        "diqa_5000": None,
        "tablebank": {"150": 0.50, "200": 0.30, "300": 0.20},
        "pubtabnet": {"150": 0.50, "200": 0.30, "300": 0.20},
        "funsd_plus": None,
        "voxel51_receipts": None,
        "nist_db2": None,
        "invoices_kaggle": None,
        "doclaynet": None,  # Already 150-300 DPI
        # RAG enhancements
        "obelics": None,  # Web images (variable DPI)
        "multimodal_textbook": None,  # Video keyframes
        "im2latex": None,  # Rendered formulas
        "mathverse": None,  # Rendered diagrams
        "iam_handwriting": None,  # Already 300 DPI
    }


class AugmentationPipeline:
    """Multi-dimensional augmentation (from Phase 2/3)."""

    def __init__(self):
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
                    A.GaussNoise(p=1.0),
                    A.ISONoise(color_shift=(0.01, 0.1), p=1.0),
                    A.MultiplicativeNoise(multiplier=(0.9, 1.1), p=1.0),
                ],
                p=1.0,
            ),
            "skew": A.Rotate(limit=15, border_mode=0, p=1.0),
            "illumination": A.OneOf(
                [
                    A.RandomBrightnessContrast(
                        brightness_limit=0.3, contrast_limit=0.3, p=1.0
                    ),
                    A.RandomGamma(gamma_limit=(50, 150), p=1.0),
                    A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=1.0),
                ],
                p=1.0,
            ),
            "artifacts": A.ImageCompression(quality_range=(10, 90), p=1.0),
        }

    def apply_defects(
        self, image: np.ndarray, num_defects: int
    ) -> tuple[np.ndarray, list[str]]:
        """Apply random defects."""
        if num_defects == 0:
            return image, []

        defect_pool = list(self.defect_transforms.keys())
        if num_defects > 1 and random.random() < 0.5:  # nosec B311
            defect_pool = [d for d in defect_pool if d != "artifacts"]

        applied_defects = random.sample(  # nosec B311
            defect_pool, min(num_defects, len(defect_pool))
        )

        for defect in applied_defects:
            transform = self.defect_transforms[defect]
            image = transform(image=image)["image"]

        return image, applied_defects


class Phase7DatasetGenerator:
    """Generate Phase 7 150K dataset."""

    def __init__(
        self,
        output_dir: Path,
        config: Phase7DatasetConfig,
        nfs_root: Path = Path("/mnt/unraid/image_detection"),
    ):
        self.output_dir = output_dir
        self.config = config
        self.nfs_root = nfs_root
        self.augmentor = AugmentationPipeline()
        self.labeler = ContinuousWeakSupervisionLabeler()
        self.actual_distributions = {
            key: defaultdict(int) for key in ["color_mode", "orientation", "combined_defects", "document_type", "category", "severity", "defect_type"]
        }
        self.setup_output_directories()

    def setup_output_directories(self):
        """Create output structure."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "samples_metadata").mkdir(exist_ok=True)

    def load_source_datasets(self) -> dict[str, list]:
        """Load 8 source datasets."""
        datasets = {}
        benchmarks = self.nfs_root / "benchmarks"
        training = self.nfs_root / "training"

        # 1. DIQA-5000 (degraded variants only - train/res + val/res)
        diqa_train_path = benchmarks / "diqa-5000/train/res"
        diqa_val_path = benchmarks / "diqa-5000/val/res"
        diqa_files = []
        if diqa_train_path.exists():
            diqa_files.extend(sorted(diqa_train_path.glob("*.jpg")))
        if diqa_val_path.exists():
            diqa_files.extend(sorted(diqa_val_path.glob("*.jpg")))

        if diqa_files:
            datasets["diqa_5000"] = diqa_files[: self.config.COMPOSITION["diqa_5000"]]
            logger.info(f"DIQA-5000: {len(datasets['diqa_5000'])} samples (degraded variants only)")

        # 2. TableBank (FIX PATH: capital T)
        tablebank_path = benchmarks / "tablebank/TableBank/Detection/images"
        if tablebank_path.exists():
            all_files = list(tablebank_path.glob("*.jpg"))
            datasets["tablebank"] = random.sample(  # nosec B311
                all_files, min(self.config.COMPOSITION["tablebank"], len(all_files))
            )
            logger.info(f"TableBank: {len(datasets['tablebank'])} samples")
        else:
            logger.warning(f"TableBank not found at {tablebank_path}")
            datasets["tablebank"] = []

        # 3. PubTabNet (FIX PATH: subdirectory)
        pubtabnet_path = benchmarks / "pubtabnet/pubtabnet/train"
        if pubtabnet_path.exists():
            all_files = list(pubtabnet_path.glob("*.png"))
            datasets["pubtabnet"] = random.sample(  # nosec B311
                all_files, min(self.config.COMPOSITION["pubtabnet"], len(all_files))
            )
            logger.info(f"PubTabNet: {len(datasets['pubtabnet'])} samples")
        else:
            logger.warning(f"PubTabNet not found at {pubtabnet_path}")
            datasets["pubtabnet"] = []

        # 4. FUNSD+
        funsd_path = benchmarks / "funsd_plus/train"
        if funsd_path.exists():
            try:
                funsd_dataset = load_from_disk(str(funsd_path))
                target = self.config.COMPOSITION["funsd_plus"]
                multiplier = max(1, target // len(funsd_dataset))
                all_indices = list(range(len(funsd_dataset))) * multiplier
                random.shuffle(all_indices)  # nosec B311
                datasets["funsd_plus"] = [
                    (funsd_dataset, idx) for idx in all_indices[:target]
                ]
                logger.info(f"FUNSD+: {len(datasets['funsd_plus'])} samples")
            except Exception as e:
                logger.error(f"FUNSD+ load error: {e}")
                datasets["funsd_plus"] = []

        # 5. Voxel51 Mobile Receipts ⭐
        voxel51_path = training / "mobile_receipts_voxel51/train"
        if voxel51_path.exists():
            try:
                voxel51_dataset = load_from_disk(str(voxel51_path))
                datasets["voxel51_receipts"] = [
                    (voxel51_dataset, idx)
                    for idx in range(
                        min(len(voxel51_dataset), self.config.COMPOSITION["voxel51_receipts"])
                    )
                ]
                logger.info(f"Voxel51: {len(datasets['voxel51_receipts'])} samples")
            except Exception as e:
                logger.error(f"Voxel51 load error: {e}")
                datasets["voxel51_receipts"] = []

        # 6. NIST DB2 ⭐
        nist_path = training / "nist_db2/data"
        if nist_path.exists():
            all_files = list(nist_path.rglob("*.png"))
            datasets["nist_db2"] = random.sample(  # nosec B311
                all_files, min(self.config.COMPOSITION["nist_db2"], len(all_files))
            )
            logger.info(f"NIST DB2: {len(datasets['nist_db2'])} samples")

        # 7. Kaggle Invoices ⭐
        kaggle_path = training / "invoices_kaggle"
        if kaggle_path.exists():
            all_files = list(kaggle_path.rglob("*.jpg"))
            datasets["invoices_kaggle"] = random.sample(  # nosec B311
                all_files, min(self.config.COMPOSITION["invoices_kaggle"], len(all_files))
            )
            logger.info(f"Kaggle Invoices: {len(datasets['invoices_kaggle'])} samples")
        else:
            datasets["invoices_kaggle"] = []

        # 8. DocLayNet (Phase 9 element coverage - figures) ⭐
        doclaynet_path = benchmarks / "doclaynet/documents/png"
        if doclaynet_path.exists():
            all_files = list(doclaynet_path.glob("*.png"))
            datasets["doclaynet"] = random.sample(  # nosec B311
                all_files, min(self.config.COMPOSITION["doclaynet"], len(all_files))
            )
            logger.info(f"DocLayNet: {len(datasets['doclaynet'])} samples (Phase 9 prep)")
        else:
            logger.warning(f"DocLayNet not found at {doclaynet_path}")
            datasets["doclaynet"] = []

        # 9. OBELICS (streaming - images-in-text) ⭐ RAG
        if self.config.COMPOSITION.get("obelics", 0) > 0:
            try:
                logger.info(f"Loading OBELICS via streaming ({self.config.COMPOSITION['obelics']} samples)...")
                obelics = load_dataset("HuggingFaceM4/OBELICS", split="train", streaming=True)
                obelics_samples = []
                for idx, row in enumerate(obelics.shuffle(seed=42).take(self.config.COMPOSITION["obelics"])):
                    obelics_samples.append((row, idx))
                datasets["obelics"] = obelics_samples
                logger.info(f"OBELICS: {len(datasets['obelics'])} samples")
            except Exception as e:
                logger.error(f"OBELICS load error: {e}")
                datasets["obelics"] = []

        # 10. Multimodal Textbook (JSON format - educational diagrams) ⭐ RAG
        if self.config.COMPOSITION.get("multimodal_textbook", 0) > 0:
            try:
                logger.info(f"Loading Multimodal Textbook ({self.config.COMPOSITION['multimodal_textbook']} samples)...")
                # Use 'default' config to load JSON format (not WebDataset TAR)
                textbook = load_dataset("DAMO-NLP-SG/multimodal_textbook", "default", split="train", streaming=True)
                textbook_samples = []
                for idx, row in enumerate(textbook.shuffle(seed=42).take(self.config.COMPOSITION["multimodal_textbook"])):
                    textbook_samples.append((row, idx))
                datasets["multimodal_textbook"] = textbook_samples
                logger.info(f"Textbook: {len(datasets['multimodal_textbook'])} samples")
            except Exception as e:
                logger.error(f"Textbook load error: {e}")
                datasets["multimodal_textbook"] = []
        else:
            datasets["multimodal_textbook"] = []

        # 11. im2latex-100K (LaTeX formulas) ⭐ RAG
        im2latex_path = training / "im2latex_100k"
        if im2latex_path.exists() and self.config.COMPOSITION.get("im2latex", 0) > 0:
            try:
                im2latex_dataset = load_dataset("yuntian-deng/im2latex-100k", cache_dir=str(im2latex_path), split="train")
                target = self.config.COMPOSITION["im2latex"]
                sampled_indices = random.sample(range(len(im2latex_dataset)), min(target, len(im2latex_dataset)))
                datasets["im2latex"] = [(im2latex_dataset, idx) for idx in sampled_indices]
                logger.info(f"im2latex: {len(datasets['im2latex'])} samples")
            except Exception as e:
                logger.error(f"im2latex load error: {e}")
                datasets["im2latex"] = []

        # 12. MathVerse (geometry diagrams) ⭐ RAG
        mathverse_path = training / "mathverse"
        if mathverse_path.exists() and self.config.COMPOSITION.get("mathverse", 0) > 0:
            try:
                mathverse_dataset = load_dataset("AI4Math/MathVerse", "testmini", cache_dir=str(mathverse_path), split="testmini")
                target = self.config.COMPOSITION["mathverse"]
                datasets["mathverse"] = [(mathverse_dataset, idx) for idx in range(min(len(mathverse_dataset), target))]
                logger.info(f"MathVerse: {len(datasets['mathverse'])} samples")
            except Exception as e:
                logger.error(f"MathVerse load error: {e}")
                datasets["mathverse"] = []

        # 13. IAM Handwriting (IMPLEMENT - was deferred) ⭐ RAG
        iam_path = training / "iam_handwriting"
        if iam_path.exists() and self.config.COMPOSITION.get("iam_handwriting", 0) > 0:
            try:
                logger.info(f"Loading IAM Handwriting ({self.config.COMPOSITION['iam_handwriting']} samples)...")
                # Load train.parquet directly (single file, not glob pattern)
                iam_dataset = load_dataset("parquet", data_files=str(iam_path / "data/train.parquet"), split="train")
                target = self.config.COMPOSITION["iam_handwriting"]
                datasets["iam_handwriting"] = [(iam_dataset, idx) for idx in range(min(len(iam_dataset), target))]
                logger.info(f"IAM: {len(datasets['iam_handwriting'])} samples")
            except Exception as e:
                logger.error(f"IAM load error: {e}")
                datasets["iam_handwriting"] = []

        total_loaded = sum(len(v) for v in datasets.values())
        logger.info(f"Total loaded: {total_loaded:,}")

        return datasets

    def generate_dataset(self):
        """Generate 170K dataset with complete RAG coverage."""
        print(f"\n{'=' * 80}")
        print("PHASE 7: 170K CONTINUOUS-LABEL IQA DATASET")
        print("Complete RAG Coverage: Formulas + Textbooks + Images-in-Text")
        print(f"{'=' * 80}\n")

        source_datasets = self.load_source_datasets()

        sample_id = 0
        all_metadata = []

        for dataset_name, items in source_datasets.items():
            if not items:
                continue

            print(f"\nProcessing {dataset_name}: {len(items)} samples")

            for idx, item in enumerate(tqdm(items, desc=dataset_name)):
                try:
                    sample_metadata = self.generate_sample(item, dataset_name, sample_id)
                    all_metadata.append(sample_metadata)
                    sample_id += 1
                except Exception as e:
                    logger.error(f"Error in {dataset_name} sample {idx}: {e}", exc_info=True)
                    continue

        self.save_global_metadata(all_metadata)
        self.create_splits(all_metadata)
        self.print_statistics(sample_id, all_metadata)

    def generate_sample(
        self, source_item, dataset_name: str, sample_id: int
    ) -> dict[str, Any]:
        """Generate sample with augmentation + continuous labeling."""
        # Load image
        if isinstance(source_item, tuple):
            dataset_obj, idx = source_item
            image = dataset_obj[idx]["image"]
            if not isinstance(image, Image.Image):
                image = Image.fromarray(image)
        else:
            image = Image.open(source_item)

        if image.mode != "RGB":
            image = image.convert("RGB")

        # DPI upsampling
        image, target_dpi, current_dpi = self.apply_dpi_upsampling(image, dataset_name)

        # Orientation
        orientation, image = self.apply_orientation(image)

        # Augmentation
        aug_level = self.choose_augmentation_level(dataset_name)
        num_defects = self.choose_num_defects(aug_level)
        image_np = np.array(image)
        image_np, applied_defects = self.augmentor.apply_defects(image_np, num_defects)

        # Color conversion
        color_mode, image_np = self.apply_color_conversion(image_np)

        # JPEG quality
        jpeg_quality = self.choose_jpeg_quality()

        # Save image
        output_filename = f"sample_{sample_id:06d}.jpg"
        output_path = self.output_dir / "images" / output_filename

        if len(image_np.shape) == 2:  # Grayscale
            Image.fromarray(image_np, mode="L").save(
                output_path, "JPEG", quality=jpeg_quality
            )
        else:
            Image.fromarray(image_np).save(output_path, "JPEG", quality=jpeg_quality)

        # Generate continuous labels ⭐ PHASE 7 NEW
        image_bgr = (
            cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            if len(image_np.shape) == 3
            else image_np
        )
        temp_path = self.output_dir / "images" / f"_temp_{sample_id}.jpg"
        cv2.imwrite(str(temp_path), image_bgr)

        continuous_result = self.labeler.label_image(temp_path)
        temp_path.unlink()

        # Validate correspondence
        self.validate_correspondence(applied_defects, continuous_result["continuous_scores"])

        # Build metadata
        source_filename = (
            str(source_item.name)
            if isinstance(source_item, Path)
            else f"{dataset_name}_{sample_id}"
        )

        metadata = {
            "sample_id": sample_id,
            "filename": output_filename,
            "source_dataset": dataset_name,
            "source_file": source_filename,
            "color_mode": color_mode,
            "orientation": orientation,
            "dpi": target_dpi if target_dpi else current_dpi,
            "num_defects": num_defects,
            "applied_defects": applied_defects,
            "jpeg_quality": jpeg_quality,
            "layout_type": self.infer_layout_type(dataset_name),
            "text_density": self.infer_text_density(dataset_name),
            "background": "plain",
            "language": "english",
            "document_type": self.infer_document_type(dataset_name),
            "category": self.infer_category(dataset_name),
            "severity": self.infer_severity(num_defects),
            "continuous_scores": continuous_result["continuous_scores"],
            "detector_confidences": continuous_result["detector_confidences"],
            "sample_weight": continuous_result["sample_weight"],
            "smoothing_applied": continuous_result["smoothing_applied"],
            "augmentation_level": aug_level,
            # Phase 9 forward compatibility
            "element_types": self.infer_element_types(dataset_name),
        }

        self.update_distributions(metadata)

        # Save per-sample metadata
        sample_meta_path = (
            self.output_dir / "samples_metadata" / f"sample_{sample_id:06d}.json"
        )
        with open(sample_meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def choose_augmentation_level(self, dataset_name: str) -> str:
        """Choose augmentation level."""
        strategy = self.config.AUGMENTATION_STRATEGY.get(dataset_name, {"clean": 1.0})
        levels = list(strategy.keys())
        weights = list(strategy.values())
        return random.choices(levels, weights=weights)[0]  # nosec B311

    def choose_num_defects(self, augmentation_level: str) -> int:
        """Choose number of defects."""
        defect_map = {
            "clean": 0,
            "light": random.choices([0, 1], weights=[0.3, 0.7])[0],  # nosec B311
            "medium": random.choices([1, 2], weights=[0.6, 0.4])[0],  # nosec B311
            "heavy": random.choices([2, 3], weights=[0.5, 0.5])[0],  # nosec B311
        }
        return defect_map.get(augmentation_level, 1)

    def apply_dpi_upsampling(
        self, image: Image.Image, dataset_name: str
    ) -> tuple[Image.Image, int | None, int]:
        """Apply DPI upsampling if needed."""
        dpi_strategy = self.config.DPI_STRATEGY.get(dataset_name)
        if dpi_strategy is None:
            return image, None, self.estimate_dpi(image)

        target_dpi = random.choices(  # nosec B311
            [int(k) for k in dpi_strategy.keys()], weights=list(dpi_strategy.values())
        )[0]
        current_dpi = self.estimate_dpi(image)

        if target_dpi > current_dpi:
            scale_factor = target_dpi / current_dpi
            new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        return image, target_dpi, current_dpi

    def apply_orientation(self, image: Image.Image) -> tuple[str, Image.Image]:
        """Apply orientation transformation."""
        current = "portrait" if image.size[0] < image.size[1] else "landscape"
        rand = random.random()  # nosec B311

        if rand < 0.05:
            min_side = min(image.size)
            left = (image.width - min_side) // 2
            top = (image.height - min_side) // 2
            image = image.crop((left, top, left + min_side, top + min_side))
            return "square", image

        if rand < 0.25 and current == "portrait":
            image = image.rotate(90, expand=True)
            return "landscape", image

        return current, image

    def apply_color_conversion(self, image_np: np.ndarray) -> tuple[str, np.ndarray]:
        """Apply color mode conversion."""
        rand = random.random()  # nosec B311

        if rand < 0.05:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            _, bw = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            return "1", bw

        if rand < 0.40:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            return "L", gray

        return "RGB", image_np

    def choose_jpeg_quality(self) -> int:
        """Choose JPEG quality."""
        quality_ranges = {"high": (90, 100), "medium": (70, 89), "low": (50, 69), "very_low": (30, 49)}
        level = random.choices(list(quality_ranges.keys()), weights=[0.30, 0.40, 0.20, 0.10])[0]  # nosec B311
        return random.randint(*quality_ranges[level])  # nosec B311

    def validate_correspondence(self, applied_defects: list[str], continuous_scores: dict[str, float]):
        """Validate augmentation-label correspondence."""
        for defect in applied_defects:
            score = continuous_scores.get(defect, 1.0)
            if score > 0.7:
                logger.warning(
                    f"Mismatch: applied {defect} but score={score:.2f} (expected <0.7)"
                )

    def estimate_dpi(self, image: Image.Image) -> int:
        """Estimate DPI."""
        width_inches = 8.5 if image.size[0] <= image.size[1] else 11.0
        return int(image.size[0] / width_inches)

    def infer_layout_type(self, dataset_name: str) -> str:
        """Infer layout type."""
        return "single_column"

    def infer_text_density(self, dataset_name: str) -> str:
        """Infer text density."""
        density_map = {
            # Base sources
            "diqa_5000": "medium",
            "tablebank": "sparse",
            "pubtabnet": "medium",
            "funsd_plus": "sparse",
            "voxel51_receipts": "dense",
            "nist_db2": "sparse",
            "invoices_kaggle": "medium",
            "doclaynet": "medium",  # Mix of layouts
            # RAG enhancements
            "obelics": "medium",  # Web articles
            "multimodal_textbook": "sparse",  # Educational slides
            "im2latex": "none",  # Pure formulas
            "mathverse": "sparse",  # Diagrams with minimal text
            "iam_handwriting": "dense",
        }
        return density_map.get(dataset_name, "medium")

    def infer_element_types(self, dataset_name: str) -> list[str]:
        """Infer element types for Phase 9 forward compatibility."""
        element_map = {
            # Base sources
            "diqa_5000": ["text"],
            "tablebank": ["table"],
            "pubtabnet": ["table", "formula"],  # Scientific papers
            "funsd_plus": ["form", "handwriting"],
            "voxel51_receipts": ["text"],
            "nist_db2": ["table", "form"],
            "invoices_kaggle": ["table", "text"],
            "doclaynet": ["table", "figure", "text", "formula"],  # All 11 classes
            # RAG enhancements
            "obelics": ["embedded_image", "figure_in_context"],
            "multimodal_textbook": ["diagram", "formula_on_slide", "educational_figure"],
            "im2latex": ["formula", "equation", "mathematical_notation"],
            "mathverse": ["geometry_diagram", "annotated_figure"],
            "iam_handwriting": ["handwriting"],
        }
        return element_map.get(dataset_name, ["text"])

    def infer_document_type(self, dataset_name: str) -> str:
        """Infer document type."""
        type_map = {
            # Base sources
            "diqa_5000": "image_only",
            "tablebank": "born_digital",
            "pubtabnet": "born_digital",
            "funsd_plus": "image_only",
            "voxel51_receipts": "mobile",
            "nist_db2": "image_only",
            "invoices_kaggle": "born_digital",
            "doclaynet": "hybrid",  # Mix of born-digital and scanned
            # RAG enhancements
            "obelics": "born_digital",  # Web content
            "multimodal_textbook": "image_only",  # Video keyframes
            "im2latex": "born_digital",  # Rendered LaTeX
            "mathverse": "born_digital",  # Rendered diagrams
            "iam_handwriting": "image_only",
        }
        return type_map.get(dataset_name, "born_digital")

    def infer_category(self, dataset_name: str) -> str:
        """Infer category."""
        category_map = {
            # Base sources
            "diqa_5000": "mixed_layout",
            "tablebank": "tables",
            "pubtabnet": "scientific",
            "funsd_plus": "forms",
            "voxel51_receipts": "receipts",
            "nist_db2": "forms",
            "invoices_kaggle": "invoices",
            "doclaynet": "mixed_layout",  # Has all 11 DocLayNet element classes
            # RAG enhancements
            "obelics": "web_document",
            "multimodal_textbook": "educational",
            "im2latex": "scientific",
            "mathverse": "educational",
            "iam_handwriting": "handwriting",
        }
        return category_map.get(dataset_name, "mixed_layout")

    def infer_severity(self, num_defects: int) -> str:
        """Infer severity from defect count."""
        if num_defects == 0:
            return "mild"
        elif num_defects == 1:
            return random.choice(["mild", "moderate"])  # nosec B311
        elif num_defects == 2:
            return random.choice(["moderate", "severe"])  # nosec B311
        else:
            return "severe"

    def update_distributions(self, metadata: dict[str, Any]):
        """Update distribution tracking."""
        self.actual_distributions["color_mode"][metadata["color_mode"]] += 1
        self.actual_distributions["orientation"][metadata["orientation"]] += 1
        self.actual_distributions["combined_defects"][metadata["num_defects"]] += 1
        self.actual_distributions["document_type"][metadata["document_type"]] += 1
        self.actual_distributions["category"][metadata["category"]] += 1
        self.actual_distributions["severity"][metadata["severity"]] += 1

        for defect in metadata["applied_defects"]:
            self.actual_distributions["defect_type"][defect] += 1

    def create_splits(self, all_metadata: list[dict[str, Any]]):
        """Create 70/15/15 splits."""
        random.shuffle(all_metadata)  # nosec B311

        n_total = len(all_metadata)
        n_train = int(n_total * 0.70)
        n_val = int(n_total * 0.15)

        train_meta = all_metadata[:n_train]
        val_meta = all_metadata[n_train : n_train + n_val]
        test_meta = all_metadata[n_train + n_val :]

        for split_name, split_meta in [
            ("train", train_meta),
            ("val", val_meta),
            ("test", test_meta),
        ]:
            split_file = self.output_dir / f"{split_name}_metadata.json"
            with open(split_file, "w") as f:
                json.dump(split_meta, f, indent=2)
            logger.info(f"{split_name}: {len(split_meta)} samples")

    def save_global_metadata(self, all_metadata: list[dict[str, Any]]):
        """Save global metadata."""
        continuous_stats = {}
        for detector in ["blur", "contrast", "skew", "noise", "illumination", "compression", "binarization", "bleed_through"]:
            scores = [m["continuous_scores"][detector] for m in all_metadata]
            continuous_stats[detector] = {
                "mean": float(np.mean(scores)),
                "std": float(np.std(scores)),
                "min": float(np.min(scores)),
                "max": float(np.max(scores)),
            }

        weights = [m["sample_weight"] for m in all_metadata]

        metadata_path = self.output_dir / "metadata.json"
        global_metadata = {
            "total_samples": len(all_metadata),
            "generation_timestamp": datetime.now().isoformat(),
            "phase": "phase7_continuous",
            "config": {
                "composition": self.config.COMPOSITION,
                "augmentation_strategy": self.config.AUGMENTATION_STRATEGY,
            },
            "actual_distributions": {k: dict(v) for k, v in self.actual_distributions.items()},
            "continuous_label_stats": continuous_stats,
            "sample_weight_stats": {
                "mean": float(np.mean(weights)),
                "std": float(np.std(weights)),
                "min": float(np.min(weights)),
                "max": float(np.max(weights)),
            },
        }

        with open(metadata_path, "w") as f:
            json.dump(global_metadata, f, indent=2)

        logger.info(f"Metadata saved: {metadata_path}")

    def print_statistics(self, total_samples: int, all_metadata: list[dict[str, Any]]):
        """Print statistics."""
        print(f"\n{'=' * 80}")
        print("GENERATION COMPLETE")
        print(f"{'=' * 80}")
        print(f"Total: {total_samples:,}")
        print(f"Size: ~{total_samples * 0.17 / 1000:.1f} GB")

        print("\n=== Distributions ===")
        for dim, values in self.actual_distributions.items():
            if values:
                print(f"\n{dim}:")
                for k, v in sorted(values.items(), key=lambda x: -x[1])[:5]:
                    k_str = str(k)
                    print(f"  {k_str:20s}: {v:6d} ({v/total_samples*100:5.1f}%)")

        print("\n=== Continuous Scores (sample) ===")
        sample_scores = all_metadata[0]["continuous_scores"]
        for detector, score in list(sample_scores.items())[:4]:
            print(f"  {detector:15s}: {score:.3f}")

        print("\n=== Next Steps ===")
        print("1. Validate: python scripts/validate_phase7_dataset.py")
        print(f"2. Upload: gsutil -m rsync -r {self.output_dir} gs://image_detection_b/training/iqa_phase7_150k_continuous/")
        print(f"{'=' * 80}\n")


def main():
    parser = argparse.ArgumentParser(description="Generate Phase 7 150K dataset")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data/training/iqa_phase7_150k_continuous",
        help="Output directory",
    )
    parser.add_argument(
        "--nfs-root",
        type=Path,
        default=Path("/mnt/unraid/image_detection"),
        help="NFS root path",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-samples", type=int, help="Override for testing")

    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    config = Phase7DatasetConfig()
    if args.max_samples:
        scale = args.max_samples / config.TOTAL_SAMPLES
        config.COMPOSITION = {k: max(1, int(v * scale)) for k, v in config.COMPOSITION.items()}
        config.TOTAL_SAMPLES = args.max_samples

    generator = Phase7DatasetGenerator(args.output_dir, config, args.nfs_root)
    generator.generate_dataset()


if __name__ == "__main__":
    main()
