"""Formula and math expression parsers for the annotation system.

This package contains parsers for mathematical formula datasets including:
- Im2latexParser: LaTeX formula images with source code (103K formulas)

Datasets covered:
    - im2latex / im2latex-100k: Rendered LaTeX formulas from ArXiv papers

Example:
    >>> from image_preprocessing_detector.annotation.parsers.formula import (
    ...     register_formula_parsers,
    ... )
    >>> from image_preprocessing_detector.annotation.parsers.registry import (
    ...     ParserRegistry,
    ... )
    >>>
    >>> registry = ParserRegistry()
    >>> register_formula_parsers(registry)
    >>> parser = registry.get_parser("im2latex")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import ParserRegistry

from .im2latex import Im2latexParser


def register_formula_parsers(registry: ParserRegistry) -> None:
    """Register all formula parsers with the registry.

    Args:
        registry (ParserRegistry): ParserRegistry instance to register parsers with.
    """
    registry.register(Im2latexParser())


__all__ = [
    "Im2latexParser",
    "register_formula_parsers",
]
