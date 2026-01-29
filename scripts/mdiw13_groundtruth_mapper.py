#!/usr/bin/env python3
"""Map MDIW-13 test competition ground truth labels to language/script codes.

The TestCompetitionGroundtruth.txt file contains numeric labels (0-12) for each
test sample. This script maps those labels to ISO 639-1 language codes and
ISO 15924 script codes.

Label Mapping (from Readme.txt):
    0 = Arabic      → ar / Arab
    1 = Bangla      → bn / Beng
    2 = Gujarati    → gu / Gujr
    3 = Gurmukhi    → pa / Guru  (Punjabi)
    4 = Hindi       → hi / Deva
    5 = Japanese    → ja / Jpan
    6 = Kannada     → kn / Knda
    7 = Malayalam   → ml / Mlym
    8 = Oriya       → or / Orya
    9 = Roman       → en / Latn  (English assumed for Roman script)
    10 = Tamil      → ta / Taml
    11 = Telugu     → te / Telu
    12 = Thai       → th / Thai

Usage:
    # Load mapper and get label for a sample
    from scripts.mdiw13_groundtruth_mapper import MDIW13GroundTruthMapper

    mapper = MDIW13GroundTruthMapper()
    label = mapper.get_label("sample000001.png")
    # Returns: {"language_code": "en", "script_code": "Latn", "script_name": "Roman"}
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ScriptLabel:
    """Language and script label for a sample."""
    language_code: str  # ISO 639-1
    script_code: str    # ISO 15924
    script_name: str    # Original name from dataset
    numeric_id: int     # Original numeric label


# Mapping from numeric label to (language_code, script_code, script_name)
NUMERIC_TO_LABEL = {
    0: ScriptLabel("ar", "Arab", "Arabic", 0),
    1: ScriptLabel("bn", "Beng", "Bangla", 1),
    2: ScriptLabel("gu", "Gujr", "Gujarati", 2),
    3: ScriptLabel("pa", "Guru", "Gurmukhi", 3),  # Punjabi uses Gurmukhi script
    4: ScriptLabel("hi", "Deva", "Hindi", 4),
    5: ScriptLabel("ja", "Jpan", "Japanese", 5),
    6: ScriptLabel("kn", "Knda", "Kannada", 6),
    7: ScriptLabel("ml", "Mlym", "Malayalam", 7),
    8: ScriptLabel("or", "Orya", "Oriya", 8),
    9: ScriptLabel("en", "Latn", "Roman", 9),  # Roman = Latin script, assuming English
    10: ScriptLabel("ta", "Taml", "Tamil", 10),
    11: ScriptLabel("te", "Telu", "Telugu", 11),
    12: ScriptLabel("th", "Thai", "Thai", 12),
}


class MDIW13GroundTruthMapper:
    """Maps MDIW-13 test competition samples to their ground truth labels."""

    DEFAULT_GT_PATH = Path(
        "/mnt/e/image_detection/01_base_data/language/mdiw13/"
        "SIW_Database/ICDAR_SIW_Competition/TestCompetitionGroundtruth.txt"
    )

    def __init__(self, groundtruth_path: Path | None = None):
        """Initialize mapper with ground truth file.

        Args:
            groundtruth_path: Path to TestCompetitionGroundtruth.txt.
                            Uses default path if not specified.
        """
        self.groundtruth_path = groundtruth_path or self.DEFAULT_GT_PATH
        self._labels: dict[int, int] = {}  # sample_number -> numeric_label
        self._loaded = False

    def _load_labels(self) -> None:
        """Load labels from ground truth file (lazy loading)."""
        if self._loaded:
            return

        if not self.groundtruth_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {self.groundtruth_path}")

        with open(self.groundtruth_path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    try:
                        numeric_label = int(line)
                        if 0 <= numeric_label <= 12:
                            self._labels[line_num] = numeric_label
                        else:
                            logger.warning(f"Invalid label {numeric_label} at line {line_num}")
                    except ValueError:
                        logger.warning(f"Non-numeric label at line {line_num}: {line}")

        self._loaded = True
        logger.info(f"Loaded {len(self._labels)} ground truth labels")

    def _extract_sample_number(self, filename: str) -> int | None:
        """Extract sample number from filename (e.g., 'sample000001.png' -> 1)."""
        match = re.match(r"sample(\d+)\.\w+", filename)
        if match:
            return int(match.group(1))
        return None

    def get_label(self, filename: str) -> ScriptLabel | None:
        """Get language/script label for a test sample.

        Args:
            filename: Sample filename (e.g., 'sample000001.png')

        Returns:
            ScriptLabel with language_code, script_code, script_name, numeric_id
            or None if sample not found
        """
        self._load_labels()

        sample_num = self._extract_sample_number(filename)
        if sample_num is None:
            return None

        numeric_label = self._labels.get(sample_num)
        if numeric_label is None:
            return None

        return NUMERIC_TO_LABEL.get(numeric_label)

    def get_label_by_number(self, sample_number: int) -> ScriptLabel | None:
        """Get label by sample number directly."""
        self._load_labels()
        numeric_label = self._labels.get(sample_number)
        if numeric_label is None:
            return None
        return NUMERIC_TO_LABEL.get(numeric_label)

    def get_all_labels(self) -> dict[int, ScriptLabel]:
        """Get all labels as {sample_number: ScriptLabel}."""
        self._load_labels()
        return {
            num: NUMERIC_TO_LABEL[label]
            for num, label in self._labels.items()
        }

    def get_distribution(self) -> dict[str, int]:
        """Get distribution of scripts in the test set."""
        self._load_labels()
        counts: dict[str, int] = {}
        for numeric_label in self._labels.values():
            script_label = NUMERIC_TO_LABEL.get(numeric_label)
            if script_label:
                name = script_label.script_name
                counts[name] = counts.get(name, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))


def main():
    """Show ground truth statistics."""
    mapper = MDIW13GroundTruthMapper()

    print("\nMDIW-13 Test Competition Ground Truth Statistics")
    print("=" * 60)

    distribution = mapper.get_distribution()
    total = sum(distribution.values())

    print(f"\nTotal samples: {total}")
    print("\nScript Distribution:")
    print("-" * 40)
    print(f"{'Script':<15} {'Code':<6} {'Count':<8} {'%':>6}")
    print("-" * 40)

    for script_name, count in distribution.items():
        # Find script code
        for label in NUMERIC_TO_LABEL.values():
            if label.script_name == script_name:
                code = label.script_code
                lang = label.language_code
                break
        pct = 100 * count / total
        print(f"{script_name:<15} {code:<6} {count:<8} {pct:>5.1f}%")

    print("-" * 40)
    print(f"{'TOTAL':<15} {'':6} {total:<8} 100.0%")

    # Sample verification
    print("\n\nSample Verification (first 5 samples):")
    print("-" * 50)
    for i in range(1, 6):
        label = mapper.get_label_by_number(i)
        if label:
            print(f"  sample{i:06d}.png -> {label.script_name} ({label.language_code}/{label.script_code})")


if __name__ == "__main__":
    main()
