"""Nox sessions for local testing and documentation workflows.

Nox is a command-line tool that automates testing in multiple Python environments.
This file defines sessions for documentation validation, building, and serving.

Usage:
    # Documentation sessions
    nox -s fm          # Validate and autofix front matter
    nox -s docs        # Build documentation
    nox -s serve       # Serve documentation locally
    nox -s docstrings  # Check docstring coverage

    # Compliance sessions
    nox -s reuse       # Check REUSE compliance
    nox -s sbom        # Generate SBOM
    nox -s scan        # Scan SBOM for vulnerabilities

    # Multi-version testing sessions
    nox -s tests           # Run tests on all Python versions
    nox -s tests-3.12      # Run tests on specific version
    nox -s type_check      # Run mypy on all versions
    nox -s lint            # Run ruff on all versions
    nox -s quality         # Run all quality checks (pre-commit)
    nox -s ci              # Run full CI validation suite

    # Advanced usage
    nox -l                 # List all available sessions
    nox -t ml              # Run all ML-tagged sessions
    nox -s tests -- -k test_schema  # Pass pytest arguments
"""

import nox

# Supported Python versions (aligned with pyproject.toml: >=3.10,<3.15)
PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13", "3.14"]

# Use the same Python version as the project
nox.options.sessions = ["fm", "docs"]
nox.options.reuse_existing_virtualenvs = True

# Optional: Use uv as the venv backend for speed (falls back to virtualenv if uv not available)
nox.options.default_venv_backend = "uv|virtualenv"


@nox.session(python="3.12")
def fm(session: nox.Session) -> None:
    """Validate and autofix front matter in documentation.

    This session installs the required dependencies and runs the front matter
    validation script with autofix enabled.
    """
    session.install("pydantic>=2.0", "python-frontmatter>=1.1", "ruamel.yaml>=0.18")
    session.run("python", "tools/validate_front_matter.py", "docs", "--fix")


@nox.session(python="3.12")
def docs(session: nox.Session) -> None:
    """Build documentation with MkDocs.

    This session installs the project with docs dependencies and builds
    the documentation in strict mode.
    """
    session.install("-e", ".[dev]")
    session.run("mkdocs", "build", "--strict")


@nox.session(python="3.12")
def serve(session: nox.Session) -> None:
    """Serve documentation locally for development.

    This session starts the MkDocs development server with live reloading.
    Access at http://127.0.0.1:8000
    """
    session.install("-e", ".[dev]")
    session.run("mkdocs", "serve")


@nox.session(python="3.12")
def docstrings(session: nox.Session) -> None:
    """Check docstring coverage with interrogate and pydocstyle.

    This session validates that docstrings meet the Google style convention
    and that coverage meets the minimum threshold.
    """
    session.install("pydocstyle>=6.3", "interrogate>=1.7")
    session.run("pydocstyle", "src/")
    session.run("interrogate", "-c", "pyproject.toml", "src/")


@nox.session(python="3.12")
def validate(session: nox.Session) -> None:
    """Run all validation checks for documentation.

    This session combines front matter validation, docstring checks,
    and documentation building to ensure everything is correct.
    """
    session.install(
        "-e",
        ".[dev]",
        "pydantic>=2.0",
        "python-frontmatter>=1.1",
        "ruamel.yaml>=0.18",
        "pydocstyle>=6.3",
        "interrogate>=1.7",
    )
    session.run("python", "tools/validate_front_matter.py", "docs", "--fix")
    session.run("pydocstyle", "src/")
    session.run("interrogate", "-c", "pyproject.toml", "src/")
    session.run("mkdocs", "build", "--strict")


@nox.session(python="3.12")
def reuse(session: nox.Session) -> None:
    """Check REUSE compliance.

    This session uses the REUSE tool to verify that all files have proper
    licensing information according to the REUSE specification.
    Requires Docker to be installed and running.
    """
    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{session.posargs[0] if session.posargs else '.'}:/data",
        "fsfe/reuse:latest",
        "lint",
        external=True,
    )


@nox.session(python="3.12")
def reuse_spdx(session: nox.Session) -> None:
    """Generate REUSE SPDX document.

    This session generates an SPDX document from the REUSE metadata.
    The SPDX file is saved to reuse-spdx.json in the current directory.
    Requires Docker to be installed and running.
    """
    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{session.posargs[0] if session.posargs else '.'}:/data",
        "fsfe/reuse:latest",
        "spdx",
        "--output",
        "/data/reuse-spdx.json",
        external=True,
    )
    session.log("SPDX document generated: reuse-spdx.json")


@nox.session(python="3.12")
def sbom(session: nox.Session) -> None:
    """Generate CycloneDX SBOM.

    This session generates Software Bill of Materials (SBOM) in CycloneDX format
    for runtime, development, and complete dependency sets.
    """
    session.install("cyclonedx-bom==4.6.1")

    # Generate runtime SBOM (production dependencies only)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-runtime.json",
        "--no-dev",
    )
    session.log("Runtime SBOM generated: sbom-runtime.json")

    # Generate development SBOM (dev dependencies only)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-dev.json",
        "--only",
        "dev",
    )
    session.log("Development SBOM generated: sbom-dev.json")

    # Generate complete SBOM (all dependencies)
    session.run(
        "cyclonedx-py",
        "poetry",
        "--of",
        "json",
        "-o",
        "sbom-complete.json",
    )
    session.log("Complete SBOM generated: sbom-complete.json")


@nox.session(python="3.12")
def scan(session: nox.Session) -> None:
    """Scan SBOM for vulnerabilities.

    This session uses Trivy to scan the generated SBOMs for known vulnerabilities.
    Requires Docker to be installed and running.
    Requires SBOM files to be generated first (run 'nox -s sbom').
    """
    import pathlib

    sbom_file = session.posargs[0] if session.posargs else "sbom-runtime.json"

    if not pathlib.Path(sbom_file).exists():
        session.error(f"SBOM file not found: {sbom_file}. Run 'nox -s sbom' first.")

    session.run(
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{pathlib.Path().absolute()}:/workspace",
        "aquasec/trivy:latest",
        "sbom",
        f"/workspace/{sbom_file}",
        "--severity",
        "CRITICAL,HIGH",
        "--format",
        "table",
        external=True,
    )


@nox.session(python="3.12")
def compliance(session: nox.Session) -> None:
    """Run all compliance checks.

    This session runs REUSE compliance checks and generates SBOMs
    for comprehensive compliance validation.
    """
    session.log("Running REUSE compliance check...")
    reuse(session)

    session.log("Generating SBOMs...")
    sbom(session)

    session.log("Scanning runtime SBOM for vulnerabilities...")
    scan(session)

    session.log("All compliance checks completed successfully!")


# ============================================================================
# Multi-Version Testing Sessions
# ============================================================================


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run test suite across all supported Python versions.

    This session runs the full test suite with coverage reporting
    for each Python version specified in PYTHON_VERSIONS.

    Usage:
        nox -s tests              # Run on all Python versions
        nox -s tests-3.12         # Run only on Python 3.12
        nox -s tests -- -k test_schema  # Pass pytest args
    """
    session.install(".[dev]")
    args = session.posargs or ["-v", "--cov=src", "--cov-report=term-missing"]
    session.run("pytest", *args)


@nox.session(python=PYTHON_VERSIONS)
def tests_no_cov(session: nox.Session) -> None:
    """Run tests without coverage (faster for quick checks).

    Useful for rapid iteration during development.
    """
    session.install(".[dev]")
    args = session.posargs or ["-v", "-x"]  # -x stops at first failure
    session.run("pytest", *args)


@nox.session(python=PYTHON_VERSIONS)
def type_check(session: nox.Session) -> None:
    """Run type checking with mypy across Python versions.

    Different Python versions may have different typing behaviors,
    so testing across versions ensures broad compatibility.
    """
    session.install(".[dev]")
    session.run("mypy", "src")


@nox.session(python=PYTHON_VERSIONS)
def lint(session: nox.Session) -> None:
    """Run ruff linting across Python versions."""
    session.install(".[dev]")
    session.run("ruff", "check", "src", "tests")


@nox.session(python=PYTHON_VERSIONS, tags=["ml"])
def tests_ml(session: nox.Session) -> None:
    """Run tests with ML dependencies (torch, etc).

    Tagged as 'ml' so you can run: nox -t ml
    """
    session.install(".[dev,ml]")
    session.run("pytest", "-v", "-m", "not slow")


@nox.session(python="3.12")
@nox.parametrize("opencv", ["4.8.0", "4.9.0", "4.10.0"])
def tests_opencv_compat(session: nox.Session, opencv: str) -> None:
    """Test compatibility with different OpenCV versions.

    This creates separate sessions:
        - tests_opencv_compat(opencv='4.8.0')
        - tests_opencv_compat(opencv='4.9.0')
        - tests_opencv_compat(opencv='4.10.0')
    """
    session.install(f"opencv-python-headless=={opencv}")
    session.install(".[dev]")
    session.run("pytest", "-v", "-m", "integration")


@nox.session(python="3.12")
def quality(session: nox.Session) -> None:
    """Run all quality checks (lint, type check, tests).

    This is your pre-commit quality gate for the current dev version.
    """
    session.install(".[dev]")
    session.log("🔍 Running ruff format check...")
    session.run("ruff", "format", "--check", "src", "tests")

    session.log("🔍 Running ruff lint...")
    session.run("ruff", "check", "src", "tests")

    session.log("🔍 Running mypy...")
    session.run("mypy", "src")

    session.log("🧪 Running tests...")
    session.run("pytest", "-v", "--cov=src", "--cov-fail-under=80")

    session.log("✅ All quality checks passed!")


@nox.session(python=False)
def ci(session: nox.Session) -> None:
    """Run full CI validation suite across all Python versions.

    This is what your CI/CD should run. It coordinates multiple sessions.
    """
    session.log("🚀 Running full CI validation...")

    # Run tests on all Python versions
    for py_version in PYTHON_VERSIONS:
        if py_version_available(session, py_version):
            session.notify(f"tests-{py_version}")
            session.notify(f"type_check-{py_version}")
        else:
            session.warn(f"Python {py_version} not available, skipping")

    # Run quality checks on default version
    session.notify("quality")


def py_version_available(session: nox.Session, version: str) -> bool:
    """Check if a Python version is available on the system."""
    try:
        session.run("python" + version, "--version", silent=True, external=True)
    except Exception:
        return False
    else:
        return True
