"""Tests for metrics module stub implementations.

Tests for scenarios when prometheus_client is not available.
"""

from unittest.mock import patch

import pytest


class TestMetricsWithoutPrometheus:
    """Tests for metrics module when prometheus_client is not available."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        import image_preprocessing_detector.monitoring as monitoring
        from image_preprocessing_detector.monitoring import (
            MetricsCollector,
        )

        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        monitoring._metrics = None

    def test_get_metrics_without_prometheus(self) -> None:
        """Test get_metrics returns stub message when prometheus not available."""
        # Import module and patch PROMETHEUS_AVAILABLE
        import image_preprocessing_detector.monitoring as monitoring

        original_available = monitoring.PROMETHEUS_AVAILABLE

        try:
            # Set prometheus as not available
            monitoring.PROMETHEUS_AVAILABLE = False

            # Create a collector and get metrics
            collector = monitoring.MetricsCollector()
            result = collector.get_metrics()

            assert result == b"# prometheus_client not installed\n"
        finally:
            # Restore original state
            monitoring.PROMETHEUS_AVAILABLE = original_available

    def test_start_server_without_prometheus(self) -> None:
        """Test start_server does nothing when prometheus not available."""
        import image_preprocessing_detector.monitoring as monitoring

        original_available = monitoring.PROMETHEUS_AVAILABLE

        try:
            monitoring.PROMETHEUS_AVAILABLE = False

            collector = monitoring.MetricsCollector()
            # Should not raise, just return early
            collector.start_server(port=9999)

        finally:
            monitoring.PROMETHEUS_AVAILABLE = original_available

    def test_start_server_with_prometheus(self) -> None:
        """Test start_server calls start_http_server when prometheus available."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            pytest.skip("prometheus_client not installed")

        collector = monitoring.MetricsCollector()

        with patch.object(monitoring, "start_http_server") as mock_server:
            collector.start_server(port=8080)
            mock_server.assert_called_once()


class TestStubImplementations:
    """Tests for stub class implementations."""

    def test_stub_counter(self) -> None:
        """Test stub Counter implementation."""
        # Import the stub implementations
        import image_preprocessing_detector.monitoring as monitoring

        # Create stub if prometheus not available, or test passes anyway
        if not monitoring.PROMETHEUS_AVAILABLE:
            counter = monitoring.Counter("test_counter", "Test counter")
            labeled = counter.labels(label1="value1")
            # These should not raise
            labeled.inc()
            labeled.inc(5)

    def test_stub_gauge(self) -> None:
        """Test stub Gauge implementation."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            gauge = monitoring.Gauge("test_gauge", "Test gauge")
            labeled = gauge.labels(label1="value1")
            labeled.set(42)
            labeled.inc()
            labeled.inc(5)
            labeled.dec()
            labeled.dec(3)

    def test_stub_histogram(self) -> None:
        """Test stub Histogram implementation."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            histogram = monitoring.Histogram(
                "test_histogram", "Test histogram", buckets=[0.1, 0.5, 1.0]
            )
            labeled = histogram.labels(label1="value1")
            labeled.observe(0.25)

    def test_stub_info(self) -> None:
        """Test stub Info implementation."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            info = monitoring.Info("test_info", "Test info")
            info.info({"key": "value"})

    def test_stub_generate_latest(self) -> None:
        """Test stub generate_latest returns empty bytes."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            result = monitoring.generate_latest()
            assert result == b""

    def test_stub_start_http_server(self) -> None:
        """Test stub start_http_server does nothing."""
        import image_preprocessing_detector.monitoring as monitoring

        if not monitoring.PROMETHEUS_AVAILABLE:
            # Should not raise
            monitoring.start_http_server(8000)


class TestMetricsConfigStartServer:
    """Tests for MetricsConfig with server startup."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset the singleton before each test."""
        import image_preprocessing_detector.monitoring as monitoring
        from image_preprocessing_detector.monitoring import MetricsCollector

        MetricsCollector._instance = None
        MetricsCollector._initialized = False
        monitoring._metrics = None

    def test_config_with_start_server_false(self) -> None:
        """Test MetricsConfig with start_server=False."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        config = MetricsConfig(start_server=False)
        assert config.start_server is False

    def test_config_with_custom_port(self) -> None:
        """Test MetricsConfig with custom port."""
        from image_preprocessing_detector.monitoring import MetricsConfig

        config = MetricsConfig(port=9090)
        assert config.port == 9090
