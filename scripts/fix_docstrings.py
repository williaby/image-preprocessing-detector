#!/usr/bin/env python3
"""Fix pydoclint violations in Google-style docstrings.

Handles:
  DOC105/109/110: Args entries missing type hints -> add (TypeHint)
  DOC203: Returns section missing type prefix -> add ReturnType: prefix
  DOC301: __init__ has its own docstring -> remove it
  DOC001/101/201: malformed/missing sections (bad Raises -> remove it)
  DOC502: Raises section with no raise statements -> remove Raises section

Usage:
    python scripts/fix_docstrings.py src/path/to/module/
    python scripts/fix_docstrings.py src/path/to/file.py
"""
from __future__ import annotations

import ast
import re
import sys
import textwrap
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _annotation_str(node: ast.expr) -> str:
    return ast.unparse(node)


def _collect_funcs(source: str) -> dict[int, dict]:
    """Return a map of function-def lineno -> info."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    result: dict[int, dict] = {}

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.cls_stack: list[ast.ClassDef] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.cls_stack.append(node)
            self.generic_visit(node)
            self.cls_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._proc(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._proc(node)
            self.generic_visit(node)

        def _proc(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            args: list[str] = []
            anns: dict[str, str] = {}
            for a in node.args.args:
                if a.arg in ("self", "cls"):
                    continue
                args.append(a.arg)
                if a.annotation:
                    anns[a.arg] = _annotation_str(a.annotation)
            for a in node.args.kwonlyargs:
                args.append(a.arg)
                if a.annotation:
                    anns[a.arg] = _annotation_str(a.annotation)

            ret: str | None = None
            if node.returns:
                ret = _annotation_str(node.returns)

            has_raise = any(
                isinstance(n, ast.Raise) and n.exc is not None
                for n in ast.walk(node)
            )

            # Find docstring node extent
            ds_start = ds_end = None
            if (node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                ds_node = node.body[0]
                ds_start = ds_node.lineno
                ds_end = ds_node.end_lineno or ds_node.lineno

            # Does enclosing class have a docstring?
            cls_has_ds = False
            if self.cls_stack:
                cls = self.cls_stack[-1]
                if (cls.body
                        and isinstance(cls.body[0], ast.Expr)
                        and isinstance(cls.body[0].value, ast.Constant)
                        and isinstance(cls.body[0].value.value, str)):
                    cls_has_ds = True

            result[node.lineno] = {
                "name": node.name,
                "args": args,
                "anns": anns,
                "ret": ret,
                "has_raise": has_raise,
                "ds_start": ds_start,
                "ds_end": ds_end,
                "is_init": node.name == "__init__",
                "cls_has_ds": cls_has_ds,
            }

    Visitor().visit(tree)
    return result


# ---------------------------------------------------------------------------
# Docstring content manipulation
# ---------------------------------------------------------------------------

_SECTION_HEADERS = re.compile(
    r'^(\s*)(Args|Returns?|Raises?|Notes?|Examples?|Yields?|Attributes?'
    r'|See Also|References?|Warning|Warnings?)\s*:\s*$',
    re.IGNORECASE,
)

_ARGS_HDR = re.compile(r'^\s*(Args|Arguments?|Parameters?)\s*:\s*$', re.IGNORECASE)
_RETURNS_HDR = re.compile(r'^\s*(Returns?|Yields?)\s*:\s*$', re.IGNORECASE)
_RAISES_HDR = re.compile(r'^\s*(Raises?)\s*:\s*$', re.IGNORECASE)

# Arg entry: "    arg_name: description" (no type)
_ARG_NO_TYPE = re.compile(r'^(\s+)(\*{0,2}[a-zA-Z_]\w*)\s*:\s+(.+)$')
# Arg entry: "    arg_name (type): description"
_ARG_WITH_TYPE = re.compile(r'^(\s+)(\*{0,2}[a-zA-Z_]\w*)\s+\(([^)]+)\)\s*:\s+(.+)$')


def _is_section_hdr(line: str) -> bool:
    return bool(_SECTION_HEADERS.match(line.rstrip()))


def _section_body_range(ds_content_lines: list[str], hdr_idx: int) -> list[int]:
    """Return indices of lines belonging to the section body (after header)."""
    indices = []
    for i in range(hdr_idx + 1, len(ds_content_lines)):
        if _is_section_hdr(ds_content_lines[i]):
            break
        indices.append(i)
    return indices


def _fix_docstring_content(
    raw: str,
    args: list[str],
    anns: dict[str, str],
    ret: str | None,
    has_raise: bool,
    indent: str,  # the indent of the function/method definition
) -> str:
    """Fix a docstring's content string and return the new content string."""
    # We operate on lines of the content (NOT the surrounding quotes)
    lines = raw.splitlines(keepends=True)
    # Ensure last line ends with newline for consistent processing
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    changed = False

    # ---- Step 1: Fix/remove malformed Raises sections ----
    # Find Raises header
    raises_hdr_idx = next((i for i, l in enumerate(lines) if _RAISES_HDR.match(l.rstrip())), None)
    if raises_hdr_idx is not None:
        body_idxs = _section_body_range(lines, raises_hdr_idx)
        body_text = "".join(lines[i] for i in body_idxs)

        # Remove if: "No exceptions raised" pattern OR no raise statements
        if re.search(r'No exceptions raised', body_text, re.IGNORECASE) or not has_raise:
            to_remove = set([raises_hdr_idx] + body_idxs)
            lines = [l for i, l in enumerate(lines) if i not in to_remove]
            changed = True

    # ---- Step 2: Fix args type hints (DOC105/109/110) and remove extra args (DOC102/103) ----
    args_hdr_idx = next((i for i, l in enumerate(lines) if _ARGS_HDR.match(l.rstrip())), None)
    if args_hdr_idx is not None:
        body_idxs = _section_body_range(lines, args_hdr_idx)
        # Build set of args in function signature for DOC102/103 check
        args_set = set(args)

        to_remove_idxs: set[int] = set()
        # Track continuation lines belonging to an arg
        current_extra_arg = False  # True if we're in an "extra" arg's continuation
        current_arg_start_indent: str = ''

        for bi in body_idxs:
            line = lines[bi]
            m_with = _ARG_WITH_TYPE.match(line.rstrip())
            m_no = _ARG_NO_TYPE.match(line.rstrip())

            if m_with or m_no:
                # New arg entry
                current_extra_arg = False
                if m_with:
                    arg_name = m_with.group(2).lstrip('*')
                    existing_type = m_with.group(3).strip()
                    desc = m_with.group(4)
                    correct_type = anns.get(arg_name)
                    ws = m_with.group(1)
                    # Check if this arg is in the function signature
                    if arg_name not in args_set:
                        # DOC102/103: remove this spurious arg entry
                        to_remove_idxs.add(bi)
                        current_extra_arg = True
                        current_arg_start_indent = ws
                    elif correct_type and existing_type != correct_type:
                        lines[bi] = f"{ws}{arg_name} ({correct_type}): {desc}\n"
                        changed = True
                elif m_no:
                    arg_name = m_no.group(2).lstrip('*')
                    desc = m_no.group(3)
                    ws = m_no.group(1)
                    # Check if this arg is in the function signature
                    if arg_name not in args_set:
                        # DOC102/103: remove this spurious arg entry
                        to_remove_idxs.add(bi)
                        current_extra_arg = True
                        current_arg_start_indent = ws
                    else:
                        current_extra_arg = False
                        type_hint = anns.get(arg_name)
                        if type_hint:
                            lines[bi] = f"{ws}{arg_name} ({type_hint}): {desc}\n"
                            changed = True
            else:
                # Continuation line
                if current_extra_arg and line.strip():
                    # Check if this is a continuation of the extra arg (more indented)
                    line_ws = line[:len(line) - len(line.lstrip())]
                    if len(line_ws) > len(current_arg_start_indent):
                        to_remove_idxs.add(bi)
                    else:
                        current_extra_arg = False
                elif current_extra_arg and not line.strip():
                    # Blank line - stop tracking continuation
                    current_extra_arg = False

        if to_remove_idxs:
            lines = [l for i, l in enumerate(lines) if i not in to_remove_idxs]
            changed = True

    # ---- Step 3: Fix Returns type prefix (DOC203) ----
    if ret and ret != "None":
        returns_hdr_idx = next(
            (i for i, l in enumerate(lines) if _RETURNS_HDR.match(l.rstrip())), None
        )
        if returns_hdr_idx is not None:
            body_idxs = _section_body_range(lines, returns_hdr_idx)
            # Find first non-empty body line
            first_body_idx = next(
                (bi for bi in body_idxs if lines[bi].strip()), None
            )
            if first_body_idx is not None:
                first_line = lines[first_body_idx]
                ws = first_line[: len(first_line) - len(first_line.lstrip())]
                stripped = first_line.strip()

                # Check if the line already starts with correct type prefix
                # Pattern: "SomeType: description" or "SomeType (optional): description"
                m = re.match(r'^(.+?)\s*:\s+(.*)$', stripped, re.DOTALL)
                if m:
                    existing_prefix = m.group(1).strip()
                    if existing_prefix == ret:
                        pass  # Already correct
                    elif _looks_like_type(existing_prefix):
                        # Has a type but wrong one - replace
                        rest = m.group(2)
                        lines[first_body_idx] = f"{ws}{ret}: {rest}\n"
                        changed = True
                    else:
                        # Whole "type" is actually a description - prepend real type
                        lines[first_body_idx] = f"{ws}{ret}: {stripped}\n"
                        changed = True
                else:
                    # No colon at all - prepend type
                    if stripped:
                        lines[first_body_idx] = f"{ws}{ret}: {stripped}\n"
                        changed = True
        # else: DOC201 - missing Returns section entirely.
        # We add it at the end of the docstring content (before trailing blank/empty)
        # BUT only if this is not just a single-line property docstring.
        # We'll handle DOC201 by inserting a Returns block at the end.
        # This is tricky because we don't want to break single-line docstrings.
        # We defer this for explicit handling.

    if not changed:
        return raw

    result = "".join(lines)
    return result


def _looks_like_type(s: str) -> bool:
    """Return True if s looks like a Python type annotation string."""
    s = s.strip()
    if not s:
        return False
    # Remove content inside brackets to check for spaces
    bracket_depth = 0
    outer_chars = []
    for ch in s:
        if ch in ('[', '(', '{'):
            bracket_depth += 1
        elif ch in (']', ')', '}'):
            bracket_depth -= 1
        elif bracket_depth == 0:
            outer_chars.append(ch)
    outer = ''.join(outer_chars)
    # Allow " | " for union types
    outer_no_union = re.sub(r'\s*\|\s*', '', outer)
    if ' ' in outer_no_union:
        return False
    # Must start with letter or underscore
    return bool(re.match(r'^[A-Za-z_\[]', s))


# ---------------------------------------------------------------------------
# File-level processing


def fix_file(filepath: Path) -> bool:
    """Fix pydoclint violations in a single Python file."""
    source = filepath.read_text(encoding='utf-8')
    funcs = _collect_funcs(source)
    if not funcs:
        return False

    lines = source.splitlines(keepends=True)

    # Collect patches: (ds_start_0idx, ds_end_0idx, new_lines)
    patches: list[tuple[int, int, list[str]]] = []

    for func_lineno, info in sorted(funcs.items(), reverse=True):
        ds_start = info['ds_start']
        ds_end = info['ds_end']
        if ds_start is None or ds_end is None:
            continue

        # 0-based indices
        s = ds_start - 1
        e = ds_end - 1
        ds_lines = lines[s:e + 1]

        if not ds_lines:
            continue

        # ---- DOC301: Remove __init__ docstring if class has one ----
        if info['is_init'] and info['cls_has_ds']:
            # Remove the docstring lines entirely
            # But keep any blank line after docstring - handled by just removing
            patches.append((s, e, []))
            continue

        # ---- Parse the docstring ----
        raw_full = ''.join(ds_lines)
        is_single_line = (ds_start == ds_end)

        # Get the content of the docstring (between the triple quotes)
        first_line_stripped = ds_lines[0].lstrip()
        base_indent = ds_lines[0][:len(ds_lines[0]) - len(ds_lines[0].lstrip())]

        if first_line_stripped.startswith('"""'):
            q = '"""'
        elif first_line_stripped.startswith("'''"):
            q = "'''"
        else:
            continue

        if is_single_line:
            # Content is between the quotes on one line
            inner = first_line_stripped[3:]
            if inner.endswith(q + '\n'):
                inner = inner[:-4]
            elif inner.endswith(q):
                inner = inner[:-3]
            content = inner
        else:
            # Multi-line: extract content lines (between opening and closing quotes)
            # First line: content after opening """
            first_after_q = first_line_stripped[3:]
            content_lines = [first_after_q] if first_after_q.strip() else []
            # Middle lines (unchanged)
            for line in ds_lines[1:-1]:
                content_lines.append(line)
            # Last line: content before closing """
            last_line = ds_lines[-1]
            last_stripped = last_line.lstrip()
            if last_stripped.rstrip() in (q, q + '\n'):
                # Just closing quote, no content
                pass
            else:
                # Content before the closing quote
                idx = last_stripped.rfind(q)
                if idx > 0:
                    content_lines.append(last_line[:len(last_line)-len(last_stripped)] + last_stripped[:idx])
            content = ''.join(content_lines)

        # ---- Apply fixes to content ----
        new_content = _fix_docstring_content(
            content,
            info['args'],
            info['anns'],
            info['ret'],
            info['has_raise'],
            base_indent,
        )

        if new_content == content:
            continue

        # ---- Reconstruct docstring source lines ----
        if is_single_line:
            new_single = new_content.strip()
            if '\n' not in new_single:
                # Keep single-line
                new_line = f'{base_indent}{q}{new_single}{q}\n'
                patches.append((s, e, [new_line]))
            else:
                # Convert to multi-line
                new_lines = _build_multiline_docstring(new_content, base_indent, q)
                patches.append((s, e, new_lines))
        else:
            # Reconstruct multi-line
            new_lines = _reconstruct_multiline(ds_lines, new_content, base_indent, q)
            patches.append((s, e, new_lines))

    if not patches:
        return False

    # Apply patches bottom-up (already sorted in reverse order above)
    new_lines = list(lines)
    for s, e, replacement in patches:
        new_lines[s:e + 1] = replacement

    new_source = ''.join(new_lines)
    if new_source == source:
        return False

    # Verify it's valid Python
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        print(f"  SYNTAX ERROR after fix in {filepath}: {exc}", file=sys.stderr)
        return False

    filepath.write_text(new_source, encoding='utf-8')
    return True


def _build_multiline_docstring(content: str, base_indent: str, q: str) -> list[str]:
    """Build multi-line docstring lines from content string."""
    content_lines = content.splitlines(keepends=True)
    result: list[str] = []

    # Opening: """First line
    first = content_lines[0].rstrip() if content_lines else ''
    if first:
        result.append(f'{base_indent}{q}{first}\n')
    else:
        result.append(f'{base_indent}{q}\n')

    for line in content_lines[1:]:
        stripped = line.rstrip()
        if stripped:
            # Re-indent relative to base
            line_ws = line[: len(line) - len(line.lstrip())]
            # Use original indentation from content
            result.append(line if line.endswith('\n') else line + '\n')
        else:
            result.append('\n')

    result.append(f'{base_indent}{q}\n')
    return result


def _reconstruct_multiline(
    orig_lines: list[str],
    new_content: str,
    base_indent: str,
    q: str,
) -> list[str]:
    """Reconstruct multi-line docstring preserving original structure."""
    orig_content_lines: list[str] = []

    # Extract original content lines (between opening and closing quotes)
    # First line after quotes
    first = orig_lines[0].lstrip()[3:]  # after opening """
    orig_content_lines.append(first)
    # Middle lines
    for line in orig_lines[1:-1]:
        orig_content_lines.append(line)

    # Build new content lines
    new_content_lines = new_content.splitlines(keepends=True)
    if new_content_lines and not new_content_lines[-1].endswith('\n'):
        new_content_lines[-1] += '\n'

    result: list[str] = []

    # Opening line
    if new_content_lines:
        first_new = new_content_lines[0].rstrip()
        if first_new:
            result.append(f'{base_indent}{q}{first_new}\n')
        else:
            result.append(f'{base_indent}{q}\n')
            # Re-add it as empty
        remaining = new_content_lines[1:] if first_new else new_content_lines
    else:
        result.append(f'{base_indent}{q}\n')
        remaining = []

    for line in remaining:
        result.append(line if line.endswith('\n') else line + '\n')

    # Closing quote
    # Get indent of closing quote from original
    last_orig = orig_lines[-1]
    closing_indent = last_orig[:len(last_orig) - len(last_orig.lstrip())]
    result.append(f'{closing_indent}{q}\n')

    return result


def process_directory(dirpath: Path) -> tuple[int, int]:
    processed = changed = 0
    for py_file in sorted(dirpath.rglob('*.py')):
        processed += 1
        try:
            if fix_file(py_file):
                changed += 1
                print(f'  Fixed: {py_file}')
        except Exception as exc:
            import traceback
            print(f'  ERROR {py_file}: {exc}', file=sys.stderr)
            traceback.print_exc()
    return processed, changed


def main() -> None:
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <path>...', file=sys.stderr)
        sys.exit(1)

    total_p = total_c = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_dir():
            print(f'Processing directory: {path}')
            p, c = process_directory(path)
            total_p += p
            total_c += c
        elif path.is_file():
            try:
                if fix_file(path):
                    total_c += 1
                    print(f'Fixed: {path}')
                total_p += 1
            except Exception as exc:
                print(f'ERROR {path}: {exc}', file=sys.stderr)
        else:
            print(f'Not found: {path}', file=sys.stderr)

    print(f'\nProcessed {total_p} files, changed {total_c}')


if __name__ == '__main__':
    main()
