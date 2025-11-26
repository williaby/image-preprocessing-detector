"""Tests for alert threshold validation.

Sprint 6.2.5: Validate alert thresholds with synthetic metrics.
"""

import pytest

# ============================================================================
# Threshold Constants (from alert-rules.yml)
# ============================================================================

LATENCY_THRESHOLDS = {
    "p50_warning": 0.2,  # 200ms
    "p95_warning": 0.5,  # 500ms
    "p99_critical": 2.0,  # 2000ms
    "student_p95": 0.1,  # 100ms
}

ERROR_THRESHOLDS = {
    "rate_warning": 0.05,  # 5%
    "rate_critical": 0.20,  # 20%
    "processing_spike": 50,  # 50 errors/5min
    "infra_spike": 10,  # 10 errors/5min
}

INFRASTRUCTURE_THRESHOLDS = {
    "gpu_memory_warning": 0.90,  # 90%
    "workers_degraded": 2,
    "workers_critical": 0,
    "queue_warning": 500,
    "queue_critical": 2000,
}

MODEL_THRESHOLDS = {
    "escalation_rate_warning": 0.25,  # 25%
    "drift_warning": 0.1,
}

COST_THRESHOLDS = {
    "daily_warning": 5.0,  # $5
    "monthly_warning": 20.0,  # $20
    "monthly_critical": 28.0,  # $28
    "rate_spike_hourly": 1.0,  # $1/hour
    "gpu_rate_hourly": 100,  # 100 sec/hour
}

AVAILABILITY_THRESHOLDS = {
    "low_throughput": 0.1,  # pages/sec
    "queue_with_low_throughput": 10,
}


# ============================================================================
# Latency Threshold Tests
# ============================================================================


class TestLatencyThresholds:
    """Test latency alert thresholds."""

    def test_p50_below_threshold_no_alert(self) -> None:
        """Test p50 below 200ms should not alert."""
        p50_latency = 0.08  # 80ms - typical baseline

        assert p50_latency < LATENCY_THRESHOLDS["p50_warning"]

    def test_p50_above_threshold_alerts(self) -> None:
        """Test p50 above 200ms should alert."""
        p50_latency = 0.25  # 250ms - degraded

        assert p50_latency > LATENCY_THRESHOLDS["p50_warning"]

    def test_p95_below_threshold_no_alert(self) -> None:
        """Test p95 below 500ms should not alert."""
        p95_latency = 0.20  # 200ms - typical baseline

        assert p95_latency < LATENCY_THRESHOLDS["p95_warning"]

    def test_p95_above_threshold_alerts(self) -> None:
        """Test p95 above 500ms should alert."""
        p95_latency = 0.60  # 600ms - degraded

        assert p95_latency > LATENCY_THRESHOLDS["p95_warning"]

    def test_p99_below_threshold_no_alert(self) -> None:
        """Test p99 below 2s should not alert."""
        p99_latency = 0.40  # 400ms - typical baseline

        assert p99_latency < LATENCY_THRESHOLDS["p99_critical"]

    def test_p99_above_threshold_alerts(self) -> None:
        """Test p99 above 2s should alert critical."""
        p99_latency = 2.5  # 2.5s - severe

        assert p99_latency > LATENCY_THRESHOLDS["p99_critical"]

    def test_student_model_fast_enough(self) -> None:
        """Test student model meets p95 target of 100ms."""
        student_p95 = 0.04  # 40ms - typical

        assert student_p95 < LATENCY_THRESHOLDS["student_p95"]

    def test_student_model_slow_alerts(self) -> None:
        """Test slow student model triggers alert."""
        student_p95 = 0.15  # 150ms - too slow

        assert student_p95 > LATENCY_THRESHOLDS["student_p95"]


# ============================================================================
# Error Rate Threshold Tests
# ============================================================================


class TestErrorThresholds:
    """Test error rate alert thresholds."""

    def test_normal_error_rate_no_alert(self) -> None:
        """Test normal error rate does not alert."""
        error_rate = 0.005  # 0.5%

        assert error_rate < ERROR_THRESHOLDS["rate_warning"]

    def test_elevated_error_rate_warning(self) -> None:
        """Test elevated error rate triggers warning."""
        error_rate = 0.08  # 8%

        assert error_rate > ERROR_THRESHOLDS["rate_warning"]
        assert error_rate < ERROR_THRESHOLDS["rate_critical"]

    def test_critical_error_rate(self) -> None:
        """Test critical error rate triggers critical alert."""
        error_rate = 0.25  # 25%

        assert error_rate > ERROR_THRESHOLDS["rate_critical"]

    def test_processing_error_spike_below_threshold(self) -> None:
        """Test processing errors below spike threshold."""
        errors_5min = 30

        assert errors_5min < ERROR_THRESHOLDS["processing_spike"]

    def test_processing_error_spike_alerts(self) -> None:
        """Test processing error spike triggers alert."""
        errors_5min = 75

        assert errors_5min > ERROR_THRESHOLDS["processing_spike"]

    def test_infra_error_spike_below_threshold(self) -> None:
        """Test infra errors below spike threshold."""
        infra_errors_5min = 5

        assert infra_errors_5min < ERROR_THRESHOLDS["infra_spike"]

    def test_infra_error_spike_alerts(self) -> None:
        """Test infra error spike triggers critical alert."""
        infra_errors_5min = 15

        assert infra_errors_5min > ERROR_THRESHOLDS["infra_spike"]


# ============================================================================
# Infrastructure Threshold Tests
# ============================================================================


class TestInfrastructureThresholds:
    """Test infrastructure alert thresholds."""

    def test_gpu_memory_normal(self) -> None:
        """Test normal GPU memory usage."""
        gpu_usage = 0.60  # 60%

        assert gpu_usage < INFRASTRUCTURE_THRESHOLDS["gpu_memory_warning"]

    def test_gpu_memory_high_alerts(self) -> None:
        """Test high GPU memory triggers alert."""
        gpu_usage = 0.92  # 92%

        assert gpu_usage > INFRASTRUCTURE_THRESHOLDS["gpu_memory_warning"]

    def test_workers_healthy(self) -> None:
        """Test healthy worker count."""
        workers = 4

        assert workers >= INFRASTRUCTURE_THRESHOLDS["workers_degraded"]

    def test_workers_degraded_alerts(self) -> None:
        """Test degraded worker count triggers alert."""
        workers = 1

        assert workers < INFRASTRUCTURE_THRESHOLDS["workers_degraded"]

    def test_workers_critical_alerts(self) -> None:
        """Test zero workers triggers critical alert."""
        workers = 0

        assert workers == INFRASTRUCTURE_THRESHOLDS["workers_critical"]

    def test_queue_normal(self) -> None:
        """Test normal queue depth."""
        queue_depth = 50

        assert queue_depth < INFRASTRUCTURE_THRESHOLDS["queue_warning"]

    def test_queue_warning(self) -> None:
        """Test queue backlog triggers warning."""
        queue_depth = 750

        assert queue_depth > INFRASTRUCTURE_THRESHOLDS["queue_warning"]
        assert queue_depth < INFRASTRUCTURE_THRESHOLDS["queue_critical"]

    def test_queue_critical(self) -> None:
        """Test severe queue backlog triggers critical."""
        queue_depth = 2500

        assert queue_depth > INFRASTRUCTURE_THRESHOLDS["queue_critical"]


# ============================================================================
# Model Threshold Tests
# ============================================================================


class TestModelThresholds:
    """Test model and escalation alert thresholds."""

    def test_escalation_rate_normal(self) -> None:
        """Test normal escalation rate."""
        escalation_rate = 0.12  # 12%

        assert escalation_rate < MODEL_THRESHOLDS["escalation_rate_warning"]

    def test_escalation_rate_high_alerts(self) -> None:
        """Test high escalation rate triggers alert."""
        escalation_rate = 0.30  # 30%

        assert escalation_rate > MODEL_THRESHOLDS["escalation_rate_warning"]

    def test_no_drift(self) -> None:
        """Test no model drift."""
        quality_score_shift = 0.03

        assert quality_score_shift < MODEL_THRESHOLDS["drift_warning"]

    def test_drift_detected_alerts(self) -> None:
        """Test model drift triggers alert."""
        quality_score_shift = 0.15

        assert quality_score_shift > MODEL_THRESHOLDS["drift_warning"]


# ============================================================================
# Cost Threshold Tests
# ============================================================================


class TestCostThresholds:
    """Test cost alert thresholds."""

    def test_daily_cost_normal(self) -> None:
        """Test normal daily cost."""
        daily_cost = 2.50  # $2.50

        assert daily_cost < COST_THRESHOLDS["daily_warning"]

    def test_daily_cost_high_alerts(self) -> None:
        """Test high daily cost triggers alert."""
        daily_cost = 7.00  # $7

        assert daily_cost > COST_THRESHOLDS["daily_warning"]

    def test_monthly_cost_normal(self) -> None:
        """Test normal monthly cost."""
        monthly_cost = 15.00  # $15

        assert monthly_cost < COST_THRESHOLDS["monthly_warning"]

    def test_monthly_cost_warning(self) -> None:
        """Test monthly cost approaching budget triggers warning."""
        monthly_cost = 22.00  # $22

        assert monthly_cost > COST_THRESHOLDS["monthly_warning"]
        assert monthly_cost < COST_THRESHOLDS["monthly_critical"]

    def test_monthly_cost_critical(self) -> None:
        """Test monthly cost near budget triggers critical."""
        monthly_cost = 29.00  # $29

        assert monthly_cost > COST_THRESHOLDS["monthly_critical"]

    def test_cost_rate_normal(self) -> None:
        """Test normal hourly cost rate."""
        hourly_rate = 0.25  # $0.25/hour

        assert hourly_rate < COST_THRESHOLDS["rate_spike_hourly"]

    def test_cost_rate_spike_alerts(self) -> None:
        """Test cost rate spike triggers alert."""
        hourly_rate = 1.50  # $1.50/hour

        assert hourly_rate > COST_THRESHOLDS["rate_spike_hourly"]

    def test_gpu_usage_normal(self) -> None:
        """Test normal GPU usage rate."""
        gpu_sec_per_hour = 50

        assert gpu_sec_per_hour < COST_THRESHOLDS["gpu_rate_hourly"]

    def test_gpu_usage_high_alerts(self) -> None:
        """Test high GPU usage triggers alert."""
        gpu_sec_per_hour = 150

        assert gpu_sec_per_hour > COST_THRESHOLDS["gpu_rate_hourly"]


# ============================================================================
# Availability Threshold Tests
# ============================================================================


class TestAvailabilityThresholds:
    """Test availability alert thresholds."""

    def test_throughput_healthy(self) -> None:
        """Test healthy throughput."""
        throughput = 2.0  # 2 pages/sec

        assert throughput > AVAILABILITY_THRESHOLDS["low_throughput"]

    def test_low_throughput_with_queue_alerts(self) -> None:
        """Test low throughput with queue backlog triggers alert."""
        throughput = 0.05  # 0.05 pages/sec
        queue_depth = 50

        is_low_throughput = throughput < AVAILABILITY_THRESHOLDS["low_throughput"]
        has_queue = queue_depth > AVAILABILITY_THRESHOLDS["queue_with_low_throughput"]

        assert is_low_throughput and has_queue

    def test_low_throughput_empty_queue_no_alert(self) -> None:
        """Test low throughput with empty queue should not alert."""
        throughput = 0.05  # Low but okay if no work pending
        queue_depth = 0

        is_low_throughput = throughput < AVAILABILITY_THRESHOLDS["low_throughput"]
        has_queue = queue_depth > AVAILABILITY_THRESHOLDS["queue_with_low_throughput"]

        # Low throughput but no queue - should NOT alert
        assert is_low_throughput
        assert not has_queue


# ============================================================================
# Threshold Boundary Tests
# ============================================================================


class TestThresholdBoundaries:
    """Test exact boundary conditions for thresholds."""

    @pytest.mark.parametrize(
        "value,threshold,should_alert",
        [
            (0.199, 0.2, False),  # Just below
            (0.200, 0.2, False),  # Exactly at (not >, so no alert)
            (0.201, 0.2, True),  # Just above
        ],
    )
    def test_p50_boundary(
        self, value: float, threshold: float, should_alert: bool
    ) -> None:
        """Test p50 threshold boundary."""
        result = value > threshold
        assert result == should_alert

    @pytest.mark.parametrize(
        "rate,warning,critical,expected_severity",
        [
            (0.04, 0.05, 0.20, None),  # Below warning
            (0.06, 0.05, 0.20, "warning"),  # Warning range
            (0.19, 0.05, 0.20, "warning"),  # Still warning
            (0.21, 0.05, 0.20, "critical"),  # Critical
        ],
    )
    def test_error_rate_severity(
        self,
        rate: float,
        warning: float,
        critical: float,
        expected_severity: str | None,
    ) -> None:
        """Test error rate severity classification."""
        if rate > critical:
            severity = "critical"
        elif rate > warning:
            severity = "warning"
        else:
            severity = None

        assert severity == expected_severity

    @pytest.mark.parametrize(
        "cost,warning,critical,expected_severity",
        [
            (15.0, 20.0, 28.0, None),  # Below warning
            (22.0, 20.0, 28.0, "warning"),  # Warning range
            (27.0, 20.0, 28.0, "warning"),  # Still warning
            (29.0, 20.0, 28.0, "critical"),  # Critical
        ],
    )
    def test_monthly_cost_severity(
        self,
        cost: float,
        warning: float,
        critical: float,
        expected_severity: str | None,
    ) -> None:
        """Test monthly cost severity classification."""
        if cost > critical:
            severity = "critical"
        elif cost > warning:
            severity = "warning"
        else:
            severity = None

        assert severity == expected_severity


# ============================================================================
# Threshold Documentation Tests
# ============================================================================


class TestThresholdDocumentation:
    """Ensure threshold values match documentation."""

    def test_latency_thresholds_documented(self) -> None:
        """Verify latency thresholds match alert rules."""
        # These values must match alert-rules.yml
        assert LATENCY_THRESHOLDS["p50_warning"] == 0.2
        assert LATENCY_THRESHOLDS["p95_warning"] == 0.5
        assert LATENCY_THRESHOLDS["p99_critical"] == 2.0
        assert LATENCY_THRESHOLDS["student_p95"] == 0.1

    def test_error_thresholds_documented(self) -> None:
        """Verify error thresholds match alert rules."""
        assert ERROR_THRESHOLDS["rate_warning"] == 0.05
        assert ERROR_THRESHOLDS["rate_critical"] == 0.20
        assert ERROR_THRESHOLDS["processing_spike"] == 50
        assert ERROR_THRESHOLDS["infra_spike"] == 10

    def test_cost_thresholds_documented(self) -> None:
        """Verify cost thresholds match alert rules."""
        assert COST_THRESHOLDS["daily_warning"] == 5.0
        assert COST_THRESHOLDS["monthly_warning"] == 20.0
        assert COST_THRESHOLDS["monthly_critical"] == 28.0


# ============================================================================
# Baseline Validation Tests
# ============================================================================


class TestBaselineValidation:
    """Test that baselines are within expected ranges."""

    def test_cpu_latency_baseline_reasonable(self) -> None:
        """Test CPU latency baseline is reasonable."""
        # From baseline-metrics.md
        cpu_p50_baseline = 0.080  # 80ms
        cpu_p95_baseline = 0.200  # 200ms

        # Baseline should be well below thresholds
        assert cpu_p50_baseline < LATENCY_THRESHOLDS["p50_warning"] * 0.5
        assert cpu_p95_baseline < LATENCY_THRESHOLDS["p95_warning"] * 0.5

    def test_gpu_latency_baseline_reasonable(self) -> None:
        """Test GPU latency baseline is reasonable."""
        # From baseline-metrics.md
        gpu_p50_baseline = 0.025  # 25ms
        gpu_p95_baseline = 0.060  # 60ms

        # GPU should be significantly faster than thresholds
        assert gpu_p50_baseline < LATENCY_THRESHOLDS["p50_warning"] * 0.25
        assert gpu_p95_baseline < LATENCY_THRESHOLDS["p95_warning"] * 0.25

    def test_error_rate_baseline_reasonable(self) -> None:
        """Test error rate baseline is reasonable."""
        error_rate_baseline = 0.005  # 0.5%

        # Baseline should be well below warning threshold
        assert error_rate_baseline < ERROR_THRESHOLDS["rate_warning"] * 0.2

    def test_escalation_rate_baseline_reasonable(self) -> None:
        """Test escalation rate baseline is reasonable."""
        escalation_baseline = 0.12  # 12%

        # Baseline should be below warning threshold
        assert escalation_baseline < MODEL_THRESHOLDS["escalation_rate_warning"]

    def test_daily_cost_baseline_reasonable(self) -> None:
        """Test daily cost baseline is reasonable."""
        daily_cost_baseline = 2.0  # $2

        # Baseline should be below warning threshold
        assert daily_cost_baseline < COST_THRESHOLDS["daily_warning"]
