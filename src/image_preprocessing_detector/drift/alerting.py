"""Drift alerting module - Sprint 6.3.3.

Alert when drift metrics exceed thresholds with dry-run support.

This module provides:
- DriftAlert: Alert data structure with samples for triage
- AlertManager: Manages alert creation and dispatch
- AlertDispatcher: Sends alerts to various channels
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Drift thresholds (aligned with Sprint 6.3.1)
KL_WARNING_THRESHOLD = 0.15
KL_CRITICAL_THRESHOLD = 0.30
PSI_WARNING_THRESHOLD = 0.10
PSI_CRITICAL_THRESHOLD = 0.25

# Performance thresholds (aligned with Sprint 6.3.2)
MAP_DROP_WARNING_THRESHOLD = 0.03  # 3%
MAP_DROP_CRITICAL_THRESHOLD = 0.05  # 5%
F1_DROP_WARNING_THRESHOLD = 0.03
F1_DROP_CRITICAL_THRESHOLD = 0.05

# Alert configuration
DEFAULT_COOLDOWN_MINUTES = 60
MAX_SAMPLES_IN_ALERT = 10
ALERT_HISTORY_RETENTION_DAYS = 30


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of drift alerts."""

    KL_DIVERGENCE = "kl_divergence"
    PSI_SHIFT = "psi_shift"
    MAP_DROP = "map_drop"
    F1_DROP = "f1_drop"
    PRECISION_DROP = "precision_drop"
    RECALL_DROP = "recall_drop"
    DISTRIBUTION_SHIFT = "distribution_shift"
    MODEL_DRIFT = "model_drift"


class AlertChannel(Enum):
    """Alert dispatch channels."""

    LOG = "log"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"
    WEBHOOK = "webhook"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class DriftSample:
    """Sample included in alert for triage."""

    sample_id: str
    value: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_id": self.sample_id,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DriftAlert:
    """Alert for drift detection."""

    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    feature: str
    current_value: float
    threshold: float
    baseline_value: float | None
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    samples: list[DriftSample] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    runbook_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "feature": self.feature,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "baseline_value": self.baseline_value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "samples": [s.to_dict() for s in self.samples[:MAX_SAMPLES_IN_ALERT]],
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "runbook_url": self.runbook_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DriftAlert":
        """Create from dictionary."""
        return cls(
            alert_id=data["alert_id"],
            alert_type=AlertType(data["alert_type"]),
            severity=AlertSeverity(data["severity"]),
            feature=data["feature"],
            current_value=data["current_value"],
            threshold=data["threshold"],
            baseline_value=data.get("baseline_value"),
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            samples=[],  # Simplified - samples not restored
            metadata=data.get("metadata", {}),
            acknowledged=data.get("acknowledged", False),
            resolved=data.get("resolved", False),
            runbook_url=data.get("runbook_url"),
        )


@dataclass
class AlertConfig:
    """Configuration for alert thresholds and behavior."""

    # Distribution drift thresholds
    kl_warning: float = KL_WARNING_THRESHOLD
    kl_critical: float = KL_CRITICAL_THRESHOLD
    psi_warning: float = PSI_WARNING_THRESHOLD
    psi_critical: float = PSI_CRITICAL_THRESHOLD

    # Performance drift thresholds
    map_drop_warning: float = MAP_DROP_WARNING_THRESHOLD
    map_drop_critical: float = MAP_DROP_CRITICAL_THRESHOLD
    f1_drop_warning: float = F1_DROP_WARNING_THRESHOLD
    f1_drop_critical: float = F1_DROP_CRITICAL_THRESHOLD

    # Alert behavior
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES
    dry_run: bool = False
    enabled_channels: list[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.LOG]
    )

    # Runbook URLs
    runbook_base_url: str = "https://docs.example.com/runbooks/drift"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "kl_warning": self.kl_warning,
            "kl_critical": self.kl_critical,
            "psi_warning": self.psi_warning,
            "psi_critical": self.psi_critical,
            "map_drop_warning": self.map_drop_warning,
            "map_drop_critical": self.map_drop_critical,
            "f1_drop_warning": self.f1_drop_warning,
            "f1_drop_critical": self.f1_drop_critical,
            "cooldown_minutes": self.cooldown_minutes,
            "dry_run": self.dry_run,
            "enabled_channels": [c.value for c in self.enabled_channels],
            "runbook_base_url": self.runbook_base_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertConfig":
        """Create from dictionary."""
        channels = [AlertChannel(c) for c in data.get("enabled_channels", ["log"])]
        return cls(
            kl_warning=data.get("kl_warning", KL_WARNING_THRESHOLD),
            kl_critical=data.get("kl_critical", KL_CRITICAL_THRESHOLD),
            psi_warning=data.get("psi_warning", PSI_WARNING_THRESHOLD),
            psi_critical=data.get("psi_critical", PSI_CRITICAL_THRESHOLD),
            map_drop_warning=data.get("map_drop_warning", MAP_DROP_WARNING_THRESHOLD),
            map_drop_critical=data.get("map_drop_critical", MAP_DROP_CRITICAL_THRESHOLD),
            f1_drop_warning=data.get("f1_drop_warning", F1_DROP_WARNING_THRESHOLD),
            f1_drop_critical=data.get("f1_drop_critical", F1_DROP_CRITICAL_THRESHOLD),
            cooldown_minutes=data.get("cooldown_minutes", DEFAULT_COOLDOWN_MINUTES),
            dry_run=data.get("dry_run", False),
            enabled_channels=channels,
            runbook_base_url=data.get(
                "runbook_base_url", "https://docs.example.com/runbooks/drift"
            ),
        )


# ============================================================================
# Alert Dispatcher Protocol
# ============================================================================


class AlertDispatcherProtocol(Protocol):
    """Protocol for alert dispatchers."""

    def dispatch(self, alert: DriftAlert) -> bool:
        """Dispatch an alert. Returns True if successful."""
        ...


# ============================================================================
# Alert Dispatchers
# ============================================================================


class LogDispatcher:
    """Dispatches alerts to the logging system."""

    def dispatch(self, alert: DriftAlert) -> bool:
        """Log the alert."""
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(
                f"[DRIFT ALERT] {alert.alert_type.value}: {alert.message}",
                extra={"alert": alert.to_dict()},
            )
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(
                f"[DRIFT ALERT] {alert.alert_type.value}: {alert.message}",
                extra={"alert": alert.to_dict()},
            )
        else:
            logger.info(
                f"[DRIFT ALERT] {alert.alert_type.value}: {alert.message}",
                extra={"alert": alert.to_dict()},
            )
        return True


class WebhookDispatcher:
    """Dispatches alerts to a webhook endpoint."""

    def __init__(self, webhook_url: str, timeout: int = 30):
        """Initialize webhook dispatcher.

        Args:
            webhook_url: URL to POST alerts to
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    def dispatch(self, alert: DriftAlert) -> bool:
        """Send alert to webhook."""
        try:
            import urllib.request

            payload = json.dumps(alert.to_dict()).encode("utf-8")
            request = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Failed to dispatch alert to webhook: {e}")
            return False


class SlackDispatcher:
    """Dispatches alerts to Slack."""

    def __init__(self, webhook_url: str):
        """Initialize Slack dispatcher.

        Args:
            webhook_url: Slack incoming webhook URL
        """
        self.webhook_url = webhook_url

    def dispatch(self, alert: DriftAlert) -> bool:
        """Send alert to Slack."""
        try:
            import urllib.request

            # Format Slack message
            color = {
                AlertSeverity.CRITICAL: "#FF0000",
                AlertSeverity.WARNING: "#FFA500",
                AlertSeverity.INFO: "#0000FF",
            }.get(alert.severity, "#808080")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Drift Alert: {alert.alert_type.value}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Feature",
                                "value": alert.feature,
                                "short": True,
                            },
                            {
                                "title": "Current Value",
                                "value": f"{alert.current_value:.4f}",
                                "short": True,
                            },
                            {
                                "title": "Threshold",
                                "value": f"{alert.threshold:.4f}",
                                "short": True,
                            },
                        ],
                        "footer": f"Alert ID: {alert.alert_id}",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ]
            }

            if alert.runbook_url:
                payload["attachments"][0]["fields"].append(
                    {"title": "Runbook", "value": alert.runbook_url, "short": False}
                )

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Failed to dispatch alert to Slack: {e}")
            return False


class DryRunDispatcher:
    """Dispatcher for dry-run mode - logs but doesn't page."""

    def __init__(self) -> None:
        """Initialize dry-run dispatcher."""
        self.dispatched_alerts: list[DriftAlert] = []

    def dispatch(self, alert: DriftAlert) -> bool:
        """Record alert without actually dispatching."""
        self.dispatched_alerts.append(alert)
        logger.info(
            f"[DRY-RUN] Would dispatch {alert.severity.value} alert: {alert.message}"
        )
        return True

    def get_dispatched_alerts(self) -> list[DriftAlert]:
        """Get list of alerts that would have been dispatched."""
        return list(self.dispatched_alerts)

    def clear(self) -> None:
        """Clear dispatched alerts."""
        self.dispatched_alerts.clear()


# ============================================================================
# Alert History
# ============================================================================


class AlertHistory:
    """Tracks alert history for cooldown and deduplication."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        retention_days: int = ALERT_HISTORY_RETENTION_DAYS,
    ):
        """Initialize alert history.

        Args:
            storage_path: Optional path for persistence
            retention_days: Days to retain alert history
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.retention_days = retention_days
        self._alerts: dict[str, DriftAlert] = {}
        self._last_alert_times: dict[str, datetime] = {}

        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_history()

    def _load_history(self) -> None:
        """Load alert history from storage."""
        if not self.storage_path:
            return

        history_file = self.storage_path / "alert_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)

                cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

                for item in data.get("alerts", []):
                    alert = DriftAlert.from_dict(item)
                    if alert.timestamp > cutoff:
                        self._alerts[alert.alert_id] = alert

                for key, ts in data.get("last_alert_times", {}).items():
                    dt = datetime.fromisoformat(ts)
                    if dt > cutoff:
                        self._last_alert_times[key] = dt

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error loading alert history: {e}")

    def _save_history(self) -> None:
        """Save alert history to storage."""
        if not self.storage_path:
            return

        history_file = self.storage_path / "alert_history.json"

        data = {
            "alerts": [a.to_dict() for a in self._alerts.values()],
            "last_alert_times": {
                k: v.isoformat() for k, v in self._last_alert_times.items()
            },
        }

        with open(history_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_alert(self, alert: DriftAlert) -> None:
        """Add alert to history."""
        self._alerts[alert.alert_id] = alert
        key = self._get_cooldown_key(alert)
        self._last_alert_times[key] = alert.timestamp
        self._save_history()

    def get_alert(self, alert_id: str) -> DriftAlert | None:
        """Get alert by ID."""
        return self._alerts.get(alert_id)

    def is_in_cooldown(
        self,
        alert_type: AlertType,
        feature: str,
        cooldown_minutes: int,
    ) -> bool:
        """Check if alert is in cooldown period.

        Args:
            alert_type: Type of alert
            feature: Feature name
            cooldown_minutes: Cooldown period in minutes

        Returns:
            True if in cooldown period
        """
        key = f"{alert_type.value}:{feature}"
        last_time = self._last_alert_times.get(key)

        if not last_time:
            return False

        cooldown_until = last_time + timedelta(minutes=cooldown_minutes)
        return datetime.utcnow() < cooldown_until

    def _get_cooldown_key(self, alert: DriftAlert) -> str:
        """Get cooldown key for an alert."""
        return f"{alert.alert_type.value}:{alert.feature}"

    def get_recent_alerts(
        self,
        hours: int = 24,
        severity: AlertSeverity | None = None,
    ) -> list[DriftAlert]:
        """Get recent alerts.

        Args:
            hours: Hours of history to include
            severity: Filter by severity (optional)

        Returns:
            List of recent alerts
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in self._alerts.values() if a.timestamp > cutoff]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark alert as acknowledged."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.acknowledged = True
            self._save_history()
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.resolved = True
            self._save_history()
            return True
        return False

    def cleanup_old_alerts(self) -> int:
        """Remove old alerts beyond retention period.

        Returns:
            Number of alerts removed
        """
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        old_alerts = [
            aid for aid, alert in self._alerts.items() if alert.timestamp < cutoff
        ]

        for aid in old_alerts:
            del self._alerts[aid]

        old_times = [
            key for key, dt in self._last_alert_times.items() if dt < cutoff
        ]

        for key in old_times:
            del self._last_alert_times[key]

        if old_alerts or old_times:
            self._save_history()

        return len(old_alerts)


# ============================================================================
# Alert Manager
# ============================================================================


class AlertManager:
    """Manages drift alert creation and dispatch.

    Handles:
    - Alert threshold evaluation
    - Cooldown management
    - Multi-channel dispatch
    - Dry-run mode for validation
    """

    def __init__(
        self,
        config: AlertConfig,
        history: AlertHistory | None = None,
    ):
        """Initialize alert manager.

        Args:
            config: Alert configuration
            history: Optional alert history tracker
        """
        self.config = config
        self.history = history or AlertHistory()
        self._dispatchers: dict[AlertChannel, AlertDispatcherProtocol] = {
            AlertChannel.LOG: LogDispatcher(),
        }
        self._alert_counter = 0

        # Set up dry-run dispatcher if enabled
        if config.dry_run:
            self._dry_run_dispatcher = DryRunDispatcher()
        else:
            self._dry_run_dispatcher = None

    def add_dispatcher(
        self, channel: AlertChannel, dispatcher: AlertDispatcherProtocol
    ) -> None:
        """Add a dispatcher for a channel.

        Args:
            channel: Alert channel
            dispatcher: Dispatcher implementation
        """
        self._dispatchers[channel] = dispatcher

    def check_kl_divergence(
        self,
        feature: str,
        kl_value: float,
        samples: list[tuple[str, float]] | None = None,
    ) -> DriftAlert | None:
        """Check KL divergence and create alert if needed.

        Args:
            feature: Feature name
            kl_value: KL divergence value
            samples: Optional list of (sample_id, value) for triage

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if kl_value >= self.config.kl_critical:
            severity = AlertSeverity.CRITICAL
            threshold = self.config.kl_critical
        elif kl_value >= self.config.kl_warning:
            severity = AlertSeverity.WARNING
            threshold = self.config.kl_warning
        else:
            return None

        return self._create_and_dispatch_alert(
            alert_type=AlertType.KL_DIVERGENCE,
            severity=severity,
            feature=feature,
            current_value=kl_value,
            threshold=threshold,
            baseline_value=0.0,  # KL baseline is 0 (identical)
            message=(
                f"KL divergence for {feature} is {kl_value:.4f}, "
                f"exceeding {severity.value} threshold of {threshold:.4f}"
            ),
            samples=samples,
        )

    def check_psi(
        self,
        feature: str,
        psi_value: float,
        samples: list[tuple[str, float]] | None = None,
    ) -> DriftAlert | None:
        """Check PSI and create alert if needed.

        Args:
            feature: Feature name
            psi_value: PSI value
            samples: Optional list of (sample_id, value) for triage

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        if psi_value >= self.config.psi_critical:
            severity = AlertSeverity.CRITICAL
            threshold = self.config.psi_critical
        elif psi_value >= self.config.psi_warning:
            severity = AlertSeverity.WARNING
            threshold = self.config.psi_warning
        else:
            return None

        return self._create_and_dispatch_alert(
            alert_type=AlertType.PSI_SHIFT,
            severity=severity,
            feature=feature,
            current_value=psi_value,
            threshold=threshold,
            baseline_value=0.0,
            message=(
                f"PSI for {feature} is {psi_value:.4f}, "
                f"exceeding {severity.value} threshold of {threshold:.4f}"
            ),
            samples=samples,
        )

    def check_map_drop(
        self,
        current_map: float,
        baseline_map: float,
        samples: list[tuple[str, float]] | None = None,
    ) -> DriftAlert | None:
        """Check mAP drop and create alert if needed.

        Args:
            current_map: Current mAP value
            baseline_map: Baseline mAP value
            samples: Optional list of (sample_id, value) for triage

        Returns:
            Alert if drop exceeds threshold, None otherwise
        """
        if baseline_map == 0:
            return None

        drop = (baseline_map - current_map) / baseline_map

        if drop >= self.config.map_drop_critical:
            severity = AlertSeverity.CRITICAL
            threshold = self.config.map_drop_critical
        elif drop >= self.config.map_drop_warning:
            severity = AlertSeverity.WARNING
            threshold = self.config.map_drop_warning
        else:
            return None

        return self._create_and_dispatch_alert(
            alert_type=AlertType.MAP_DROP,
            severity=severity,
            feature="mAP",
            current_value=current_map,
            threshold=baseline_map * (1 - threshold),
            baseline_value=baseline_map,
            message=(
                f"mAP dropped from {baseline_map:.4f} to {current_map:.4f} "
                f"({drop * 100:.1f}% drop), exceeding {severity.value} "
                f"threshold of {threshold * 100:.1f}%"
            ),
            samples=samples,
        )

    def check_f1_drop(
        self,
        current_f1: float,
        baseline_f1: float,
        samples: list[tuple[str, float]] | None = None,
    ) -> DriftAlert | None:
        """Check F1 drop and create alert if needed.

        Args:
            current_f1: Current F1 value
            baseline_f1: Baseline F1 value
            samples: Optional list of (sample_id, value) for triage

        Returns:
            Alert if drop exceeds threshold, None otherwise
        """
        if baseline_f1 == 0:
            return None

        drop = (baseline_f1 - current_f1) / baseline_f1

        if drop >= self.config.f1_drop_critical:
            severity = AlertSeverity.CRITICAL
            threshold = self.config.f1_drop_critical
        elif drop >= self.config.f1_drop_warning:
            severity = AlertSeverity.WARNING
            threshold = self.config.f1_drop_warning
        else:
            return None

        return self._create_and_dispatch_alert(
            alert_type=AlertType.F1_DROP,
            severity=severity,
            feature="F1",
            current_value=current_f1,
            threshold=baseline_f1 * (1 - threshold),
            baseline_value=baseline_f1,
            message=(
                f"F1 dropped from {baseline_f1:.4f} to {current_f1:.4f} "
                f"({drop * 100:.1f}% drop), exceeding {severity.value} "
                f"threshold of {threshold * 100:.1f}%"
            ),
            samples=samples,
        )

    def _create_and_dispatch_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        feature: str,
        current_value: float,
        threshold: float,
        baseline_value: float | None,
        message: str,
        samples: list[tuple[str, float]] | None = None,
    ) -> DriftAlert | None:
        """Create and dispatch an alert.

        Args:
            alert_type: Type of drift alert
            severity: Alert severity
            feature: Feature name
            current_value: Current metric value
            threshold: Threshold that was exceeded
            baseline_value: Baseline value for comparison
            message: Alert message
            samples: Optional samples for triage

        Returns:
            Created alert or None if in cooldown
        """
        # Check cooldown
        if self.history.is_in_cooldown(
            alert_type, feature, self.config.cooldown_minutes
        ):
            logger.debug(
                f"Alert for {alert_type.value}:{feature} is in cooldown, skipping"
            )
            return None

        # Generate alert ID
        self._alert_counter += 1
        alert_id = f"{alert_type.value}-{feature}-{self._alert_counter}"

        # Create samples list
        drift_samples = []
        if samples:
            for sample_id, value in samples[:MAX_SAMPLES_IN_ALERT]:
                drift_samples.append(
                    DriftSample(
                        sample_id=sample_id,
                        value=value,
                        timestamp=datetime.utcnow(),
                    )
                )

        # Create alert
        alert = DriftAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            feature=feature,
            current_value=current_value,
            threshold=threshold,
            baseline_value=baseline_value,
            message=message,
            samples=drift_samples,
            runbook_url=f"{self.config.runbook_base_url}/{alert_type.value}",
        )

        # Add to history
        self.history.add_alert(alert)

        # Dispatch
        self._dispatch_alert(alert)

        return alert

    def _dispatch_alert(self, alert: DriftAlert) -> None:
        """Dispatch alert to configured channels."""
        if self.config.dry_run and self._dry_run_dispatcher:
            self._dry_run_dispatcher.dispatch(alert)
            return

        for channel in self.config.enabled_channels:
            dispatcher = self._dispatchers.get(channel)
            if dispatcher:
                try:
                    success = dispatcher.dispatch(alert)
                    if not success:
                        logger.warning(
                            f"Failed to dispatch alert {alert.alert_id} to {channel.value}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error dispatching alert to {channel.value}: {e}"
                    )

    def get_dry_run_alerts(self) -> list[DriftAlert]:
        """Get alerts from dry-run mode.

        Returns:
            List of alerts that would have been dispatched
        """
        if self._dry_run_dispatcher:
            return self._dry_run_dispatcher.get_dispatched_alerts()
        return []

    def clear_dry_run_alerts(self) -> None:
        """Clear dry-run alert buffer."""
        if self._dry_run_dispatcher:
            self._dry_run_dispatcher.clear()


# ============================================================================
# Integration Functions
# ============================================================================


def create_alert_manager(
    config: AlertConfig | None = None,
    storage_path: str | Path | None = None,
) -> AlertManager:
    """Create an alert manager with default configuration.

    Args:
        config: Optional alert configuration
        storage_path: Optional path for alert history storage

    Returns:
        Configured AlertManager instance
    """
    if config is None:
        config = AlertConfig()

    history = AlertHistory(storage_path) if storage_path else AlertHistory()

    return AlertManager(config, history)


def check_drift_and_alert(
    alert_manager: AlertManager,
    kl_values: dict[str, float] | None = None,
    psi_values: dict[str, float] | None = None,
    map_values: tuple[float, float] | None = None,  # (current, baseline)
    f1_values: tuple[float, float] | None = None,  # (current, baseline)
) -> list[DriftAlert]:
    """Check multiple drift metrics and create alerts.

    Convenience function to check multiple metrics at once.

    Args:
        alert_manager: AlertManager instance
        kl_values: Dict of feature -> KL divergence values
        psi_values: Dict of feature -> PSI values
        map_values: Tuple of (current_map, baseline_map)
        f1_values: Tuple of (current_f1, baseline_f1)

    Returns:
        List of created alerts
    """
    alerts = []

    if kl_values:
        for feature, kl in kl_values.items():
            alert = alert_manager.check_kl_divergence(feature, kl)
            if alert:
                alerts.append(alert)

    if psi_values:
        for feature, psi_val in psi_values.items():
            alert = alert_manager.check_psi(feature, psi_val)
            if alert:
                alerts.append(alert)

    if map_values:
        current_map, baseline_map = map_values
        alert = alert_manager.check_map_drop(current_map, baseline_map)
        if alert:
            alerts.append(alert)

    if f1_values:
        current_f1, baseline_f1 = f1_values
        alert = alert_manager.check_f1_drop(current_f1, baseline_f1)
        if alert:
            alerts.append(alert)

    return alerts


__all__ = [
    # Classes
    "AlertConfig",
    "AlertHistory",
    "AlertManager",
    "DriftAlert",
    "DriftSample",
    "DryRunDispatcher",
    "LogDispatcher",
    "SlackDispatcher",
    "WebhookDispatcher",
    # Enums
    "AlertChannel",
    "AlertSeverity",
    "AlertType",
    # Functions
    "check_drift_and_alert",
    "create_alert_manager",
    # Constants
    "DEFAULT_COOLDOWN_MINUTES",
    "F1_DROP_CRITICAL_THRESHOLD",
    "F1_DROP_WARNING_THRESHOLD",
    "KL_CRITICAL_THRESHOLD",
    "KL_WARNING_THRESHOLD",
    "MAP_DROP_CRITICAL_THRESHOLD",
    "MAP_DROP_WARNING_THRESHOLD",
    "MAX_SAMPLES_IN_ALERT",
    "PSI_CRITICAL_THRESHOLD",
    "PSI_WARNING_THRESHOLD",
]
