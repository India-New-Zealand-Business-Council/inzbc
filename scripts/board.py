"""Safe edits to the GitHub Projects v2 board.

Two failure modes cost real work on this project, and both are silent. This script exists so
neither can happen again.

**1. Adding a single-select option wipes every item's value for that field.**
`updateProjectV2Field` replaces the whole option set rather than appending to it, and an item's
stored value is a reference to an option *id*, not to its name. Re-sending the existing options
with the same names still mints new ids, so every item that used one is orphaned. There is no
append operation in the API. `add-option` therefore snapshots, mutates, restores and verifies.

**2. A bulk edit loop can fail every call and still report success.**
The first attempt at populating fields failed 204 times in a row: the generated plan file had
CRLF line endings, so every option id carried a trailing `\\r` and the API correctly rejected it.
`gh` errors were piped away and the loop never checked an exit code. Every function here counts
failures and prints them.

Everything is keyed on option **names**, never ids, so a snapshot stays valid across a field
rebuild. That is the whole point.

Usage:

    python scripts/board.py snapshot                     # back up before touching anything
    python scripts/board.py restore board-snapshot.json  # put values back
    python scripts/board.py add-option Phase "Phase 5 (M5)"
    python scripts/board.py verify                       # report items missing a field value
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

OWNER = "India-New-Zealand-Business-Council"
PROJECT_NUMBER = "1"
PROJECT_ID = "PVT_kwDOEku5vs4BeYLi"
SNAPSHOT = Path(__file__).resolve().parent.parent / "board-snapshot.json"

# Colours cycle; GitHub rejects an unknown name. Only used when creating options.
COLORS = ["GRAY", "BLUE", "GREEN", "PURPLE", "YELLOW", "ORANGE", "RED", "PINK"]


def gh(args: list[str]) -> str:
    """Run a gh command, failing loudly. Never swallow the error: see docstring, failure 2."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def single_select_fields() -> dict[str, tuple[str, dict[str, str]]]:
    """Field name -> (field id, {option name: option id}). Read fresh every time, never cached."""
    data = json.loads(gh(["project", "field-list", PROJECT_NUMBER, "--owner", OWNER,
                          "--format", "json"]))
    return {f["name"]: (f["id"], {o["name"]: o["id"] for o in f.get("options", [])})
            for f in data["fields"] if f.get("options")}


def items() -> list[dict[str, Any]]:
    data = json.loads(gh(["project", "item-list", PROJECT_NUMBER, "--owner", OWNER,
                          "--format", "json", "--limit", "500"]))
    return data["items"]


def _key(field_name: str) -> str:
    """`gh` lowercases field names and strips spaces when it emits item JSON."""
    return field_name.lower().replace(" ", "")


def snapshot(path: Path = SNAPSHOT) -> dict[str, Any]:
    """Record every item's field values by NAME, so the file survives a field rebuild."""
    fields = single_select_fields()
    rows = []
    for item in items():
        content = item.get("content") or {}
        rows.append({
            "id": item["id"],
            "number": content.get("number"),
            "title": item.get("title", "")[:120],
            "values": {name: item[_key(name)] for name in fields if _key(name) in item},
        })
    payload = {"project": PROJECT_ID, "fields": sorted(fields), "items": rows}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    missing = sum(len(fields) - len(r["values"]) for r in rows)
    print(f"snapshot: {len(rows)} items -> {path.name} ({missing} field values unset)")
    return payload


def restore(path: Path = SNAPSHOT) -> int:
    """Re-apply a snapshot, resolving option names against the field's CURRENT ids."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = single_select_fields()
    live = {item["id"] for item in items()}
    applied = failed = skipped = 0
    for row in payload["items"]:
        if row["id"] not in live:
            skipped += 1
            continue
        for field_name, option_name in row["values"].items():
            if field_name not in fields:
                print(f"  field gone: {field_name}")
                failed += 1
                continue
            field_id, options = fields[field_name]
            option_id = options.get(option_name)
            if option_id is None:
                print(f"  option gone: {field_name}={option_name} (item {row['number']})")
                failed += 1
                continue
            result = subprocess.run(
                ["gh", "project", "item-edit", "--project-id", PROJECT_ID, "--id", row["id"],
                 "--field-id", field_id, "--single-select-option-id", option_id],
                capture_output=True, text=True, check=False)
            if result.returncode == 0:
                applied += 1
            else:
                failed += 1
                print(f"  #{row['number']} {field_name}: {result.stderr.strip()[:120]}")
    print(f"restore: applied={applied} failed={failed} skipped={skipped} (items no longer on board)")
    return failed


def add_option(field_name: str, option_name: str) -> int:
    """Add one option to a single-select field without losing every item's current value."""
    fields = single_select_fields()
    if field_name not in fields:
        raise SystemExit(f"no single-select field named {field_name!r}. Have: {sorted(fields)}")
    field_id, options = fields[field_name]
    if option_name in options:
        print(f"{field_name!r} already has {option_name!r}; nothing to do")
        return 0

    backup = SNAPSHOT.with_name(f"board-before-{field_name.lower()}-option.json")
    snapshot(backup)

    names = list(options) + [option_name]
    payload = {
        "query": """
            mutation($f: ID!, $o: [ProjectV2SingleSelectFieldOptionInput!]!) {
              updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: $o}) {
                projectV2Field { ... on ProjectV2SingleSelectField { options { name } } }
              }
            }""",
        "variables": {
            "f": field_id,
            "o": [{"name": n, "color": COLORS[i % len(COLORS)], "description": ""}
                  for i, n in enumerate(names)],
        },
    }
    # Passed as a file: the option list contains characters that -f mangles.
    tmp = Path(tempfile.gettempdir()) / "board-option-mutation.json"
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    gh(["api", "graphql", "--input", str(tmp)])
    tmp.unlink(missing_ok=True)
    print(f"{field_name!r} options are now: {names}")

    # The ids just changed, so every item's value for this field is now dangling.
    failed = restore(backup)
    still_unset = verify(quiet=True)
    if failed or still_unset:
        print(f"WARNING: {failed} restores failed, {still_unset} items still missing a value. "
              f"The snapshot is at {backup}; fix and re-run restore before doing anything else.")
    else:
        print("verified: every item kept its value")
        backup.unlink(missing_ok=True)
    return failed


def verify(quiet: bool = False) -> int:
    """Report items missing a value for any single-select field."""
    fields = single_select_fields()
    gaps = []
    for item in items():
        missing = [name for name in fields if _key(name) not in item]
        if missing:
            content = item.get("content") or {}
            gaps.append((content.get("number"), item.get("title", "")[:60], missing))
    if not quiet:
        for number, title, missing in gaps:
            print(f"  #{number} {title} -> missing {', '.join(missing)}")
        print(f"verify: {len(gaps)} items with an unset field")
    return len(gaps)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    command, *rest = argv
    if command == "snapshot":
        snapshot(Path(rest[0]) if rest else SNAPSHOT)
    elif command == "restore":
        return 1 if restore(Path(rest[0]) if rest else SNAPSHOT) else 0
    elif command == "add-option":
        if len(rest) != 2:
            raise SystemExit('usage: add-option <field> "<option name>"')
        return 1 if add_option(rest[0], rest[1]) else 0
    elif command == "verify":
        return 1 if verify() else 0
    else:
        raise SystemExit(f"unknown command {command!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
