# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Pytest plugin to detect weak assertions in tests.

This plugin analyzes test functions to identify patterns that may indicate
insufficient test coverage or weak assertions:

1. Tests with no assertions at all
2. Tests with only trivial assertions (assert True, assert 1, etc.)
3. Tests that only check truthiness without value verification
4. Tests that use overly broad checks (assert len(x) > 0)

Usage:
    # Enable the plugin in conftest.py or pyproject.toml
    pytest_plugins = ["tests.plugins.weak_assertion_detector"]

    # Run with weak assertion report
    pytest --weak-assertions

    # Fail on weak assertions (CI mode)
    pytest --weak-assertions --fail-on-weak

Configuration (pyproject.toml):
    [tool.pytest.ini_options]
    weak_assertion_patterns = [
        "assert True",
        "assert False",
        "assert 1",
        "assert result",
    ]
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.nodes import Item
    from _pytest.terminal import TerminalReporter


# Common string constants (S1192: avoid duplicate string literals)
TRUTHINESS_CHECK_MSG = "Checks truthiness only, not specific value"


@dataclass
class WeakAssertionInfo:
    """Information about a weak assertion pattern detected."""

    test_name: str
    file_path: str
    line_number: int
    pattern: str
    severity: str  # "warning" or "error"
    message: str


@dataclass
class TestAssertionStats:
    """Statistics about assertions in a test."""

    test_name: str
    file_path: str
    total_assertions: int = 0
    weak_assertions: int = 0
    strong_assertions: int = 0
    patterns_found: list[WeakAssertionInfo] = field(default_factory=list)

    @property
    def has_weak_assertions(self) -> bool:
        """Check if test has any weak assertions."""
        return self.weak_assertions > 0

    @property
    def has_no_assertions(self) -> bool:
        """Check if test has no assertions at all."""
        return self.total_assertions == 0


class WeakAssertionVisitor(ast.NodeVisitor):
    """AST visitor to detect weak assertion patterns."""

    # Patterns that indicate weak assertions
    TRIVIAL_PATTERNS: ClassVar[dict[str, str]] = {
        "assert True": "Trivial assertion - always passes",
        "assert False": "Trivial assertion - always fails",
        "assert 1": "Trivial numeric assertion",
        "assert 0": "Trivial numeric assertion",
        "assert None": "Assertion on None (falsy)",
    }

    # Patterns that may indicate weak assertions (warnings)
    SUSPICIOUS_PATTERNS: ClassVar[dict[str, str]] = {
        "assert result": TRUTHINESS_CHECK_MSG,
        "assert response": TRUTHINESS_CHECK_MSG,
        "assert data": TRUTHINESS_CHECK_MSG,
        "assert output": TRUTHINESS_CHECK_MSG,
        "assert ret": TRUTHINESS_CHECK_MSG,
        "assert value": TRUTHINESS_CHECK_MSG,
    }

    def __init__(self, source_lines: list[str]):
        """Initialize visitor.

        Args:
            source_lines: Source code lines for context extraction.
        """
        self.source_lines = source_lines
        self.assertions: list[dict] = []
        self.weak_patterns: list[WeakAssertionInfo] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        """Visit assert statements."""
        self.assertions.append(
            {
                "line": node.lineno,
                "col": node.col_offset,
                "node": node,
            }
        )

        # Get the assertion source
        if node.lineno <= len(self.source_lines):
            line = self.source_lines[node.lineno - 1].strip()

            # Check for trivial patterns (errors)
            for pattern, message in self.TRIVIAL_PATTERNS.items():
                if pattern in line:
                    self.weak_patterns.append(
                        WeakAssertionInfo(
                            test_name="",  # Filled in later
                            file_path="",  # Filled in later
                            line_number=node.lineno,
                            pattern=pattern,
                            severity="error",
                            message=message,
                        )
                    )

            # Check for suspicious patterns (warnings)
            for pattern, message in self.SUSPICIOUS_PATTERNS.items():
                # Only match simple assertions like "assert result"
                # Not "assert result == expected"
                if line == pattern or line.startswith(f"{pattern},"):
                    self.weak_patterns.append(
                        WeakAssertionInfo(
                            test_name="",
                            file_path="",
                            line_number=node.lineno,
                            pattern=pattern,
                            severity="warning",
                            message=message,
                        )
                    )

            # Check for overly broad length checks
            if "assert len(" in line and "> 0" in line:
                self.weak_patterns.append(
                    WeakAssertionInfo(
                        test_name="",
                        file_path="",
                        line_number=node.lineno,
                        pattern="assert len(x) > 0",
                        severity="warning",
                        message="Overly broad check - consider asserting specific length",
                    )
                )

        self.generic_visit(node)


def analyze_test_function(item: Item) -> TestAssertionStats | None:
    """Analyze a test function for weak assertions.

    Args:
        item: Pytest test item.

    Returns:
        TestAssertionStats if analysis succeeded, None otherwise.
    """
    # Get the test function
    if not hasattr(item, "function"):
        return None

    func = item.function
    file_path = str(item.fspath) if hasattr(item, "fspath") else str(item.path)

    try:
        source = inspect.getsource(func)
        # Dedent to handle methods in classes
        source = textwrap.dedent(source)
        source_lines = source.split("\n")
        tree = ast.parse(source)
    except (OSError, SyntaxError, TypeError):
        return None

    visitor = WeakAssertionVisitor(source_lines)
    visitor.visit(tree)

    # Update pattern info with test details
    for pattern in visitor.weak_patterns:
        pattern.test_name = item.name
        pattern.file_path = file_path

    stats = TestAssertionStats(
        test_name=item.name,
        file_path=file_path,
        total_assertions=len(visitor.assertions),
        weak_assertions=len(
            [p for p in visitor.weak_patterns if p.severity == "error"]
        ),
        strong_assertions=len(visitor.assertions) - len(visitor.weak_patterns),
        patterns_found=visitor.weak_patterns,
    )

    return stats


def _write_report_header(terminalreporter: TerminalReporter) -> None:
    """Write the report header section."""
    terminalreporter.write_line("")
    terminalreporter.write_line("=" * 60, bold=True)
    terminalreporter.write_line("WEAK ASSERTION REPORT", bold=True)
    terminalreporter.write_line("=" * 60)


def _write_no_assertion_section(
    terminalreporter: TerminalReporter,
    no_assertion_tests: list[TestAssertionStats],
) -> None:
    """Write the 'tests with no assertions' section."""
    if not no_assertion_tests:
        return
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"Tests with NO assertions ({len(no_assertion_tests)}):",
        red=True,
        bold=True,
    )
    for stats in no_assertion_tests:
        rel_path = Path(stats.file_path).name
        terminalreporter.write_line(f"  - {rel_path}::{stats.test_name}")


def _write_weak_assertion_section(
    terminalreporter: TerminalReporter,
    weak_assertion_tests: list[TestAssertionStats],
) -> None:
    """Write the 'tests with weak assertions' section."""
    if not weak_assertion_tests:
        return
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"Tests with WEAK assertions ({len(weak_assertion_tests)}):",
        red=True,
        bold=True,
    )
    for stats in weak_assertion_tests:
        rel_path = Path(stats.file_path).name
        terminalreporter.write_line(f"  - {rel_path}::{stats.test_name}")
        for pattern in stats.patterns_found:
            if pattern.severity == "error":
                terminalreporter.write_line(
                    f"      Line {pattern.line_number}: {pattern.pattern} - {pattern.message}"
                )


def _write_warning_section(
    terminalreporter: TerminalReporter,
    warning_tests: list[TestAssertionStats],
) -> None:
    """Write the 'tests with suspicious patterns' section."""
    if not warning_tests:
        return
    terminalreporter.write_line("")
    terminalreporter.write_line(
        f"Tests with SUSPICIOUS patterns ({len(warning_tests)}):",
        yellow=True,
    )
    for stats in warning_tests:
        rel_path = Path(stats.file_path).name
        terminalreporter.write_line(f"  - {rel_path}::{stats.test_name}")
        for pattern in stats.patterns_found:
            if pattern.severity == "warning":
                terminalreporter.write_line(
                    f"      Line {pattern.line_number}: {pattern.pattern} - {pattern.message}"
                )


def _write_report_footer(
    terminalreporter: TerminalReporter,
    no_assertion_tests: list[TestAssertionStats],
    weak_assertion_tests: list[TestAssertionStats],
    warning_tests: list[TestAssertionStats],
    fail_on_weak: bool,
) -> None:
    """Write the report footer with summary and optional failure message."""
    terminalreporter.write_line("")
    terminalreporter.write_line("-" * 60)
    total_issues = len(no_assertion_tests) + len(weak_assertion_tests)
    terminalreporter.write_line(
        f"Total: {total_issues} tests with issues, {len(warning_tests)} warnings"
    )
    if fail_on_weak and (no_assertion_tests or weak_assertion_tests):
        terminalreporter.write_line(
            "FAILED: --fail-on-weak is enabled",
            red=True,
            bold=True,
        )


class WeakAssertionPlugin:
    """Pytest plugin for weak assertion detection."""

    def __init__(self, config: Config):
        """Initialize plugin.

        Args:
            config: Pytest config object.
        """
        self.config = config
        self.stats: list[TestAssertionStats] = []
        self.enabled = config.getoption("weak_assertions", False)
        self.fail_on_weak = config.getoption("fail_on_weak", False)

    def pytest_runtest_call(self, item: Item) -> None:
        """Analyze each test after collection."""
        if not self.enabled:
            return

        stats = analyze_test_function(item)
        if stats:
            self.stats.append(stats)

    def pytest_terminal_summary(
        self, terminalreporter: TerminalReporter, _exitstatus: int
    ) -> None:
        """Print summary of weak assertions."""
        if not self.enabled or not self.stats:
            return

        # Collect issues
        no_assertion_tests = [s for s in self.stats if s.has_no_assertions]
        weak_assertion_tests = [s for s in self.stats if s.has_weak_assertions]
        warning_tests = [
            s
            for s in self.stats
            if s.patterns_found
            and all(p.severity == "warning" for p in s.patterns_found)
        ]

        if not no_assertion_tests and not weak_assertion_tests and not warning_tests:
            terminalreporter.write_line("")
            terminalreporter.write_line(
                "Weak Assertion Report: All tests have strong assertions!",
                green=True,
                bold=True,
            )
            return

        _write_report_header(terminalreporter)
        _write_no_assertion_section(terminalreporter, no_assertion_tests)
        _write_weak_assertion_section(terminalreporter, weak_assertion_tests)
        _write_warning_section(terminalreporter, warning_tests)
        _write_report_footer(
            terminalreporter,
            no_assertion_tests,
            weak_assertion_tests,
            warning_tests,
            self.fail_on_weak,
        )

    def pytest_sessionfinish(self, session, _exitstatus: int) -> None:
        """Modify exit status if fail_on_weak is enabled."""
        if not self.enabled or not self.fail_on_weak:
            return

        no_assertion_tests = [s for s in self.stats if s.has_no_assertions]
        weak_assertion_tests = [s for s in self.stats if s.has_weak_assertions]

        if no_assertion_tests or weak_assertion_tests:
            # Directly modify the session's exit status
            session.exitstatus = 1


def pytest_addoption(parser: Parser) -> None:
    """Add command line options for weak assertion detection."""
    group = parser.getgroup("weak_assertions", "Weak assertion detection")
    group.addoption(
        "--weak-assertions",
        action="store_true",
        default=False,
        help="Enable weak assertion detection and report",
    )
    group.addoption(
        "--fail-on-weak",
        action="store_true",
        default=False,
        help="Fail test run if weak assertions are detected",
    )


def pytest_configure(config: Config) -> None:
    """Configure the plugin."""
    if config.getoption("weak_assertions", False):
        plugin = WeakAssertionPlugin(config)
        config.pluginmanager.register(plugin, "weak_assertion_plugin")


# Export for explicit registration
__all__ = [
    "WeakAssertionPlugin",
    "WeakAssertionVisitor",
    "analyze_test_function",
    "pytest_addoption",
    "pytest_configure",
]
