"""Tests for noxfile.py nox sessions.

This module tests all nox session functions to ensure they install
the correct dependencies and run the correct commands.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

# Skip if nox is not available (required to import noxfile.py)
pytest.importorskip("nox", reason="nox required for noxfile tests")

# Import noxfile module from root directory
noxfile_path = Path(__file__).parent.parent.parent / "noxfile.py"
spec = importlib.util.spec_from_file_location("noxfile", noxfile_path)
noxfile = importlib.util.module_from_spec(spec)
sys.modules["noxfile"] = noxfile
spec.loader.exec_module(noxfile)


class TestNoxConfiguration:
    """Test nox module-level configuration."""

    def test_default_sessions_configured(self):
        """Test that default sessions are configured correctly."""
        assert noxfile.nox.options.sessions == ["fm", "docs"]

    def test_reuse_virtualenvs_enabled(self):
        """Test that virtualenv reuse is enabled."""
        assert noxfile.nox.options.reuse_existing_virtualenvs is True


class TestFmSession:
    """Test the front matter validation session."""

    def test_fm_installs_dependencies(self):
        """Test that fm session installs required dependencies."""
        session = MagicMock()
        noxfile.fm(session)

        session.install.assert_called_once_with(
            "pydantic>=2.0", "python-frontmatter>=1.1", "ruamel.yaml>=0.18"
        )

    def test_fm_runs_validation_script(self):
        """Test that fm session runs validation script with autofix."""
        session = MagicMock()
        noxfile.fm(session)

        session.run.assert_called_once_with(
            "python", "tools/validate_front_matter.py", "docs", "--fix"
        )

    def test_fm_session_complete_workflow(self):
        """Test complete fm session workflow."""
        session = MagicMock()
        noxfile.fm(session)

        # Verify install happens before run
        assert session.install.call_count == 1
        assert session.run.call_count == 1
        assert session.method_calls[0][0] == "install"
        assert session.method_calls[1][0] == "run"


class TestDocsSession:
    """Test the documentation building session."""

    def test_docs_installs_project_with_dev_extras(self):
        """Test that docs session installs project with dev extras."""
        session = MagicMock()
        noxfile.docs(session)

        session.install.assert_called_once_with("-e", ".[dev]")

    def test_docs_builds_in_strict_mode(self):
        """Test that docs session builds documentation in strict mode."""
        session = MagicMock()
        noxfile.docs(session)

        session.run.assert_called_once_with("mkdocs", "build", "--strict")

    def test_docs_session_complete_workflow(self):
        """Test complete docs session workflow."""
        session = MagicMock()
        noxfile.docs(session)

        # Verify install happens before run
        assert session.install.call_count == 1
        assert session.run.call_count == 1
        assert session.method_calls[0][0] == "install"
        assert session.method_calls[1][0] == "run"


class TestServeSession:
    """Test the documentation serving session."""

    def test_serve_installs_project_with_dev_extras(self):
        """Test that serve session installs project with dev extras."""
        session = MagicMock()
        noxfile.serve(session)

        session.install.assert_called_once_with("-e", ".[dev]")

    def test_serve_runs_mkdocs_server(self):
        """Test that serve session runs MkDocs development server."""
        session = MagicMock()
        noxfile.serve(session)

        session.run.assert_called_once_with("mkdocs", "serve")

    def test_serve_session_complete_workflow(self):
        """Test complete serve session workflow."""
        session = MagicMock()
        noxfile.serve(session)

        # Verify install happens before run
        assert session.install.call_count == 1
        assert session.run.call_count == 1
        assert session.method_calls[0][0] == "install"
        assert session.method_calls[1][0] == "run"


class TestDocstringsSession:
    """Test the docstring validation session."""

    def test_docstrings_installs_dependencies(self):
        """Test that docstrings session installs required dependencies."""
        session = MagicMock()
        noxfile.docstrings(session)

        session.install.assert_called_once_with("pydocstyle>=6.3", "interrogate>=1.7")

    def test_docstrings_runs_pydocstyle(self):
        """Test that docstrings session runs pydocstyle checker."""
        session = MagicMock()
        noxfile.docstrings(session)

        assert call("pydocstyle", "src/") in session.run.call_args_list

    def test_docstrings_runs_interrogate(self):
        """Test that docstrings session runs interrogate checker."""
        session = MagicMock()
        noxfile.docstrings(session)

        assert (
            call("interrogate", "-c", "pyproject.toml", "src/")
            in session.run.call_args_list
        )

    def test_docstrings_session_complete_workflow(self):
        """Test complete docstrings session workflow."""
        session = MagicMock()
        noxfile.docstrings(session)

        # Verify install happens before runs
        assert session.install.call_count == 1
        assert session.run.call_count == 2
        assert session.method_calls[0][0] == "install"
        assert session.method_calls[1][0] == "run"
        assert session.method_calls[2][0] == "run"


class TestValidateSession:
    """Test the combined validation session."""

    def test_validate_installs_all_dependencies(self):
        """Test that validate session installs all required dependencies."""
        session = MagicMock()
        noxfile.validate(session)

        session.install.assert_called_once_with(
            "-e",
            ".[dev]",
            "pydantic>=2.0",
            "python-frontmatter>=1.1",
            "ruamel.yaml>=0.18",
            "pydocstyle>=6.3",
            "interrogate>=1.7",
        )

    def test_validate_runs_front_matter_validation(self):
        """Test that validate session runs front matter validation."""
        session = MagicMock()
        noxfile.validate(session)

        assert (
            call("python", "tools/validate_front_matter.py", "docs", "--fix")
            in session.run.call_args_list
        )

    def test_validate_runs_pydocstyle(self):
        """Test that validate session runs pydocstyle checker."""
        session = MagicMock()
        noxfile.validate(session)

        assert call("pydocstyle", "src/") in session.run.call_args_list

    def test_validate_runs_interrogate(self):
        """Test that validate session runs interrogate checker."""
        session = MagicMock()
        noxfile.validate(session)

        assert (
            call("interrogate", "-c", "pyproject.toml", "src/")
            in session.run.call_args_list
        )

    def test_validate_builds_docs_in_strict_mode(self):
        """Test that validate session builds documentation in strict mode."""
        session = MagicMock()
        noxfile.validate(session)

        assert call("mkdocs", "build", "--strict") in session.run.call_args_list

    def test_validate_session_complete_workflow(self):
        """Test complete validate session workflow."""
        session = MagicMock()
        noxfile.validate(session)

        # Verify install happens before all runs
        assert session.install.call_count == 1
        assert session.run.call_count == 4
        assert session.method_calls[0][0] == "install"

        # Verify all run calls are present
        run_calls = [call[0] for call in session.method_calls if call[0] == "run"]
        assert len(run_calls) == 4

    def test_validate_session_execution_order(self):
        """Test that validate session executes commands in correct order."""
        session = MagicMock()
        noxfile.validate(session)

        # Get all run calls in order
        run_calls = [call for call in session.method_calls if call[0] == "run"]

        # Verify execution order
        assert len(run_calls) == 4
        # Front matter validation first
        assert run_calls[0][1] == (
            "python",
            "tools/validate_front_matter.py",
            "docs",
            "--fix",
        )
        # pydocstyle second
        assert run_calls[1][1] == ("pydocstyle", "src/")
        # interrogate third
        assert run_calls[2][1] == ("interrogate", "-c", "pyproject.toml", "src/")
        # mkdocs build last
        assert run_calls[3][1] == ("mkdocs", "build", "--strict")


class TestReuseSession:
    """Test the REUSE compliance checking session."""

    def test_reuse_runs_docker_command(self):
        """Test that reuse session runs Docker with REUSE lint command."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse(session)

        args = session.run.call_args[0]
        assert "docker" in args
        assert "fsfe/reuse:latest" in args
        assert "lint" in args

    def test_reuse_uses_default_path(self):
        """Test that reuse session uses default path when no args provided."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse(session)

        args = session.run.call_args[0]
        assert ".:/data" in str(args)

    def test_reuse_uses_custom_path(self):
        """Test that reuse session uses custom path from args."""
        session = MagicMock()
        session.posargs = ["/custom/path"]
        noxfile.reuse(session)

        args = session.run.call_args[0]
        assert "/custom/path:/data" in str(args)

    def test_reuse_uses_external_flag(self):
        """Test that reuse session uses external=True for Docker."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse(session)

        assert session.run.call_args[1]["external"] is True


class TestReuseSpdxSession:
    """Test the REUSE SPDX generation session."""

    def test_reuse_spdx_runs_docker_spdx_command(self):
        """Test that reuse_spdx session runs Docker with SPDX command."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse_spdx(session)

        args = session.run.call_args[0]
        assert "docker" in args
        assert "fsfe/reuse:latest" in args
        assert "spdx" in args

    def test_reuse_spdx_generates_json_output(self):
        """Test that reuse_spdx session generates JSON output file."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse_spdx(session)

        args = session.run.call_args[0]
        assert "/data/reuse-spdx.json" in str(args)

    def test_reuse_spdx_logs_success_message(self):
        """Test that reuse_spdx session logs success message."""
        session = MagicMock()
        session.posargs = []
        noxfile.reuse_spdx(session)

        session.log.assert_called_once_with("SPDX document generated: reuse-spdx.json")


class TestSbomSession:
    """Test the SBOM generation session."""

    def test_sbom_installs_cyclonedx_bom(self):
        """Test that sbom session installs cyclonedx-bom package."""
        session = MagicMock()
        noxfile.sbom(session)

        session.install.assert_called_once_with("cyclonedx-bom==4.6.1")

    def test_sbom_generates_complete_sbom(self):
        """Test that sbom session generates complete SBOM from environment.

        Note: UV migration simplified SBOM generation to a single complete
        environment-based SBOM, replacing the separate runtime/dev/complete files.
        """
        session = MagicMock()
        noxfile.sbom(session)

        calls = session.run.call_args_list
        complete_call = [c for c in calls if "sbom-complete.json" in str(c)]
        assert len(complete_call) == 1
        # Verify it uses environment-based generation (UV approach)
        assert "environment" in str(complete_call[0])

    def test_sbom_logs_generation(self):
        """Test that sbom session logs SBOM generation and UV note."""
        session = MagicMock()
        noxfile.sbom(session)

        log_calls = session.log.call_args_list
        assert len(log_calls) == 2
        assert "Complete SBOM generated" in str(log_calls[0])
        assert "granular SBOMs" in str(log_calls[1])


class TestScanSession:
    """Test the SBOM scanning session."""

    def test_scan_imports_pathlib(self, monkeypatch):
        """Test that scan session imports pathlib."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        # Verify pathlib was used
        mock_exists.assert_called_once()

    def test_scan_checks_sbom_file_exists(self, monkeypatch):
        """Test that scan session checks if SBOM file exists."""
        import pathlib

        mock_exists = MagicMock(return_value=False)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        session.error.assert_called_once()
        assert "sbom-complete.json" in str(session.error.call_args)

    def test_scan_uses_default_sbom_file(self, monkeypatch):
        """Test that scan session uses default SBOM file (sbom-complete.json for UV)."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        args = session.run.call_args[0]
        assert "/workspace/sbom-complete.json" in str(args)

    def test_scan_uses_custom_sbom_file(self, monkeypatch):
        """Test that scan session uses custom SBOM file from args."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = ["custom-sbom.json"]
        noxfile.scan(session)

        args = session.run.call_args[0]
        assert "/workspace/custom-sbom.json" in str(args)

    def test_scan_runs_trivy_docker_command(self, monkeypatch):
        """Test that scan session runs Trivy Docker command."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        args = session.run.call_args[0]
        assert "docker" in args
        assert "aquasec/trivy:latest" in args

    def test_scan_uses_severity_filter(self, monkeypatch):
        """Test that scan session uses severity filter."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        args = session.run.call_args[0]
        assert "--severity" in args
        assert "CRITICAL,HIGH" in args


class TestComplianceSession:
    """Test the comprehensive compliance session."""

    def test_compliance_calls_reuse_session(self, monkeypatch):
        """Test that compliance session calls reuse session."""
        mock_reuse = MagicMock()
        monkeypatch.setattr(noxfile, "reuse", mock_reuse)
        monkeypatch.setattr(noxfile, "sbom", MagicMock())
        monkeypatch.setattr(noxfile, "scan", MagicMock())

        session = MagicMock()
        noxfile.compliance(session)

        mock_reuse.assert_called_once_with(session)

    def test_compliance_calls_sbom_session(self, monkeypatch):
        """Test that compliance session calls sbom session."""
        monkeypatch.setattr(noxfile, "reuse", MagicMock())
        mock_sbom = MagicMock()
        monkeypatch.setattr(noxfile, "sbom", mock_sbom)
        monkeypatch.setattr(noxfile, "scan", MagicMock())

        session = MagicMock()
        noxfile.compliance(session)

        mock_sbom.assert_called_once_with(session)

    def test_compliance_calls_scan_session(self, monkeypatch):
        """Test that compliance session calls scan session."""
        monkeypatch.setattr(noxfile, "reuse", MagicMock())
        monkeypatch.setattr(noxfile, "sbom", MagicMock())
        mock_scan = MagicMock()
        monkeypatch.setattr(noxfile, "scan", mock_scan)

        session = MagicMock()
        noxfile.compliance(session)

        mock_scan.assert_called_once_with(session)

    def test_compliance_logs_progress(self, monkeypatch):
        """Test that compliance session logs progress messages."""
        monkeypatch.setattr(noxfile, "reuse", MagicMock())
        monkeypatch.setattr(noxfile, "sbom", MagicMock())
        monkeypatch.setattr(noxfile, "scan", MagicMock())

        session = MagicMock()
        noxfile.compliance(session)

        log_calls = session.log.call_args_list
        assert len(log_calls) == 4
        assert "REUSE compliance" in str(log_calls[0])
        assert "Generating SBOM" in str(log_calls[1])
        assert "Scanning SBOM" in str(log_calls[2])
        assert "completed successfully" in str(log_calls[3])


class TestModuleAttributes:
    """Test that noxfile module has expected attributes."""

    def test_noxfile_has_nox_module(self):
        """Test that noxfile imports nox module."""
        assert hasattr(noxfile, "nox")

    def test_noxfile_has_all_session_functions(self):
        """Test that noxfile defines all expected session functions."""
        assert hasattr(noxfile, "fm")
        assert hasattr(noxfile, "docs")
        assert hasattr(noxfile, "serve")
        assert hasattr(noxfile, "docstrings")
        assert hasattr(noxfile, "validate")
        assert hasattr(noxfile, "reuse")
        assert hasattr(noxfile, "reuse_spdx")
        assert hasattr(noxfile, "sbom")
        assert hasattr(noxfile, "scan")
        assert hasattr(noxfile, "compliance")

    def test_session_functions_are_callable(self):
        """Test that all session functions are callable."""
        assert callable(noxfile.fm)
        assert callable(noxfile.docs)
        assert callable(noxfile.serve)
        assert callable(noxfile.docstrings)
        assert callable(noxfile.validate)
        assert callable(noxfile.reuse)
        assert callable(noxfile.reuse_spdx)
        assert callable(noxfile.sbom)
        assert callable(noxfile.scan)
        assert callable(noxfile.compliance)

    def test_module_has_docstring(self):
        """Test that noxfile module has a docstring."""
        assert noxfile.__doc__ is not None
        assert len(noxfile.__doc__) > 0

    def test_session_functions_have_docstrings(self):
        """Test that all session functions have docstrings."""
        assert noxfile.fm.__doc__ is not None
        assert noxfile.docs.__doc__ is not None
        assert noxfile.serve.__doc__ is not None
        assert noxfile.docstrings.__doc__ is not None
        assert noxfile.validate.__doc__ is not None
        assert noxfile.reuse.__doc__ is not None
        assert noxfile.reuse_spdx.__doc__ is not None
        assert noxfile.sbom.__doc__ is not None
        assert noxfile.scan.__doc__ is not None
        assert noxfile.compliance.__doc__ is not None


class TestTestsSession:
    """Test the multi-version tests session."""

    def test_tests_installs_dev_extras(self):
        """Test that tests session installs project with dev extras."""
        session = MagicMock()
        session.posargs = []
        noxfile.tests(session)

        session.install.assert_called_once_with(".[dev]")

    def test_tests_runs_pytest_with_coverage(self):
        """Test that tests session runs pytest with coverage by default."""
        session = MagicMock()
        session.posargs = []
        noxfile.tests(session)

        session.run.assert_called_once_with(
            "pytest", "-v", "--cov=src", "--cov-report=term-missing"
        )

    def test_tests_uses_custom_args(self):
        """Test that tests session uses custom arguments when provided."""
        session = MagicMock()
        session.posargs = ["-k", "test_schema"]
        noxfile.tests(session)

        session.run.assert_called_once_with("pytest", "-k", "test_schema")

    def test_tests_session_workflow(self):
        """Test complete tests session workflow."""
        session = MagicMock()
        session.posargs = []
        noxfile.tests(session)

        assert session.install.call_count == 1
        assert session.run.call_count == 1


class TestTestsNoCovSession:
    """Test the tests_no_cov session."""

    def test_tests_no_cov_installs_dev_extras(self):
        """Test that tests_no_cov session installs project with dev extras."""
        session = MagicMock()
        session.posargs = []
        noxfile.tests_no_cov(session)

        session.install.assert_called_once_with(".[dev]")

    def test_tests_no_cov_runs_pytest_without_coverage(self):
        """Test that tests_no_cov session runs pytest without coverage."""
        session = MagicMock()
        session.posargs = []
        noxfile.tests_no_cov(session)

        session.run.assert_called_once_with("pytest", "-v", "-x")

    def test_tests_no_cov_uses_custom_args(self):
        """Test that tests_no_cov session uses custom arguments."""
        session = MagicMock()
        session.posargs = ["-k", "test_fast"]
        noxfile.tests_no_cov(session)

        session.run.assert_called_once_with("pytest", "-k", "test_fast")


class TestTypeCheckSession:
    """Test the type checking session."""

    def test_type_check_installs_dev_extras(self):
        """Test that type_check session installs project with dev extras."""
        session = MagicMock()
        noxfile.type_check(session)

        session.install.assert_called_once_with(".[dev]")

    def test_type_check_runs_mypy(self):
        """Test that type_check session runs mypy on src directory."""
        session = MagicMock()
        noxfile.type_check(session)

        session.run.assert_called_once_with("mypy", "src")


class TestLintSession:
    """Test the linting session."""

    def test_lint_installs_dev_extras(self):
        """Test that lint session installs project with dev extras."""
        session = MagicMock()
        noxfile.lint(session)

        session.install.assert_called_once_with(".[dev]")

    def test_lint_runs_ruff(self):
        """Test that lint session runs ruff on src and tests directories."""
        session = MagicMock()
        noxfile.lint(session)

        session.run.assert_called_once_with("ruff", "check", "src", "tests")


class TestTestsMlSession:
    """Test the ML tests session."""

    def test_tests_ml_installs_dev_and_ml_extras(self):
        """Test that tests_ml session installs project with dev and ml extras."""
        session = MagicMock()
        noxfile.tests_ml(session)

        session.install.assert_called_once_with(".[dev,ml]")

    def test_tests_ml_runs_pytest_excluding_slow_tests(self):
        """Test that tests_ml session runs pytest excluding slow tests."""
        session = MagicMock()
        noxfile.tests_ml(session)

        session.run.assert_called_once_with("pytest", "-v", "-m", "not slow")


class TestTestsOpencvCompatSession:
    """Test the OpenCV compatibility tests session."""

    def test_tests_opencv_compat_installs_specific_opencv_version(self):
        """Test that tests_opencv_compat installs specific OpenCV version."""
        session = MagicMock()
        noxfile.tests_opencv_compat(session, opencv="4.8.0")

        # Verify OpenCV is installed before project dev extras
        calls = session.install.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("opencv-python-headless==4.8.0",)
        assert calls[1][0] == (".[dev]",)

    def test_tests_opencv_compat_runs_integration_tests(self):
        """Test that tests_opencv_compat runs integration tests."""
        session = MagicMock()
        noxfile.tests_opencv_compat(session, opencv="4.9.0")

        session.run.assert_called_once_with("pytest", "-v", "-m", "integration")

    def test_tests_opencv_compat_with_different_versions(self):
        """Test tests_opencv_compat with different OpenCV versions."""
        for opencv_version in ["4.8.0", "4.9.0", "4.10.0"]:
            session = MagicMock()
            noxfile.tests_opencv_compat(session, opencv=opencv_version)

            # Verify correct OpenCV version is installed
            install_calls = session.install.call_args_list
            assert install_calls[0][0] == (f"opencv-python-headless=={opencv_version}",)


class TestQualitySession:
    """Test the quality checks session."""

    def test_quality_installs_dev_extras(self):
        """Test that quality session installs project with dev extras."""
        session = MagicMock()
        noxfile.quality(session)

        session.install.assert_called_once_with(".[dev]")

    def test_quality_runs_ruff_format_check(self):
        """Test that quality session runs ruff format check."""
        session = MagicMock()
        noxfile.quality(session)

        run_calls = session.run.call_args_list
        format_call = [c for c in run_calls if "format" in str(c)]
        assert len(format_call) == 1
        assert format_call[0][0] == ("ruff", "format", "--check", "src", "tests")

    def test_quality_runs_ruff_lint(self):
        """Test that quality session runs ruff lint."""
        session = MagicMock()
        noxfile.quality(session)

        run_calls = session.run.call_args_list
        lint_call = [c for c in run_calls if c[0] == ("ruff", "check", "src", "tests")]
        assert len(lint_call) == 1

    def test_quality_runs_mypy(self):
        """Test that quality session runs mypy type checking."""
        session = MagicMock()
        noxfile.quality(session)

        run_calls = session.run.call_args_list
        mypy_call = [c for c in run_calls if c[0] == ("mypy", "src")]
        assert len(mypy_call) == 1

    def test_quality_runs_pytest_with_coverage_threshold(self):
        """Test that quality session runs pytest with coverage threshold."""
        session = MagicMock()
        noxfile.quality(session)

        run_calls = session.run.call_args_list
        pytest_call = [
            c
            for c in run_calls
            if "pytest" in str(c) and "--cov-fail-under=80" in str(c)
        ]
        assert len(pytest_call) == 1

    def test_quality_logs_progress(self):
        """Test that quality session logs progress messages."""
        session = MagicMock()
        noxfile.quality(session)

        log_calls = session.log.call_args_list
        assert len(log_calls) >= 5  # At least 5 log messages
        # Check for key log messages
        log_messages = [str(call) for call in log_calls]
        assert any("ruff format" in msg for msg in log_messages)
        assert any("ruff lint" in msg for msg in log_messages)
        assert any("mypy" in msg for msg in log_messages)
        assert any("tests" in msg for msg in log_messages)

    def test_quality_session_execution_order(self):
        """Test that quality session executes checks in correct order."""
        session = MagicMock()
        noxfile.quality(session)

        # Get all method calls in order
        method_calls = session.method_calls

        # Find indices of key operations
        install_idx = next(i for i, c in enumerate(method_calls) if c[0] == "install")
        run_indices = [i for i, c in enumerate(method_calls) if c[0] == "run"]

        # Verify install happens first
        assert install_idx < min(run_indices)

        # Verify all run calls happen after install
        assert all(idx > install_idx for idx in run_indices)


class TestCiSession:
    """Test the CI validation session."""

    def test_ci_notifies_tests_for_available_python_versions(self, monkeypatch):
        """Test that ci session notifies tests for available Python versions."""
        session = MagicMock()

        # Mock py_version_available to return True for all versions
        monkeypatch.setattr(noxfile, "py_version_available", lambda s, v: True)

        noxfile.ci(session)

        # Verify notify was called for each Python version
        notify_calls = session.notify.call_args_list
        # Should have tests-X.Y and type_check-X.Y for each version, plus quality
        expected_notifications = len(noxfile.PYTHON_VERSIONS) * 2 + 1
        assert len(notify_calls) == expected_notifications

    def test_ci_skips_unavailable_python_versions(self, monkeypatch):
        """Test that ci session skips unavailable Python versions."""
        session = MagicMock()

        # Mock py_version_available to return False for all versions
        monkeypatch.setattr(noxfile, "py_version_available", lambda s, v: False)

        noxfile.ci(session)

        # Should only notify quality session
        notify_calls = session.notify.call_args_list
        assert len(notify_calls) == 1
        assert notify_calls[0][0] == ("quality",)

    def test_ci_warns_about_unavailable_versions(self, monkeypatch):
        """Test that ci session warns about unavailable Python versions."""
        session = MagicMock()

        # Mock py_version_available to return False
        monkeypatch.setattr(noxfile, "py_version_available", lambda s, v: False)

        noxfile.ci(session)

        # Should have warnings for each unavailable version
        warn_calls = session.warn.call_args_list
        assert len(warn_calls) == len(noxfile.PYTHON_VERSIONS)
        for warn_call in warn_calls:
            assert "not available" in str(warn_call)

    def test_ci_notifies_quality_session(self, monkeypatch):
        """Test that ci session always notifies quality session."""
        session = MagicMock()

        # Mock py_version_available to return True
        monkeypatch.setattr(noxfile, "py_version_available", lambda s, v: True)

        noxfile.ci(session)

        notify_calls = session.notify.call_args_list
        quality_calls = [c for c in notify_calls if c[0] == ("quality",)]
        assert len(quality_calls) == 1

    def test_ci_logs_start_message(self, monkeypatch):
        """Test that ci session logs start message."""
        session = MagicMock()

        # Mock py_version_available to avoid unnecessary notifications
        monkeypatch.setattr(noxfile, "py_version_available", lambda s, v: False)

        noxfile.ci(session)

        log_calls = session.log.call_args_list
        assert len(log_calls) >= 1
        assert "CI validation" in str(log_calls[0])


class TestPyVersionAvailableHelper:
    """Test the py_version_available helper function."""

    def test_py_version_available_returns_true_for_available_version(self):
        """Test that py_version_available returns True when version is available."""
        session = MagicMock()
        session.run = MagicMock()  # Simulate successful run

        result = noxfile.py_version_available(session, "3.12")

        assert result is True
        session.run.assert_called_once_with(
            "python3.12", "--version", silent=True, external=True
        )

    def test_py_version_available_returns_false_for_unavailable_version(self):
        """Test that py_version_available returns False when version is unavailable."""
        session = MagicMock()
        session.run = MagicMock(side_effect=Exception("Not found"))

        result = noxfile.py_version_available(session, "3.99")

        assert result is False

    def test_py_version_available_handles_different_exceptions(self):
        """Test that py_version_available handles different exception types."""
        session = MagicMock()

        # Test various exception types
        for exception in [
            FileNotFoundError("Not found"),
            RuntimeError("Failed"),
            ValueError("Invalid"),
        ]:
            session.run = MagicMock(side_effect=exception)
            result = noxfile.py_version_available(session, "3.10")
            assert result is False

    def test_py_version_available_passes_correct_args(self):
        """Test that py_version_available passes correct arguments to session.run."""
        session = MagicMock()

        noxfile.py_version_available(session, "3.11")

        # Verify correct arguments were passed
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert call_args[0] == ("python3.11", "--version")
        assert call_args[1]["silent"] is True
        assert call_args[1]["external"] is True


class TestPythonVersionsConstant:
    """Test the PYTHON_VERSIONS constant."""

    def test_python_versions_is_list(self):
        """Test that PYTHON_VERSIONS is a list."""
        assert isinstance(noxfile.PYTHON_VERSIONS, list)

    def test_python_versions_contains_valid_versions(self):
        """Test that PYTHON_VERSIONS contains valid version strings."""
        for version in noxfile.PYTHON_VERSIONS:
            assert isinstance(version, str)
            # Version format should be X.Y
            parts = version.split(".")
            assert len(parts) == 2
            assert all(part.isdigit() for part in parts)

    def test_python_versions_includes_expected_versions(self):
        """Test that PYTHON_VERSIONS includes expected Python versions."""
        # According to noxfile, should support 3.10-3.14
        expected_versions = ["3.10", "3.11", "3.12", "3.13", "3.14"]
        assert expected_versions == noxfile.PYTHON_VERSIONS


class TestNoxOptions:
    """Test nox options configuration."""

    def test_default_venv_backend_configured(self):
        """Test that default venv backend is configured."""
        assert hasattr(noxfile.nox.options, "default_venv_backend")
        assert noxfile.nox.options.default_venv_backend == "uv|virtualenv"
