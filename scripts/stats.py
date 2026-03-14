#!/usr/bin/env python3
"""Aggregate analytics across all canto JSON files.

Usage:
    uv run scripts/stats.py          # terminal output
    uv run scripts/stats.py --json   # JSON to stdout
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "json"

CANTICA_COUNTS = {"Inferno": 34, "Purgatorio": 33, "Paradiso": 33}


def gather_stats() -> dict:
    json_files = sorted(
        f for f in JSON_DIR.glob("*.json") if f.name != "canto.schema.json"
    )

    cantica_done = Counter()
    type_counter = Counter()
    author_counter = Counter()
    confidence_counter = Counter()
    conn_per_canto = []

    for path in json_files:
        with open(path) as f:
            data = json.load(f)
        cantica_done[data["cantica"]] += 1
        conns = data["connections"]
        conn_per_canto.append(len(conns))
        for conn in conns:
            type_counter[conn["type"]] += 1
            author_counter[conn["source_author"]] += 1
            confidence_counter[conn["confidence"]] += 1

    total_cantos = len(json_files)
    total_connections = sum(conn_per_canto)

    return {
        "total_cantos": total_cantos,
        "max_cantos": 100,
        "cantica": {
            name: {"done": cantica_done.get(name, 0), "total": count}
            for name, count in CANTICA_COUNTS.items()
        },
        "connections_by_type": dict(type_counter.most_common()),
        "total_connections": total_connections,
        "top_authors": dict(author_counter.most_common(10)),
        "confidence": dict(confidence_counter.most_common()),
        "per_canto": {
            "min": min(conn_per_canto) if conn_per_canto else 0,
            "max": max(conn_per_canto) if conn_per_canto else 0,
            "avg": round(sum(conn_per_canto) / len(conn_per_canto), 1)
            if conn_per_canto
            else 0,
        },
    }


def print_stats(stats: dict) -> None:
    total = stats["total_cantos"]
    max_c = stats["max_cantos"]
    parts = []
    for name, info in stats["cantica"].items():
        parts.append(f"{name[:3]}: {info['done']}")
    print(f"Cantos: {total}/{max_c} ({', '.join(parts)})\n")

    print("Connections by type:")
    total_conn = stats["total_connections"]
    for conn_type, count in stats["connections_by_type"].items():
        pct = round(count / total_conn * 100) if total_conn else 0
        print(f"  {conn_type:<12} {count:>4}  ({pct}%)")

    print("\nTop 10 authors:")
    for i, (author, count) in enumerate(stats["top_authors"].items(), 1):
        print(f"  {i:>2}. {author:<20} {count:>4}")

    conf = stats["confidence"]
    conf_parts = []
    for level, count in conf.items():
        pct = round(count / total_conn * 100) if total_conn else 0
        conf_parts.append(f"{level} {count} ({pct}%)")
    print(f"\nConfidence: {', '.join(conf_parts)}")

    p = stats["per_canto"]
    print(f"Connections per canto: min={p['min']}, max={p['max']}, avg={p['avg']}")


def main() -> int:
    stats = gather_stats()

    if "--json" in sys.argv:
        json.dump(stats, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_stats(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
