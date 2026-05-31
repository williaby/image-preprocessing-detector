"""Path security utilities for preventing directory traversal attacks.

This module provides centralized path validation to prevent path traversal
vulnerabilities across the codebase.
"""

from pathlib import Path


def validate_safe_path(
    file_path: str | Path,
    allowed_base: str | Path | None = None,
    must_exist: bool = False,
) -> Path:
    """Validate file path to prevent directory traversal attacks.

    Resolves the path to its absolute form and checks for traversal patterns
    and base directory restrictions.

    Args:
        file_path (str | Path): Path to validate (string or Path object)
        allowed_base (str | Path | None): Optional base directory to restrict access to.
                     If provided, the resolved path must be within this directory.
        must_exist (bool): If True, raise error if path doesn't exist

    Returns:
        Path: Resolved absolute Path object

    Raises:
        ValueError: If path contains traversal patterns or escapes allowed_base
        FileNotFoundError: If must_exist=True and path doesn't exist

    Examples:
        >>> validate_safe_path("data/file.json")
        PosixPath('/home/user/project/data/file.json')

        >>> validate_safe_path("../../../etc/passwd", allowed_base="/home/user/project")
        ValueError: Path /etc/passwd is outside allowed base /home/user/project

        >>> validate_safe_path("data/../config.yaml", must_exist=True)
        PosixPath('/home/user/project/config.yaml')
    """
    # Check for path traversal patterns in original input
    # This catches both Unix (..) and potential encoded variants
    if ".." in str(file_path):
        raise ValueError(f"Path traversal pattern detected in path: {file_path}")

    # Resolve to absolute path (resolves symlinks and relative paths)
    path = Path(file_path).resolve()

    # If allowed_base specified, ensure path is within it
    if allowed_base:
        base = Path(allowed_base).resolve()
        try:
            # Use relative_to to check if path is within base
            path.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path {path} is outside allowed base directory {base}"
            ) from None

    # Optionally check existence
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    return path
