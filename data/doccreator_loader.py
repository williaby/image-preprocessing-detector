"""DocCreator XML Ground Truth Loader for Phase 7 Continuous Labels.

Parses DocCreator's XML ground truth files to extract continuous severity
labels for document degradations.

DocCreator provides physics-based document degradation with 7 models:
- Ink Degradation (fading, bleeding)
- Bleed-Through (show-through from reverse side)
- Adaptive Blur (spatially-varying blur)
- Paper Deformation (warping, folding)
- Phantom Character (ghost impressions)
- Noise (paper aging, scanner noise)
- Watermark

Reference:
    - DocCreator: https://doc-creator.labri.fr/
    - Phase 7 Strategy: docs/development/phase-7-continuous-labels-strategy.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from image_preprocessing_detector.utils.datetime_compat import utc_now


@dataclass
class DocCreatorLabel:
    """Continuous label from DocCreator XML ground truth.

    All severity values are in range [0, 1]:
    - 0.0 = no degradation
    - 1.0 = maximum degradation

    Attributes:
        blur_severity: Blur from adaptive_blur, motion_blur, defocus
        noise_severity: Noise from paper_aging, scanner_noise
        ink_degradation: Ink fading, bleeding, broken characters
        bleed_through: Show-through from reverse side
        paper_deformation: Warping, folding, geometric distortion
        phantom_character: Ghost impressions from adjacent pages
        watermark_severity: Watermark opacity/visibility
        overall_quality: Computed as 1 - max(severities)
        source_xml: Path to original XML file
        raw_degradations: List of all degradation entries from XML
    """

    blur_severity: float = 0.0
    noise_severity: float = 0.0
    ink_degradation: float = 0.0
    bleed_through: float = 0.0
    paper_deformation: float = 0.0
    phantom_character: float = 0.0
    watermark_severity: float = 0.0
    overall_quality: float = 1.0
    source_xml: str = ""
    raw_degradations: list[dict[str, Any]] = field(default_factory=list)
    generation_timestamp: str = field(
        default_factory=lambda: utc_now().isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns format compatible with ContinuousQualityLabel schema.
        """
        return {
            # Continuous severity scores
            "blur_severity": self.blur_severity,
            "noise_severity": self.noise_severity,
            "ink_degradation": self.ink_degradation,
            "bleed_through": self.bleed_through,
            "paper_deformation": self.paper_deformation,
            "phantom_character": self.phantom_character,
            "watermark_severity": self.watermark_severity,
            "overall_quality": self.overall_quality,
            # Map to standard schema (skew/contrast/compression may not apply)
            "skew_severity": self.paper_deformation * 0.5,  # Partial mapping
            "contrast_severity": 0.0,  # DocCreator doesn't model contrast
            "compression_severity": 0.0,  # DocCreator doesn't model JPEG
            # Metadata
            "label_source": "doccreator",
            "label_confidence": 1.0,  # Perfect ground truth
            "label_variance": 0.0,
            "source_xml": self.source_xml,
            "generation_timestamp": self.generation_timestamp,
            # Backward-compatible quality_scores
            "quality_scores": {
                "blur": self.blur_severity,
                "noise": self.noise_severity,
                "ink": self.ink_degradation,
                "bleed": self.bleed_through,
                "deformation": self.paper_deformation,
                "overall": self.overall_quality,
            },
            # Backward-compatible binary labels (threshold = 0.3)
            "labels": {
                "blur": {
                    "value": int(self.blur_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "doccreator",
                    "severity": self.blur_severity,
                },
                "noise": {
                    "value": int(self.noise_severity >= 0.3),
                    "confidence": 1.0,
                    "source": "doccreator",
                    "severity": self.noise_severity,
                },
                "skew": {
                    "value": int(self.paper_deformation >= 0.3),
                    "confidence": 1.0,
                    "source": "doccreator",
                    "severity": self.paper_deformation,
                },
                "illumination": {
                    "value": 0,  # Not modeled by DocCreator
                    "confidence": 1.0,
                    "source": "doccreator",
                    "severity": 0.0,
                },
                "artifacts": {
                    "value": int(self.ink_degradation >= 0.3),
                    "confidence": 1.0,
                    "source": "doccreator",
                    "severity": self.ink_degradation,
                },
            },
            # Raw degradation data for debugging/analysis
            "raw_degradations": self.raw_degradations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocCreatorLabel:
        """Create from dictionary."""
        return cls(
            blur_severity=data.get("blur_severity", 0.0),
            noise_severity=data.get("noise_severity", 0.0),
            ink_degradation=data.get("ink_degradation", 0.0),
            bleed_through=data.get("bleed_through", 0.0),
            paper_deformation=data.get("paper_deformation", 0.0),
            phantom_character=data.get("phantom_character", 0.0),
            watermark_severity=data.get("watermark_severity", 0.0),
            overall_quality=data.get("overall_quality", 1.0),
            source_xml=data.get("source_xml", ""),
            raw_degradations=data.get("raw_degradations", []),
        )


# Mapping from DocCreator degradation types to our schema
DEGRADATION_TYPE_MAPPING = {
    # Blur types
    "adaptive_blur": "blur",
    "motion_blur": "blur",
    "defocus_blur": "blur",
    "out_of_focus": "blur",
    "gaussian_blur": "blur",
    # Noise types
    "paper_noise": "noise",
    "scanner_noise": "noise",
    "salt_pepper": "noise",
    "speckle": "noise",
    "gaussian_noise": "noise",
    # Ink degradation types
    "ink_fading": "ink",
    "ink_bleeding": "ink",
    "broken_characters": "ink",
    "character_degradation": "ink",
    "ink_mottling": "ink",
    # Bleed-through types
    "bleed_through": "bleed",
    "show_through": "bleed",
    "verso_bleed": "bleed",
    # Paper deformation types
    "paper_deformation": "deformation",
    "warping": "deformation",
    "folding": "deformation",
    "curling": "deformation",
    "geometric_distortion": "deformation",
    # Phantom character types
    "phantom_character": "phantom",
    "ghost_impression": "phantom",
    # Watermark types
    "watermark": "watermark",
    "stamp": "watermark",
    "background_pattern": "watermark",
}


def parse_doccreator_xml(xml_path: str | Path) -> DocCreatorLabel:
    """Parse DocCreator XML ground truth to continuous labels.

    Args:
        xml_path: Path to DocCreator XML file

    Returns:
        DocCreatorLabel with continuous severity values

    Raises:
        FileNotFoundError: If XML file doesn't exist
        ET.ParseError: If XML is malformed

    Example:
        >>> label = parse_doccreator_xml("degraded_001_gt.xml")
        >>> print(f"Blur: {label.blur_severity:.2f}")
        >>> print(f"Overall quality: {label.overall_quality:.2f}")
    """
    xml_path = Path(xml_path)

    if not xml_path.exists():
        raise FileNotFoundError(f"DocCreator XML not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Initialize severity accumulators
    severities = {
        "blur": 0.0,
        "noise": 0.0,
        "ink": 0.0,
        "bleed": 0.0,
        "deformation": 0.0,
        "phantom": 0.0,
        "watermark": 0.0,
    }

    raw_degradations = []

    # Parse all degradation elements
    for degradation in root.findall(".//degradation"):
        deg_type = degradation.get("type", "").lower()
        deg_method = degradation.get("method", "")
        severity_str = degradation.get("severity", "0.0")

        try:
            severity = float(severity_str)
            severity = max(0.0, min(1.0, severity))  # Clamp to [0, 1]
        except ValueError:
            severity = 0.0

        # Extract parameters
        params = {}
        params_elem = degradation.find("params")
        if params_elem is not None:
            for param in params_elem:
                param_value = param.text
                # Try to convert to appropriate type
                try:
                    if "." in str(param_value):
                        param_value = float(param_value)
                    else:
                        param_value = int(param_value)
                except (ValueError, TypeError):
                    pass  # Keep as string
                params[param.tag] = param_value

        # Store raw degradation for debugging
        raw_degradations.append(
            {
                "type": deg_type,
                "method": deg_method,
                "severity": severity,
                "params": params,
            }
        )

        # Map to our schema categories
        category = DEGRADATION_TYPE_MAPPING.get(deg_type)
        if category is None:
            # Try matching by substring
            for key, cat in DEGRADATION_TYPE_MAPPING.items():
                if key in deg_type or deg_type in key:
                    category = cat
                    break

        if category:
            # Use max severity if multiple degradations of same type
            severities[category] = max(severities[category], severity)

    # Calculate overall quality (inverse of max severity)
    max_severity = max(severities.values())
    overall_quality = 1.0 - max_severity

    return DocCreatorLabel(
        blur_severity=severities["blur"],
        noise_severity=severities["noise"],
        ink_degradation=severities["ink"],
        bleed_through=severities["bleed"],
        paper_deformation=severities["deformation"],
        phantom_character=severities["phantom"],
        watermark_severity=severities["watermark"],
        overall_quality=overall_quality,
        source_xml=str(xml_path),
        raw_degradations=raw_degradations,
    )


def parse_doccreator_directory(
    directory: str | Path,
    xml_pattern: str = "*_gt.xml",
) -> list[tuple[Path, DocCreatorLabel]]:
    """Parse all DocCreator XML files in a directory.

    Args:
        directory: Directory containing XML files
        xml_pattern: Glob pattern for XML files (default: *_gt.xml)

    Returns:
        List of (xml_path, label) tuples

    Example:
        >>> labels = parse_doccreator_directory("doccreator_output/")
        >>> for xml_path, label in labels:
        ...     print(f"{xml_path.stem}: quality={label.overall_quality:.2f}")
    """
    directory = Path(directory)
    results = []

    for xml_path in directory.glob(xml_pattern):
        try:
            label = parse_doccreator_xml(xml_path)
            results.append((xml_path, label))
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Warning: Failed to parse {xml_path}: {e}")

    return results


def find_image_for_xml(xml_path: str | Path) -> Path | None:
    """Find the corresponding image file for a DocCreator XML.

    DocCreator typically names files as:
    - image_001.png + image_001_gt.xml
    - degraded_001.png + degraded_001_gt.xml

    Args:
        xml_path: Path to XML file

    Returns:
        Path to corresponding image, or None if not found
    """
    xml_path = Path(xml_path)
    base_name = xml_path.stem.replace("_gt", "")
    parent = xml_path.parent

    # Try common image extensions
    for ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]:
        image_path = parent / f"{base_name}{ext}"
        if image_path.exists():
            return image_path

    return None


def create_label_file(
    xml_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """Create a JSON label file from DocCreator XML.

    Args:
        xml_path: Path to DocCreator XML
        output_path: Optional output path (default: same name with _labels.json)

    Returns:
        Path to created JSON file
    """
    xml_path = Path(xml_path)
    label = parse_doccreator_xml(xml_path)

    if output_path is None:
        base_name = xml_path.stem.replace("_gt", "")
        output_path = xml_path.parent / f"{base_name}_labels.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(label.to_dict(), f, indent=2)

    return output_path


class DocCreatorDataset:
    """Dataset loader for DocCreator-generated images with XML ground truth.

    Provides iteration over image-label pairs from a DocCreator output directory.

    Args:
        root_dir: Directory containing images and XML files
        xml_pattern: Glob pattern for XML files
        transform: Optional image transform function

    Example:
        >>> dataset = DocCreatorDataset("doccreator_output/")
        >>> for image_path, label in dataset:
        ...     image = cv2.imread(str(image_path))
        ...     print(f"Blur: {label.blur_severity:.2f}")
    """

    def __init__(
        self,
        root_dir: str | Path,
        xml_pattern: str = "*_gt.xml",
        transform: Any = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.transform = transform

        # Parse all XML files
        self._samples: list[tuple[Path, Path, DocCreatorLabel]] = []

        for xml_path in self.root_dir.rglob(xml_pattern):
            image_path = find_image_for_xml(xml_path)
            if image_path is not None:
                try:
                    label = parse_doccreator_xml(xml_path)
                    self._samples.append((image_path, xml_path, label))
                except ET.ParseError as e:
                    print(f"Warning: Failed to parse {xml_path}: {e}")

        print(f"Loaded {len(self._samples)} DocCreator samples from {root_dir}")

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, idx: int) -> tuple[Path, DocCreatorLabel]:
        """Get image path and label for index."""
        image_path, _xml_path, label = self._samples[idx]
        return image_path, label

    def get_statistics(self) -> dict[str, Any]:
        """Calculate dataset statistics."""
        if not self._samples:
            return {"count": 0}

        severities = {
            "blur": [],
            "noise": [],
            "ink": [],
            "bleed": [],
            "deformation": [],
            "overall": [],
        }

        for _, _, label in self._samples:
            severities["blur"].append(label.blur_severity)
            severities["noise"].append(label.noise_severity)
            severities["ink"].append(label.ink_degradation)
            severities["bleed"].append(label.bleed_through)
            severities["deformation"].append(label.paper_deformation)
            severities["overall"].append(label.overall_quality)

        import numpy as np

        stats = {"count": len(self._samples)}
        for key, values in severities.items():
            arr = np.array(values)
            stats[key] = {
                "mean": float(arr.mean()),
                "std": float(arr.std()),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "median": float(np.median(arr)),
            }

        return stats

    def export_labels(self, output_dir: str | Path) -> list[Path]:
        """Export all labels to JSON files.

        Args:
            output_dir: Directory to save label files

        Returns:
            List of created label file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        for image_path, _xml_path, label in self._samples:
            label_path = output_dir / f"{image_path.stem}_labels.json"
            with open(label_path, "w") as f:
                json.dump(label.to_dict(), f, indent=2)
            created_files.append(label_path)

        return created_files


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python doccreator_loader.py <xml_path_or_directory>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_file():
        # Parse single XML
        label = parse_doccreator_xml(path)
        print(json.dumps(label.to_dict(), indent=2))
    elif path.is_dir():
        # Parse directory
        dataset = DocCreatorDataset(path)
        stats = dataset.get_statistics()
        print("\nDataset Statistics:")
        print(json.dumps(stats, indent=2))
    else:
        print(f"Error: {path} not found")
        sys.exit(1)
