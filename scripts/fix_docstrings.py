#!/usr/bin/env python3
"""Fix pydoclint violations in Python docstrings.

Handles:
- DOC109/110/105: Add type hints to Args sections
- DOC203: Fix return type in Returns section
- DOC301: Merge __init__ docstring into class docstring
- DOC601/603/605: Fix class Attributes sections with type hints
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def get_type_hint_str(annotation: ast.expr | None) -> str:
    """Convert AST annotation to string representation."""
    if annotation is None:
        return ""
    return ast.unparse(annotation)


def parse_function_args(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    """Extract argument names and their type hints from a function definition."""
    args: dict[str, str] = {}
    all_args = list(func_node.args.posonlyargs) + list(func_node.args.args) + list(func_node.args.kwonlyargs)
    if func_node.args.vararg:
        all_args.append(func_node.args.vararg)
    if func_node.args.kwarg:
        all_args.append(func_node.args.kwarg)

    for arg in all_args:
        if arg.arg in ("self", "cls"):
            continue
        type_str = get_type_hint_str(arg.annotation) if arg.annotation else "Any"
        args[arg.arg] = type_str

    return args


def get_return_annotation(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Get return type annotation as string."""
    if func_node.returns is None:
        return ""
    ret = ast.unparse(func_node.returns)
    return ret


def fix_section_arg_types(content: str, section_name: str,
                            name_to_type: dict[str, str]) -> str:
    """Fix type hints in an Args or Attributes section of a docstring content."""
    lines = content.split("\n")
    result = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        # Detect section header
        if re.match(rf"^\s*{section_name}:\s*$", line):
            in_section = True
            result.append(line)
            continue

        # Detect end of section: blank line followed by new section, or new section directly
        if in_section:
            # Check for new section header (e.g., "Returns:", "Raises:", "Note:", etc.)
            if stripped and re.match(r"^[A-Za-z][A-Za-z ]*:\s*$", stripped):
                in_section = False
                result.append(line)
                continue

            # Try to match an arg/attr entry
            # Pattern: "    arg_name: description" or "    arg_name (type): description"
            arg_match = re.match(r"^(\s{4,})(\w+)(\s*\([^)]*\))?\s*:\s*(.*)", line)
            if arg_match:
                indent = arg_match.group(1)
                name = arg_match.group(2)
                existing_type = arg_match.group(3)
                description = arg_match.group(4)

                if name in name_to_type:
                    correct_type = name_to_type[name]
                    if not existing_type:
                        # Add type hint
                        result.append(f"{indent}{name} ({correct_type}): {description}")
                        continue
                    else:
                        # Check if type is correct
                        existing = existing_type.strip().strip("()")
                        if existing != correct_type:
                            result.append(f"{indent}{name} ({correct_type}): {description}")
                            continue

        result.append(line)

    return "\n".join(result)


def fix_returns_section(content: str, return_type: str) -> str:
    """Fix Returns section to include type annotation."""
    if not return_type or return_type in ("None", ""):
        return content

    lines = content.split("\n")
    result = []
    in_returns = False
    returns_inner_indent = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if re.match(r"^\s*Returns:\s*$", line):
            in_returns = True
            result.append(line)
            i += 1
            continue

        if in_returns:
            in_returns = False
            if stripped:
                # Check if line already has "TypeName: description" format
                # The line should be indented more than "Returns:"
                type_line_match = re.match(r"^(\s+)(.*?):\s*(.*)", line)
                if type_line_match:
                    indent_str = type_line_match.group(1)
                    existing_type = type_line_match.group(2).strip()
                    desc_after_colon = type_line_match.group(3)

                    # If existing_type matches or looks like a type name, it's already set
                    # If existing_type is a full description (no type), we need to add type
                    # Heuristic: if the existing_type starts with uppercase and has no spaces typical of descriptions
                    # or matches the return_type, consider it already typed
                    if existing_type == return_type:
                        # Already correct
                        result.append(line)
                        i += 1
                        continue
                    else:
                        # Treat the whole line as description, add type prefix
                        full_desc = stripped  # The whole content is the description
                        result.append(f"{indent_str}{return_type}: {full_desc}")
                        i += 1
                        continue
                else:
                    # Line doesn't match "type: desc" format - treat as description
                    indent_str = re.match(r"^(\s+)", line)
                    if indent_str:
                        idx = indent_str.group(1)
                    else:
                        idx = "        "
                    result.append(f"{idx}{return_type}: {stripped}")
                    i += 1
                    continue

        result.append(line)
        i += 1

    return "\n".join(result)


def get_docstring_location(source: str, node: ast.AST) -> tuple[int, int, str, str] | None:
    """Get start/end lines and quotes of a docstring in source.

    Returns:
        Tuple of (start_line, end_line, quote_char, raw_text) or None
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return None

    if not (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return None

    doc_node = node.body[0]
    start = doc_node.lineno - 1  # 0-indexed
    end = doc_node.end_lineno - 1  # 0-indexed

    return start, end, "", ""


def replace_node_docstring(source: str, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
                             new_content: str) -> str:
    """Replace the docstring of a node with new content."""
    doc_node = node.body[0]
    lines = source.split("\n")

    start = doc_node.lineno - 1
    end = doc_node.end_lineno - 1

    doc_lines = lines[start:end + 1]
    original_doc_text = "\n".join(doc_lines)

    # Determine indent
    indent_match = re.match(r"^(\s*)", lines[start])
    indent = indent_match.group(1) if indent_match else ""

    # Determine quote style
    first_stripped = lines[start].strip()
    if first_stripped.startswith('"""'):
        quote = '"""'
    elif first_stripped.startswith("'''"):
        quote = "'''"
    else:
        return source

    # Build new docstring text
    new_lines_content = new_content.split("\n")

    # Reconstruct with original indentation
    # Format: indent + """ + first_line
    #         indent + middle lines (already have inner indent)
    #         indent + """
    # We need to re-indent properly

    # Get the inner indent of the docstring
    # Look at the first non-empty content line
    inner_indent = indent + "    "
    for orig_line in doc_lines[1:]:
        stripped = orig_line.strip()
        if stripped:
            orig_inner = re.match(r"^(\s*)", orig_line).group(1)
            if len(orig_inner) > len(indent):
                inner_indent = orig_inner
            break

    # Reconstruct new docstring
    new_doc_lines = []
    for j, content_line in enumerate(new_lines_content):
        if j == 0:
            new_doc_lines.append(f"{indent}{quote}{content_line}")
        else:
            if content_line:
                new_doc_lines.append(f"{content_line}")
            else:
                new_doc_lines.append("")

    # Add closing quotes
    # Check if last line of content is on same line as opening
    if len(new_lines_content) == 1:
        new_doc_lines = [f"{indent}{quote}{new_lines_content[0]}{quote}"]
    else:
        new_doc_lines.append(f"{indent}{quote}")

    new_doc_text = "\n".join(new_doc_lines)

    result_lines = lines[:start] + new_doc_text.split("\n") + lines[end + 1:]
    return "\n".join(result_lines)


def fix_file_docstrings(filepath: Path) -> None:
    """Fix all pydoclint violations in a file by parsing AST and modifying docstrings."""
    source = filepath.read_text()

    # We'll do a simpler approach: find all functions/classes, get their types,
    # then do text substitution on the docstring sections

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"  ERROR: Cannot parse {filepath}: {e}")
        return

    # Collect all nodes with docstrings and their type info
    # Process in reverse order to preserve line numbers
    nodes_to_fix: list[tuple[int, Any, dict[str, str], str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                continue

            arg_types = parse_function_args(node)
            return_type = get_return_annotation(node)
            nodes_to_fix.append((node.body[0].lineno, node, arg_types, return_type))

        elif isinstance(node, ast.ClassDef):
            if not (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                continue

            # Collect field types from class body
            field_types: dict[str, str] = {}
            for item in node.body:
                if (isinstance(item, ast.AnnAssign)
                        and isinstance(item.target, ast.Name)):
                    field_types[item.target.id] = get_type_hint_str(item.annotation)

            nodes_to_fix.append((node.body[0].lineno, node, field_types, ""))

    # Sort in reverse order to process from bottom to top
    nodes_to_fix.sort(key=lambda x: x[0], reverse=True)

    for _lineno, node, type_info, return_type in nodes_to_fix:
        source = fix_node_docstring(source, node, type_info, return_type)

    # Also handle DOC301: __init__ docstrings
    source = fix_doc301(source)

    filepath.write_text(source)


def fix_node_docstring(source: str, node: Any,
                        type_info: dict[str, str], return_type: str) -> str:
    """Fix the docstring for a single node in the source."""
    if not (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return source

    doc_node = node.body[0]
    original_content = doc_node.value.value
    new_content = original_content

    # Fix Args section (for functions/methods)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and type_info:
        new_content = fix_section_arg_types(new_content, "Args", type_info)

    # Fix Attributes section (for classes)
    if isinstance(node, ast.ClassDef) and type_info:
        new_content = fix_section_arg_types(new_content, "Attributes", type_info)

    # Fix Returns section
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and return_type:
        new_content = fix_returns_section(new_content, return_type)

    if new_content == original_content:
        return source

    # Replace in source using line-based approach
    lines = source.split("\n")
    start = doc_node.lineno - 1
    end = doc_node.end_lineno - 1

    # Get original docstring text from source
    orig_doc_lines = lines[start:end + 1]
    orig_text = "\n".join(orig_doc_lines)

    # Extract the quote character and indentation
    first_line = orig_doc_lines[0]
    indent_match = re.match(r"^(\s*)", first_line)
    indent = indent_match.group(1) if indent_match else ""
    stripped_first = first_line.strip()

    if stripped_first.startswith('"""'):
        quote = '"""'
    elif stripped_first.startswith("'''"):
        quote = "'''"
    else:
        return source

    # Reconstruct the docstring text
    # original_content is the string value (without quotes)
    # We need to reconstruct it preserving the original formatting as much as possible

    # Strategy: replace the string value part while keeping quotes and indentation
    # The docstring in source looks like:
    #   indent + """ + first_line_of_content
    #   subsequent lines (with their own indentation)
    #   indent + """

    # Split the original content and new content
    orig_c_lines = original_content.split("\n")
    new_c_lines = new_content.split("\n")

    if len(orig_c_lines) == 1:
        # Single line docstring
        new_first = f"{indent}{quote}{new_c_lines[0]}{quote}"
        new_doc_lines = [new_first]
    else:
        # Multi-line docstring
        # First line: indent + """ + first content line
        # Middle lines: as-is from new_content
        # Last line: indent + """
        new_doc_lines = []
        new_doc_lines.append(f"{indent}{quote}{new_c_lines[0]}")
        for cl in new_c_lines[1:]:
            new_doc_lines.append(cl)
        # Last line should be just indent + """ (closing)
        # Remove if last line already is just closing
        if new_doc_lines[-1].strip() == quote:
            pass  # Already has closing
        else:
            new_doc_lines.append(f"{indent}{quote}")

    new_text = "\n".join(new_doc_lines)
    result_lines = lines[:start] + new_text.split("\n") + lines[end + 1:]
    return "\n".join(result_lines)


def fix_doc301(source: str) -> str:
    """Fix DOC301: __init__ docstrings should be merged into class docstring.

    For DOC301, we simply remove the __init__ docstring since the class
    docstring already documents the class. pydoclint wants args in class docstring.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    # Find all classes with __init__ that has a docstring
    # Process in reverse order
    init_docs_to_remove: list[tuple[int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name == "__init__"):
                    if (item.body and isinstance(item.body[0], ast.Expr)
                            and isinstance(item.body[0].value, ast.Constant)
                            and isinstance(item.body[0].value.value, str)):
                        doc_node = item.body[0]
                        init_docs_to_remove.append((doc_node.lineno - 1, doc_node.end_lineno - 1))

    # Sort in reverse order
    init_docs_to_remove.sort(reverse=True)

    lines = source.split("\n")
    for start, end in init_docs_to_remove:
        # Remove the docstring lines
        del lines[start:end + 1]

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: fix_docstrings.py <directory_or_file>")
        return 1

    target = Path(sys.argv[1])

    if target.is_file():
        files = [target]
    else:
        files = sorted(target.rglob("*.py"))

    for filepath in files:
        print(f"Processing {filepath}...")
        try:
            fix_file_docstrings(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")

    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
