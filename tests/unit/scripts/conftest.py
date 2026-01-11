# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Pytest configuration for scripts tests.

This conftest ensures proper cleanup of module mocks to prevent
test pollution across test files.
"""

import sys

import pytest


@pytest.fixture(scope="module", autouse=True)
def cleanup_module_mocks():
    """Clean up module-level mocks after all tests in this directory.

    Some script tests mock modules like albumentations at the module level.
    This fixture ensures those mocks are removed after the tests complete
    to prevent pollution of other test files.
    """
    # Track modules that might be mocked
    mocked_modules = ["albumentations", "datasets"]

    # Store original state
    original_modules = {}
    for mod in mocked_modules:
        if mod in sys.modules:
            original_modules[mod] = sys.modules[mod]

    yield

    # Restore or remove mocked modules
    for mod in mocked_modules:
        if mod in original_modules:
            # Module existed before, restore it
            sys.modules[mod] = original_modules[mod]
        elif mod in sys.modules:
            # Module didn't exist before but was added (mocked), remove it
            del sys.modules[mod]
