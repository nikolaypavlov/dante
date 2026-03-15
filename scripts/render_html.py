#!/usr/bin/env python3
"""Render canto JSON files to self-contained HTML visualizations.

Usage:
    uv run scripts/render_html.py              # render all json/*.json
    uv run scripts/render_html.py inf_01       # render single canto
    uv run scripts/render_html.py --check      # dry-run, report diffs
    uv run scripts/render_html.py --index      # generate html/index.html
    uv run scripts/render_html.py --dist       # build flat site into dist/
"""

import colorsys
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "json"
HTML_DIR = ROOT / "html"
TEMPLATE_DIR = ROOT / "templates"

CANTICA_SEQUENCE = [
    ("Inferno", "inf", "Inf.", 34),
    ("Purgatorio", "purg", "Purg.", 33),
    ("Paradiso", "par", "Par.", 33),
]

THEME_CLASS = {
    "Inferno": "",
    "Purgatorio": "theme-purgatorio",
    "Paradiso": "theme-paradiso",
}

CANONICAL_AUTHORS = {
    "\u0414\u0430\u043d\u0442\u0435": {"f": "#281a08", "s": "#d4a853"},
    "\u0412\u0435\u0440\u0433\u0456\u043b\u0456\u0439": {
        "f": "#1a0e28",
        "s": "#a06ece",
    },
    "\u041e\u0432\u0456\u0434\u0456\u0439": {"f": "#280e1a", "s": "#ce5a8a"},
    "\u041b\u0443\u043a\u0430\u043d": {"f": "#0e2028", "s": "#5abecc"},
    "\u0421\u0442\u0430\u0446\u0456\u0439": {"f": "#0e1428", "s": "#5a7ece"},
    "\u0413\u043e\u043c\u0435\u0440": {"f": "#28140e", "s": "#ce7a5a"},
    "\u0411\u0456\u0431\u043b\u0456\u044f": {"f": "#280e0e", "s": "#ce5a5a"},
}

CANONICAL_AUTHORS_PARADISO = {
    "\u0414\u0430\u043d\u0442\u0435": {"f": "#f0e4c8", "s": "#a07820"},
    "\u0412\u0435\u0440\u0433\u0456\u043b\u0456\u0439": {"f": "#e8daf0", "s": "#7048a0"},
    "\u041e\u0432\u0456\u0434\u0456\u0439": {"f": "#f0dae4", "s": "#a04068"},
    "\u041b\u0443\u043a\u0430\u043d": {"f": "#daeaf0", "s": "#3090a0"},
    "\u0421\u0442\u0430\u0446\u0456\u0439": {"f": "#dae0f0", "s": "#4060a0"},
    "\u0413\u043e\u043c\u0435\u0440": {"f": "#f0e0da", "s": "#a06038"},
    "\u0411\u0456\u0431\u043b\u0456\u044f": {"f": "#f0dada", "s": "#a04040"},
}

CANONICAL_HUES = set()
for _style in CANONICAL_AUTHORS.values():
    r = int(_style["s"][1:3], 16) / 255
    g = int(_style["s"][3:5], 16) / 255
    b = int(_style["s"][5:7], 16) / 255
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    CANONICAL_HUES.add(round(h * 360))


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


def slugify(ref: str) -> str:
    """Generate a node ID from a source reference string."""
    ref = re.sub(r"\([^)]*\)", "", ref)
    ref = ref.lower()
    ref = re.sub(r"[^a-z0-9]", "_", ref)
    ref = re.sub(r"_+", "_", ref)
    return ref.strip("_")


def author_color(name: str, paradiso: bool = False) -> dict:
    """Generate deterministic fill/stroke colors for a non-canonical author."""
    digest = int(hashlib.md5(name.encode()).hexdigest(), 16)
    hue = digest % 360
    while any(abs(hue - ch) < 20 or abs(hue - ch) > 340 for ch in CANONICAL_HUES):
        hue = (hue + 23) % 360
    h = hue / 360.0
    if paradiso:
        r, g, b = colorsys.hls_to_rgb(h, 0.92, 0.35)
        fill = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        r, g, b = colorsys.hls_to_rgb(h, 0.40, 0.50)
        stroke = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    else:
        r, g, b = colorsys.hls_to_rgb(h, 0.12, 0.40)
        fill = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        r, g, b = colorsys.hls_to_rgb(h, 0.60, 0.50)
        stroke = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    return {"f": fill, "s": stroke}


def build_canto_data(data: dict, cantica: str = "") -> tuple[list, dict, dict]:
    """Transform JSON connections into LINKS_DATA, NODES_RAW, AUTHOR_STYLES."""
    connections = data["connections"]
    links = []
    nodes = {}
    authors_seen = set()

    # Group connections by base ID (strip trailing letter suffix)
    groups = []
    current_group = []
    current_base = None
    for conn in connections:
        base = re.sub(r"[a-z]$", "", conn["id"])
        if base != current_base:
            if current_group:
                groups.append(current_group)
            current_group = [conn]
            current_base = base
        else:
            current_group.append(conn)
    if current_group:
        groups.append(current_group)

    for group_idx, group in enumerate(groups):
        dante_id = f"d_{group_idx + 1:02d}"
        first = group[0]

        # Create Dante node (col 0) if not already present
        if dante_id not in nodes:
            nodes[dante_id] = {
                "label": first["dante_ref"],
                "sub": first["dante_sub"],
                "author": "\u0414\u0430\u043d\u0442\u0435",
                "col": 0,
            }
            authors_seen.add("\u0414\u0430\u043d\u0442\u0435")

        for conn in group:
            source_slug = slugify(conn["source_ref"])
            conn_type = conn["type"]
            desc_dante = conn["desc_dante"]
            desc_source = conn["desc_source"]

            if conn["chain"]:
                # Chained connection: intermediaries at col 1, source at col 2
                if source_slug not in nodes:
                    nodes[source_slug] = {
                        "label": conn["source_ref"],
                        "sub": conn["source_sub"],
                        "author": conn["source_author"],
                        "col": 2,
                    }
                    authors_seen.add(conn["source_author"])

                for chain_item in conn["chain"]:
                    chain_slug = slugify(chain_item["ref"])
                    if chain_slug not in nodes:
                        nodes[chain_slug] = {
                            "label": chain_item["ref"],
                            "sub": chain_item["sub"],
                            "author": chain_item["author"],
                            "col": 1,
                        }
                        authors_seen.add(chain_item["author"])

                    # Dante -> chain intermediary
                    links.append(
                        {
                            "from": dante_id,
                            "to": chain_slug,
                            "type": conn_type,
                            "dF": desc_dante,
                            "dT": chain_item["desc"],
                        }
                    )
                    # Chain intermediary -> primary source
                    links.append(
                        {
                            "from": chain_slug,
                            "to": source_slug,
                            "type": conn_type,
                            "dF": desc_source,
                            "dT": desc_source,
                        }
                    )
            else:
                # Direct connection: source at col 1
                if source_slug not in nodes:
                    nodes[source_slug] = {
                        "label": conn["source_ref"],
                        "sub": conn["source_sub"],
                        "author": conn["source_author"],
                        "col": 1,
                    }
                    authors_seen.add(conn["source_author"])

                links.append(
                    {
                        "from": dante_id,
                        "to": source_slug,
                        "type": conn_type,
                        "dF": desc_dante,
                        "dT": desc_source,
                    }
                )

    # Build author styles
    is_paradiso = cantica == "Paradiso"
    canonical = CANONICAL_AUTHORS_PARADISO if is_paradiso else CANONICAL_AUTHORS
    styles = {}
    for name in sorted(authors_seen):
        if name in canonical:
            styles[name] = canonical[name]
        else:
            styles[name] = author_color(name, paradiso=is_paradiso)

    return links, nodes, styles


def js_string(s: str) -> str:
    """Escape a string for use in a JS string literal."""
    return (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def format_links_data(links: list) -> str:
    """Format LINKS_DATA as a JS array literal."""
    parts = []
    for link in links:
        parts.append(
            '  { from:"%s", to:"%s", type:"%s",\n'
            '    dF:"%s",\n'
            '    dT:"%s" }'
            % (
                link["from"],
                link["to"],
                link["type"],
                js_string(link["dF"]),
                js_string(link["dT"]),
            )
        )
    return "[\n" + ",\n".join(parts) + ",\n]"


def format_nodes_raw(nodes: dict) -> str:
    """Format NODES_RAW as a JS object literal."""
    parts = []
    for node_id, node in nodes.items():
        parts.append(
            '  "%s": { label:"%s", sub:"%s", author:"%s", col:%d }'
            % (
                node_id,
                js_string(node["label"]),
                js_string(node["sub"]),
                js_string(node["author"]),
                node["col"],
            )
        )
    return "{\n" + ",\n".join(parts) + ",\n}"


def format_author_styles(styles: dict) -> str:
    """Format AUTHOR_STYLES as a JS object literal."""
    parts = []
    for name, colors in styles.items():
        parts.append(
            '  "%s": {f:"%s",s:"%s"}' % (js_string(name), colors["f"], colors["s"])
        )
    return "{\n" + ",\n".join(parts) + ",\n}"


def build_full_sequence() -> list[tuple[str, str, str, int]]:
    """Return the full 100-canto sequence as (prefix, abbrev, cantica, num)."""
    seq = []
    for cantica, prefix, abbrev, count in CANTICA_SEQUENCE:
        for num in range(1, count + 1):
            seq.append((prefix, abbrev, cantica, num))
    return seq


def get_nav(prefix: str, num: int) -> tuple[str, str]:
    """Return (prev_link_html, next_link_html) for navigation arrows."""
    seq = build_full_sequence()

    current_idx = None
    for i, (p, _a, _c, n) in enumerate(seq):
        if p == prefix and n == num:
            current_idx = i
            break

    if current_idx is None:
        return ('<span class="nav-arrow"></span>', '<span class="nav-arrow"></span>')

    if current_idx == 0:
        prev_html = '<span class="nav-arrow"></span>'
    else:
        pp, pa, _pc, pn = seq[current_idx - 1]
        prev_file = f"{pp}_{pn:02d}"
        prev_label = f"{pa} {int_to_roman(pn)}"
        prev_html = (
            f'<a class="nav-arrow" href="{prev_file}.html">\u2190 {prev_label}</a>'
        )

    if current_idx == len(seq) - 1:
        next_html = '<span class="nav-arrow"></span>'
    else:
        np, na, _nc, nn = seq[current_idx + 1]
        next_file = f"{np}_{nn:02d}"
        next_label = f"{na} {int_to_roman(nn)}"
        next_html = (
            f'<a class="nav-arrow" href="{next_file}.html">{next_label} \u2192</a>'
        )

    return prev_html, next_html


def render_canto(
    json_path: Path,
    env: Environment,
    check: bool = False,
    out_dir: Path | None = None,
    css_path: str = "../dante-theme.css",
) -> bool:
    """Render a single canto. Returns True if changes were made/detected."""
    with open(json_path) as f:
        data = json.load(f)

    canto_num = data["canto_num"]
    canto_label = data["canto"]

    stem = json_path.stem
    prefix = stem.split("_")[0]

    cantica_full = {
        "inf": "Inferno",
        "purg": "Purgatorio",
        "par": "Paradiso",
    }[prefix]

    links, nodes, styles = build_canto_data(data, cantica=cantica_full)
    prev_link, next_link = get_nav(prefix, canto_num)

    template = env.get_template("canto.html.j2")
    html = template.render(
        theme_class=THEME_CLASS[cantica_full],
        title=canto_label,
        h1=f"{cantica_full} {int_to_roman(canto_num)}",
        prev_link=prev_link,
        next_link=next_link,
        links_data=format_links_data(links),
        nodes_raw=format_nodes_raw(nodes),
        author_styles=format_author_styles(styles),
        current_file=stem,
        css_path=css_path,
    )

    target = out_dir if out_dir else HTML_DIR
    out_path = target / f"{stem}.html"

    if check:
        if out_path.exists():
            existing = out_path.read_text()
            if existing == html:
                return False
            else:
                print(f"  DIFF: {stem}.html")
                return True
        else:
            print(f"  NEW:  {stem}.html")
            return True

    target.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    print(f"  rendered {stem}.html")
    return True


def render_index(
    env: Environment,
    out_dir: Path | None = None,
    css_path: str = "../dante-theme.css",
) -> None:
    """Generate index.html with navigation hub and progress tracking."""
    seq = build_full_sequence()
    target = out_dir if out_dir else HTML_DIR
    cantos = []
    for prefix, abbrev, cantica, num in seq:
        stem = f"{prefix}_{num:02d}"
        json_exists = (JSON_DIR / f"{stem}.json").exists()
        html_exists = (target / f"{stem}.html").exists()
        conn_count = 0
        if json_exists:
            with open(JSON_DIR / f"{stem}.json") as f:
                data = json.load(f)
            conn_count = len(data["connections"])
        cantos.append(
            {
                "stem": stem,
                "label": f"{abbrev} {int_to_roman(num)}",
                "cantica": cantica,
                "json_exists": json_exists,
                "html_exists": html_exists,
                "conn_count": conn_count,
            }
        )

    template = env.get_template("index.html.j2")
    html = template.render(
        cantos=cantos,
        cantica_list=CANTICA_SEQUENCE,
        css_path=css_path,
    )
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / "index.html"
    out_path.write_text(html)
    print("  rendered index.html")


def build_dist(env: Environment) -> int:
    """Build flat site into dist/ for deployment."""
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()

    # Copy CSS
    shutil.copy2(ROOT / "dante-theme.css", dist_dir / "dante-theme.css")

    # Render all cantos into dist/ with flat CSS path
    json_files = sorted(
        f for f in JSON_DIR.glob("*.json") if f.name != "canto.schema.json"
    )
    for path in json_files:
        render_canto(path, env, out_dir=dist_dir, css_path="dante-theme.css")

    # Render index
    render_index(env, out_dir=dist_dir, css_path="dante-theme.css")

    print(f"\nBuilt {len(json_files) + 1} files into dist/")
    return 0


def main() -> int:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )

    args = sys.argv[1:]

    if "--dist" in args:
        return build_dist(env)

    if "--index" in args:
        render_index(env)
        return 0

    check = "--check" in args
    args = [a for a in args if a != "--check"]

    if args:
        json_files = []
        for arg in args:
            stem = arg.removesuffix(".json").removesuffix(".html")
            path = JSON_DIR / f"{stem}.json"
            if not path.exists():
                print(f"File not found: {path}", file=sys.stderr)
                return 2
            json_files.append(path)
    else:
        json_files = sorted(
            f for f in JSON_DIR.glob("*.json") if f.name != "canto.schema.json"
        )

    if not json_files:
        print("No JSON files found in", JSON_DIR)
        return 1

    changed = 0
    for path in json_files:
        try:
            if render_canto(path, env, check=check):
                changed += 1
        except Exception as e:
            print(f"  ERROR {path.name}: {e}", file=sys.stderr)
            return 1

    if check:
        if changed:
            print(f"\n{changed} file(s) differ from rendered output.")
            return 1
        else:
            print(f"\nOK: {len(json_files)} file(s) match rendered output.")
            return 0

    print(f"\nRendered {len(json_files)} file(s), {changed} changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
