#!/usr/bin/env python3
"""Generate a synthetic proof-of-concept dataset for OOD detection validation.

Creates controlled in-distribution and out-of-distribution document images with
real Unicode text per script and script-appropriate Noto fonts. Since all
generation parameters are known, we can verify the OOD detection pipeline
end-to-end with exact ground truth.

Incorporates v4 font diversity fixes: per-script font selection, font style
tracking in metadata, and RTL-aware rendering for Arabic/Hebrew scripts.

The dataset includes:
  - In-distribution (ID): Documents resembling DIQA-5000 characteristics
    (Latin/Cyrillic, medium DPI, moderate degradation, standard layouts)
  - OOD by script: Unusual scripts not in DIQA-5000 (Tibetan, Myanmar, Ethiopic)
  - OOD by degradation: Extreme quality (pristine or heavily degraded)
  - OOD by resolution: Very low (72 DPI) or very high (600 DPI)
  - OOD by layout: Complex/unusual layouts (forms, multi-column)
  - OOD by color: Binarized or extreme color shifts
  - Edge cases: Multi-script documents, vertical CJK, blank-like pages

Total: ~500 images (fast to generate, enough for statistical significance).

Usage:
    PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
        uv run python3 scripts/generate_ood_poc_dataset.py \
        --output results/ood_poc_dataset/ \
        --seed 42

    # Then run the full OOD evaluation pipeline:
    # 1. Extract embeddings for ID and each OOD category
    # 2. Fit OOD detector on ID embeddings
    # 3. Evaluate AUROC per OOD category
    # 4. Assign synthetic VLM labels (based on known quality parameters)
    # 5. Run full Tier 1 + Tier 2 evaluation
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@dataclass
class OODCategory:
    """Definition of an OOD category for the PoC dataset."""

    name: str
    description: str
    n_images: int
    is_ood: bool
    generation_params: dict[str, Any]


# ---------------------------------------------------------------------------
# Dataset specification
# ---------------------------------------------------------------------------

# In-distribution: resembles DIQA-5000 (scanned/digital documents, Latin/Cyrillic,
# standard quality range, moderate DPI)
ID_CATEGORIES = [
    OODCategory(
        name="id_standard",
        description="Standard documents similar to DIQA-5000",
        n_images=100,
        is_ood=False,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color", "grayscale"],
        },
    ),
    OODCategory(
        name="id_cyrillic",
        description="Cyrillic documents (in DIQA-5000 distribution)",
        n_images=50,
        is_ood=False,
        generation_params={
            "scripts": ["Cyrl"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
        },
    ),
]

OOD_CATEGORIES = [
    # Script OOD: scripts not in DIQA-5000
    OODCategory(
        name="ood_script_tibetan",
        description="Tibetan script (never in DIQA-5000)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Tibt"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
        },
    ),
    OODCategory(
        name="ood_script_myanmar",
        description="Myanmar script (never in DIQA-5000)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Mymr"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
        },
    ),
    OODCategory(
        name="ood_script_ethiopic",
        description="Ethiopic script (never in DIQA-5000)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Ethi"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
        },
    ),
    # Degradation OOD: extreme quality levels
    OODCategory(
        name="ood_pristine",
        description="Pristine documents (unnaturally clean for DIQA-5000)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [400, 600],
            "quality_tiers": ["PRISTINE"],
            "color_modes": ["color"],
        },
    ),
    OODCategory(
        name="ood_heavily_degraded",
        description="Heavily degraded documents (beyond DIQA-5000 range)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [100, 150],
            "quality_tiers": ["DEGRADED"],
            "color_modes": ["grayscale"],
        },
    ),
    # Resolution OOD: extreme DPI
    OODCategory(
        name="ood_very_low_dpi",
        description="Very low resolution (72 DPI thumbnails)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [72],
            "quality_tiers": ["LOW"],
            "color_modes": ["color"],
        },
    ),
    OODCategory(
        name="ood_very_high_dpi",
        description="Very high resolution (600 DPI archival)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [600],
            "quality_tiers": ["HIGH"],
            "color_modes": ["color"],
        },
    ),
    # Layout OOD: unusual document structures
    OODCategory(
        name="ood_form_layout",
        description="Form-based layouts (structured fields, not prose)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM"],
            "color_modes": ["color"],
        },
    ),
    # Color OOD: unusual color modes
    OODCategory(
        name="ood_binarized",
        description="Binarized documents (black and white only)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM"],
            "color_modes": ["binarized"],
        },
    ),
    # Multi-script OOD
    OODCategory(
        name="ood_multiscript",
        description="Multi-script documents (Arabic + Latin mix)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Arab", "Latn"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
        },
    ),
    # CJK vertical text OOD
    OODCategory(
        name="ood_cjk_vertical",
        description="CJK vertical text (tategaki)",
        n_images=30,
        is_ood=True,
        generation_params={
            "scripts": ["Jpan"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
            "force_vertical": True,
        },
    ),
    # Adversarial font OOD: fonts designed to break script classifiers
    OODCategory(
        name="ood_adversarial_fraktur",
        description="Latin Blackletter/Fraktur (structural destruction of Latin features)",
        n_images=20,
        is_ood=True,
        generation_params={
            "scripts": ["Latn"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
            "adversarial_font": "fraktur",
        },
    ),
    OODCategory(
        name="ood_adversarial_nastaliq",
        description="Arabic Nastaliq/calligraphic (cascading calligraphic transfer)",
        n_images=20,
        is_ood=True,
        generation_params={
            "scripts": ["Arab"],
            "dpi_tiers": [200, 300],
            "quality_tiers": ["MEDIUM", "HIGH"],
            "color_modes": ["color"],
            "adversarial_font": "nastaliq",
        },
    ),
]


def generate_synthetic_quality_labels(
    quality_tier: str,
    dpi: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    """Generate synthetic quality labels based on known generation parameters.

    These simulate what a VLM or human rater would assign, enabling
    end-to-end pipeline testing without actual VLM inference.

    Args:
        quality_tier: Generation quality tier.
        dpi: Image DPI.
        rng: Random number generator.

    Returns:
        Dict with overall, sharpness, color scores (1-5 scale).
    """
    tier_to_base = {
        "PRISTINE": 4.5,
        "HIGH": 4.0,
        "MEDIUM": 3.0,
        "LOW": 2.0,
        "DEGRADED": 1.5,
    }
    base = tier_to_base.get(quality_tier, 3.0)

    # DPI affects sharpness perception
    dpi_bonus = 0.0
    if dpi >= 400:
        dpi_bonus = 0.3
    elif dpi >= 300:
        dpi_bonus = 0.1
    elif dpi <= 72:
        dpi_bonus = -1.0
    elif dpi <= 100:
        dpi_bonus = -0.5

    noise = rng.normal(0, 0.2, 3)

    overall = np.clip(base + noise[0], 1.0, 5.0)
    sharpness = np.clip(base + dpi_bonus + noise[1], 1.0, 5.0)
    color = np.clip(base + noise[2], 1.0, 5.0)

    return {
        "overall": float(overall),
        "sharpness": float(sharpness),
        "color": float(color),
    }


def quality_score_to_category(score: float) -> str:
    """Map a continuous quality score to a categorical label.

    Args:
        score: Quality score (1-5 scale).

    Returns:
        Category string (excellent/good/fair/poor/bad).
    """
    if score >= 4.5:
        return "excellent"
    if score >= 3.5:
        return "good"
    if score >= 2.5:
        return "fair"
    if score >= 1.5:
        return "poor"
    return "bad"


def try_generate_images(
    category: OODCategory,
    output_dir: Path,
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    """Attempt to generate images using the synth generator, fall back to simple PIL.

    Args:
        category: OOD category specification.
        output_dir: Directory to save images.
        rng: Random number generator.

    Returns:
        List of metadata dicts per generated image.
    """
    cat_dir = output_dir / category.name
    cat_dir.mkdir(parents=True, exist_ok=True)

    params = category.generation_params
    scripts = params["scripts"]
    dpi_tiers = params["dpi_tiers"]
    quality_tiers = params["quality_tiers"]
    color_modes = params.get("color_modes", ["color"])

    records = []
    for i in range(category.n_images):
        script = scripts[i % len(scripts)]
        dpi = dpi_tiers[i % len(dpi_tiers)]
        quality = quality_tiers[i % len(quality_tiers)]
        color_mode = color_modes[i % len(color_modes)]

        img_id = f"{category.name}_{i:04d}"
        img_path = cat_dir / f"{img_id}.jpg"

        # Generate a simple synthetic document image
        force_vertical = params.get("force_vertical", False)
        adversarial_font = params.get("adversarial_font")
        font_info = _generate_simple_document(
            output_path=str(img_path),
            script=script,
            dpi=dpi,
            quality_tier=quality,
            color_mode=color_mode,
            rng=rng,
            force_vertical=force_vertical,
            adversarial_font=adversarial_font,
        )

        # Generate synthetic quality labels
        labels = generate_synthetic_quality_labels(quality, dpi, rng)
        categories = {dim: quality_score_to_category(s) for dim, s in labels.items()}

        record = {
            "image_id": f"{category.name}/{img_id}.jpg",
            "image_path": str(img_path),
            "category": category.name,
            "is_ood": category.is_ood,
            "ood_reason": category.description if category.is_ood else None,
            "generation_params": {
                "script": script,
                "dpi": dpi,
                "quality_tier": quality,
                "color_mode": color_mode,
                "font_family": font_info["font_family"],
                "font_style": font_info["font_style"],
                "writing_direction": font_info["writing_direction"],
            },
            "synthetic_scores": labels,
            "synthetic_categories": categories,
        }
        records.append(record)

    log.info(
        "Generated %d images for %s (is_ood=%s)",
        len(records),
        category.name,
        category.is_ood,
    )
    return records


# ---------------------------------------------------------------------------
# Per-script Unicode text samples and font paths
# ---------------------------------------------------------------------------
# Real Unicode text ensures each script produces visually distinct embeddings.
# This fixes the v3 single-font bug where all scripts looked identical.

SCRIPT_TEXT: dict[str, list[str]] = {
    "Latn": [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse.",
    ],
    "Cyrl": [
        "\u0412 \u043d\u0430\u0447\u0430\u043b\u0435 \u0431\u044b\u043b\u043e \u0441\u043b\u043e\u0432\u043e, \u0438 \u0441\u043b\u043e\u0432\u043e \u0431\u044b\u043b\u043e \u0443 \u0431\u043e\u0433\u0430.",
        "\u041a\u0430\u0436\u0434\u044b\u0439 \u0447\u0435\u043b\u043e\u0432\u0435\u043a \u0438\u043c\u0435\u0435\u0442 \u043f\u0440\u0430\u0432\u043e \u043d\u0430 \u0436\u0438\u0437\u043d\u044c \u0438 \u0441\u0432\u043e\u0431\u043e\u0434\u0443.",
        "\u041c\u043e\u0441\u043a\u0432\u0430 \u0441\u0442\u043e\u043b\u0438\u0446\u0430 \u0420\u043e\u0441\u0441\u0438\u0438 \u0438 \u043a\u0440\u0443\u043f\u043d\u0435\u0439\u0448\u0438\u0439 \u0433\u043e\u0440\u043e\u0434.",
        "\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a \u043e\u0434\u0438\u043d \u0438\u0437 \u0441\u0430\u043c\u044b\u0445 \u0440\u0430\u0441\u043f\u0440\u043e\u0441\u0442\u0440\u0430\u043d\u0451\u043d\u043d\u044b\u0445.",
    ],
    "Arab": [
        "\u0628\u0633\u0645 \u0627\u0644\u0644\u0647 \u0627\u0644\u0631\u062d\u0645\u0646 \u0627\u0644\u0631\u062d\u064a\u0645 \u0648\u0627\u0644\u0635\u0644\u0627\u0629 \u0648\u0627\u0644\u0633\u0644\u0627\u0645 \u0639\u0644\u0649 \u0631\u0633\u0648\u0644\u0647 \u0627\u0644\u0643\u0631\u064a\u0645",
        "\u0627\u0644\u0639\u0644\u0645 \u0646\u0648\u0631 \u0648\u0627\u0644\u062c\u0647\u0644 \u0638\u0644\u0627\u0645 \u0648\u0627\u0644\u0642\u0631\u0627\u0621\u0629 \u0645\u0641\u062a\u0627\u062d \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
        "\u0644\u0643\u0644 \u0625\u0646\u0633\u0627\u0646 \u0627\u0644\u062d\u0642 \u0641\u064a \u0627\u0644\u062d\u064a\u0627\u0629 \u0648\u0627\u0644\u062d\u0631\u064a\u0629 \u0648\u0633\u0644\u0627\u0645\u0629 \u0634\u062e\u0635\u0647",
        "\u0627\u0644\u0644\u063a\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0645\u0646 \u0623\u0643\u062b\u0631 \u0627\u0644\u0644\u063a\u0627\u062a \u0627\u0646\u062a\u0634\u0627\u0631\u0627 \u0641\u064a \u0627\u0644\u0639\u0627\u0644\u0645",
    ],
    "Tibt": [
        "\u0f56\u0f7c\u0f51\u0f0b\u0f66\u0f90\u0f51\u0f0b\u0f56\u0f66\u0f9f\u0f53\u0f0b\u0f60\u0f42\u0fb2\u0f7c\u0f0b\u0f66\u0fa4\u0fb1\u0f72\u0f0b\u0f51\u0f44\u0f0b\u0f60\u0f42\u0fb2\u0f7c\u0f0b\u0f62\u0f90\u0fb1\u0f7a\u0f53\u0f0b",
        "\u0f46\u0f7c\u0f66\u0f0b\u0f50\u0f58\u0f66\u0f0b\u0f46\u0f51\u0f0b\u0f66\u0f44\u0f66\u0f0b\u0f62\u0f92\u0fb1\u0f66\u0f0b\u0f40\u0fb1\u0f72\u0f0b\u0f42\u0f53\u0f66\u0f0b\u0f66\u0f0b\u0f60\u0f42\u0fb2\u0f7c\u0f0b",
        "\u0f56\u0f51\u0f42\u0f0b\u0f63\u0f51\u0f53\u0f0b\u0f42\u0fb1\u0f72\u0f0b\u0f62\u0f72\u0f42\u0f0b\u0f42\u0f53\u0f66\u0f0b\u0f66\u0f0b\u0f63\u0f7c\u0f0b\u0f62\u0f92\u0fb1\u0f74\u0f66\u0f0b\u0f60\u0f42\u0fb2\u0f7c\u0f0b",
        "\u0f66\u0fa3\u0f72\u0f44\u0f0b\u0f66\u0f9f\u0f7c\u0f56\u0f66\u0f0b\u0f63\u0f66\u0f0b\u0f42\u0f66\u0f74\u0f44\u0f0b\u0f56\u0f0b\u0f56\u0f66\u0f9f\u0f53\u0f0b\u0f60\u0f42\u0fb2\u0f7c\u0f0b\u0f62\u0f90\u0fb1\u0f7a\u0f53\u0f0b",
    ],
    "Mymr": [
        "\u1019\u1014\u1000\u103a\u1014\u1036\u1036\u1014\u1000\u103a \u1021\u1001\u103b\u102d\u1014\u103a \u101e\u1010\u103a\u1019\u103e\u1010\u103a\u1001\u103b\u1000\u103a",
        "\u101c\u1030\u1010\u102d\u102f\u1004\u103a\u1038\u101e\u100a\u103a \u1021\u1001\u103d\u1004\u103a\u1037\u1021\u101b\u1031\u1038 \u101b\u103e\u102d\u1010\u101a\u103a",
        "\u1019\u103c\u1014\u103a\u1019\u102c\u1018\u102c\u101e\u102c\u101e\u100a\u103a \u1021\u101c\u103d\u1014\u103a \u1019\u1014\u1000\u103a\u1014\u1036\u1036\u1014\u1000\u103a",
        "\u1015\u100a\u102c\u101b\u1031\u1038 \u1021\u1019\u103c\u1032\u1037\u1005\u102c\u1038 \u1005\u102c\u1019\u103b\u1000\u103a\u1014\u103e\u102c\u101e\u100a\u103a",
    ],
    "Ethi": [
        "\u12a0\u121b\u122d\u129b \u1264\u1270 \u121d\u1215\u122d\u1275 \u12e8\u12a2\u1275\u12ee\u1335\u12eb \u1265\u1204\u122b\u12ca \u1218\u12f0\u1260\u129b",
        "\u1260\u1275\u121d\u1205\u122d\u1275 \u12ed\u1205 \u12a0\u121b\u122d\u129b \u1260\u12e8\u1275\u12ec\u1335\u12eb\u12cd \u1265\u1204\u122d",
        "\u12a5\u12eb\u1295\u12f3\u1295\u12f1 \u120d\u12f5 \u12e8\u1270\u12c8\u1208\u12f0 \u1290\u1339 \u1260\u12ad\u1265\u122d \u12a5\u1293 \u1260\u1218\u1265\u1275",
        "\u1201\u1209\u121d \u1230\u12cd \u1290\u1339 \u1206\u1290\u12cd \u12e8\u1270\u12c8\u1208\u12f1 \u12e8\u1218\u1295\u134d\u1235 \u12ad\u1265\u122d",
    ],
    "Jpan": [
        "\u56fd\u969b\u9023\u5408\u4e16\u754c\u4eba\u6a29\u5ba3\u8a00\u7b2c\u4e00\u6761\u3059\u3079\u3066\u306e\u4eba\u9593\u306f",
        "\u751f\u307e\u308c\u306a\u304c\u3089\u306b\u3057\u3066\u81ea\u7531\u3067\u3042\u308a\u304b\u3064\u5c0a\u53b3\u3068\u6a29\u5229\u3068\u306b\u3064\u3044\u3066",
        "\u5e73\u7b49\u3067\u3042\u308b\u4eba\u9593\u306f\u7406\u6027\u3068\u826f\u5fc3\u3068\u3092\u6388\u3051\u3089\u308c\u3066\u304a\u308a",
        "\u4e92\u3044\u306b\u540c\u80de\u306e\u7cbe\u795e\u3092\u3082\u3063\u3066\u884c\u52d5\u3057\u306a\u3051\u308c\u3070\u306a\u3089\u306a\u3044",
    ],
}

# Font paths per script — use Noto fonts when available for authentic rendering.
# Falls back to DejaVuSans (Latin-only) if script-specific font is missing.
SCRIPT_FONTS: dict[str, list[str]] = {
    "Latn": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Cyrl": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "Arab": [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
    ],
    "Tibt": [
        "/usr/share/fonts/truetype/noto/NotoSerifTibetan-Regular.ttf",
    ],
    "Mymr": [
        "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Regular.ttf",
    ],
    "Ethi": [
        "/usr/share/fonts/truetype/noto/NotoSansEthiopic-Regular.ttf",
    ],
    "Jpan": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ],
}

# Adversarial fonts from v4 font diversity strategy — designed to break classifiers.
# Extracted from git commit e74165f (fonts/synthetic-gen/).
# These are checked at runtime; if missing, the category falls back gracefully.
_ADVERSARIAL_FONT_DIR = Path(__file__).parent.parent / "fonts" / "synthetic-gen"
ADVERSARIAL_FONTS: dict[str, list[str]] = {
    # Fraktur: Blackletter destroys standard Latin glyph features
    "fraktur": [
        str(_ADVERSARIAL_FONT_DIR / "UnifrakturMaguntia-Book.ttf"),
        "/tmp/adversarial_fonts/UnifrakturMaguntia-Book.ttf",
    ],
    # Nastaliq: cascading calligraphic Arabic, very different from Naskh
    "nastaliq": [
        str(_ADVERSARIAL_FONT_DIR / "Gulzar-Regular.ttf"),
        "/tmp/adversarial_fonts/Gulzar-Regular.ttf",
    ],
}

# RTL scripts need right-aligned rendering
RTL_SCRIPTS: set[str] = {"Arab", "Hebr"}

# Writing direction per script (for metadata tracking)
SCRIPT_DIRECTION: dict[str, str] = {
    "Latn": "ltr",
    "Cyrl": "ltr",
    "Arab": "rtl",
    "Hebr": "rtl",
    "Tibt": "ltr",
    "Mymr": "ltr",
    "Ethi": "ltr",
    "Jpan": "ltr",  # default horizontal; vertical handled separately
}


def _load_script_font(
    script: str,
    size: int,
    rng: np.random.Generator,
    adversarial_font: str | None = None,
) -> tuple[Any, str]:
    """Load an appropriate font for the given script.

    Tries adversarial font override first (if specified), then script-specific
    Noto fonts, then DejaVuSans fallback.

    Args:
        script: ISO 15924 script code.
        size: Font size in points.
        rng: Random number generator (for selecting among multiple fonts).
        adversarial_font: Optional adversarial font key (e.g. "fraktur", "nastaliq").

    Returns:
        Tuple of (PIL font object, font family name).
    """
    from PIL import ImageFont

    # Try adversarial font first if specified
    if adversarial_font and adversarial_font in ADVERSARIAL_FONTS:
        for font_path in ADVERSARIAL_FONTS[adversarial_font]:
            try:
                font = ImageFont.truetype(font_path, size)
                family = Path(font_path).stem
                return font, family
            except OSError:
                continue
        log.warning(
            "Adversarial font '%s' not found, falling back to standard fonts",
            adversarial_font,
        )

    candidates = SCRIPT_FONTS.get(script, [])
    # Shuffle to add font diversity (v4 pattern)
    if len(candidates) > 1:
        idx = int(rng.integers(0, len(candidates)))
        candidates = [candidates[idx]] + [
            c for j, c in enumerate(candidates) if j != idx
        ]

    for font_path in candidates:
        try:
            font = ImageFont.truetype(font_path, size)
            family = Path(font_path).stem
            return font, family
        except OSError:
            continue

    # Fallback: DejaVuSans (Latin only, but better than nothing)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
        )
        return font, "DejaVuSans"
    except OSError:
        return ImageFont.load_default(), "default"


def _render_vertical_text(
    draw: Any,
    text_lines: list[str],
    font: Any,
    font_size: int,
    fg: tuple[int, int, int],
    width: int,
    height: int,
    scale: float,
    rng: np.random.Generator,
) -> None:
    """Render CJK text in vertical (tategaki) layout, right-to-left columns.

    Args:
        draw: PIL ImageDraw object.
        text_lines: Text lines to render.
        font: PIL font object.
        font_size: Font size in points.
        fg: Foreground color tuple.
        width: Image width.
        height: Image height.
        scale: DPI scale factor.
        rng: Random number generator.
    """
    margin = int(40 * scale)
    col_spacing = int(font_size * 1.8)
    char_spacing = int(font_size * 1.4)

    # Start from right side (tategaki reads right-to-left)
    x = width - margin - font_size
    line_idx = 0

    while x > margin:
        text_line = text_lines[line_idx % len(text_lines)]
        line_idx += 1
        char_count = int(rng.uniform(0.4, 1.0) * len(text_line))

        y = margin
        for char in text_line[:char_count]:
            if y > height - margin:
                break
            draw.text((x, y), char, fill=fg, font=font)
            y += char_spacing

        x -= col_spacing


def _classify_font_style(font_family: str) -> str:
    """Classify font typographic style from family name.

    Args:
        font_family: Font family name (e.g. stem of font filename).

    Returns:
        One of: serif, sans, display, handwriting, adversarial, unknown.
    """
    lower = font_family.lower()
    if "fraktur" in lower or "maguntia" in lower:
        return "adversarial"
    if "gulzar" in lower:
        return "adversarial"
    if "serif" in lower and "sans" not in lower:
        return "serif"
    if "sans" in lower or "dejavu" in lower:
        return "sans"
    if "kufi" in lower:
        return "display"
    return "unknown"


def _generate_simple_document(
    output_path: str,
    script: str,
    dpi: int,
    quality_tier: str,
    color_mode: str,
    rng: np.random.Generator,
    force_vertical: bool = False,
    adversarial_font: str | None = None,
) -> dict[str, str]:
    """Generate a simple synthetic document image using PIL.

    Creates a document-like image with real Unicode text per script and
    script-appropriate Noto fonts. Supports LTR, RTL, and vertical writing
    directions. Optionally uses adversarial fonts to test classifier limits.

    Args:
        output_path: Path to save the image.
        script: Script code (affects text and font selection).
        dpi: Target DPI (affects image size).
        quality_tier: Quality tier (affects degradation).
        color_mode: Color mode (color/grayscale/binarized).
        rng: Random number generator.
        force_vertical: Render text vertically (tategaki for CJK).
        adversarial_font: Optional adversarial font key (e.g. "fraktur").

    Returns:
        Dict with font_family, font_style, and writing_direction for metadata.
    """
    from PIL import Image, ImageDraw

    # Scale image size by DPI
    scale = dpi / 300.0
    width = int(800 * scale)
    height = int(1100 * scale)

    # Background color based on quality/color mode
    if color_mode == "binarized":
        bg = (255, 255, 255)
        fg = (0, 0, 0)
    elif color_mode == "grayscale":
        bg_val = int(rng.uniform(220, 250))
        bg = (bg_val, bg_val, bg_val)
        fg_val = int(rng.uniform(10, 60))
        fg = (fg_val, fg_val, fg_val)
    else:
        bg = (
            int(rng.uniform(230, 255)),
            int(rng.uniform(230, 255)),
            int(rng.uniform(230, 255)),
        )
        fg = (
            int(rng.uniform(0, 50)),
            int(rng.uniform(0, 50)),
            int(rng.uniform(0, 50)),
        )

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Load script-appropriate font (v4 fix: per-script fonts, not single font)
    font_size = max(8, int(12 * scale))
    font, font_family = _load_script_font(script, font_size, rng, adversarial_font)

    # Classify font style (mirrors v4 font_style tracking)
    font_style = _classify_font_style(font_family)

    # Determine writing direction
    is_rtl = script in RTL_SCRIPTS
    if force_vertical:
        writing_direction = "vertical"
    elif is_rtl:
        writing_direction = "rtl"
    else:
        writing_direction = "ltr"

    # Get real Unicode text for this script
    text_lines = SCRIPT_TEXT.get(script, [f"Placeholder text for {script} script."])

    if force_vertical:
        # Vertical CJK tategaki rendering (right-to-left columns)
        _render_vertical_text(
            draw, text_lines, font, font_size, fg, width, height, scale, rng
        )
    else:
        # Horizontal rendering (LTR or RTL)
        y = int(40 * scale)
        line_spacing = int(20 * scale)
        margin = int(40 * scale)

        line_idx = 0
        while y < height - int(40 * scale):
            text_line = text_lines[line_idx % len(text_lines)]
            line_idx += 1

            # Vary line length
            char_count = int(rng.uniform(0.5, 1.0) * len(text_line))
            snippet = text_line[:char_count]

            if is_rtl:
                # Right-align RTL text
                try:
                    bbox = draw.textbbox((0, 0), snippet, font=font)
                    text_w = bbox[2] - bbox[0]
                except (AttributeError, TypeError):
                    text_w = len(snippet) * font_size // 2
                x_pos = max(margin, width - margin - text_w)
            else:
                x_pos = margin

            draw.text((x_pos, y), snippet, fill=fg, font=font)
            y += line_spacing

    # Apply degradation based on quality tier
    if quality_tier == "DEGRADED":
        arr = np.array(img)
        noise = rng.normal(0, 25, arr.shape).astype(np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
    elif quality_tier == "LOW":
        arr = np.array(img)
        noise = rng.normal(0, 10, arr.shape).astype(np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    # Convert color mode
    if color_mode == "grayscale":
        img = img.convert("L").convert("RGB")
    elif color_mode == "binarized":
        img = img.convert("L")
        arr = np.array(img)
        arr = ((arr > 128) * 255).astype(np.uint8)
        img = Image.fromarray(arr).convert("RGB")

    # Save with appropriate quality
    jpeg_q = (
        95
        if quality_tier in ("PRISTINE", "HIGH")
        else 75
        if quality_tier == "MEDIUM"
        else 50
    )
    img.save(output_path, "JPEG", quality=jpeg_q)

    return {
        "font_family": font_family,
        "font_style": font_style,
        "writing_direction": writing_direction,
    }


def main() -> None:
    """Generate the OOD proof-of-concept dataset."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic OOD proof-of-concept dataset"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/ood_poc_dataset",
        help="Output directory",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    all_categories = ID_CATEGORIES + OOD_CATEGORIES
    all_records: list[dict[str, Any]] = []

    log.info("Generating OOD PoC dataset with %d categories", len(all_categories))
    total_images = sum(c.n_images for c in all_categories)
    log.info(
        "Total images: %d (ID: %d, OOD: %d)",
        total_images,
        sum(c.n_images for c in ID_CATEGORIES),
        sum(c.n_images for c in OOD_CATEGORIES),
    )

    for category in all_categories:
        records = try_generate_images(category, output_dir, rng)
        all_records.extend(records)

    # Save manifest
    manifest = {
        "dataset": "ood_poc_synthetic",
        "version": "1.0.0",
        "seed": args.seed,
        "total_images": len(all_records),
        "n_id": sum(1 for r in all_records if not r["is_ood"]),
        "n_ood": sum(1 for r in all_records if r["is_ood"]),
        "categories": [
            {
                "name": c.name,
                "description": c.description,
                "n_images": c.n_images,
                "is_ood": c.is_ood,
            }
            for c in all_categories
        ],
    }
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # Save per-image metadata as JSONL
    with open(output_dir / "metadata.jsonl", "w") as f:
        f.writelines(json.dumps(record) + "\n" for record in all_records)

    # Save ID and OOD image lists separately (for evaluate_ood_detection.py)
    id_images = [r for r in all_records if not r["is_ood"]]
    ood_images = [r for r in all_records if r["is_ood"]]

    with open(output_dir / "id_images.json", "w") as f:
        json.dump([r["image_path"] for r in id_images], f, indent=2)

    # Group OOD by category
    ood_by_cat: dict[str, list[str]] = {}
    for r in ood_images:
        cat = r["category"]
        if cat not in ood_by_cat:
            ood_by_cat[cat] = []
        ood_by_cat[cat].append(r["image_path"])

    for cat, paths in ood_by_cat.items():
        with open(output_dir / f"ood_{cat}_images.json", "w") as f:
            json.dump(paths, f, indent=2)

    log.info("=" * 60)
    log.info("Dataset generated: %s", output_dir)
    log.info("  Total: %d images", len(all_records))
    log.info("  In-distribution: %d images", len(id_images))
    log.info(
        "  Out-of-distribution: %d images (%d categories)",
        len(ood_images),
        len(ood_by_cat),
    )
    log.info("")
    log.info("Next steps:")
    log.info("  1. Extract embeddings: scripts/extract_siglip2_embeddings.py")
    log.info("  2. Fit OOD detector: --fit-ood on ID embeddings")
    log.info("  3. Evaluate: scripts/evaluate_ood_detection.py")
    log.info("  4. Run VLM experiment: scripts/run_vlm_prompting_experiment.py")
    log.info("     (or use synthetic labels from metadata.jsonl for dry-run testing)")


if __name__ == "__main__":
    main()
