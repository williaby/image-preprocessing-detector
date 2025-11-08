"""Tests for noxfile.py nox sessions.

This module tests all nox session functions to ensure they install
the correct dependencies and run the correct commands.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

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

    def test_sbom_generates_runtime_sbom(self):
        """Test that sbom session generates runtime SBOM."""
        session = MagicMock()
        noxfile.sbom(session)

        calls = session.run.call_args_list
        runtime_call = [c for c in calls if "sbom-runtime.json" in str(c)]
        assert len(runtime_call) == 1
        assert "--no-dev" in str(runtime_call[0])

    def test_sbom_generates_dev_sbom(self):
        """Test that sbom session generates development SBOM."""
        session = MagicMock()
        noxfile.sbom(session)

        calls = session.run.call_args_list
        dev_call = [c for c in calls if "sbom-dev.json" in str(c)]
        assert len(dev_call) == 1
        assert "--only" in str(dev_call[0])

    def test_sbom_generates_complete_sbom(self):
        """Test that sbom session generates complete SBOM."""
        session = MagicMock()
        noxfile.sbom(session)

        calls = session.run.call_args_list
        complete_call = [c for c in calls if "sbom-complete.json" in str(c)]
        assert len(complete_call) == 1

    def test_sbom_logs_all_generations(self):
        """Test that sbom session logs all SBOM generations."""
        session = MagicMock()
        noxfile.sbom(session)

        log_calls = session.log.call_args_list
        assert len(log_calls) == 3
        assert "Runtime SBOM generated" in str(log_calls[0])
        assert "Development SBOM generated" in str(log_calls[1])
        assert "Complete SBOM generated" in str(log_calls[2])


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
        assert "sbom-runtime.json" in str(session.error.call_args)

    def test_scan_uses_default_sbom_file(self, monkeypatch):
        """Test that scan session uses default SBOM file."""
        import pathlib

        mock_exists = MagicMock(return_value=True)
        monkeypatch.setattr(pathlib.Path, "exists", mock_exists)

        session = MagicMock()
        session.posargs = []
        noxfile.scan(session)

        args = session.run.call_args[0]
        assert "/workspace/sbom-runtime.json" in str(args)

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
        assert "Generating SBOMs" in str(log_calls[1])
        assert "Scanning runtime SBOM" in str(log_calls[2])
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
