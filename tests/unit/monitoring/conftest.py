"""Pytest fixtures for monitoring tests.

Handles Prometheus registry isolation to prevent duplicate metric registration
errors when running multiple tests.
"""

import pytest

# Try to import prometheus_client for cleanup
try:
    from prometheus_client import REGISTRY

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    REGISTRY = None


@pytest.fixture(autouse=True)
def reset_metrics_collector() -> None:
    """Reset MetricsCollector singleton and Prometheus registry between tests.

    This fixture runs automatically before each test to ensure clean state.
    """
    # Import here to avoid circular imports
    from image_preprocessing_detector.monitoring import MetricsCollector

    # Reset the singleton
    MetricsCollector._instance = None
    MetricsCollector._initialized = False

    # Clean up Prometheus registry if available
    if PROMETHEUS_AVAILABLE and REGISTRY is not None:
        # Get all collector names that start with our namespace prefixes
        collectors_to_remove = [*REGISTRY._names_to_collectors.values()]

        # Unregister each collector
        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                # Ignore errors during cleanup
                pass
