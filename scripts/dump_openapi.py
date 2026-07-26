"""Write the API's OpenAPI schema to schemas/openapi.json.

The TypeScript client is generated from this file and never hand-written (ADR-0001), so CI
regenerates it and fails if the result differs from what is committed.

Writes atomically. A redirect (`python ... > schemas/openapi.json`) truncates the target before
the interpreter runs, so an import error would silently destroy the committed schema and leave
the drift check comparing an empty file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "schemas" / "openapi.json"


def main() -> int:
    try:
        from services.api.main import app
    except ModuleNotFoundError as exc:
        print(
            f"error: {exc.name} is not installed. Run `pip install -e \".[dev]\"` first.",
            file=sys.stderr,
        )
        return 1

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print(f"wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
