---
owner: docs-team
purpose: Augmentation pipeline module documentation for synthetic generation.
schema_type: common
status: active
tags:
- architecture
- level_3
- synthetic_generation
- augmentation
title: "Augmentation Pipeline - Hybrid Architecture"
---

# Augmentation Pipeline - Hybrid Architecture

**Parent**: [Level 3 Synthetic Generation Index](index.md)
**Primary Source**: `src/.../synthetic/augmentation_hybrid.py` (~350 LOC)

## Overview

The synthetic generation pipeline uses a hybrid augmentation architecture that applies document aging effects to rendered synthetic images. Three aging profiles (MODERN, AGED, HISTORICAL) create diversity in the training data to improve model robustness across document conditions.

## Transform Ordering (Critical)

A key architectural constraint is the ordering of geometric transforms relative to augmentation:

```
1. Text Rendering (clean image)
2. Geometric Transforms (orientation + skew)     <-- FIRST
3. Augmentation Pipeline (aging + degradation)    <-- SECOND
4. Post-Processing (measurement + metadata)
```

**Why this order matters**: Applying geometric transforms (rotation, skew) after augmentation would rotate noise patterns and aging artifacts, creating unrealistic "rotated noise" that doesn't appear in real documents. Real-world documents are aged/degraded *in place*, then possibly scanned at an angle.

**Bug Fix (2026-02-09)**: The pipeline previously applied augmentation before geometric transforms. The `_apply_geometric_transforms()` method was extracted and moved to operate on the clean rendered image before any degradation is applied.

## Document Age Profiles

### MODERN (80% probability)

No aging effects applied. The image retains its clean rendered appearance with only the geometric transforms (orientation, skew) and color mode conversion.

### AGED (15% probability)

Simulates documents that are 10-50 years old:

| Effect | Implementation | Parameters |
|--------|---------------|------------|
| Yellowing | Sepia color shift | Hue shift: 20-30, Saturation boost: 10-20% |
| Foxing | Random brown patches | 5-15 spots, radius 2-8px, opacity 0.3-0.6 |
| Ink Fading | Contrast reduction | 10-20% reduction, applied to text regions |
| Paper texture | Subtle noise | Gaussian noise sigma 3-8 |

### HISTORICAL (5% probability)

Simulates documents 50+ years old with significant degradation:

| Effect | Implementation | Parameters |
|--------|---------------|------------|
| Heavy yellowing | Strong sepia shift | Hue shift: 35-50, Saturation boost: 25-40% |
| Dense foxing | Many brown patches | 20-40 spots, radius 3-12px, opacity 0.5-0.8 |
| Severe ink fading | Major contrast loss | 30-50% reduction |
| Edge degradation | Border erosion | 2-5px irregular edge removal |
| Paper warping | Subtle distortion | Low-frequency sinusoidal warp, amplitude 1-3px |

## DPI Tier Selection

7 tiers with weighted random selection:

| Tier | DPI | Weight | Typical Use Case |
|------|-----|--------|-----------------|
| SCREEN_LOW | 72 | 5% | Web screenshots |
| SCREEN_STANDARD | 100 | 8% | Digital documents |
| PRINT_LOW | 150 | 12% | Low-quality prints |
| PRINT_STANDARD | 200 | 15% | Standard prints |
| STANDARD | 300 | 35% | Default scanning DPI |
| HIGH | 400 | 15% | High-quality scans |
| ARCHIVAL | 600 | 10% | Archival scanning |

**Safety Rails**: DPI values are clamped to 150-600 range for training. Values below 150 produce characters too small for reliable detection; values above 600 provide diminishing returns.

**Character Height Target**: 32-48px optimal for SigLIP 2 ViT-B/16 patch size (16px). The `_measure_char_height()` method validates this after rendering.

## Color Mode Distribution

| Mode | Probability | Channels | Use Case |
|------|-------------|----------|----------|
| COLOR | 60% | RGB (3) | Born-digital, color scans |
| GRAYSCALE | 30% | L (1) | B&W scans, photocopies |
| BINARIZED | 10% | 1-bit | OCR-optimized, fax documents |

Color mode is applied as a post-processing step after augmentation, ensuring aging effects interact correctly with the color space.

## Configuration

All augmentation parameters are defined in `src/.../synthetic/config.py` using Pydantic v2 models:

```python
class AugmentationConfig(BaseModel):
    aged_probability: float = 0.15
    historical_probability: float = 0.05
    # Remaining probability = MODERN (0.80)

    foxing_min_spots: int = 5
    foxing_max_spots: int = 40
    yellowing_hue_range: tuple[int, int] = (20, 50)
    ink_fade_range: tuple[float, float] = (0.1, 0.5)
```

## Source Files

| File | LOC | Role |
|------|-----|------|
| `src/.../synthetic/augmentation_hybrid.py` | ~350 | HybridAugmenter class, aging profiles |
| `src/.../synthetic/config.py` | ~300 | DPI tiers, ColorMode, augmentation params |
| `src/.../synthetic/generator.py` | ~400 | `_apply_geometric_transforms()`, `_measure_char_height()` |

---

*Last Updated: February 2026*
