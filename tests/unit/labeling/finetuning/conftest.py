# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Pytest configuration for finetuning tests.

This conftest ensures proper test isolation for tests that use mocking
to avoid interference between test classes.
"""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def ensure_real_albumentations():
    """Ensure albumentations is the real module, not a mock.

    Other test files (like test_generate_100k_iqa_dataset.py) mock
    albumentations at module level. This fixture removes any mock
    before running tests that need the real module.
    """
    # Check if albumentations is mocked
    if "albumentations" in sys.modules:
        alb = sys.modules["albumentations"]
        if isinstance(alb, MagicMock):
            # Remove the mock so real import happens
            del sys.modules["albumentations"]

    # Also clear our module that imports albumentations
    modules_to_clear = [
        "image_preprocessing_detector.labeling.finetuning.musiq_dataset",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    # No teardown needed - setup-only fixture
