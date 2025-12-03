"""
Shared path validation utilities to prevent path traversal attacks.

This module provides secure path handling for CLI scripts that accept
file paths as arguments. Use these utilities instead of directly opening
files from user input.

Usage:
    from _path_security import validate_path, validate_input_path, validate_output_path

    # For input files that must exist
    safe_path = validate_input_path(args.input_file)
    with open(safe_path) as f:
        data = f.read()

    # For output files (parent must exist)
    safe_path = validate_output_path(args.output_file)
    with open(safe_path, "w") as f:
        f.write(data)
"""

from pathlib import Path


class PathValidationError(ValueError):
    """Raised when path validation fails."""


def validate_path(path: Path, *, must_exist: bool = True) -> Path:
    """
    Validate and resolve a path to prevent path traversal attacks.

    Args:
        path: The path to validate
        must_exist: Whether the path must already exist (default: True)

    Returns:
        Resolved absolute path

    Raises:
        PathValidationError: If path validation fails
    """
    try:
        resolved = path.resolve(strict=must_exist)
    except (OSError, RuntimeError, ValueError) as e:
        # pathlib may raise ValueError for certain inputs (e.g. null bytes)
        # Convert low-level exceptions to the public PathValidationError
        msg = f"Invalid path: {path}"
        raise PathValidationError(msg) from e

    # Ensure path doesn't contain suspicious patterns
    path_str = str(resolved)
    if "\x00" in path_str:
        msg = f"Path contains null bytes: {path}"
        raise PathValidationError(msg)

    return resolved


def validate_input_path(path: Path) -> Path:
    """
    Validate an input file path (must exist).

    Args:
        path: The input file path to validate

    Returns:
        Resolved absolute path

    Raises:
        PathValidationError: If path validation fails or file doesn't exist
    """
    return validate_path(path, must_exist=True)


def validate_output_path(path: Path) -> Path:
    """
    Validate an output file path (parent directory must exist).

    Args:
        path: The output file path to validate

    Returns:
        Resolved absolute path with validated parent

    Raises:
        PathValidationError: If parent directory validation fails
    """
    # Validate parent directory exists
    parent = validate_path(path.parent, must_exist=True)
    return parent / path.name


def validate_directory(path: Path, *, must_exist: bool = True) -> Path:
    """
    Validate a directory path.

    Args:
        path: The directory path to validate
        must_exist: Whether the directory must already exist (default: True)

    Returns:
        Resolved absolute path

    Raises:
        PathValidationError: If validation fails or path is not a directory
    """
    resolved = validate_path(path, must_exist=must_exist)
    if must_exist and not resolved.is_dir():
        msg = f"Path is not a directory: {resolved}"
        raise PathValidationError(msg)
    return resolved
