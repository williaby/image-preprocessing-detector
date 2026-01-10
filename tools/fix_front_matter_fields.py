#!/usr/bin/env python3
"""Fix front matter fields that have invalid values or extra fields.

Fixes:
- Invalid status values → 'draft'
- Extra inputs (version, last_updated) → removed
- Redundant H1 headings → removed from body
"""

from __future__ import annotations

import re
from pathlib import Path

from ruamel.yaml import YAML


def fix_file(path: Path) -> bool:
    """Fix front matter issues in a file.

    Returns True if changes were made.
    """
    text = path.read_text(encoding="utf-8")

    # Find front matter block
    match = re.search(r"^---\n.*?\n---\n", text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return False

    # Parse YAML with round-trip preservation
    yrt = YAML(typ="rt")
    yrt.preserve_quotes = True
    yrt.allow_duplicate_keys = False

    yaml_text = text[match.start() + 4 : match.end() - 4]
    try:
        data = yrt.load(yaml_text)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    changed = False

    # Fix invalid status
    valid_statuses = {"draft", "in-review", "published"}
    if "status" in data and data["status"] not in valid_statuses:
        print(f"  Fixing status: {data['status']} → draft")
        data["status"] = "draft"
        changed = True

    # Remove extra inputs (any field not in CommonFM schema)
    extra_fields = [
        "version", "last_updated", "created", "deprecated_date",
        "superseded_by", "parent_doc", "reviewed_by"
    ]
    for field in extra_fields:
        if field in data:
            print(f"  Removing extra field: {field}")
            del data[field]
            changed = True

    # Add missing purpose field
    if "purpose" not in data and "title" in data:
        title = data["title"]
        purpose = f"Documentation for {title}."
        print(f"  Adding missing purpose: {purpose}")
        data["purpose"] = purpose
        changed = True

    # Get the body content after front matter
    body = text[match.end():]

    # Check for redundant H1 if we have a title
    if "title" in data:
        title = data["title"]
        # Look for H1 heading that matches title
        h1_pattern = re.compile(r"^\s*#\s+" + re.escape(title) + r"\s*$\n?", re.MULTILINE)
        if h1_pattern.search(body):
            print(f"  Removing redundant H1: # {title}")
            body = h1_pattern.sub("", body, count=1)
            changed = True

    if not changed:
        return False

    # Write changes back
    from io import StringIO
    out = StringIO()
    yrt.dump(data, out)
    new_yaml = out.getvalue().rstrip()
    new_content = f"---\n{new_yaml}\n---\n{body.lstrip()}"
    path.write_text(new_content, encoding="utf-8")

    return True


def main() -> int:
    """Fix remaining front matter issues."""
    import subprocess
    import json

    # Get list of files with issues
    result = subprocess.run(
        ["uv", "run", "python", "tools/validate_front_matter.py", "docs", "--emit-json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to get validation results")
        return 1

    # Find files with issues
    files_to_fix = []
    for item in data:
        if not item["ok"]:
            files_to_fix.append((Path(item["file"]), item.get("errors", [])))

    print(f"Found {len(files_to_fix)} files with issues")

    fixed = 0
    for path, errors in files_to_fix:
        if path.exists():
            print(f"\n{path}:")
            for err in errors:
                print(f"  Issue: {err}")
            if fix_file(path):
                fixed += 1
                print(f"  ✓ Fixed")

    print(f"\nFixed {fixed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
