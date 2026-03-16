"""Cross-version datetime compatibility layer for Python 3.10-3.13+.

Handles UTC constant, deprecated methods, and timezone operations to ensure
consistent behavior across Python versions.

Phase 1: Emergency fix for Python 3.10 compatibility
Phase 2: Full compatibility layer (expanded incrementally)
"""

import sys
import warnings
from datetime import datetime, timedelta, timezone
from functools import lru_cache

# Version detection
PY_VERSION = sys.version_info[:2]
PY_311_PLUS = PY_VERSION >= (3, 11)

# UTC constant compatibility - works across all Python 3.10+
# Use lowercase _utc internally to avoid BasedPyright reportConstantRedefinition
if PY_311_PLUS:
    try:
        from datetime import (  # type: ignore[attr-defined,unused-ignore]  # mypy 3.10 target
            UTC as _utc,
        )
    except ImportError:
        # Fallback if datetime.UTC unavailable
        _utc = timezone.utc
else:
    _utc = timezone.utc

# Export as uppercase constant
UTC = _utc

# Export the UTC constant for consistent imports
__all__ = [
    "UTC",
    "MockDatetime",
    "aware_to_naive",
    "datetime",  # Re-export datetime class for unified imports
    "ensure_aware",
    "is_aware",
    "is_naive",
    "local_now",
    # Testing utilities
    "mock_now",
    "naive_to_aware",
    "parse_iso",
    "safe_compare",
    "timedelta",
    "timestamp_now",
    "to_iso",
    "utc_from_timestamp",
    "utc_now",
]


# Global variable to hold mocked time (for testing utilities)
_mock_now_time: datetime | None = None

# Note: utc_now() is defined later with mock support


def utc_from_timestamp(timestamp: float) -> datetime:
    """Create UTC datetime from timestamp.

    Replaces deprecated datetime.utcfromtimestamp().

    Args:
        timestamp: Unix timestamp

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(timestamp, UTC)


def local_now() -> datetime:
    """Get current time in the system's local timezone.

    Returns:
        Timezone-aware datetime in local timezone
    """
    return datetime.now().astimezone()


def timestamp_now() -> float:
    """Get current UTC time as Unix timestamp.

    Useful for caching, TTL calculations, and performance measurements.

    Returns:
        Unix timestamp (seconds since epoch)
    """
    if _mock_now_time is not None:
        return _mock_now_time.timestamp()
    return datetime.now(UTC).timestamp()


def parse_iso(iso_string: str, assume_utc: bool = True) -> datetime:
    """Parse ISO format datetime string with timezone handling.

    Args:
        iso_string: ISO format datetime string (e.g., "2023-01-01T12:00:00Z")
        assume_utc: If True, assume UTC for naive datetimes (default: True)

    Returns:
        Timezone-aware datetime

    Raises:
        ValueError: If string cannot be parsed
    """
    try:
        # Normalize Z suffix to +00:00 for Python 3.10 compatibility
        # (datetime.fromisoformat only supports Z suffix from Python 3.11+)
        if iso_string.endswith("Z"):
            iso_string = iso_string[:-1] + "+00:00"

        # Handle timezone-aware ISO strings
        if "+" in iso_string or iso_string.count("-") > 2:
            # Has timezone offset
            dt = datetime.fromisoformat(iso_string)
        else:
            # Naive datetime
            dt = datetime.fromisoformat(iso_string)
            if assume_utc:
                dt = dt.replace(tzinfo=UTC)

        if is_aware(dt):
            return dt
        default_tz = UTC if assume_utc else None
        return ensure_aware(dt, default_tz)
    except ValueError as e:
        raise ValueError(f"Invalid ISO datetime string '{iso_string}': {e}") from e


def to_iso(dt: datetime, include_timezone: bool = True) -> str:
    """Convert datetime to ISO format string.

    Args:
        dt: Datetime to convert
        include_timezone: Include timezone info in output (default: True)

    Returns:
        ISO format string
    """
    if is_naive(dt):
        dt = ensure_aware(dt, UTC)

    if include_timezone:
        # Use 'Z' suffix for UTC, otherwise keep timezone offset
        if dt.tzinfo == UTC:
            return dt.isoformat().replace("+00:00", "Z")
        return dt.isoformat()

    # Strip timezone for naive-style output
    return dt.replace(tzinfo=None).isoformat()


def is_aware(dt: datetime) -> bool:
    """Check if datetime is timezone-aware.

    Args:
        dt: Datetime object to check

    Returns:
        True if datetime has timezone information
    """
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def is_naive(dt: datetime) -> bool:
    """Check if datetime is naive (no timezone).

    Args:
        dt: Datetime object to check

    Returns:
        True if datetime has no timezone information
    """
    return not is_aware(dt)


def ensure_aware(dt: datetime, tz: timezone | None = None) -> datetime:
    """Ensure datetime is timezone-aware.

    If naive, assumes UTC unless another timezone specified.

    Args:
        dt: Datetime object
        tz: Timezone to apply if datetime is naive (defaults to UTC)

    Returns:
        Timezone-aware datetime
    """
    if is_aware(dt):
        return dt
    return dt.replace(tzinfo=tz or UTC)


def naive_to_aware(dt: datetime, tz: timezone | None = None) -> datetime:
    """Convert naive datetime to aware.

    Args:
        dt: Naive datetime object
        tz: Target timezone (defaults to UTC)

    Returns:
        Timezone-aware datetime

    Raises:
        ValueError: If datetime is already timezone-aware
    """
    if is_aware(dt):
        raise ValueError("datetime is already timezone-aware")

    target_tz = tz or UTC
    return dt.replace(tzinfo=target_tz)


def aware_to_naive(dt: datetime, preserve_utc: bool = True) -> datetime:
    """Convert aware datetime to naive.

    Args:
        dt: Timezone-aware datetime
        preserve_utc: If True, converts to UTC first (recommended for storage)

    Returns:
        Naive datetime

    Raises:
        ValueError: If datetime is already naive
    """
    if is_naive(dt):
        raise ValueError("datetime is already naive")

    if preserve_utc:
        # Convert to UTC then strip timezone - safe for database storage
        utc_dt = dt.astimezone(UTC)
        return utc_dt.replace(tzinfo=None)
    # Just strip timezone (keeps local time) - use with caution
    return dt.replace(tzinfo=None)


@lru_cache(maxsize=128)
def _normalize_for_comparison(dt: datetime) -> datetime:
    """Normalize datetime for comparison (cached for performance).

    Args:
        dt: Datetime to normalize

    Returns:
        Timezone-aware datetime in UTC
    """
    if is_aware(dt):
        return dt.astimezone(UTC)
    return ensure_aware(dt, UTC)


def safe_compare(dt1: datetime, dt2: datetime) -> int:
    """Safely compare datetimes regardless of timezone awareness.

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        -1 if dt1 < dt2, 0 if equal, 1 if dt1 > dt2
    """
    norm1 = _normalize_for_comparison(dt1)
    norm2 = _normalize_for_comparison(dt2)

    if norm1 < norm2:
        return -1
    if norm1 > norm2:
        return 1
    return 0


# Migration helpers - temporary functions to catch issues during migration
def assert_datetime_aware(dt: datetime, context: str = "") -> datetime:
    """Temporary helper to catch naive datetime bugs during migration.

    Args:
        dt: Datetime to check
        context: Context string for debugging

    Returns:
        The same datetime object

    Warns:
        If datetime is naive (during migration period)
    """
    if is_naive(dt):
        warnings.warn(
            f"Naive datetime detected in {context}. Consider using ensure_aware() or utc_now()",
            DeprecationWarning,
            stacklevel=2,
        )
    return dt


# Legacy compatibility aliases (can be removed after migration)
def utcnow_compat() -> datetime:
    """Legacy compatibility for datetime.utcnow() - use utc_now() instead."""
    warnings.warn(
        "utcnow_compat() is deprecated, use utc_now() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return _original_utc_now()


def utcfromtimestamp_compat(timestamp: float) -> datetime:
    """Legacy compatibility for datetime.utcfromtimestamp() - use utc_from_timestamp() instead."""
    warnings.warn(
        "utcfromtimestamp_compat() is deprecated, use utc_from_timestamp() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return utc_from_timestamp(timestamp)


# Testing utilities - support for mocking utc_now() behavior


class MockDatetime:
    """Context manager for mocking utc_now() calls in tests.

    Usage:
        with MockDatetime("2023-01-01T12:00:00Z"):
            # Code that calls utc_now() will return the mocked time
            assert utc_now() == datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    """

    def __init__(self, mock_time: str | datetime) -> None:
        """Initialize mock datetime context.

        Args:
            mock_time: Time to mock (ISO string or datetime object)
        """
        if isinstance(mock_time, str):
            self.mock_time = parse_iso(mock_time)
        else:
            self.mock_time = ensure_aware(mock_time, UTC)

        self.previous_mock_time: datetime | None = None

    def __enter__(self) -> "MockDatetime":
        """Start mocking datetime functions."""
        global _mock_now_time  # Datetime mocking requires global state
        self.previous_mock_time = _mock_now_time
        _mock_now_time = self.mock_time
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Stop mocking datetime functions."""
        global _mock_now_time  # Datetime mocking requires global state
        _mock_now_time = self.previous_mock_time


# Global variable is already defined above


def mock_now(mock_time: str | datetime | None = None) -> datetime:
    """Get mocked current time for testing, or real time if not mocking.

    Args:
        mock_time: Time to mock (ISO string or datetime object).
                  If None, uses global mock time or real time.

    Returns:
        Mocked or real current UTC time
    """
    if mock_time is not None:
        if isinstance(mock_time, str):
            return parse_iso(mock_time)
        return ensure_aware(mock_time, UTC)

    if _mock_now_time is not None:
        return _mock_now_time

    return _original_utc_now()


# Modify utc_now to use mock when available
def _original_utc_now() -> datetime:
    """Original UTC now implementation."""
    return datetime.now(UTC)


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime.

    Replaces deprecated datetime.utcnow() with proper timezone handling.

    In tests, will return mocked time if MockDatetime context is active.

    Returns:
        Timezone-aware datetime in UTC
    """
    if _mock_now_time is not None:
        return _mock_now_time
    return _original_utc_now()
