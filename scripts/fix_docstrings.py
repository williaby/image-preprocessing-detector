#!/usr/bin/env python3
"""Fix pydoclint violations in Python docstrings.

Fixes DOC105/DOC109/DOC110 (missing type hints in Args) and
DOC203 (return type not in docstring Returns section).
Uses AST to get actual type annotations and updates docstrings.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def get_annotation_str(node: ast.expr | None) -> str:
    """Convert AST annotation node to string representation."""
    if node is None:
        return ""
    return ast.unparse(node)


def extract_function_signatures(source: str) -> dict[int, dict]:
    """Extract function/method signatures from source code.

    Returns dict mapping line number to signature info.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    signatures: dict[int, dict] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args_info = {}

            # Process regular args (skip self/cls)
            for arg in node.args.args:
                if arg.arg not in ("self", "cls"):
                    ann = get_annotation_str(arg.annotation)
                    if ann:
                        args_info[arg.arg] = ann

            # Process keyword-only args
            for arg in node.args.kwonlyargs:
                ann = get_annotation_str(arg.annotation)
                if ann:
                    args_info[arg.arg] = ann

            # Process *args
            if node.args.vararg:
                ann = get_annotation_str(node.args.vararg.annotation)
                if ann:
                    args_info[node.args.vararg.arg] = ann

            # Process **kwargs
            if node.args.kwarg:
                ann = get_annotation_str(node.args.kwarg.annotation)
                if ann:
                    args_info[node.args.kwarg.arg] = ann

            # Return type
            return_ann = get_annotation_str(node.returns)

            signatures[node.lineno] = {
                "name": node.name,
                "args": args_info,
                "returns": return_ann,
                "end_lineno": node.end_lineno,
            }

    return signatures


def extract_class_attributes(source: str) -> dict[str, dict[str, str]]:
    """Extract class attribute type hints from source.

    Returns dict mapping class name to {attr_name: type_str}.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    classes: dict[str, dict[str, str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            attrs: dict[str, str] = {}
            # Look at class body for annotated assignments
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    ann = get_annotation_str(item.annotation)
                    if ann:
                        attrs[item.target.id] = ann
            classes[node.name] = attrs

    return classes


def parse_docstring_sections(docstring: str) -> dict[str, tuple[int, int]]:
    """Parse docstring into sections.

    Returns dict mapping section name to (start_line_idx, end_line_idx).
    The indices are into the lines list of the docstring.
    """
    lines = docstring.split("\n")

    # Known Google-style section headers
    section_headers = {
        "Args", "Arguments", "Parameters", "Returns", "Return",
        "Yields", "Raises", "Note", "Notes", "Example", "Examples",
        "Attributes", "Todo", "References", "See Also", "Warns", "Warning",
    }

    # Detect base indent of sections (first indented line after the opening)
    # Section headers are typically indented 4 or 8 spaces
    section_indent = None
    section_pattern = re.compile(r"^(\s+)(\w[\w\s]*):\s*$")

    for line in lines[1:]:  # skip the summary line
        m = section_pattern.match(line)
        if m and m.group(2).strip() in section_headers:
            section_indent = len(m.group(1))
            break

    if section_indent is None:
        return {}

    sections: dict[str, tuple[int, int]] = {}
    current_section = None
    current_start = None

    for i, line in enumerate(lines):
        m = section_pattern.match(line)
        if m and len(m.group(1)) == section_indent and m.group(2).strip() in section_headers:
            # End previous section
            if current_section is not None:
                sections[current_section] = (current_start, i)
            current_section = m.group(2).strip()
            current_start = i
        elif line.strip().startswith('"""') or line.strip().startswith("'''"):
            if current_section is not None:
                sections[current_section] = (current_start, i)
                current_section = None

    if current_section is not None:
        sections[current_section] = (current_start, len(lines))

    return sections


def fix_args_in_section_lines(
    lines: list[str],
    section_start: int,
    section_end: int,
    func_args: dict[str, str],
    arg_indent: int,
) -> tuple[list[str], int]:
    """Fix type hints in Args/Attributes section lines.

    Returns (modified_lines, num_fixes).
    """
    fixes = 0
    # Pattern: "    arg_name: description" (no type)
    # We want "    arg_name (type): description"
    arg_no_type = re.compile(r"^(\s{" + str(arg_indent) + r"})(\*{0,2}[\w]+):\s*(.*)$")
    arg_with_type = re.compile(r"^(\s{" + str(arg_indent) + r"})(\*{0,2}[\w]+)\s*\(.*?\):\s*(.*)$")

    result = list(lines)
    for i in range(section_start + 1, min(section_end, len(lines))):
        line = lines[i]
        # Check if this is an arg line at the expected indent
        m = arg_no_type.match(line)
        if m:
            indent_str = m.group(1)
            arg_name = m.group(2)
            description = m.group(3)
            lookup = arg_name.lstrip("*")
            if lookup in func_args:
                result[i] = f"{indent_str}{arg_name} ({func_args[lookup]}): {description}"
                fixes += 1
        # Already has type - skip (correct)

    return result, fixes


def get_arg_indent(lines: list[str], section_start: int, section_end: int) -> int:
    """Detect indent of arg entries within an Args section."""
    # Section header is at section_start, args follow
    section_line = lines[section_start]
    section_m = re.match(r"^(\s+)", section_line)
    section_indent = len(section_m.group(1)) if section_m else 0

    # Args are indented more than the section header
    for i in range(section_start + 1, min(section_end, len(lines))):
        line = lines[i]
        if not line.strip():
            continue
        m = re.match(r"^(\s+)\S", line)
        if m:
            arg_indent = len(m.group(1))
            if arg_indent > section_indent:
                return arg_indent

    return section_indent + 4  # default


def fix_returns_section_lines(
    lines: list[str],
    section_start: int,
    section_end: int,
    return_type: str,
) -> tuple[list[str], int]:
    """Fix Returns section to include type hint.

    Returns (modified_lines, num_fixes).
    """
    if not return_type or return_type in ("None", ""):
        return lines, 0

    result = list(lines)
    fixes = 0

    # Find the first content line in the Returns section
    section_line = lines[section_start]
    section_m = re.match(r"^(\s+)", section_line)
    section_indent = len(section_m.group(1)) if section_m else 0
    content_indent = section_indent + 4

    for i in range(section_start + 1, min(section_end, len(lines))):
        line = lines[i]
        if not line.strip():
            continue

        # This is the first content line
        stripped = line.strip()

        # Check if it already has the right format "Type: description"
        # A valid type format: starts with a type name (no spaces except for generics)
        type_desc_pattern = re.compile(r"^(\s+)([\w\[\]|,\s\.\*]+):\s*(.*)$")
        m = type_desc_pattern.match(line)

        if m:
            existing_type = m.group(2).strip()
            # Is this a proper type annotation or a plain description?
            # Plain descriptions usually start with uppercase English words
            # Type annotations usually look like: str, int, float, dict[str, Any], etc.
            is_plain_desc = bool(re.match(
                r"^(The|A |An |If |This |Whether|True|False|List of|Dict|Returns|"
                r"[A-Z][a-z]+\s+[a-z])",
                existing_type
            ))

            if is_plain_desc:
                # Needs to be prefixed with the return type
                ind = " " * content_indent
                result[i] = f"{ind}{return_type}: {stripped}"
                fixes += 1
            # else: already has a type annotation - check if it matches
            # (we won't fix mismatches here - those are harder)
        else:
            # No colon pattern - just add the type
            ind = " " * content_indent
            result[i] = f"{ind}{return_type}: {stripped}"
            fixes += 1

        break  # Only fix the first content line

    return result, fixes


def fix_docstring_in_file(filepath: Path) -> int:
    """Fix pydoclint violations in a Python file.

    Returns the number of fixes made.
    """
    source = filepath.read_text(encoding="utf-8")
    signatures = extract_function_signatures(source)
    class_attrs = extract_class_attributes(source)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"  SKIP (SyntaxError): {filepath}")
        return 0

    lines = source.split("\n")
    total_fixes = 0

    # Process all functions/methods
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.body:
            continue
        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr) or not isinstance(
            first_stmt.value, ast.Constant
        ):
            continue
        if not isinstance(first_stmt.value.value, str):
            continue

        # Found a docstring
        doc_start = first_stmt.lineno - 1  # 0-indexed
        doc_end = first_stmt.end_lineno - 1  # 0-indexed (inclusive)
        doc_text = "\n".join(lines[doc_start : doc_end + 1])

        sig = signatures.get(node.lineno)
        if not sig:
            continue

        func_args = sig["args"]
        return_type = sig["returns"]

        # Parse sections
        doc_lines = lines[doc_start : doc_end + 1]
        sections = parse_docstring_sections(doc_text)

        # Fix Args section
        for section_name in ("Args", "Arguments", "Parameters"):
            if section_name in sections:
                s_start, s_end = sections[section_name]
                # Adjust to absolute line indices
                abs_start = doc_start + s_start
                abs_end = doc_start + s_end

                if func_args:
                    arg_indent = get_arg_indent(lines, abs_start, abs_end)
                    new_lines, fixes = fix_args_in_section_lines(
                        lines, abs_start, abs_end, func_args, arg_indent
                    )
                    if fixes > 0:
                        lines = new_lines
                        total_fixes += fixes
                break

        # Fix Returns section
        if return_type and return_type not in ("None", ""):
            for section_name in ("Returns", "Return"):
                if section_name in sections:
                    s_start, s_end = sections[section_name]
                    abs_start = doc_start + s_start
                    abs_end = doc_start + s_end

                    # Re-read sections since lines may have changed
                    doc_text2 = "\n".join(lines[doc_start : doc_end + 1])
                    sections2 = parse_docstring_sections(doc_text2)
                    if section_name in sections2:
                        s_start2, s_end2 = sections2[section_name]
                        abs_start = doc_start + s_start2
                        abs_end = doc_start + s_end2

                    new_lines, fixes = fix_returns_section_lines(
                        lines, abs_start, abs_end, return_type
                    )
                    if fixes > 0:
                        lines = new_lines
                        total_fixes += fixes
                    break

    # Process all classes (fix Attributes section)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.body:
            continue
        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr) or not isinstance(
            first_stmt.value, ast.Constant
        ):
            continue
        if not isinstance(first_stmt.value.value, str):
            continue

        doc_start = first_stmt.lineno - 1
        doc_end = first_stmt.end_lineno - 1

        class_name = node.name
        attrs = class_attrs.get(class_name, {})
        if not attrs:
            continue

        doc_text = "\n".join(lines[doc_start : doc_end + 1])
        sections = parse_docstring_sections(doc_text)

        if "Attributes" in sections:
            s_start, s_end = sections["Attributes"]
            abs_start = doc_start + s_start
            abs_end = doc_start + s_end

            arg_indent = get_arg_indent(lines, abs_start, abs_end)
            new_lines, fixes = fix_args_in_section_lines(
                lines, abs_start, abs_end, attrs, arg_indent
            )
            if fixes > 0:
                lines = new_lines
                total_fixes += fixes

    new_source = "\n".join(lines)
    if new_source != source:
        filepath.write_text(new_source, encoding="utf-8")

    return total_fixes


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: fix_docstrings.py <path> [<path> ...]")
        sys.exit(1)

    total_fixes = 0
    total_files = 0

    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            files = list(p.rglob("*.py"))
        elif p.is_file():
            files = [p]
        else:
            print(f"Warning: {arg} is not a file or directory")
            continue

        for filepath in sorted(files):
            fixes = fix_docstring_in_file(filepath)
            if fixes > 0:
                print(f"  Fixed {fixes} issues in {filepath}")
                total_fixes += fixes
            total_files += 1

    print(f"\nTotal: {total_fixes} fixes across {total_files} files")


if __name__ == "__main__":
    main()
