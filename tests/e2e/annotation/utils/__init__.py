"""Utilities for E2E annotation tests.

Contains:
- Error injection utilities for testing failure scenarios
- Test data generators
- Validation helpers
"""

from .error_injection import (
    inject_disk_full,
    inject_enrichment_failure,
    inject_permission_denied,
)

__all__ = [
    "inject_enrichment_failure",
    "inject_disk_full",
    "inject_permission_denied",
]
