"""Tools Catalog generator for MkDocs.

This script automatically generates a Tools Catalog page that lists all script/tool
documentation pages. It runs during the MkDocs build process via the gen-files plugin.

The catalog is organized by category (validation, data, build, docs, release, misc)
and includes usage information for each tool.

Generated page: docs/tools/index.md
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
import mkdocs_gen_files

DOCS = Path("docs")


def iter_script_pages() -> list[dict[str, str]]:
    """Iterate over all script/tool documentation pages.

    Yields:
        Dictionary containing:
            - path: Relative path from docs/
            - title: Page title
            - name: Script name
            - category: Script category
            - usage: Usage example
            - description: Short description
    """
    script_pages = []

    for md_file in DOCS.rglob("*.md"):
        # Skip build artifacts
        if "site" in md_file.parts:
            continue

        try:
            post = frontmatter.load(md_file)
            meta = post.metadata

            # Only include script pages
            if isinstance(meta, dict) and meta.get("schema_type") == "script":
                rel_path = md_file.relative_to(DOCS)

                script_pages.append(
                    {
                        "path": rel_path.as_posix(),
                        "title": meta.get("title", "Untitled"),
                        "name": meta.get("name", ""),
                        "category": (meta.get("category") or "misc").lower(),
                        "usage": meta.get("usage", ""),
                        "description": meta.get("description", ""),
                    }
                )
        except Exception:  # nosec B112  # noqa: S112 (intentional skip on parse errors)
            # Skip files with parsing errors (intentional)
            continue

    return script_pages


def generate_catalog() -> str:
    """Generate the Tools Catalog markdown content.

    Returns:
        Markdown content for the catalog page.
    """
    items = iter_script_pages()

    # Sort by category, then by name
    items.sort(key=lambda x: (x["category"], x["name"] or x["title"]))

    lines = [
        "# Tools Catalog",
        "",
        "This page lists all available tools and scripts in the project, ",
        "organized by category.",
        "",
    ]

    current_category = None

    for item in items:
        category = item["category"]

        # Add category heading if changed
        if category != current_category:
            current_category = category
            lines.append(f"\n## {category.replace('_', ' ').title()}\n")

        # Create entry
        label = item["name"] or item["title"]
        link = f"[{label}](../{item['path']})"

        # Add description if available
        desc = f" — {item['description']}" if item["description"] else ""

        # Add usage if available
        usage = f"\n    - Usage: `{item['usage']}`" if item["usage"] else ""

        lines.append(f"- {link}{desc}{usage}")

    # Add footer
    lines.extend(
        [
            "",
            "---",
            "",
            "*This catalog is automatically generated during the build process.*",
            "",
        ]
    )

    return "\n".join(lines)


# Generate the catalog during build
with mkdocs_gen_files.open("tools/index.md", "w") as f:
    f.write(generate_catalog())
