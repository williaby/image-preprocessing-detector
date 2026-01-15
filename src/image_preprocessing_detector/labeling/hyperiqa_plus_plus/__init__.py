# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""HyperIQA++ Enhanced Document IQA Model.

This module implements HyperIQA++ with 7 research-validated enhancements
for document image quality assessment:

1. High-resolution input (1600x1600) - DocIQ
2. Soft label distribution prediction - DeQA-Doc
3. Multi-scale feature fusion - DocIQ
4. Spatial attention - DocIQ-Simplified
5. PCGrad optimizer - VQualA 2025
6. NormInNormLoss - Li et al. 2020
7. Extended training (60 epochs) - DocIQ

Target Performance: 0.85 PLCC on DIQA-5000 test set

References:
    - DocIQ: arXiv:2509.17012
    - DeQA-Doc: arXiv:2507.12796
    - NormInNormLoss: Li et al., ACM MM 2020
"""

from image_preprocessing_detector.labeling.hyperiqa_plus_plus.loss import (
    MultiTaskIQALoss,
    NormInNormLoss,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.model import (
    HyperIQAPlusPlus,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.modules import (
    MultiScaleFeatureFusion,
    SoftLabelHead,
    SpatialAttentionModule,
)
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.pcgrad import PCGrad
from image_preprocessing_detector.labeling.hyperiqa_plus_plus.utils import (
    create_soft_labels,
)

__all__ = [
    "HyperIQAPlusPlus",
    "MultiScaleFeatureFusion",
    "MultiTaskIQALoss",
    "NormInNormLoss",
    "PCGrad",
    "SoftLabelHead",
    "SpatialAttentionModule",
    "create_soft_labels",
]
