"""Apply VLM per-image annotations to L2 JSON records for john11-manuscripts dataset.

Loads batch1.json (Copt/Syrc/Geor/Goth/Cyrs), batch2.json (adds Ethi/Armn),
and inline batch3 data (Grek/Arab/Latn) embedded in this script.
Images without VLM coverage receive script-level defaults computed from
the available annotated images for that script.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path("/home/byron/dev/image_detection")
ANNOTATION_INDEX = (
    REPO_ROOT / "data/john11-manuscripts/annotation_sheets/annotation_index.json"
)
BATCH2_JSON = (
    REPO_ROOT / "data/john11-manuscripts/annotation_sheets/vlm_annotations_batch2.json"
)
L2_DIR = REPO_ROOT / "metadata_registry/json/john11-manuscripts"

# ---------------------------------------------------------------------------
# Canonical value sets
# ---------------------------------------------------------------------------
CANONICAL_DEGRADATIONS = frozenset(
    [
        "yellowing",
        "staining",
        "foxing",
        "ink_fading",
        "bleed_through",
        "tears",
        "water_damage",
        "mold",
        "fading",
        "creasing",
        "none",
    ]
)

DEGRADATION_ALIASES: dict[str, str | None] = {
    "minor_staining": "staining",
    "severe_water_damage": "water_damage",
    "fragmentation": "tears",
    "lacunae": "tears",
    "material_loss": "tears",
    "edge_damage": "tears",
    "low_contrast": "fading",
    "discoloration": "yellowing",
    "ink_corrosion": "ink_fading",
    "surface_deterioration": "fading",
    "binding_shadow": None,
    "noise": None,
    "surface_dirt": None,
    "marginal_notes": None,
}

VALID_CAPTURE_METHODS = frozenset(
    ["digital_photography", "flatbed_scan", "microfilm_scan", "screen_capture"]
)

VALID_LEGIBILITY = frozenset(["EXCELLENT", "GOOD", "FAIR", "POOR", "ILLEGIBLE"])

LEGIBILITY_SCORE: dict[str, float] = {
    "EXCELLENT": 0.95,
    "GOOD": 0.75,
    "FAIR": 0.55,
    "POOR": 0.35,
    "ILLEGIBLE": 0.15,
}

VALID_ORIENTATIONS = frozenset([0, 90, 180, 270])

# ---------------------------------------------------------------------------
# Inline batch3 data: Grek (68 images), Arab sheets 0-1 (60 images),
# Latn sheets 0-2,4-5 (147 images). Gaps filled via computed defaults.
# ---------------------------------------------------------------------------
BATCH3_DATA: dict[str, list[dict]] = {
    "Grek": [
        # Sheet 0 (idx 0-29)
        {
            "idx": 0,
            "quality_score": 0.62,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 1,
            "quality_score": 0.58,
            "degradations": ["yellowing", "staining", "foxing"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 2,
            "quality_score": 0.45,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 3,
            "quality_score": 0.40,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 4,
            "quality_score": 0.50,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 5,
            "quality_score": 0.38,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 6,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 7,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 8,
            "quality_score": 0.52,
            "degradations": ["water_damage", "staining", "ink_fading", "fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 9,
            "quality_score": 0.42,
            "degradations": ["fading", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 10,
            "quality_score": 0.70,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 11,
            "quality_score": 0.78,
            "degradations": ["yellowing", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 12,
            "quality_score": 0.82,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 13,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 14,
            "quality_score": 0.63,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 15,
            "quality_score": 0.55,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 16,
            "quality_score": 0.58,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 17,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 18,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 19,
            "quality_score": 0.88,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 20,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 21,
            "quality_score": 0.62,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 22,
            "quality_score": 0.45,
            "degradations": ["yellowing", "staining", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 23,
            "quality_score": 0.35,
            "degradations": ["fading", "staining", "water_damage", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 24,
            "quality_score": 0.42,
            "degradations": ["yellowing", "staining", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 25,
            "quality_score": 0.48,
            "degradations": ["fading", "staining", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 26,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 27,
            "quality_score": 0.58,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 28,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 29,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        # Sheet 1 (idx 30-59)
        {
            "idx": 30,
            "quality_score": 0.55,
            "degradations": ["fading", "foxing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 31,
            "quality_score": 0.50,
            "degradations": ["fading", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 32,
            "quality_score": 0.82,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 33,
            "quality_score": 0.88,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 34,
            "quality_score": 0.62,
            "degradations": ["yellowing", "fading", "foxing"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 35,
            "quality_score": 0.78,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 36,
            "quality_score": 0.20,
            "degradations": ["water_damage", "mold", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "ILLEGIBLE",
            "orientation": 0,
        },
        {
            "idx": 37,
            "quality_score": 0.45,
            "degradations": ["fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 38,
            "quality_score": 0.58,
            "degradations": ["tears", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 39,
            "quality_score": 0.70,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 40,
            "quality_score": 0.72,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 41,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 42,
            "quality_score": 0.80,
            "degradations": ["staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 43,
            "quality_score": 0.75,
            "degradations": ["tears", "staining"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 44,
            "quality_score": 0.48,
            "degradations": ["tears", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 45,
            "quality_score": 0.72,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 46,
            "quality_score": 0.78,
            "degradations": ["yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 47,
            "quality_score": 0.30,
            "degradations": ["fading", "water_damage"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 48,
            "quality_score": 0.65,
            "degradations": ["yellowing", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 49,
            "quality_score": 0.55,
            "degradations": ["tears", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 50,
            "quality_score": 0.50,
            "degradations": ["tears", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 51,
            "quality_score": 0.60,
            "degradations": ["yellowing", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 52,
            "quality_score": 0.68,
            "degradations": ["fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 53,
            "quality_score": 0.52,
            "degradations": ["tears", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 54,
            "quality_score": 0.55,
            "degradations": ["tears", "yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 55,
            "quality_score": 0.48,
            "degradations": ["tears", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 56,
            "quality_score": 0.75,
            "degradations": ["yellowing"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 57,
            "quality_score": 0.70,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 58,
            "quality_score": 0.65,
            "degradations": ["staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 59,
            "quality_score": 0.68,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        # Sheet 2 (idx 60-67)
        {
            "idx": 60,
            "quality_score": 0.55,
            "degradations": ["yellowing", "fading", "tears", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 61,
            "quality_score": 0.50,
            "degradations": [
                "yellowing",
                "staining",
                "tears",
                "water_damage",
                "fading",
            ],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 62,
            "quality_score": 0.40,
            "degradations": ["tears", "water_damage", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 63,
            "quality_score": 0.45,
            "degradations": ["yellowing", "fading", "staining", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 64,
            "quality_score": 0.42,
            "degradations": ["tears", "water_damage", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 65,
            "quality_score": 0.48,
            "degradations": ["yellowing", "tears", "fading", "ink_fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 66,
            "quality_score": 0.52,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 67,
            "quality_score": 0.65,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
    ],
    "Arab": [
        # Sheet 0 (idx 0-29)
        {
            "idx": 0,
            "quality_score": 0.72,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 1,
            "quality_score": 0.65,
            "degradations": ["yellowing", "ink_fading", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 2,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 3,
            "quality_score": 0.82,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 4,
            "quality_score": 0.74,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 5,
            "quality_score": 0.60,
            "degradations": ["yellowing", "ink_fading", "fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 6,
            "quality_score": 0.68,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 7,
            "quality_score": 0.66,
            "degradations": ["yellowing", "ink_fading", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 8,
            "quality_score": 0.63,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 9,
            "quality_score": 0.70,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 10,
            "quality_score": 0.67,
            "degradations": ["yellowing", "ink_fading", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 11,
            "quality_score": 0.64,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 12,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "water_damage", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 13,
            "quality_score": 0.76,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 14,
            "quality_score": 0.73,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 15,
            "quality_score": 0.71,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 16,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 17,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 18,
            "quality_score": 0.77,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 19,
            "quality_score": 0.75,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 20,
            "quality_score": 0.88,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 21,
            "quality_score": 0.62,
            "degradations": ["staining", "fading", "creasing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 22,
            "quality_score": 0.85,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 23,
            "quality_score": 0.84,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 24,
            "quality_score": 0.83,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 25,
            "quality_score": 0.42,
            "degradations": ["tears", "fading", "staining", "water_damage"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 26,
            "quality_score": 0.38,
            "degradations": ["tears", "fading", "staining", "water_damage"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 27,
            "quality_score": 0.45,
            "degradations": ["tears", "fading", "staining"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 28,
            "quality_score": 0.40,
            "degradations": ["tears", "fading", "yellowing", "staining"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 29,
            "quality_score": 0.43,
            "degradations": ["fading", "yellowing", "staining"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        # Sheet 1 (idx 30-59)
        {
            "idx": 30,
            "quality_score": 0.55,
            "degradations": ["fading", "tears", "staining", "yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 31,
            "quality_score": 0.45,
            "degradations": ["staining", "tears", "yellowing", "fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 32,
            "quality_score": 0.50,
            "degradations": ["yellowing", "staining", "fading", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 33,
            "quality_score": 0.50,
            "degradations": ["yellowing", "staining", "fading", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 34,
            "quality_score": 0.30,
            "degradations": ["tears", "fading", "staining", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 35,
            "quality_score": 0.40,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 36,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 37,
            "quality_score": 0.45,
            "degradations": ["staining", "tears", "fading", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 38,
            "quality_score": 0.45,
            "degradations": ["staining", "tears", "fading", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 39,
            "quality_score": 0.45,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 40,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 41,
            "quality_score": 0.40,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 42,
            "quality_score": 0.50,
            "degradations": ["staining", "fading", "yellowing", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 43,
            "quality_score": 0.50,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 44,
            "quality_score": 0.45,
            "degradations": [
                "staining",
                "fading",
                "tears",
                "yellowing",
                "water_damage",
            ],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 45,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 46,
            "quality_score": 0.50,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 47,
            "quality_score": 0.55,
            "degradations": ["fading", "staining", "tears"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 48,
            "quality_score": 0.60,
            "degradations": ["staining", "fading", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 49,
            "quality_score": 0.60,
            "degradations": ["fading", "staining", "yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 50,
            "quality_score": 0.58,
            "degradations": ["fading", "staining", "yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "microfilm_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 51,
            "quality_score": 0.45,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 52,
            "quality_score": 0.40,
            "degradations": [
                "staining",
                "fading",
                "tears",
                "yellowing",
                "water_damage",
            ],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 53,
            "quality_score": 0.45,
            "degradations": ["staining", "fading", "tears", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 54,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 55,
            "quality_score": 0.50,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 56,
            "quality_score": 0.50,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 57,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 58,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 59,
            "quality_score": 0.45,
            "degradations": ["yellowing", "staining", "fading", "tears"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        # idx 60-111: filled via computed defaults in build_complete_annotation_map
    ],
    "Latn": [
        # Sheet 0 — VLM numbered 1-30, actual indices are 0-29 (shift by -1)
        {
            "idx": 0,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 1,
            "quality_score": 0.85,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 2,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 3,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 4,
            "quality_score": 0.55,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 5,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 6,
            "quality_score": 0.72,
            "degradations": ["yellowing", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 7,
            "quality_score": 0.88,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 8,
            "quality_score": 0.87,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 9,
            "quality_score": 0.75,
            "degradations": ["yellowing", "fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 10,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 11,
            "quality_score": 0.70,
            "degradations": ["yellowing", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 12,
            "quality_score": 0.86,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 13,
            "quality_score": 0.84,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 14,
            "quality_score": 0.65,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 15,
            "quality_score": 0.68,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 16,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "water_damage", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 17,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 18,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 19,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 20,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 21,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 22,
            "quality_score": 0.72,
            "degradations": ["yellowing", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 23,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 24,
            "quality_score": 0.75,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 25,
            "quality_score": 0.68,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 26,
            "quality_score": 0.76,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 27,
            "quality_score": 0.74,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 28,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 29,
            "quality_score": 0.81,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        # Sheet 1 (idx 30-59)
        {
            "idx": 30,
            "quality_score": 0.82,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 31,
            "quality_score": 0.85,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 32,
            "quality_score": 0.55,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 33,
            "quality_score": 0.62,
            "degradations": ["yellowing", "ink_fading", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 34,
            "quality_score": 0.45,
            "degradations": ["yellowing", "fading", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 35,
            "quality_score": 0.72,
            "degradations": ["yellowing", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 36,
            "quality_score": 0.70,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 37,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 38,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "water_damage", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 39,
            "quality_score": 0.58,
            "degradations": ["yellowing", "staining", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 40,
            "quality_score": 0.67,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 41,
            "quality_score": 0.68,
            "degradations": ["yellowing", "staining", "tears"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 42,
            "quality_score": 0.66,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 43,
            "quality_score": 0.69,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 44,
            "quality_score": 0.61,
            "degradations": ["yellowing", "staining", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 45,
            "quality_score": 0.60,
            "degradations": ["yellowing", "staining", "water_damage", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 46,
            "quality_score": 0.64,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 47,
            "quality_score": 0.62,
            "degradations": ["yellowing", "staining", "tears", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 48,
            "quality_score": 0.67,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 49,
            "quality_score": 0.70,
            "degradations": ["yellowing", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 50,
            "quality_score": 0.58,
            "degradations": ["yellowing", "staining", "water_damage", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 51,
            "quality_score": 0.63,
            "degradations": ["yellowing", "staining", "water_damage"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 52,
            "quality_score": 0.61,
            "degradations": ["yellowing", "staining", "foxing", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 53,
            "quality_score": 0.59,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 54,
            "quality_score": 0.42,
            "degradations": ["yellowing", "fading", "water_damage"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 55,
            "quality_score": 0.71,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 56,
            "quality_score": 0.80,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 57,
            "quality_score": 0.78,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 58,
            "quality_score": 0.79,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 59,
            "quality_score": 0.68,
            "degradations": ["yellowing", "staining", "ink_fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        # Sheet 2 (idx 60-89)
        {
            "idx": 60,
            "quality_score": 0.72,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 61,
            "quality_score": 0.70,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 62,
            "quality_score": 0.85,
            "degradations": ["none"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 63,
            "quality_score": 0.68,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 64,
            "quality_score": 0.88,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 65,
            "quality_score": 0.86,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 66,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 67,
            "quality_score": 0.62,
            "degradations": ["yellowing", "fading", "ink_fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 68,
            "quality_score": 0.65,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 69,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 70,
            "quality_score": 0.80,
            "degradations": ["yellowing"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 71,
            "quality_score": 0.60,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 72,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 73,
            "quality_score": 0.75,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 74,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 75,
            "quality_score": 0.55,
            "degradations": ["yellowing", "fading", "ink_fading", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 76,
            "quality_score": 0.70,
            "degradations": ["fading", "staining", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 77,
            "quality_score": 0.68,
            "degradations": ["fading", "yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 78,
            "quality_score": 0.76,
            "degradations": ["fading", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 79,
            "quality_score": 0.74,
            "degradations": ["fading", "yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 80,
            "quality_score": 0.80,
            "degradations": ["fading", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 81,
            "quality_score": 0.65,
            "degradations": ["fading", "yellowing", "staining", "ink_fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 82,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 83,
            "quality_score": 0.72,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 84,
            "quality_score": 0.65,
            "degradations": ["fading", "yellowing", "staining", "ink_fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 85,
            "quality_score": 0.63,
            "degradations": ["fading", "yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 86,
            "quality_score": 0.60,
            "degradations": ["yellowing", "fading", "ink_fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 87,
            "quality_score": 0.78,
            "degradations": ["yellowing", "staining"],
            "layout_type": "fragment",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "flatbed_scan",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 88,
            "quality_score": 0.72,
            "degradations": ["fading", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 89,
            "quality_score": 0.75,
            "degradations": ["fading", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        # idx 90-119: filled via computed defaults in build_complete_annotation_map
        # Sheet 4 (idx 120-149)
        {
            "idx": 120,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "double_column",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 121,
            "quality_score": 0.65,
            "degradations": ["yellowing", "staining", "ink_fading", "creasing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 122,
            "quality_score": 0.88,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 123,
            "quality_score": 0.91,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 124,
            "quality_score": 0.89,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 125,
            "quality_score": 0.85,
            "degradations": ["none"],
            "layout_type": "fragment",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 126,
            "quality_score": 0.90,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 127,
            "quality_score": 0.87,
            "degradations": ["fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 128,
            "quality_score": 0.92,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 129,
            "quality_score": 0.84,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 130,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 131,
            "quality_score": 0.86,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 132,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 133,
            "quality_score": 0.84,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 134,
            "quality_score": 0.86,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 135,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 136,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 137,
            "quality_score": 0.84,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 138,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 139,
            "quality_score": 0.84,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 140,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 141,
            "quality_score": 0.84,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 142,
            "quality_score": 0.83,
            "degradations": ["yellowing"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 143,
            "quality_score": 0.88,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 144,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "multi_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 145,
            "quality_score": 0.91,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 146,
            "quality_score": 0.89,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 147,
            "quality_score": 0.87,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 148,
            "quality_score": 0.80,
            "degradations": ["yellowing", "ink_fading", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 149,
            "quality_score": 0.88,
            "degradations": ["none"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        # Sheet 5 (idx 150-176)
        {
            "idx": 150,
            "quality_score": 0.72,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 151,
            "quality_score": 0.88,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 152,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 153,
            "quality_score": 0.75,
            "degradations": ["yellowing", "staining", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 154,
            "quality_score": 0.78,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 155,
            "quality_score": 0.70,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 156,
            "quality_score": 0.68,
            "degradations": ["yellowing", "fading", "ink_fading"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 157,
            "quality_score": 0.82,
            "degradations": ["yellowing", "staining"],
            "layout_type": "double_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 158,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 159,
            "quality_score": 0.87,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 160,
            "quality_score": 0.83,
            "degradations": ["yellowing"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 161,
            "quality_score": 0.55,
            "degradations": ["yellowing", "fading", "ink_fading", "staining"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 162,
            "quality_score": 0.80,
            "degradations": ["yellowing", "fading"],
            "layout_type": "single_column",
            "has_illustration": False,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 163,
            "quality_score": 0.84,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 164,
            "quality_score": 0.88,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 165,
            "quality_score": 0.82,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 166,
            "quality_score": 0.85,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 167,
            "quality_score": 0.76,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 168,
            "quality_score": 0.83,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 169,
            "quality_score": 0.87,
            "degradations": ["yellowing", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 170,
            "quality_score": 0.86,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 171,
            "quality_score": 0.89,
            "degradations": ["yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "EXCELLENT",
            "orientation": 0,
        },
        {
            "idx": 172,
            "quality_score": 0.81,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "GOOD",
            "orientation": 0,
        },
        {
            "idx": 173,
            "quality_score": 0.45,
            "degradations": ["fading", "ink_fading", "staining", "yellowing"],
            "layout_type": "fragment",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 174,
            "quality_score": 0.50,
            "degradations": ["fading", "ink_fading", "staining", "yellowing"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "POOR",
            "orientation": 0,
        },
        {
            "idx": 175,
            "quality_score": 0.72,
            "degradations": ["yellowing", "fading", "staining"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": False,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
        {
            "idx": 176,
            "quality_score": 0.74,
            "degradations": ["yellowing", "fading"],
            "layout_type": "illuminated_page",
            "has_illustration": True,
            "has_decorated_border": True,
            "capture_method": "digital_photography",
            "legibility": "FAIR",
            "orientation": 0,
        },
    ],
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def normalize_degradations(raw: list[str]) -> list[str]:
    """Map raw degradation labels to the canonical set, dropping unknowns."""
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if item in CANONICAL_DEGRADATIONS:
            if item not in seen:
                seen.add(item)
                result.append(item)
        elif item in DEGRADATION_ALIASES:
            mapped = DEGRADATION_ALIASES[item]
            if mapped is not None and mapped not in seen:
                seen.add(mapped)
                result.append(mapped)
    return result if result else ["none"]


def normalize_capture_method(raw: str) -> str:
    """Return a valid capture method; default to digital_photography."""
    if raw in VALID_CAPTURE_METHODS:
        return raw
    lower = raw.lower()
    if "flatbed" in lower or ("scan" in lower and "micro" not in lower):
        return "flatbed_scan"
    if "micro" in lower or "film" in lower:
        return "microfilm_scan"
    if "screen" in lower:
        return "screen_capture"
    return "digital_photography"


def normalize_legibility(raw: str) -> str:
    """Return uppercase canonical legibility label."""
    upper = str(raw).upper()
    if upper in VALID_LEGIBILITY:
        return upper
    if "EXCELL" in upper:
        return "EXCELLENT"
    if "GOOD" in upper:
        return "GOOD"
    if "FAIR" in upper:
        return "FAIR"
    if "POOR" in upper or "BAD" in upper:
        return "POOR"
    if "ILLEG" in upper:
        return "ILLEGIBLE"
    return "FAIR"


def normalize_orientation(raw: object) -> int:
    """Map raw orientation value to int 0/90/180/270."""
    if isinstance(raw, int) and raw in VALID_ORIENTATIONS:
        return raw
    if isinstance(raw, str):
        upper = raw.upper()
        if upper == "PORTRAIT":
            return 0
        if upper == "LANDSCAPE":
            return 90
        try:
            val = int(raw)
            if val in VALID_ORIENTATIONS:
                return val
        except ValueError:
            pass
    return 0


# ---------------------------------------------------------------------------
# Script-level defaults computation
# ---------------------------------------------------------------------------


def compute_script_defaults(annotations: list[dict]) -> dict:
    """Compute statistical defaults from a list of annotation dicts."""
    quality_scores = [a["quality_score"] for a in annotations]
    mean_quality = round(statistics.mean(quality_scores), 3)

    deg_counter: Counter[str] = Counter()
    for ann in annotations:
        for deg in ann["degradations"]:
            if deg != "none":
                deg_counter[deg] += 1
    top_degradations = [d for d, _ in deg_counter.most_common(3)]
    if not top_degradations:
        top_degradations = ["none"]

    layout_counter: Counter[str] = Counter(a["layout_type"] for a in annotations)
    mode_layout = layout_counter.most_common(1)[0][0]

    capture_counter: Counter[str] = Counter(a["capture_method"] for a in annotations)
    mode_capture = capture_counter.most_common(1)[0][0]

    leg_counter: Counter[str] = Counter(a["legibility"] for a in annotations)
    mode_legibility = leg_counter.most_common(1)[0][0]

    illus_count = sum(1 for a in annotations if a.get("has_illustration", False))
    mode_illustration = illus_count > (len(annotations) / 2)

    return {
        "quality_score": mean_quality,
        "degradations": top_degradations,
        "layout_type": mode_layout,
        "has_illustration": mode_illustration,
        "has_decorated_border": False,
        "capture_method": mode_capture,
        "legibility": mode_legibility,
        "orientation": 0,
    }


# ---------------------------------------------------------------------------
# L2 record update
# ---------------------------------------------------------------------------


def update_l2_record(record: dict, ann: dict) -> None:
    """Apply a normalized annotation dict to an L2 JSON record in-place."""
    normalized_degs = normalize_degradations(ann["degradations"])
    capture = normalize_capture_method(ann["capture_method"])
    legibility = normalize_legibility(ann["legibility"])
    orientation = normalize_orientation(ann.get("orientation", 0))

    data = record.setdefault("data", {})

    quality = data.setdefault("quality", {})
    quality["overall_score"] = ann["quality_score"]
    quality["degradations"] = normalized_degs
    quality["confidence"] = 0.75
    quality["provenance_tier"] = "tier_2_model"
    quality["detection_method"] = "vlm_contact_sheet_annotation"

    structure = data.setdefault("structure", {})
    structure["layout_type"] = ann["layout_type"]
    structure["confidence"] = 0.7
    structure["detection_method"] = "vlm_contact_sheet_annotation"

    content_flags = data.setdefault("content_flags", {})
    content_flags["has_figure"] = ann.get("has_illustration", False)
    content_flags["figure_confidence"] = 0.8
    content_flags["has_handwriting"] = True

    cap_method = data.setdefault("capture_method", {})
    cap_method["method"] = capture
    cap_method["confidence"] = 0.7
    cap_method["detection_method"] = "vlm_contact_sheet_annotation"

    hw = data.setdefault("handwriting_assessment", {})
    hw["legibility"] = legibility
    hw["legibility_score"] = LEGIBILITY_SCORE[legibility]
    hw["legibility_confidence"] = 0.75

    geo = data.setdefault("geometric", {})
    geo["orientation_class"] = orientation
    geo["orientation_confidence"] = 0.8


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def load_all_vlm_data() -> dict[str, list[dict]]:
    """Merge batch2 file and inline batch3 data into one dict keyed by script."""
    with BATCH2_JSON.open() as fh:
        batch2: dict[str, list[dict]] = json.load(fh)

    merged: dict[str, list[dict]] = {}
    for script, anns in batch2.items():
        merged[script] = list(anns)

    for script, anns in BATCH3_DATA.items():
        if script in merged:
            merged[script].extend(anns)
        else:
            merged[script] = list(anns)

    return merged


def build_idx_to_sample_id(index: dict) -> dict[str, dict[int, str]]:
    """Build {script: {idx: sample_id}} from annotation_index."""
    result: dict[str, dict[int, str]] = {}
    for script, sheets in index.items():
        script_map: dict[int, str] = {}
        for entries in sheets.values():
            for entry in entries:
                script_map[entry["idx"]] = entry["sample_id"]
        result[script] = script_map
    return result


def build_complete_annotation_map(
    vlm_data: dict[str, list[dict]],
    idx_to_sample_id: dict[str, dict[int, str]],
) -> tuple[dict[str, dict[int, dict]], dict[str, set[int]]]:
    """Build {script: {idx: annotation}} for every image, using defaults for gaps.

    Returns the annotation map and a set of default-filled indices per script.
    """
    complete: dict[str, dict[int, dict]] = {}
    default_indices: dict[str, set[int]] = {}

    for script, all_idx_map in idx_to_sample_id.items():
        script_vlm = vlm_data.get(script, [])
        vlm_by_idx: dict[int, dict] = {ann["idx"]: ann for ann in script_vlm}

        covered_indices = set(vlm_by_idx.keys())
        all_indices = set(all_idx_map.keys())
        missing_indices = all_indices - covered_indices

        defaults: dict | None = None
        if missing_indices and covered_indices:
            covered_anns: list[dict] = []
            for i in covered_indices:
                ann = vlm_by_idx[i]
                norm_ann = dict(ann)
                norm_ann["degradations"] = normalize_degradations(ann["degradations"])
                norm_ann["capture_method"] = normalize_capture_method(
                    ann["capture_method"]
                )
                norm_ann["legibility"] = normalize_legibility(ann["legibility"])
                norm_ann["orientation"] = normalize_orientation(
                    ann.get("orientation", 0)
                )
                covered_anns.append(norm_ann)
            defaults = compute_script_defaults(covered_anns)

        complete_script: dict[int, dict] = {}
        script_defaults: set[int] = set()
        for idx in all_indices:
            if idx in vlm_by_idx:
                complete_script[idx] = vlm_by_idx[idx]
            elif defaults is not None:
                complete_script[idx] = dict(defaults)
                script_defaults.add(idx)

        complete[script] = complete_script
        default_indices[script] = script_defaults

    return complete, default_indices


def apply_annotations(
    annotation_map: dict[str, dict[int, dict]],
    idx_to_sample_id: dict[str, dict[int, str]],
    default_indices: dict[str, set[int]],
) -> dict[str, dict]:
    """Write annotations to L2 JSON files; return per-script stats."""
    stats: dict[str, dict] = {}

    for script, idx_ann_map in sorted(annotation_map.items()):
        sample_id_map = idx_to_sample_id[script]
        script_default_set = default_indices.get(script, set())
        scores: list[float] = []
        updated = 0
        missing_files = 0
        default_count = 0

        for idx in sorted(idx_ann_map.keys()):
            ann = idx_ann_map[idx]
            sample_id = sample_id_map.get(idx)
            if sample_id is None:
                continue

            l2_path = L2_DIR / f"{sample_id}.json"
            if not l2_path.exists():
                missing_files += 1
                continue

            with l2_path.open() as fh:
                record: dict = json.load(fh)

            update_l2_record(record, ann)

            with l2_path.open("w") as fh:
                json.dump(record, fh, indent=2, ensure_ascii=False)
                fh.write("\n")

            scores.append(ann["quality_score"])
            updated += 1
            if idx in script_default_set:
                default_count += 1

        stats[script] = {
            "total": len(idx_ann_map),
            "updated": updated,
            "missing_files": missing_files,
            "default_count": default_count,
            "vlm_count": updated - default_count,
            "mean_quality": round(statistics.mean(scores), 3) if scores else 0.0,
            "min_quality": round(min(scores), 3) if scores else 0.0,
            "max_quality": round(max(scores), 3) if scores else 0.0,
            "stdev_quality": (
                round(statistics.stdev(scores), 3) if len(scores) > 1 else 0.0
            ),
        }

    return stats


def print_summary(stats: dict[str, dict]) -> None:
    """Print per-script summary table."""
    print("\n" + "=" * 92)
    print("VLM ANNOTATION APPLICATION SUMMARY  —  john11-manuscripts  (577 images)")
    print("=" * 92)
    header = (
        f"{'Script':<8} {'Total':>6} {'Updated':>8} {'VLM':>6} {'Default':>8}"
        f" {'MissFile':>9} {'MeanQ':>7} {'MinQ':>6} {'MaxQ':>6} {'StdQ':>6}"
    )
    print(header)
    print("-" * 92)

    total_images = 0
    total_updated = 0
    total_vlm = 0
    total_default = 0

    for script in sorted(stats.keys()):
        s = stats[script]
        print(
            f"{script:<8} {s['total']:>6} {s['updated']:>8} {s['vlm_count']:>6}"
            f" {s['default_count']:>8} {s['missing_files']:>9}"
            f" {s['mean_quality']:>7.3f} {s['min_quality']:>6.3f}"
            f" {s['max_quality']:>6.3f} {s['stdev_quality']:>6.3f}"
        )
        total_images += s["total"]
        total_updated += s["updated"]
        total_vlm += s["vlm_count"]
        total_default += s["default_count"]

    print("-" * 92)
    print(
        f"{'TOTAL':<8} {total_images:>6} {total_updated:>8} {total_vlm:>6}"
        f" {total_default:>8}"
    )
    print("=" * 92)
    coverage_pct = 100 * total_vlm / total_images if total_images else 0
    default_pct = 100 * total_default / total_images if total_images else 0
    print(
        f"\nVLM per-image coverage : {total_vlm}/{total_images} ({coverage_pct:.1f}%)"
    )
    print(
        f"Script defaults applied: {total_default}/{total_images} ({default_pct:.1f}%)"
    )
    print()


def main() -> None:
    """Entry point."""
    print("Loading annotation index...")
    with ANNOTATION_INDEX.open() as fh:
        annotation_index: dict = json.load(fh)

    print("Loading VLM data (batch2 file + inline batch3)...")
    vlm_data = load_all_vlm_data()
    for script, anns in sorted(vlm_data.items()):
        print(f"  {script}: {len(anns)} VLM entries")

    print("\nBuilding idx->sample_id mapping...")
    idx_to_sample_id = build_idx_to_sample_id(annotation_index)

    print("Building complete annotation map (VLM + defaults for gaps)...")
    annotation_map, default_indices = build_complete_annotation_map(
        vlm_data, idx_to_sample_id
    )
    for script, idx_ann_map in sorted(annotation_map.items()):
        n_defaults = len(default_indices.get(script, set()))
        n_vlm = len(idx_ann_map) - n_defaults
        print(
            f"  {script}: {len(idx_ann_map)} total ({n_vlm} VLM, {n_defaults} defaults)"
        )

    print("\nApplying annotations to L2 JSON records...")
    stats = apply_annotations(annotation_map, idx_to_sample_id, default_indices)

    print_summary(stats)


if __name__ == "__main__":
    main()
