"""Tests for drift alerting module - Sprint 6.3.3.

Tests for alert creation, thresholds, cooldown, and dispatch.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from image_preprocessing_detector.drift.alerting import (
    F1_DROP_CRITICAL_THRESHOLD,
    F1_DROP_WARNING_THRESHOLD,
    KL_CRITICAL_THRESHOLD,
    KL_WARNING_THRESHOLD,
    MAP_DROP_CRITICAL_THRESHOLD,
    MAP_DROP_WARNING_THRESHOLD,
    MAX_SAMPLES_IN_ALERT,
    PSI_CRITICAL_THRESHOLD,
    PSI_WARNING_THRESHOLD,
    AlertChannel,
    AlertConfig,
    AlertHistory,
    AlertManager,
    AlertSeverity,
    AlertType,
    DriftAlert,
    DriftSample,
    DryRunDispatcher,
    LogDispatcher,
    check_drift_and_alert,
    create_alert_manager,
)
from image_preprocessing_detector.utils.datetime_compat import utc_now

# ============================================================================
# DriftSample Tests
# ============================================================================


class TestDriftSample:
    """Tests for DriftSample data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        sample = DriftSample(
            sample_id="sample_001",
            value=0.85,
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            metadata={"source": "test"},
        )

        d = sample.to_dict()

        assert d["sample_id"] == "sample_001"
        assert d["value"] == 0.85
        assert d["metadata"]["source"] == "test"


# ============================================================================
# DriftAlert Tests
# ============================================================================


class TestDriftAlert:
    """Tests for DriftAlert data class."""

    def test_to_dict(self) -> None:
        """Test serialization."""
        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="quality_score",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test alert message",
            runbook_url="https://docs.example.com/runbooks/drift/kl_divergence",
        )

        d = alert.to_dict()

        assert d["alert_id"] == "test-001"
        assert d["alert_type"] == "kl_divergence"
        assert d["severity"] == "warning"
        assert d["feature"] == "quality_score"
        assert d["current_value"] == 0.35

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "alert_id": "test-001",
            "alert_type": "kl_divergence",
            "severity": "warning",
            "feature": "quality_score",
            "current_value": 0.35,
            "threshold": 0.30,
            "baseline_value": 0.0,
            "message": "Test alert",
            "timestamp": "2025-01-15T12:00:00",
        }

        alert = DriftAlert.from_dict(data)

        assert alert.alert_id == "test-001"
        assert alert.alert_type == AlertType.KL_DIVERGENCE
        assert alert.severity == AlertSeverity.WARNING

    def test_samples_limited_in_dict(self) -> None:
        """Test samples are limited in serialization."""
        samples = [
            DriftSample(sample_id=f"s{i}", value=float(i), timestamp=utc_now())
            for i in range(20)
        ]

        alert = DriftAlert(
            alert_id="test",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
            samples=samples,
        )

        d = alert.to_dict()

        assert len(d["samples"]) == MAX_SAMPLES_IN_ALERT


# ============================================================================
# AlertConfig Tests
# ============================================================================


class TestAlertConfig:
    """Tests for AlertConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AlertConfig()

        assert config.kl_warning == KL_WARNING_THRESHOLD
        assert config.kl_critical == KL_CRITICAL_THRESHOLD
        assert config.dry_run is False

    def test_to_dict(self) -> None:
        """Test serialization."""
        config = AlertConfig(dry_run=True)

        d = config.to_dict()

        assert d["dry_run"] is True
        assert d["kl_warning"] == KL_WARNING_THRESHOLD

    def test_from_dict(self) -> None:
        """Test deserialization."""
        data = {
            "kl_warning": 0.20,
            "kl_critical": 0.40,
            "dry_run": True,
        }

        config = AlertConfig.from_dict(data)

        assert config.kl_warning == 0.20
        assert config.kl_critical == 0.40
        assert config.dry_run is True

    def test_enabled_channels(self) -> None:
        """Test channel configuration."""
        config = AlertConfig(enabled_channels=[AlertChannel.LOG, AlertChannel.SLACK])

        assert AlertChannel.LOG in config.enabled_channels
        assert AlertChannel.SLACK in config.enabled_channels


# ============================================================================
# AlertHistory Tests
# ============================================================================


class TestAlertHistory:
    """Tests for AlertHistory."""

    def test_add_and_get_alert(self) -> None:
        """Test adding and retrieving alerts."""
        history = AlertHistory()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )

        history.add_alert(alert)

        retrieved = history.get_alert("test-001")
        assert retrieved is not None
        assert retrieved.alert_id == "test-001"

    def test_cooldown_check(self) -> None:
        """Test cooldown mechanism."""
        history = AlertHistory()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="quality_score",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )

        history.add_alert(alert)

        # Should be in cooldown
        in_cooldown = history.is_in_cooldown(
            AlertType.KL_DIVERGENCE, "quality_score", 60
        )
        assert in_cooldown is True

        # Different feature should not be in cooldown
        in_cooldown = history.is_in_cooldown(
            AlertType.KL_DIVERGENCE, "different_feature", 60
        )
        assert in_cooldown is False

    def test_get_recent_alerts(self) -> None:
        """Test retrieving recent alerts."""
        history = AlertHistory()

        for i in range(5):
            alert = DriftAlert(
                alert_id=f"test-{i}",
                alert_type=AlertType.KL_DIVERGENCE,
                severity=AlertSeverity.WARNING if i < 3 else AlertSeverity.CRITICAL,
                feature="test",
                current_value=0.35,
                threshold=0.30,
                baseline_value=0.0,
                message="Test",
            )
            history.add_alert(alert)

        # Get all recent
        recent = history.get_recent_alerts(hours=1)
        assert len(recent) == 5

        # Filter by severity
        warnings = history.get_recent_alerts(hours=1, severity=AlertSeverity.WARNING)
        assert len(warnings) == 3

        critical = history.get_recent_alerts(hours=1, severity=AlertSeverity.CRITICAL)
        assert len(critical) == 2

    def test_acknowledge_alert(self) -> None:
        """Test acknowledging alerts."""
        history = AlertHistory()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )

        history.add_alert(alert)

        result = history.acknowledge_alert("test-001")
        assert result is True

        retrieved = history.get_alert("test-001")
        assert retrieved is not None
        assert retrieved.acknowledged is True

    def test_resolve_alert(self) -> None:
        """Test resolving alerts."""
        history = AlertHistory()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )

        history.add_alert(alert)

        result = history.resolve_alert("test-001")
        assert result is True

        retrieved = history.get_alert("test-001")
        assert retrieved is not None
        assert retrieved.resolved is True

    def test_persistence(self) -> None:
        """Test alert history persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and add alert
            history1 = AlertHistory(tmpdir)

            alert = DriftAlert(
                alert_id="test-001",
                alert_type=AlertType.KL_DIVERGENCE,
                severity=AlertSeverity.WARNING,
                feature="test",
                current_value=0.35,
                threshold=0.30,
                baseline_value=0.0,
                message="Test",
            )

            history1.add_alert(alert)

            # Create new instance (should load from disk)
            history2 = AlertHistory(tmpdir)

            retrieved = history2.get_alert("test-001")
            assert retrieved is not None

    def test_cleanup_old_alerts(self) -> None:
        """Test cleaning up old alerts."""
        history = AlertHistory(retention_days=1)

        # Add old alert (manually set timestamp)
        old_alert = DriftAlert(
            alert_id="old-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
            timestamp=utc_now() - timedelta(days=5),
        )
        history._alerts[old_alert.alert_id] = old_alert

        # Add recent alert
        recent_alert = DriftAlert(
            alert_id="recent-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )
        history.add_alert(recent_alert)

        removed = history.cleanup_old_alerts()

        assert removed == 1
        assert history.get_alert("old-001") is None
        assert history.get_alert("recent-001") is not None


# ============================================================================
# Dispatcher Tests
# ============================================================================


class TestLogDispatcher:
    """Tests for LogDispatcher."""

    def test_dispatch(self) -> None:
        """Test logging dispatch."""
        dispatcher = LogDispatcher()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test alert",
        )

        result = dispatcher.dispatch(alert)
        assert result is True


class TestDryRunDispatcher:
    """Tests for DryRunDispatcher."""

    def test_dispatch_records_alert(self) -> None:
        """Test dry-run dispatch records alerts."""
        dispatcher = DryRunDispatcher()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test alert",
        )

        result = dispatcher.dispatch(alert)
        assert result is True

        dispatched = dispatcher.get_dispatched_alerts()
        assert len(dispatched) == 1
        assert dispatched[0].alert_id == "test-001"

    def test_clear(self) -> None:
        """Test clearing dispatched alerts."""
        dispatcher = DryRunDispatcher()

        alert = DriftAlert(
            alert_id="test-001",
            alert_type=AlertType.KL_DIVERGENCE,
            severity=AlertSeverity.WARNING,
            feature="test",
            current_value=0.35,
            threshold=0.30,
            baseline_value=0.0,
            message="Test",
        )

        dispatcher.dispatch(alert)
        dispatcher.clear()

        assert len(dispatcher.get_dispatched_alerts()) == 0


# ============================================================================
# AlertManager Tests
# ============================================================================


class TestAlertManager:
    """Tests for AlertManager."""

    def test_check_kl_no_alert_below_threshold(self) -> None:
        """Test no alert when KL below threshold."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_kl_divergence("test", 0.10)  # Below warning
        assert alert is None

    def test_check_kl_warning_alert(self) -> None:
        """Test warning alert when KL exceeds warning threshold."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_kl_divergence("test", 0.20)  # Above warning
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.KL_DIVERGENCE

    def test_check_kl_critical_alert(self) -> None:
        """Test critical alert when KL exceeds critical threshold."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_kl_divergence("test", 0.35)  # Above critical
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_check_psi_warning_alert(self) -> None:
        """Test PSI warning alert."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_psi("test", 0.15)  # Above warning
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.PSI_SHIFT

    def test_check_psi_critical_alert(self) -> None:
        """Test PSI critical alert."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_psi("test", 0.30)  # Above critical
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_check_map_drop_warning(self) -> None:
        """Test mAP drop warning alert."""
        config = AlertConfig(map_drop_warning=0.03, map_drop_critical=0.05)
        manager = AlertManager(config)

        # 4% drop (0.90 -> 0.864)
        alert = manager.check_map_drop(0.864, 0.90)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.MAP_DROP

    def test_check_map_drop_critical(self) -> None:
        """Test mAP drop critical alert."""
        config = AlertConfig(map_drop_warning=0.03, map_drop_critical=0.05)
        manager = AlertManager(config)

        # 6% drop (0.90 -> 0.846)
        alert = manager.check_map_drop(0.846, 0.90)
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_check_f1_drop_warning(self) -> None:
        """Test F1 drop warning alert."""
        config = AlertConfig()
        manager = AlertManager(config)

        # 4% drop
        alert = manager.check_f1_drop(0.8448, 0.88)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == AlertType.F1_DROP

    def test_cooldown_prevents_duplicate_alerts(self) -> None:
        """Test cooldown prevents rapid duplicate alerts."""
        config = AlertConfig(cooldown_minutes=60)
        manager = AlertManager(config)

        # First alert
        alert1 = manager.check_kl_divergence("test", 0.35)
        assert alert1 is not None

        # Second alert within cooldown - should be None
        alert2 = manager.check_kl_divergence("test", 0.40)
        assert alert2 is None

    def test_cooldown_per_feature(self) -> None:
        """Test cooldown is per-feature."""
        config = AlertConfig(cooldown_minutes=60)
        manager = AlertManager(config)

        # First feature
        alert1 = manager.check_kl_divergence("feature1", 0.35)
        assert alert1 is not None

        # Different feature - should still alert
        alert2 = manager.check_kl_divergence("feature2", 0.35)
        assert alert2 is not None

    def test_dry_run_mode(self) -> None:
        """Test dry-run mode doesn't dispatch to channels."""
        config = AlertConfig(dry_run=True)
        manager = AlertManager(config)

        alert = manager.check_kl_divergence("test", 0.35)
        assert alert is not None

        # Should be recorded in dry-run dispatcher
        dry_run_alerts = manager.get_dry_run_alerts()
        assert len(dry_run_alerts) == 1

    def test_samples_included_in_alert(self) -> None:
        """Test samples are included in alert."""
        config = AlertConfig()
        manager = AlertManager(config)

        samples = [("s1", 0.1), ("s2", 0.2), ("s3", 0.3)]
        alert = manager.check_kl_divergence("test", 0.35, samples=samples)

        assert alert is not None
        assert len(alert.samples) == 3
        assert alert.samples[0].sample_id == "s1"

    def test_runbook_url_included(self) -> None:
        """Test runbook URL is included in alert."""
        config = AlertConfig(runbook_base_url="https://docs.example.com/runbooks")
        manager = AlertManager(config)

        alert = manager.check_kl_divergence("test", 0.35)
        assert alert is not None
        assert "kl_divergence" in alert.runbook_url

    def test_add_custom_dispatcher(self) -> None:
        """Test adding custom dispatcher."""
        config = AlertConfig(enabled_channels=[AlertChannel.WEBHOOK])
        manager = AlertManager(config)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = True
        manager.add_dispatcher(AlertChannel.WEBHOOK, mock_dispatcher)

        manager.check_kl_divergence("test", 0.35)

        mock_dispatcher.dispatch.assert_called_once()

    def test_zero_baseline_map_no_alert(self) -> None:
        """Test no alert when baseline mAP is zero."""
        config = AlertConfig()
        manager = AlertManager(config)

        alert = manager.check_map_drop(0.5, 0.0)  # Zero baseline
        assert alert is None

    def test_clear_dry_run_alerts(self) -> None:
        """Test clearing dry-run alerts."""
        config = AlertConfig(dry_run=True)
        manager = AlertManager(config)

        manager.check_kl_divergence("test", 0.35)
        manager.clear_dry_run_alerts()

        assert len(manager.get_dry_run_alerts()) == 0


# ============================================================================
# Integration Function Tests
# ============================================================================


class TestCheckDriftAndAlert:
    """Tests for check_drift_and_alert convenience function."""

    def test_check_multiple_metrics(self) -> None:
        """Test checking multiple metrics at once."""
        config = AlertConfig()
        manager = AlertManager(config)

        alerts = check_drift_and_alert(
            manager,
            kl_values={"feature1": 0.35, "feature2": 0.05},  # One above threshold
            psi_values={"feature3": 0.30},  # Above threshold
            map_values=(0.80, 0.90),  # ~11% drop
        )

        # Should have alerts for feature1 (KL), feature3 (PSI), and mAP
        assert len(alerts) >= 2

    def test_no_alerts_below_thresholds(self) -> None:
        """Test no alerts when all below thresholds."""
        config = AlertConfig()
        manager = AlertManager(config)

        alerts = check_drift_and_alert(
            manager,
            kl_values={"feature1": 0.05},
            psi_values={"feature2": 0.05},
            map_values=(0.89, 0.90),  # 1% drop
        )

        assert len(alerts) == 0


class TestCreateAlertManager:
    """Tests for create_alert_manager function."""

    def test_create_with_defaults(self) -> None:
        """Test creating manager with defaults."""
        manager = create_alert_manager()

        assert manager is not None
        assert manager.config.dry_run is False

    def test_create_with_config(self) -> None:
        """Test creating manager with custom config."""
        config = AlertConfig(dry_run=True)
        manager = create_alert_manager(config)

        assert manager.config.dry_run is True

    def test_create_with_storage(self) -> None:
        """Test creating manager with storage path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = create_alert_manager(storage_path=tmpdir)

            # Add an alert
            manager.check_kl_divergence("test", 0.35)

            # Check history file was created
            history_path = Path(tmpdir) / "alert_history.json"
            assert history_path.exists()


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_threshold_ordering(self) -> None:
        """Test thresholds are properly ordered."""
        assert KL_WARNING_THRESHOLD < KL_CRITICAL_THRESHOLD
        assert PSI_WARNING_THRESHOLD < PSI_CRITICAL_THRESHOLD
        assert MAP_DROP_WARNING_THRESHOLD < MAP_DROP_CRITICAL_THRESHOLD
        assert F1_DROP_WARNING_THRESHOLD < F1_DROP_CRITICAL_THRESHOLD

    def test_kl_critical_is_03(self) -> None:
        """Test KL critical threshold is 0.3 as specified."""
        assert KL_CRITICAL_THRESHOLD == 0.30

    def test_map_critical_is_5_percent(self) -> None:
        """Test mAP critical threshold is 5% as specified."""
        assert MAP_DROP_CRITICAL_THRESHOLD == 0.05

    def test_max_samples_reasonable(self) -> None:
        """Test max samples is reasonable."""
        assert MAX_SAMPLES_IN_ALERT >= 5
        assert MAX_SAMPLES_IN_ALERT <= 50


class TestAlertEnums:
    """Tests for alert enums."""

    def test_alert_type_values(self) -> None:
        """Test AlertType enum values."""
        assert AlertType.KL_DIVERGENCE.value == "kl_divergence"
        assert AlertType.PSI_SHIFT.value == "psi_shift"
        assert AlertType.MAP_DROP.value == "map_drop"
        assert AlertType.F1_DROP.value == "f1_drop"

    def test_alert_severity_values(self) -> None:
        """Test AlertSeverity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_alert_channel_values(self) -> None:
        """Test AlertChannel enum values."""
        assert AlertChannel.LOG.value == "log"
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.PAGERDUTY.value == "pagerduty"
        assert AlertChannel.WEBHOOK.value == "webhook"
