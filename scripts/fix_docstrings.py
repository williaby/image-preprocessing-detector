#!/usr/bin/env python3
"""Automated Google-style docstring fixer for pydoclint compliance.

Fixes DOC109/DOC110/DOC105 (missing arg type hints) and DOC203 (missing
return type) by extracting types from function signatures.  Writes back
to the original file in-place and is idempotent.

Usage:
    python scripts/fix_docstrings.py src/image_preprocessing_detector/detection/iqa_classical.py
    python scripts/fix_docstrings.py src/image_preprocessing_detector/detection/
"""

from __future__ import annotations

import ast
import re
import sys
import textwrap
from pathlib import Path


def _get_annotation_str(node: ast.expr | None) -> str | None:
    """Return a source-level string for a type annotation node."""
    if node is None:
        return None
    return ast.unparse(node)


def _parse_google_args_section(args_text: str) -> list[tuple[str, str | None, str]]:
    """Parse a Google-style Args block into (name, type, description) triples."""
    results: list[tuple[str, str | None, str]] = []
    # Each arg entry starts at column 0 within the section body; continuation
    # lines are indented further.
    pattern = re.compile(
        r"^(?P<name>\w+)"
        r"(?:\s*\((?P<type>[^)]*)\))?"
        r"\s*:\s*(?P<desc>.*)$",
    )
    lines = args_text.splitlines()
    i = 0
    while i < len(lines):
        m = pattern.match(lines[i].rstrip())
        if m:
            name = m.group("name")
            typ = m.group("type") or None
            desc = m.group("desc")
            # Gather continuation lines (indented more than the arg line)
            base_indent = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines):
                stripped = lines[j]
                if stripped == "":
                    break
                cur_indent = len(stripped) - len(stripped.lstrip())
                if cur_indent <= base_indent:
                    break
                desc += " " + stripped.strip()
                j += 1
            results.append((name, typ, desc))
            i = j
        else:
            i += 1
    return results


def _rebuild_args_section(
    entries: list[tuple[str, str | None, str]],
    indent: str,
) -> str:
    """Rebuild an Args section body from (name, type, description) triples."""
    lines: list[str] = []
    for name, typ, desc in entries:
        if typ:
            first = f"{indent}{name} ({typ}): {desc}"
        else:
            first = f"{indent}{name}: {desc}"
        lines.append(first)
    return "\n".join(lines)


def _parse_google_returns_section(returns_text: str) -> tuple[str | None, str]:
    """Parse a Google Returns section body into (type, description)."""
    stripped = returns_text.strip()
    # Pattern: "Type: description" or just "description"
    m = re.match(r"^(?P<type>[A-Za-z_][A-Za-z0-9_\[\], |.]*?):\s*(?P<desc>.+)$", stripped, re.DOTALL)
    if m:
        return m.group("type").strip(), m.group("desc").strip()
    return None, stripped


def _inject_types_into_docstring(
    docstring: str,
    sig_args: dict[str, str | None],
    return_type: str | None,
    indent: str,
) -> str:
    """Return a modified docstring with type hints added where missing."""
    # We work with normalised indentation — detect the docstring's base indent
    # from the first non-empty content line.
    lines = docstring.split("\n")

    # Identify section headers (Google style: "Section:\n")
    section_re = re.compile(r"^(\s*)(Args|Returns|Raises|Yields|Attributes)\s*:\s*$")

    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = section_re.match(line)
        if m:
            section_indent = m.group(1)
            section_name = m.group(2)
            result.append(line)
            i += 1

            # Collect the body of this section (lines indented deeper than the header)
            body_lines: list[str] = []
            while i < len(lines):
                if lines[i] == "" or (lines[i].strip() and not lines[i].startswith(section_indent + " ")):
                    break
                body_lines.append(lines[i])
                i += 1

            body_text = "\n".join(body_lines)

            if section_name == "Args" and sig_args:
                entries = _parse_google_args_section(
                    textwrap.dedent(body_text).strip()
                )
                # Determine the entry indent (one extra level beyond section header)
                entry_indent = section_indent + "    "
                updated: list[tuple[str, str | None, str]] = []
                for name, typ, desc in entries:
                    if name in sig_args and not typ:
                        new_typ = sig_args[name]
                        updated.append((name, new_typ, desc))
                    else:
                        updated.append((name, typ, desc))
                new_body = _rebuild_args_section(updated, entry_indent)
                result.append(new_body)

            elif section_name == "Returns" and return_type:
                existing_type, desc = _parse_google_returns_section(body_text)
                entry_indent = section_indent + "    "
                if not existing_type:
                    result.append(f"{entry_indent}{return_type}: {desc.strip()}")
                else:
                    result.append(body_text)

            else:
                result.append(body_text)

        else:
            result.append(line)
            i += 1

    return "\n".join(result)


class DocstringFixer(ast.NodeVisitor):
    """AST visitor that collects fixable function/method nodes."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.fixes: list[tuple[int, int, str]] = []  # (start_line, end_line, new_text)

    def _get_func_sig(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str | None]:
        """Extract {param_name: type_str} from a function signature, skipping self/cls."""
        result: dict[str, str | None] = {}
        args = node.args
        all_args: list[ast.arg] = []
        all_args.extend(args.posonlyargs)
        all_args.extend(args.args)
        if args.vararg:
            all_args.append(args.vararg)
        all_args.extend(args.kwonlyargs)
        if args.kwarg:
            all_args.append(args.kwarg)

        for arg in all_args:
            if arg.arg in ("self", "cls"):
                continue
            ann = _get_annotation_str(arg.annotation)
            result[arg.arg] = ann
        return result

    def _process_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        docstring_node = ast.get_docstring(node, clean=False)
        if not docstring_node:
            return

        sig_args = self._get_func_sig(node)
        return_type = _get_annotation_str(node.returns)
        # Skip trivial returns
        if return_type in ("None", "NoReturn"):
            return_type = None

        first_stmt = node.body[0]
        if not isinstance(first_stmt, ast.Expr) or not isinstance(first_stmt.value, ast.Constant):
            return

        # Get original docstring text as it appears in source
        start = first_stmt.col_offset
        raw = ast.get_docstring(node, clean=False) or ""

        # Check if anything needs fixing
        needs_arg_fix = any(
            ann is not None for ann in sig_args.values()
        ) and "Args:" in raw
        needs_return_fix = return_type is not None and "Returns:" in raw

        if not needs_arg_fix and not needs_return_fix:
            return

        # Get the base indent of the docstring
        indent = " " * start

        new_docstring = _inject_types_into_docstring(
            raw, sig_args if needs_arg_fix else {}, return_type if needs_return_fix else None, indent
        )

        if new_docstring != raw:
            # Record (1-based line number of the expr node, new content)
            self.fixes.append((first_stmt.lineno, first_stmt.end_lineno, new_docstring, indent))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_func(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_func(node)
        self.generic_visit(node)


def fix_file(path: Path) -> bool:
    """Fix docstring violations in a single file.  Returns True if modified."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        print(f"  SKIP (syntax error): {path}: {e}", file=sys.stderr)
        return False

    visitor = DocstringFixer(source)
    visitor.visit(tree)

    if not visitor.fixes:
        return False

    lines = source.splitlines(keepends=True)

    # Apply fixes in reverse line order so line numbers stay valid
    # Each fix is (start_line 1-based, end_line 1-based, new_docstring, indent)
    fixes = sorted(visitor.fixes, key=lambda x: x[0], reverse=True)

    for start_line, end_line, new_docstring, indent in fixes:
        # Find the triple-quote delimiters in that range
        seg = "".join(lines[start_line - 1 : end_line])
        # Detect quote style
        for q in ('"""', "'''"):
            if q in seg:
                quote = q
                break
        else:
            continue  # Can't detect, skip

        # Rebuild the docstring literal
        inner = new_docstring
        # Preserve original quoting
        new_literal = f'{indent}{quote}{inner}{quote}\n'
        lines[start_line - 1 : end_line] = [new_literal]

    new_source = "".join(lines)
    if new_source != source:
        path.write_text(new_source, encoding="utf-8")
        return True
    return False


def main() -> None:
    """Entry point: accept file or directory arguments."""
    if len(sys.argv) < 2:
        print("Usage: fix_docstrings.py <file_or_dir> [...]")
        sys.exit(1)

    targets: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            targets.extend(sorted(p.rglob("*.py")))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"Warning: {arg} not found", file=sys.stderr)

    modified = 0
    for p in targets:
        if fix_file(p):
            print(f"  fixed: {p}")
            modified += 1

    print(f"\nModified {modified}/{len(targets)} files.")


if __name__ == "__main__":
    main()
