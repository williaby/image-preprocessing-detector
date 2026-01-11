# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Pytest configuration for finetuning tests.

This conftest ensures proper test isolation for tests that use mocking
to avoid interference between test classes.
"""

import sys

import pytest


@pytest.fixture(autouse=True)
def reset_module_cache():
    """Reset relevant modules from cache to ensure test isolation.

    This prevents mocked modules from leaking between test classes.
    The musiq_dataset module imports albumentations lazily, so clearing
    it ensures fresh imports for each test.
    """
    modules_to_reset = [
        "image_preprocessing_detector.labeling.finetuning.musiq_dataset",
        "image_preprocessing_detector.labeling.arena.datasets.base",
    ]

    # Store original modules
    original_modules = {}
    for mod in modules_to_reset:
        if mod in sys.modules:
            original_modules[mod] = sys.modules[mod]

    yield

    # Restore original modules after test
    for mod, original in original_modules.items():
        if original is not None:
            sys.modules[mod] = original
