"""Tests for datetime_compat.py cross-version compatibility layer.

Ensures consistent datetime handling across Python 3.10-3.13+.
"""

import warnings
from datetime import datetime, timezone

import pytest

from image_preprocessing_detector.utils.datetime_compat import (
    UTC,
    MockDatetime,
    _normalize_for_comparison,
    assert_datetime_aware,
    aware_to_naive,
    ensure_aware,
    is_aware,
    is_naive,
    local_now,
    mock_now,
    naive_to_aware,
    parse_iso,
    safe_compare,
    timestamp_now,
    to_iso,
    utc_from_timestamp,
    utc_now,
    utcfromtimestamp_compat,
    utcnow_compat,
)


class TestUTCConstant:
    """Test UTC constant availability across Python versions."""

    def test_utc_is_timezone_utc(self) -> None:
        """UTC constant should be equivalent to timezone.utc."""
        assert timezone.utc == UTC  # noqa: UP017 - testing Python 3.10 compat

    def test_utc_offset_is_zero(self) -> None:
        """UTC should have zero offset."""
        now = datetime.now(UTC)
        assert now.utcoffset().total_seconds() == 0


class TestUtcNow:
    """Test utc_now() function."""

    def test_utc_now_returns_aware_datetime(self) -> None:
        """utc_now() should return timezone-aware datetime."""
        now = utc_now()
        assert is_aware(now)
        assert now.tzinfo == UTC

    def test_utc_now_is_recent(self) -> None:
        """utc_now() should be within a second of actual time."""
        import time

        before = time.time()
        now = utc_now()
        after = time.time()

        timestamp = now.timestamp()
        assert before <= timestamp <= after


class TestUtcFromTimestamp:
    """Test utc_from_timestamp() function."""

    def test_converts_timestamp_to_utc(self) -> None:
        """Should convert Unix timestamp to UTC datetime."""
        # Unix epoch
        dt = utc_from_timestamp(0)
        assert dt.year == 1970
        assert dt.month == 1
        assert dt.day == 1
        assert is_aware(dt)
        assert dt.tzinfo == UTC

    def test_preserves_timestamp_value(self) -> None:
        """Round-trip should preserve timestamp."""
        original = 1700000000.0
        dt = utc_from_timestamp(original)
        assert abs(dt.timestamp() - original) < 0.001


class TestLocalNow:
    """Test local_now() function."""

    def test_local_now_returns_aware_datetime(self) -> None:
        """local_now() should return timezone-aware datetime."""
        now = local_now()
        assert is_aware(now)

    def test_local_now_has_local_timezone(self) -> None:
        """local_now() should have local timezone, not necessarily UTC."""
        now = local_now()
        # Just verify it has timezone info
        assert now.tzinfo is not None


class TestTimestampNow:
    """Test timestamp_now() function."""

    def test_returns_float(self) -> None:
        """timestamp_now() should return a float."""
        ts = timestamp_now()
        assert isinstance(ts, float)

    def test_is_recent(self) -> None:
        """timestamp_now() should be recent."""
        import time

        before = time.time()
        ts = timestamp_now()
        after = time.time()

        assert before <= ts <= after

    def test_respects_mock(self) -> None:
        """timestamp_now() should respect MockDatetime."""
        mock_time = "2023-06-15T12:00:00Z"
        with MockDatetime(mock_time):
            ts = timestamp_now()
            expected = parse_iso(mock_time).timestamp()
            assert abs(ts - expected) < 0.001


class TestParseIso:
    """Test parse_iso() function."""

    def test_parse_utc_z_suffix(self) -> None:
        """Should parse ISO string with Z suffix."""
        dt = parse_iso("2023-01-15T10:30:00Z")
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert is_aware(dt)

    def test_parse_with_offset(self) -> None:
        """Should parse ISO string with timezone offset."""
        dt = parse_iso("2023-01-15T10:30:00+05:00")
        assert is_aware(dt)

    def test_parse_naive_assumes_utc(self) -> None:
        """Should assume UTC for naive datetime strings by default."""
        dt = parse_iso("2023-01-15T10:30:00", assume_utc=True)
        assert is_aware(dt)

    def test_invalid_iso_raises_valueerror(self) -> None:
        """Should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid ISO datetime string"):
            parse_iso("not-a-date")


class TestToIso:
    """Test to_iso() function."""

    def test_utc_datetime_uses_z_suffix(self) -> None:
        """UTC datetime should use Z suffix."""
        dt = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        iso = to_iso(dt)
        assert iso.endswith("Z")

    def test_naive_datetime_converted_to_utc(self) -> None:
        """Naive datetime should be converted to UTC."""
        dt = datetime(2023, 1, 15, 10, 30, 0)
        iso = to_iso(dt)
        assert is_aware(parse_iso(iso))

    def test_exclude_timezone(self) -> None:
        """Should strip timezone when include_timezone=False."""
        dt = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        iso = to_iso(dt, include_timezone=False)
        assert "+" not in iso
        assert "Z" not in iso


class TestIsAwareIsNaive:
    """Test is_aware() and is_naive() functions."""

    def test_aware_datetime_is_aware(self) -> None:
        """Aware datetime should be detected as aware."""
        dt = datetime.now(UTC)
        assert is_aware(dt) is True
        assert is_naive(dt) is False

    def test_naive_datetime_is_naive(self) -> None:
        """Naive datetime should be detected as naive."""
        dt = datetime.now()  # noqa: DTZ005 - intentional naive datetime
        assert is_naive(dt) is True
        assert is_aware(dt) is False


class TestEnsureAware:
    """Test ensure_aware() function."""

    def test_naive_becomes_aware(self) -> None:
        """Naive datetime should become aware."""
        naive = datetime(2023, 1, 15, 10, 30, 0)
        aware = ensure_aware(naive)
        assert is_aware(aware)
        assert aware.tzinfo == UTC

    def test_aware_unchanged(self) -> None:
        """Already aware datetime should be unchanged."""
        aware = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = ensure_aware(aware)
        assert result == aware

    def test_custom_timezone(self) -> None:
        """Should use provided timezone."""
        naive = datetime(2023, 1, 15, 10, 30, 0)
        custom_tz = timezone(offset=timezone.utc.utcoffset(None))  # noqa: UP017 - Py3.10 compat
        aware = ensure_aware(naive, custom_tz)
        assert is_aware(aware)


class TestNaiveToAware:
    """Test naive_to_aware() function."""

    def test_converts_naive_to_aware(self) -> None:
        """Should convert naive to aware."""
        naive = datetime(2023, 1, 15, 10, 30, 0)
        aware = naive_to_aware(naive)
        assert is_aware(aware)

    def test_raises_for_already_aware(self) -> None:
        """Should raise ValueError for already aware datetime."""
        aware = datetime.now(UTC)
        with pytest.raises(ValueError, match="already timezone-aware"):
            naive_to_aware(aware)


class TestAwareToNaive:
    """Test aware_to_naive() function."""

    def test_converts_aware_to_naive(self) -> None:
        """Should convert aware to naive."""
        aware = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        naive = aware_to_naive(aware)
        assert is_naive(naive)

    def test_raises_for_already_naive(self) -> None:
        """Should raise ValueError for already naive datetime."""
        naive = datetime.now()  # noqa: DTZ005 - intentional naive datetime
        with pytest.raises(ValueError, match="already naive"):
            aware_to_naive(naive)

    def test_preserve_utc_option(self) -> None:
        """Should convert to UTC first when preserve_utc=True."""
        aware = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        naive = aware_to_naive(aware, preserve_utc=True)
        assert naive.hour == 10  # Same as UTC hour

    def test_no_preserve_utc(self) -> None:
        """Should keep local time when preserve_utc=False."""
        aware = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        naive = aware_to_naive(aware, preserve_utc=False)
        assert is_naive(naive)


class TestSafeCompare:
    """Test safe_compare() function."""

    def test_compare_equal(self) -> None:
        """Equal datetimes should return 0."""
        dt1 = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        dt2 = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        assert safe_compare(dt1, dt2) == 0

    def test_compare_less_than(self) -> None:
        """Earlier datetime should return -1."""
        dt1 = datetime(2023, 1, 14, 10, 30, 0, tzinfo=UTC)
        dt2 = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        assert safe_compare(dt1, dt2) == -1

    def test_compare_greater_than(self) -> None:
        """Later datetime should return 1."""
        dt1 = datetime(2023, 1, 16, 10, 30, 0, tzinfo=UTC)
        dt2 = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        assert safe_compare(dt1, dt2) == 1

    def test_compare_mixed_naive_aware(self) -> None:
        """Should handle comparison of mixed naive/aware datetimes."""
        naive = datetime(2023, 1, 15, 10, 30, 0)
        aware = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        # Should not raise - both normalized to UTC
        result = safe_compare(naive, aware)
        assert result == 0


class TestNormalizeForComparison:
    """Test _normalize_for_comparison() function."""

    def test_aware_converted_to_utc(self) -> None:
        """Aware datetime should be converted to UTC."""
        dt = datetime(2023, 1, 15, 10, 30, 0, tzinfo=UTC)
        normalized = _normalize_for_comparison(dt)
        assert normalized.tzinfo == UTC

    def test_naive_assumed_utc(self) -> None:
        """Naive datetime should be assumed UTC."""
        dt = datetime(2023, 1, 15, 10, 30, 0)
        normalized = _normalize_for_comparison(dt)
        assert is_aware(normalized)


class TestAssertDatetimeAware:
    """Test assert_datetime_aware() migration helper."""

    def test_aware_passes_through(self) -> None:
        """Aware datetime should pass through unchanged."""
        aware = datetime.now(UTC)
        result = assert_datetime_aware(aware)
        assert result == aware

    def test_naive_warns(self) -> None:
        """Naive datetime should trigger deprecation warning."""
        naive = datetime.now()  # noqa: DTZ005 - intentional naive datetime
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = assert_datetime_aware(naive, "test_context")
            assert result == naive
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "test_context" in str(w[0].message)


class TestLegacyCompat:
    """Test legacy compatibility functions."""

    def test_utcnow_compat_warns(self) -> None:
        """utcnow_compat() should warn about deprecation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = utcnow_compat()
            assert is_aware(result)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_utcfromtimestamp_compat_warns(self) -> None:
        """utcfromtimestamp_compat() should warn about deprecation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = utcfromtimestamp_compat(1700000000.0)
            assert is_aware(result)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)


class TestMockDatetime:
    """Test MockDatetime context manager."""

    def test_mock_with_string(self) -> None:
        """MockDatetime should accept ISO string."""
        mock_time = "2023-06-15T12:00:00Z"
        with MockDatetime(mock_time):
            now = utc_now()
            assert now.year == 2023
            assert now.month == 6
            assert now.day == 15
            assert now.hour == 12

    def test_mock_with_datetime(self) -> None:
        """MockDatetime should accept datetime object."""
        mock_dt = datetime(2022, 12, 25, 8, 0, 0, tzinfo=UTC)
        with MockDatetime(mock_dt):
            now = utc_now()
            assert now.year == 2022
            assert now.month == 12
            assert now.day == 25

    def test_mock_restores_after_exit(self) -> None:
        """MockDatetime should restore real time after context exit."""
        with MockDatetime("2000-01-01T00:00:00Z"):
            mocked = utc_now()
            assert mocked.year == 2000

        after = utc_now()
        # After exiting context, should be back to real time
        assert after.year > 2000

    def test_nested_mocks(self) -> None:
        """Nested MockDatetime should work correctly."""
        with MockDatetime("2023-01-01T00:00:00Z"):
            outer = utc_now()
            assert outer.year == 2023
            assert outer.month == 1

            with MockDatetime("2024-06-15T12:00:00Z"):
                inner = utc_now()
                assert inner.year == 2024
                assert inner.month == 6

            # Back to outer mock
            back_to_outer = utc_now()
            assert back_to_outer.year == 2023
            assert back_to_outer.month == 1


class TestMockNow:
    """Test mock_now() function."""

    def test_mock_now_with_string(self) -> None:
        """mock_now() should accept ISO string."""
        result = mock_now("2023-06-15T12:00:00Z")
        assert result.year == 2023
        assert result.month == 6

    def test_mock_now_with_datetime(self) -> None:
        """mock_now() should accept datetime object."""
        dt = datetime(2022, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = mock_now(dt)
        assert result == dt

    def test_mock_now_uses_global_mock(self) -> None:
        """mock_now(None) should use global mock if set."""
        with MockDatetime("2020-01-01T00:00:00Z"):
            result = mock_now()
            assert result.year == 2020

    def test_mock_now_returns_real_time_when_no_mock(self) -> None:
        """mock_now(None) should return real time when no mock is set."""
        result = mock_now()
        # Should be recent (within last minute)
        now = datetime.now(UTC)
        diff = abs((now - result).total_seconds())
        assert diff < 60
