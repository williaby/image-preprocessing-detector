"""Tests for the weak assertion detector plugin.

These tests verify the plugin correctly identifies:
- Tests with no assertions
- Tests with trivial assertions (assert True, etc.)
- Tests with suspicious patterns (assert result)
- Tests with overly broad checks (assert len(x) > 0)
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

# Add tests directory to path for plugin import
_tests_dir = Path(__file__).parent.parent
if str(_tests_dir) not in sys.path:
    sys.path.insert(0, str(_tests_dir))

from plugins.weak_assertion_detector import (
    TestAssertionStats,
    WeakAssertionInfo,
    WeakAssertionVisitor,
)


class TestWeakAssertionVisitor:
    """Test the AST visitor for weak assertion detection."""

    def test_detects_no_assertions(self):
        """Test detection of functions with no assertions."""
        source = textwrap.dedent("""
            def test_something():
                x = 1 + 1
                print(x)
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 0
        assert len(visitor.weak_patterns) == 0

    def test_detects_assert_true(self):
        """Test detection of assert True pattern."""
        source = textwrap.dedent("""
            def test_something():
                assert True
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        assert len(visitor.weak_patterns) == 1
        assert visitor.weak_patterns[0].pattern == "assert True"
        assert visitor.weak_patterns[0].severity == "error"

    def test_detects_assert_false(self):
        """Test detection of assert False pattern."""
        source = textwrap.dedent("""
            def test_something():
                assert False
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.weak_patterns) == 1
        assert visitor.weak_patterns[0].pattern == "assert False"
        assert visitor.weak_patterns[0].severity == "error"

    def test_detects_trivial_numeric_assertions(self):
        """Test detection of assert 1 and assert 0 patterns."""
        source = textwrap.dedent("""
            def test_something():
                assert 1
                assert 0
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 2
        patterns = {p.pattern for p in visitor.weak_patterns}
        assert "assert 1" in patterns
        assert "assert 0" in patterns

    def test_detects_suspicious_truthiness_check(self):
        """Test detection of 'assert result' pattern (truthiness only)."""
        source = textwrap.dedent("""
            def test_something():
                result = get_data()
                assert result
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        assert len(visitor.weak_patterns) == 1
        assert visitor.weak_patterns[0].pattern == "assert result"
        assert visitor.weak_patterns[0].severity == "warning"

    def test_does_not_flag_equality_assertions(self):
        """Test that 'assert result == expected' is NOT flagged."""
        source = textwrap.dedent("""
            def test_something():
                result = get_data()
                assert result == expected
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        # Should not flag 'assert result == expected'
        assert len(visitor.weak_patterns) == 0

    def test_does_not_flag_is_none_assertions(self):
        """Test that 'assert result is not None' is NOT flagged."""
        source = textwrap.dedent("""
            def test_something():
                result = get_data()
                assert result is not None
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        assert len(visitor.weak_patterns) == 0

    def test_detects_overly_broad_length_check(self):
        """Test detection of 'assert len(x) > 0' pattern."""
        source = textwrap.dedent("""
            def test_something():
                items = get_items()
                assert len(items) > 0
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        assert len(visitor.weak_patterns) == 1
        assert visitor.weak_patterns[0].pattern == "assert len(x) > 0"
        assert visitor.weak_patterns[0].severity == "warning"

    def test_does_not_flag_specific_length_assertions(self):
        """Test that 'assert len(x) == 5' is NOT flagged."""
        source = textwrap.dedent("""
            def test_something():
                items = get_items()
                assert len(items) == 5
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 1
        assert len(visitor.weak_patterns) == 0

    def test_counts_multiple_assertions(self):
        """Test counting multiple assertions in a function."""
        source = textwrap.dedent("""
            def test_something():
                result = get_data()
                assert result is not None
                assert result.status == "ok"
                assert len(result.items) == 3
        """)
        lines = source.split("\n")
        tree = ast.parse(source)
        visitor = WeakAssertionVisitor(lines)
        visitor.visit(tree)

        assert len(visitor.assertions) == 3
        assert len(visitor.weak_patterns) == 0


class TestTestAssertionStats:
    """Test the TestAssertionStats dataclass."""

    def test_has_weak_assertions(self):
        """Test has_weak_assertions property."""
        stats = TestAssertionStats(
            test_name="test_example",
            file_path="test_file.py",
            total_assertions=2,
            weak_assertions=1,
            strong_assertions=1,
        )
        assert stats.has_weak_assertions is True

    def test_has_no_weak_assertions(self):
        """Test has_weak_assertions when none exist."""
        stats = TestAssertionStats(
            test_name="test_example",
            file_path="test_file.py",
            total_assertions=2,
            weak_assertions=0,
            strong_assertions=2,
        )
        assert stats.has_weak_assertions is False

    def test_has_no_assertions(self):
        """Test has_no_assertions property."""
        stats = TestAssertionStats(
            test_name="test_example",
            file_path="test_file.py",
            total_assertions=0,
            weak_assertions=0,
            strong_assertions=0,
        )
        assert stats.has_no_assertions is True


class TestWeakAssertionInfo:
    """Test the WeakAssertionInfo dataclass."""

    def test_creation(self):
        """Test creating WeakAssertionInfo."""
        info = WeakAssertionInfo(
            test_name="test_example",
            file_path="test_file.py",
            line_number=42,
            pattern="assert True",
            severity="error",
            message="Trivial assertion",
        )
        assert info.test_name == "test_example"
        assert info.line_number == 42
        assert info.severity == "error"


class TestPluginIntegration:
    """Integration tests for the plugin with pytest."""

    def test_plugin_can_be_imported(self):
        """Test that plugin module can be imported."""
        from plugins import weak_assertion_detector

        assert hasattr(weak_assertion_detector, "pytest_addoption")
        assert hasattr(weak_assertion_detector, "pytest_configure")
        assert hasattr(weak_assertion_detector, "WeakAssertionPlugin")
