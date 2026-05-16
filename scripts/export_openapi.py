"""Export the FastAPI OpenAPI schema to docs/api/openapi.json.

Run from the repository root:

    uv run python scripts/export_openapi.py [--output PATH]

The script imports the FastAPI app, calls ``app.openapi()``, and writes the
returned schema as pretty-printed JSON. The companion Markdown reference
files under ``docs/api/`` are not touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.json"


def _ensure_src_on_path() -> None:
    src_dir = REPO_ROOT / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def export_openapi(output_path: Path) -> Path:
    """Generate the OpenAPI spec and write it to ``output_path``.

    Returns the resolved output path for convenience.
    """
    _ensure_src_on_path()

    # Imported lazily so ``sys.path`` is configured first.
    from image_preprocessing_detector.api.app import create_app

    app = create_app()
    schema = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path for the OpenAPI JSON (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args(argv)

    written = export_openapi(args.output)
    print(f"Wrote OpenAPI schema to {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
