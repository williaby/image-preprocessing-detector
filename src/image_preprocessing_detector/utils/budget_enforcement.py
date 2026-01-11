# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Budget enforcement for Modal GPU usage.

Provides guardrails to prevent unexpected cloud GPU costs:
- Daily budget limits
- Monthly budget limits
- Warning thresholds
- Automatic fallback to CPU when budget exceeded

Phase 4 - Device Priority Execution
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from image_preprocessing_detector.utils.datetime_compat import UTC
from image_preprocessing_detector.utils.log_config import get_logger

logger = get_logger(__name__)

# Default storage location for budget tracking
DEFAULT_BUDGET_FILE = Path.home() / ".cache" / "imgprep" / "modal_budget.json"


@dataclass
class BudgetState:
    """Current budget usage state.

    Attributes:
        daily_usage_dollars: GPU cost accumulated today
        monthly_usage_dollars: GPU cost accumulated this month
        daily_gpu_seconds: GPU seconds used today
        monthly_gpu_seconds: GPU seconds used this month
        last_reset_date: Date of last daily reset (YYYY-MM-DD)
        last_month_reset: Month of last monthly reset (YYYY-MM)
        warnings_issued: Number of budget warnings issued
    """

    daily_usage_dollars: float = 0.0
    monthly_usage_dollars: float = 0.0
    daily_gpu_seconds: float = 0.0
    monthly_gpu_seconds: float = 0.0
    last_reset_date: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d")
    )
    last_month_reset: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m")
    )
    warnings_issued: int = 0


@dataclass
class BudgetConfig:
    """Budget configuration settings.

    Attributes:
        enabled: Whether budget enforcement is active
        daily_limit_dollars: Maximum daily spend
        monthly_limit_dollars: Maximum monthly spend
        cost_per_gpu_hour: Cost per GPU hour
        warning_threshold: Ratio at which to issue warnings (0-1)
    """

    enabled: bool = True
    daily_limit_dollars: float = 10.0
    monthly_limit_dollars: float = 100.0
    cost_per_gpu_hour: float = 0.36  # T4 default
    warning_threshold: float = 0.8


@dataclass
class BudgetCheckResult:
    """Result of budget check.

    Attributes:
        allowed: Whether GPU usage is allowed
        reason: Reason if not allowed
        daily_remaining: Remaining daily budget
        monthly_remaining: Remaining monthly budget
        warning: Warning message if near limit
    """

    allowed: bool
    reason: str | None = None
    daily_remaining: float = 0.0
    monthly_remaining: float = 0.0
    warning: str | None = None


class BudgetEnforcer:
    """Enforces Modal GPU budget limits.

    Tracks daily and monthly GPU usage and prevents usage when
    budget limits are exceeded.

    Example:
        >>> enforcer = BudgetEnforcer(BudgetConfig(daily_limit_dollars=5.0))
        >>> check = enforcer.check_budget()
        >>> if check.allowed:
        ...     # Run GPU inference
        ...     enforcer.record_usage(gpu_seconds=10.5)
        >>> else:
        ...     # Fall back to CPU
        ...     print(f"Budget exceeded: {check.reason}")
    """

    def __init__(
        self,
        config: BudgetConfig | None = None,
        storage_path: Path | None = None,
    ) -> None:
        """Initialize budget enforcer.

        Args:
            config: Budget configuration (uses defaults if None)
            storage_path: Path to persist budget state
        """
        self.config = config or BudgetConfig()
        self.storage_path = storage_path or DEFAULT_BUDGET_FILE
        self._state: BudgetState | None = None

        # Create storage directory
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Budget enforcer initialized",
            enabled=self.config.enabled,
            daily_limit=f"${self.config.daily_limit_dollars:.2f}",
            monthly_limit=f"${self.config.monthly_limit_dollars:.2f}",
        )

    @property
    def state(self) -> BudgetState:
        """Get current budget state, loading from disk if needed."""
        if self._state is None:
            self._state = self._load_state()
            self._check_and_reset()
        return self._state

    def _load_state(self) -> BudgetState:
        """Load budget state from disk."""
        if not self.storage_path.exists():
            return BudgetState()

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
            return BudgetState(**data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to load budget state, starting fresh", error=str(e))
            return BudgetState()

    def _save_state(self) -> None:
        """Save budget state to disk."""
        if self._state is None:
            return

        try:
            with open(self.storage_path, "w") as f:
                json.dump(asdict(self._state), f, indent=2)
        except OSError as e:
            logger.warning("Failed to save budget state", error=str(e))

    def _check_and_reset(self) -> None:
        """Check if daily/monthly reset is needed."""
        if self._state is None:
            return

        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        this_month = now.strftime("%Y-%m")

        # Daily reset
        if self._state.last_reset_date != today:
            logger.info(
                "Daily budget reset",
                previous_usage=f"${self._state.daily_usage_dollars:.4f}",
                previous_date=self._state.last_reset_date,
            )
            self._state.daily_usage_dollars = 0.0
            self._state.daily_gpu_seconds = 0.0
            self._state.last_reset_date = today
            self._state.warnings_issued = 0

        # Monthly reset
        if self._state.last_month_reset != this_month:
            logger.info(
                "Monthly budget reset",
                previous_usage=f"${self._state.monthly_usage_dollars:.4f}",
                previous_month=self._state.last_month_reset,
            )
            self._state.monthly_usage_dollars = 0.0
            self._state.monthly_gpu_seconds = 0.0
            self._state.last_month_reset = this_month

        self._save_state()

    def check_budget(self) -> BudgetCheckResult:
        """Check if GPU usage is allowed within budget.

        Returns:
            BudgetCheckResult with allowed status and remaining budget
        """
        if not self.config.enabled:
            return BudgetCheckResult(
                allowed=True,
                daily_remaining=float("inf"),
                monthly_remaining=float("inf"),
            )

        # Ensure state is current
        self._check_and_reset()
        state = self.state

        daily_remaining = self.config.daily_limit_dollars - state.daily_usage_dollars
        monthly_remaining = (
            self.config.monthly_limit_dollars - state.monthly_usage_dollars
        )

        # Check daily limit
        if state.daily_usage_dollars >= self.config.daily_limit_dollars:
            logger.warning(
                "Daily GPU budget exceeded",
                usage=f"${state.daily_usage_dollars:.4f}",
                limit=f"${self.config.daily_limit_dollars:.2f}",
            )
            return BudgetCheckResult(
                allowed=False,
                reason=(
                    f"Daily budget exceeded "
                    f"(${state.daily_usage_dollars:.4f} >= "
                    f"${self.config.daily_limit_dollars:.2f})"
                ),
                daily_remaining=0.0,
                monthly_remaining=monthly_remaining,
            )

        # Check monthly limit
        if state.monthly_usage_dollars >= self.config.monthly_limit_dollars:
            logger.warning(
                "Monthly GPU budget exceeded",
                usage=f"${state.monthly_usage_dollars:.4f}",
                limit=f"${self.config.monthly_limit_dollars:.2f}",
            )
            return BudgetCheckResult(
                allowed=False,
                reason=(
                    f"Monthly budget exceeded "
                    f"(${state.monthly_usage_dollars:.4f} >= "
                    f"${self.config.monthly_limit_dollars:.2f})"
                ),
                daily_remaining=daily_remaining,
                monthly_remaining=0.0,
            )

        # Check warning threshold
        warning = None
        daily_ratio = state.daily_usage_dollars / self.config.daily_limit_dollars
        monthly_ratio = state.monthly_usage_dollars / self.config.monthly_limit_dollars

        if daily_ratio >= self.config.warning_threshold:
            warning = (
                f"Daily budget at {daily_ratio * 100:.1f}% "
                f"(${state.daily_usage_dollars:.4f}/"
                f"${self.config.daily_limit_dollars:.2f})"
            )
            if state.warnings_issued == 0:
                logger.warning(
                    "Approaching daily budget limit", ratio=f"{daily_ratio * 100:.1f}%"
                )
                self._state.warnings_issued += 1
                self._save_state()

        elif monthly_ratio >= self.config.warning_threshold:
            warning = (
                f"Monthly budget at {monthly_ratio * 100:.1f}% "
                f"(${state.monthly_usage_dollars:.4f}/"
                f"${self.config.monthly_limit_dollars:.2f})"
            )
            if state.warnings_issued == 0:
                logger.warning(
                    "Approaching monthly budget limit",
                    ratio=f"{monthly_ratio * 100:.1f}%",
                )
                self._state.warnings_issued += 1
                self._save_state()

        return BudgetCheckResult(
            allowed=True,
            daily_remaining=daily_remaining,
            monthly_remaining=monthly_remaining,
            warning=warning,
        )

    def record_usage(self, gpu_seconds: float) -> float:
        """Record GPU usage.

        Args:
            gpu_seconds: Number of GPU seconds used

        Returns:
            Cost in dollars for this usage
        """
        if not self.config.enabled:
            return 0.0

        cost = gpu_seconds * (self.config.cost_per_gpu_hour / 3600)

        self._check_and_reset()
        state = self.state

        state.daily_usage_dollars += cost
        state.monthly_usage_dollars += cost
        state.daily_gpu_seconds += gpu_seconds
        state.monthly_gpu_seconds += gpu_seconds

        self._save_state()

        logger.debug(
            "GPU usage recorded",
            gpu_seconds=f"{gpu_seconds:.2f}",
            cost=f"${cost:.6f}",
            daily_total=f"${state.daily_usage_dollars:.4f}",
            monthly_total=f"${state.monthly_usage_dollars:.4f}",
        )

        return cost

    def get_usage_summary(self) -> dict[str, Any]:
        """Get current usage summary.

        Returns:
            Dictionary with usage statistics
        """
        self._check_and_reset()
        state = self.state

        return {
            "daily": {
                "usage_dollars": round(state.daily_usage_dollars, 6),
                "limit_dollars": self.config.daily_limit_dollars,
                "remaining_dollars": round(
                    self.config.daily_limit_dollars - state.daily_usage_dollars, 6
                ),
                "gpu_seconds": round(state.daily_gpu_seconds, 2),
                "usage_percent": round(
                    state.daily_usage_dollars / self.config.daily_limit_dollars * 100, 2
                )
                if self.config.daily_limit_dollars > 0
                else 0,
            },
            "monthly": {
                "usage_dollars": round(state.monthly_usage_dollars, 6),
                "limit_dollars": self.config.monthly_limit_dollars,
                "remaining_dollars": round(
                    self.config.monthly_limit_dollars - state.monthly_usage_dollars, 6
                ),
                "gpu_seconds": round(state.monthly_gpu_seconds, 2),
                "usage_percent": round(
                    state.monthly_usage_dollars
                    / self.config.monthly_limit_dollars
                    * 100,
                    2,
                )
                if self.config.monthly_limit_dollars > 0
                else 0,
            },
            "config": {
                "enabled": self.config.enabled,
                "cost_per_gpu_hour": self.config.cost_per_gpu_hour,
                "warning_threshold": self.config.warning_threshold,
            },
        }


def get_budget_enforcer() -> BudgetEnforcer:
    """Get budget enforcer with configuration from environment.

    Reads budget configuration from environment variables:
    - IMGPREP_MODAL_BUDGET_ENABLED: Enable budget enforcement
    - IMGPREP_MODAL_DAILY_BUDGET: Daily budget in dollars
    - IMGPREP_MODAL_MONTHLY_BUDGET: Monthly budget in dollars
    - IMGPREP_MODAL_GPU_COST_HOUR: Cost per GPU hour

    Returns:
        Configured BudgetEnforcer instance
    """
    config = BudgetConfig(
        enabled=os.getenv("IMGPREP_MODAL_BUDGET_ENABLED", "true").lower()
        in ("true", "1", "yes"),
        daily_limit_dollars=float(os.getenv("IMGPREP_MODAL_DAILY_BUDGET", "10.0")),
        monthly_limit_dollars=float(os.getenv("IMGPREP_MODAL_MONTHLY_BUDGET", "100.0")),
        cost_per_gpu_hour=float(os.getenv("IMGPREP_MODAL_GPU_COST_HOUR", "0.36")),
        warning_threshold=float(os.getenv("IMGPREP_MODAL_WARNING_THRESHOLD", "0.8")),
    )

    return BudgetEnforcer(config)
