"""Synthetic IQA dataset adapter for controlled quality assessment testing.

Generates synthetic images with known quality degradations for testing:
- Blur (Gaussian, motion, defocus)
- Skew (rotation angles)
- Noise (Gaussian, salt-and-pepper)
- Contrast (low contrast, high contrast)
- Binarization (synthetic text for thresholding tests)

"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from benchmarks.adapters.base import BaseAdapter, DatasetRegistry, PageSample


@dataclass
class SyntheticParams:
    """Parameters for synthetic image generation."""

    # Image dimensions
    width: int = 1200
    height: int = 1600
    dpi: int = 300

    # Reproducibility
    seed: int = 42  # Random seed for reproducible benchmark generation

    # Quality degradation ranges
    blur_sigmas: list[float] | None = None  # Gaussian blur sigma values
    skew_angles: list[float] | None = None  # Rotation angles in degrees
    noise_levels: list[float] | None = None  # Noise standard deviations
    contrast_factors: list[float] | None = None  # Contrast reduction factors

    def __post_init__(self) -> None:
        """Set default ranges if not provided."""
        if self.blur_sigmas is None:
            # Range from sharp (0.0) to very blurry (5.0)
            self.blur_sigmas = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

        if self.skew_angles is None:
            # Range from -5° to +5° in 0.5° increments
            self.skew_angles = [
                -5.0,
                -4.0,
                -3.0,
                -2.0,
                -1.0,
                -0.5,
                0.0,
                0.5,
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
            ]

        if self.noise_levels is None:
            # Noise standard deviations (0 = no noise)
            self.noise_levels = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]

        if self.contrast_factors is None:
            # Contrast factors (1.0 = normal, <1.0 = reduced)
            self.contrast_factors = [0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5]


@DatasetRegistry.register("synthetic_iqa")
class SyntheticIQAAdapter(BaseAdapter):
    """Adapter for synthetic IQA test images.

    Generates images with controlled quality degradations for benchmarking
    IQA metrics against ground truth.
    """

    def __init__(
        self,
        data_dir: Path,
        split: str = "test",
        cache_dir: Path | None = None,
        download: bool = False,
        subset: str = "blur",  # blur, skew, noise, contrast, binarization
        regenerate: bool = False,
    ) -> None:
        """Initialize synthetic IQA adapter.

        Args:
            data_dir: Directory to store/cache generated images
            split: Dataset split (only 'test' supported)
            cache_dir: Cache directory (same as data_dir for synthetic)
            download: Ignored (always generates locally)
            subset: Type of quality degradation to generate
            regenerate: Force regeneration even if cached
        """
        self.subset = subset
        self.regenerate = regenerate
        self.params = SyntheticParams()

        # Create data directory if downloading/generating
        if download or regenerate:
            Path(data_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(data_dir, split, cache_dir, download=download)

        # Create output directory
        self.output_dir = self.data_dir / "synthetic_iqa" / self.subset
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate or load samples
        self._load_or_generate()

    def _load_or_generate(self) -> None:
        """Load cached samples or generate new ones."""
        manifest_path = self.output_dir / "manifest.json"

        if manifest_path.exists() and not self.regenerate:
            # Load existing manifest
            with open(manifest_path) as f:
                manifest = json.load(f)
            self._sample_ids = manifest["sample_ids"]
            self._manifest = manifest
        else:
            # Generate new samples
            self._generate_samples()
            self._save_manifest()

    def _generate_samples(self) -> None:
        """Generate synthetic images based on subset type."""
        self._sample_ids = []
        self._manifest = {
            "subset": self.subset,
            "params": self.params.__dict__,
            "samples": [],
        }

        if self.subset == "blur":
            self._generate_blur_samples()
        elif self.subset == "skew":
            self._generate_skew_samples()
        elif self.subset == "noise":
            self._generate_noise_samples()
        elif self.subset == "contrast":
            self._generate_contrast_samples()
        elif self.subset == "binarization":
            self._generate_binarization_samples()
        else:
            raise ValueError(f"Unknown subset: {self.subset}")

    def _generate_blur_samples(self) -> None:
        """Generate images with varying blur levels."""
        from scipy.ndimage import gaussian_filter

        for _i, sigma in enumerate(self.params.blur_sigmas):
            sample_id = f"blur_sigma_{sigma:.2f}"
            image_path = self.output_dir / f"{sample_id}.png"

            # Create base image (sharp text)
            base_image = self._create_text_image()
            img_array = np.array(base_image)

            # Apply Gaussian blur
            if sigma > 0:
                img_array = gaussian_filter(img_array, sigma=sigma)

            # Save
            blurred_image = Image.fromarray(img_array.astype(np.uint8))
            blurred_image.save(image_path)

            # Record metadata
            self._sample_ids.append(sample_id)
            self._manifest["samples"].append(
                {
                    "sample_id": sample_id,
                    "image_path": str(image_path),
                    "ground_truth": {
                        "blur_sigma": sigma,
                        "blur_level": self._sigma_to_blur_level(sigma),
                    },
                }
            )

    def _generate_skew_samples(self) -> None:
        """Generate images with varying skew angles."""
        for angle in self.params.skew_angles:
            sample_id = f"skew_angle_{angle:+.2f}"
            image_path = self.output_dir / f"{sample_id}.png"

            # Create base image
            base_image = self._create_text_image()

            # Apply rotation
            rotated = base_image.rotate(
                angle, resample=Image.BICUBIC, expand=True, fillcolor=255
            )

            # Save
            rotated.save(image_path)

            # Record metadata
            self._sample_ids.append(sample_id)
            self._manifest["samples"].append(
                {
                    "sample_id": sample_id,
                    "image_path": str(image_path),
                    "ground_truth": {
                        "skew_angle": angle,
                    },
                }
            )

    def _generate_noise_samples(self) -> None:
        """Generate images with varying noise levels."""
        for noise_level in self.params.noise_levels:
            sample_id = f"noise_level_{noise_level:.3f}"
            image_path = self.output_dir / f"{sample_id}.png"

            # Create base image
            base_image = self._create_text_image()
            img_array = np.array(base_image, dtype=np.float32) / 255.0

            # Add Gaussian noise using modern Generator API with seed for reproducibility
            if noise_level > 0:
                rng = np.random.default_rng(seed=self.params.seed)
                noise = rng.normal(0, noise_level, img_array.shape)
                img_array = np.clip(img_array + noise, 0, 1)

            # Convert back to uint8
            noisy_image = Image.fromarray((img_array * 255).astype(np.uint8))
            noisy_image.save(image_path)

            # Calculate ground truth SNR (before adding noise)
            signal_power = np.mean(img_array**2)
            noise_power = noise_level**2
            snr_db = (
                10 * np.log10(signal_power / noise_power)
                if noise_level > 0
                else float("inf")
            )

            # Record metadata
            self._sample_ids.append(sample_id)
            self._manifest["samples"].append(
                {
                    "sample_id": sample_id,
                    "image_path": str(image_path),
                    "ground_truth": {
                        "noise_level": noise_level,
                        "snr_db": snr_db,
                    },
                }
            )

    def _generate_contrast_samples(self) -> None:
        """Generate images with varying contrast levels."""
        for contrast_factor in self.params.contrast_factors:
            sample_id = f"contrast_factor_{contrast_factor:.2f}"
            image_path = self.output_dir / f"{sample_id}.png"

            # Create base image
            base_image = self._create_text_image()
            img_array = np.array(base_image, dtype=np.float32) / 255.0

            # Adjust contrast (around mean)
            mean = np.mean(img_array)
            img_array = mean + contrast_factor * (img_array - mean)
            img_array = np.clip(img_array, 0, 1)

            # Convert back to uint8
            contrast_image = Image.fromarray((img_array * 255).astype(np.uint8))
            contrast_image.save(image_path)

            # Record metadata
            self._sample_ids.append(sample_id)
            self._manifest["samples"].append(
                {
                    "sample_id": sample_id,
                    "image_path": str(image_path),
                    "ground_truth": {
                        "contrast_factor": contrast_factor,
                    },
                }
            )

    def _generate_binarization_samples(self) -> None:
        """Generate images for binarization testing."""
        # Generate samples with varying text/background contrasts
        for _i, threshold in enumerate(range(50, 200, 25)):
            sample_id = f"binarization_threshold_{threshold}"
            image_path = self.output_dir / f"{sample_id}.png"

            # Create grayscale image with specific threshold
            base_image = self._create_text_image(text_color=threshold)
            base_image.save(image_path)

            # Record metadata
            self._sample_ids.append(sample_id)
            self._manifest["samples"].append(
                {
                    "sample_id": sample_id,
                    "image_path": str(image_path),
                    "ground_truth": {
                        "optimal_threshold": (threshold + 255) // 2,
                        "text_intensity": threshold,
                    },
                }
            )

    def _create_text_image(self, text_color: int = 0) -> Image.Image:
        """Create a base text image for testing.

        Args:
            text_color: Grayscale value for text (0=black, 255=white)

        Returns:
            PIL Image with synthetic text
        """
        # Create white background
        img = Image.new("L", (self.params.width, self.params.height), color=255)
        draw = ImageDraw.Draw(img)

        # Add sample text at various sizes
        texts = [
            ("Document Quality Assessment", 48),
            ("This is a synthetic test image for", 32),
            ("evaluating image quality metrics.", 32),
            ("Blur • Skew • Noise • Contrast", 28),
            ("Small text for detail testing", 18),
        ]

        y_offset = 200
        for text, size in texts:
            try:
                # Try to use a standard font
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
                )
            except OSError:
                # Fallback to default font
                font = ImageFont.load_default()

            # Center the text
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.params.width - text_width) // 2

            draw.text((x, y_offset), text, fill=text_color, font=font)
            y_offset += size + 30

        return img

    def _sigma_to_blur_level(self, sigma: float) -> str:
        """Convert sigma to qualitative blur level."""
        if sigma < 0.5:
            return "sharp"
        if sigma < 1.5:
            return "slight_blur"
        if sigma < 2.5:
            return "moderate_blur"
        if sigma < 4.0:
            return "heavy_blur"
        return "severe_blur"

    def _save_manifest(self) -> None:
        """Save manifest to disk."""
        manifest_path = self.output_dir / "manifest.json"
        self._manifest["sample_ids"] = self._sample_ids
        with open(manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    def __iter__(self) -> Iterator[PageSample]:
        """Iterate over synthetic samples."""
        for sample_id in self._sample_ids:
            yield self.get_sample(sample_id)

    def __len__(self) -> int:
        """Return number of samples."""
        return len(self._sample_ids)

    def get_sample(self, sample_id: str) -> PageSample:
        """Get a specific sample by ID."""
        # Find sample in manifest
        sample_info = None
        for s in self._manifest["samples"]:
            if s["sample_id"] == sample_id:
                sample_info = s
                break

        if sample_info is None:
            raise KeyError(f"Sample {sample_id} not found")

        return PageSample(
            image_path=Path(sample_info["image_path"]),
            annotations=[],  # No bounding boxes for IQA
            metadata={
                "sample_id": sample_id,
                "subset": self.subset,
                "ground_truth": sample_info["ground_truth"],
            },
        )

    @property
    def license(self) -> str:
        """License for synthetic data."""
        return "CC0-1.0"  # Public domain

    @property
    def split_info(self) -> dict[str, Any]:
        """Split information."""
        return {
            "test": len(self._sample_ids),
        }

    def download_dataset(self) -> None:
        """Synthetic datasets don't need downloading."""
        # Already generated locally
