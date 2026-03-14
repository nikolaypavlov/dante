#!/usr/bin/env python3
"""Validate canto JSON files against the schema and run semantic checks.

Usage:
    uv run scripts/validate_json.py                # validate all json/*.json
    uv run scripts/validate_json.py inf_26.json    # validate one file
    uv run scripts/validate_json.py purg_01.json purg_02.json  # validate several
    uv run scripts/validate_json.py --check-sync   # verify HTML exists and matches
"""

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "json"
HTML_DIR = ROOT / "html"
SCHEMA_PATH = JSON_DIR / "canto.schema.json"

CANTICA_PREFIX = {
    "Inferno": "inf",
    "Purgatorio": "purg",
    "Paradiso": "par",
}

CANTO_LABEL_PREFIX = {
    "Inferno": "Inf.",
    "Purgatorio": "Purg.",
    "Paradiso": "Par.",
}

FILENAME_RE = re.compile(r"^(inf|purg|par)_(\d{2})\.json$")

# Authors who accessed sources indirectly and require transmission chains
INDIRECT_AUTHORS = {
    "\u0413\u043e\u043c\u0435\u0440",
    "\u041f\u043b\u0430\u0442\u043e\u043d",
    "\u0410\u0440\u0456\u0441\u0442\u043e\u0442\u0435\u043b\u044c",
}


def int_to_roman(n: int) -> str:
    result = []
    for value, numeral in [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]:
        while n >= value:
            result.append(numeral)
            n -= value
    return "".join(result)


def validate_file(path: Path, validator: Draft7Validator) -> list[str]:
    errors: list[str] = []

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Schema validation
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        location = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"Schema: {location}: {error.message}")

    # Stop semantic checks if schema is broken
    if errors:
        return errors

    # --- Semantic checks ---

    filename = path.name
    m = FILENAME_RE.match(filename)
    if not m:
        errors.append(f"Filename '{filename}' does not match expected pattern")
        return errors

    file_prefix = m.group(1)
    file_num = int(m.group(2))

    cantica = data["cantica"]
    canto_num = data["canto_num"]
    canto_label = data["canto"]

    # canto_num matches filename number
    if canto_num != file_num:
        errors.append(
            f"canto_num={canto_num} does not match filename number {file_num}"
        )

    # cantica prefix matches filename prefix
    expected_prefix = CANTICA_PREFIX.get(cantica)
    if expected_prefix != file_prefix:
        errors.append(
            f"cantica='{cantica}' (prefix '{expected_prefix}') "
            f"does not match filename prefix '{file_prefix}'"
        )

    # canto label matches cantica + canto_num
    expected_label = (
        f"{CANTO_LABEL_PREFIX.get(cantica, '??')} {int_to_roman(canto_num)}"
    )
    if canto_label != expected_label:
        errors.append(
            f"canto='{canto_label}' does not match expected '{expected_label}'"
        )

    # Connection-level checks
    seen_ids: set[str] = set()
    for i, conn in enumerate(data["connections"]):
        cid = conn["id"]

        # Unique ID within file
        if cid in seen_ids:
            errors.append(f"connections[{i}]: duplicate id '{cid}'")
        seen_ids.add(cid)

        # ID prefix matches cantica
        if expected_prefix and not cid.startswith(f"{expected_prefix}_"):
            errors.append(
                f"connections[{i}]: id '{cid}' does not start with '{expected_prefix}_'"
            )

        # Chain required for indirect authors
        if conn["source_author"] in INDIRECT_AUTHORS and conn["chain"] is None:
            errors.append(
                f"connections[{i}]: source_author '{conn['source_author']}' "
                f"requires a transmission chain (chain must not be null)"
            )

    return errors


def check_sync(json_files: list[Path]) -> int:
    """Verify that each JSON file has a matching HTML file."""
    errors = 0
    for path in json_files:
        stem = path.stem
        html_path = HTML_DIR / f"{stem}.html"
        if not html_path.exists():
            print(f"  MISSING: {stem}.html (no HTML for {stem}.json)")
            errors += 1
    return errors


def resolve_paths(args: list[str]) -> list[Path]:
    """Turn CLI arguments into absolute paths inside JSON_DIR."""
    paths = []
    for arg in args:
        p = Path(arg)
        # Accept both bare filenames ("inf_26.json") and full/relative paths
        if not p.is_absolute():
            candidate = JSON_DIR / p.name
        else:
            candidate = p
        if not candidate.exists():
            print(f"File not found: {candidate}", file=sys.stderr)
            sys.exit(2)
        paths.append(candidate)
    return sorted(paths)


def main() -> int:
    args = sys.argv[1:]
    do_sync = "--check-sync" in args
    args = [a for a in args if a != "--check-sync"]

    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft7Validator(schema)

    if args:
        json_files = resolve_paths(args)
    else:
        json_files = sorted(
            f for f in JSON_DIR.glob("*.json") if f.name != "canto.schema.json"
        )

    if not json_files:
        print("No JSON files found in", JSON_DIR)
        return 1

    if do_sync:
        sync_errors = check_sync(json_files)
        print()
        if sync_errors == 0:
            print(f"OK: {len(json_files)} file(s) have matching HTML.")
            return 0
        else:
            print(f"FAILED: {sync_errors} JSON file(s) missing HTML counterparts.")
            return 1

    total_errors = 0

    for path in json_files:
        errors = validate_file(path, validator)
        if errors:
            print(f"\n{path.name}: {len(errors)} error(s)")
            for err in errors:
                print(f"  - {err}")
            total_errors += len(errors)

    print()
    if total_errors == 0:
        print(f"OK: {len(json_files)} file(s) validated, 0 errors.")
        return 0
    else:
        print(f"FAILED: {total_errors} error(s) across {len(json_files)} file(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
