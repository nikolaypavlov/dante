#!/usr/bin/env python3
"""Render canto JSON files to self-contained HTML visualizations.

Usage:
    uv run scripts/render_html.py              # render all json/*.json
    uv run scripts/render_html.py inf_01       # render single canto
    uv run scripts/render_html.py --check      # dry-run, report diffs
    uv run scripts/render_html.py --index      # generate html/index.html
    uv run scripts/render_html.py --dist       # build flat site into dist/
"""

import json
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "json"
HTML_DIR = ROOT / "html"
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"

CANTICA_SEQUENCE = [
    ("Inferno", "inf", "Inf.", 34),
    ("Purgatorio", "purg", "Purg.", 33),
    ("Paradiso", "par", "Par.", 33),
]

CANTICA_SLUG = {"Inferno": "inferno", "Purgatorio": "purgatorio", "Paradiso": "paradiso"}

CANTICA_LAT = {
    "Inferno": "Cantica Prima",
    "Purgatorio": "Cantica Secunda",
    "Paradiso": "Cantica Tertia",
}

PREFIX_TO_CANTICA = {"inf": "Inferno", "purg": "Purgatorio", "par": "Paradiso"}

# Author -> short icon/monogram used in card headers
AUTHOR_ICON = {
    "\u0412\u0435\u0440\u0433\u0456\u043b\u0456\u0439": "V",
    "\u041e\u0432\u0456\u0434\u0456\u0439": "O",
    "\u041b\u0443\u043a\u0430\u043d": "L",
    "\u0421\u0442\u0430\u0446\u0456\u0439": "S",
    "\u0426\u0438\u0446\u0435\u0440\u043e\u043d": "C",
    "\u0413\u043e\u0440\u0430\u0446\u0456\u0439": "H",
    "\u0421\u0435\u043d\u0435\u043a\u0430": "Sn",
    "\u0411\u0456\u0431\u043b\u0456\u044f": "\u271d",
    "\u041c\u0430\u043a\u0440\u043e\u0431\u0456\u0439": "M",
    "\u0411\u043e\u0435\u0446\u0456\u0439": "B",
    "\u0410\u0432\u0491\u0443\u0441\u0442\u0438\u043d": "A",
    "\u0406\u0441\u0438\u0434\u043e\u0440": "I",
    "\u0411\u0440\u0443\u043d\u0435\u0442\u0442\u043e \u041b\u0430\u0442\u0456\u043d\u0456": "Br",
    "\u0424\u043e\u043c\u0430 \u0410\u043a\u0432\u0456\u043d\u0441\u044c\u043a\u0438\u0439": "T",
    "\u0413\u043e\u043d\u043e\u0440\u0456\u0439 \u0410\u0432\u0491\u0443\u0441\u0442\u043e\u0434\u0443\u043d\u0441\u044c\u043a\u0438\u0439": "Hn",
    "\u041f\u0441\u0435\u0432\u0434\u043e-\u0414\u0456\u043a\u0442\u0438\u0441": "D",
    "\u041f\u0441\u0435\u0432\u0434\u043e-\u0414\u0456\u043e\u043d\u0456\u0441\u0456\u0439": "Dn",
    "\u0411\u043e\u043d\u0430\u0432\u0435\u043d\u0442\u0443\u0440\u0430": "Bn",
    "\u0411\u0435\u0440\u043d\u0430\u0440\u0434 \u041a\u043b\u0435\u0440\u0432\u043e\u0441\u044c\u043a\u0438\u0439": "Be",
    "\u0410\u043d\u0441\u0435\u043b\u044c\u043c": "An",
    "\u0413\u0443\u0433\u043e \u0421\u0435\u043d-\u0412\u0456\u043a\u0442\u043e\u0440\u0441\u044c\u043a\u0438\u0439": "Hg",
    "\u0413\u043e\u043c\u0435\u0440": "\u1f49",
    "\u041f\u043b\u0430\u0442\u043e\u043d": "\u03a0",
    "\u041f\u043b\u043e\u0442\u0456\u043d": "\u03a0\u03bb",
    "\u0410\u0440\u0438\u0441\u0442\u043e\u0442\u0435\u043b\u044c": "\u0391",
}

# Frontispicia content per cantica
FRONTISPICIA = {
    "inferno": {
        "cantica_name": "Inferno",
        "ordinal": "Cantica Prima",
        "rubric_band": "Incipit cantica prima \u00b7 De inferno",
        "incipit": (
            "Nel mezzo del cammin di nostra vita<br/>"
            "mi ritrovai per una selva oscura,<br/>"
            "ch&eacute; la diritta via era smarrita."
        ),
        "incipit_ua": (
            "\u041d\u0430 \u043f\u0456\u0432\u0448\u043b\u044f\u0445\u0443 "
            "\u0436\u0438\u0442\u0442\u044f \u0437\u0435\u043c\u043d\u043e\u0433\u043e "
            "\u043d\u0430\u0448\u043e\u0433\u043e<br/>"
            "\u044f \u043e\u043f\u0438\u043d\u0438\u0432\u0441\u044c \u0443 "
            "\u0442\u0435\u043c\u043d\u0456\u0439 \u043f\u0443\u0449\u0456, "
            "\u0431\u043e \u0432\u0442\u0440\u0430\u0442\u0438\u0432<br/>"
            "\u043f\u0443\u0442\u044c \u043f\u0440\u044f\u043c\u0443\u044e."
        ),
        "setting": (
            "Silva obscura <span class=\"star\">\u2726</span> Nox "
            "<span class=\"star\">\u2726</span> Feriae sanctae MCCC"
        ),
        "foliation": "fol. i \u00b7 recto",
    },
    "purgatorio": {
        "cantica_name": "Purgatorio",
        "ordinal": "Cantica Secunda",
        "rubric_band": "Incipit cantica secunda \u00b7 De purgatorio",
        "incipit": (
            "Per correr miglior acque alza le vele<br/>"
            "omai la navicella del mio ingegno,<br/>"
            "che lascia dietro a s&eacute; mar s&igrave; crudele."
        ),
        "incipit_ua": (
            "\u0429\u043e\u0431 \u043f\u0435\u0440\u0435\u0431\u0456\u0433\u0442\u0438 "
            "\u0432\u043e\u0434\u0438 \u043a\u0440\u0430\u0449\u0456, "
            "\u0437\u0434\u0456\u0439\u043c\u0430\u0454 \u0432\u0456\u0442\u0440\u0438\u043b\u0430<br/>"
            "\u043d\u0438\u043d\u0456 \u043a\u043e\u0440\u0430\u0431\u043b\u0438\u043a "
            "\u043c\u043e\u0433\u043e \u043c\u0438\u0441\u0442\u0435\u0446\u0442\u0432\u0430,<br/>"
            "\u044f\u043a\u0438\u0439 \u043b\u0438\u0448\u0430\u0454 \u043f\u043e\u0437\u0430\u0434 "
            "\u0441\u0435\u0431\u0435 \u0442\u0430\u043a\u0435 "
            "\u0436\u043e\u0440\u0441\u0442\u043e\u043a\u0435 \u043c\u043e\u0440\u0435."
        ),
        "setting": (
            "Insula Purgatorii <span class=\"star\">\u2726</span> Aurora "
            "<span class=\"star\">\u2726</span> Dies paschae MCCC"
        ),
        "foliation": "fol. lxviii \u00b7 recto",
    },
    "paradiso": {
        "cantica_name": "Paradiso",
        "ordinal": "Cantica Tertia",
        "rubric_band": "Incipit cantica tertia \u00b7 De paradiso",
        "incipit": (
            "La gloria di colui che tutto move<br/>"
            "per l'universo penetra, e risplende<br/>"
            "in una parte pi&ugrave; e meno altrove."
        ),
        "incipit_ua": (
            "\u0421\u043b\u0430\u0432\u0430 \u0442\u043e\u0433\u043e, \u0445\u0442\u043e "
            "\u0432\u0441\u0435 \u0440\u0443\u0448\u0438\u0442\u044c,<br/>"
            "\u043f\u0440\u043e\u043d\u0438\u0437\u0443\u0454 \u0432\u0435\u0441\u044c "
            "\u0432\u0441\u0435\u0441\u0432\u0456\u0442 \u0456 \u0441\u044f\u0454<br/>"
            "\u043f\u043e\u0434\u0435\u043a\u0443\u0434\u0438 \u0441\u0438\u043b\u044c\u043d\u0456\u0448\u0435, "
            "\u043f\u043e\u0434\u0435\u043a\u0443\u0434\u0438 \u0441\u043b\u0430\u0431\u0448\u0435."
        ),
        "setting": (
            "Coeli novem <span class=\"star\">\u2726</span> Empyreum "
            "<span class=\"star\">\u2726</span> In die paschae"
        ),
        "foliation": "fol. cxxxiv \u00b7 recto",
    },
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


def icon_for(author: str) -> str:
    return AUTHOR_ICON.get(author, author[:2])


def weight_of(confidence: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2}.get(confidence, 1)


def from_json(conns: list) -> list:
    """Convert raw JSON connections into tier-split source records.

    Chain semantics:
        source_author / source_ref = PRIMARY/ORIGINAL source (col 3).
        chain[] = intermediaries that Dante actually read (col 2).
    When chain is null: emit one 'direct' record (Dante read the source).
    When chain is non-empty: emit one 'primary' + one 'direct' per chain item.
    Intermediaries link to their primary via `transmits`.
    """
    out: list[dict] = []
    for c in conns:
        base_weight = weight_of(c["confidence"])
        chain = c.get("chain") or []
        if not chain:
            out.append(
                {
                    "id": c["id"],
                    "tier": "direct",
                    "author": c["source_author"],
                    "work": c["source_ref"],
                    "icon": icon_for(c["source_author"]),
                    "type": c["type"],
                    "weight": base_weight,
                    "lineDante": c["dante_ref"],
                    "lineSource": c["source_ref"],
                    "quoteLat": c["source_sub"],
                    "quoteUa": c["desc_source"],
                    "note": c["desc_dante"],
                    "transmits": None,
                }
            )
        else:
            primary_id = c["id"] + "_primary"
            out.append(
                {
                    "id": primary_id,
                    "tier": "primary",
                    "author": c["source_author"],
                    "work": c["source_ref"],
                    "icon": icon_for(c["source_author"]),
                    "type": c["type"],
                    "weight": base_weight,
                    "lineDante": c["dante_ref"],
                    "lineSource": c["source_ref"],
                    "quoteLat": c["source_sub"],
                    "quoteUa": c["desc_source"],
                    "note": c["desc_dante"],
                    "transmits": None,
                }
            )
            for i, ch in enumerate(chain):
                out.append(
                    {
                        "id": f"{c['id']}_inter_{i}",
                        "tier": "direct",
                        "author": ch["author"],
                        "work": ch["ref"],
                        "icon": icon_for(ch["author"]),
                        "type": c["type"],
                        "weight": base_weight,
                        "lineDante": c["dante_ref"],
                        "lineSource": ch["ref"],
                        "quoteLat": ch["sub"],
                        "quoteUa": ch["desc"],
                        "note": c["desc_dante"],
                        "transmits": primary_id,
                    }
                )
    return out


def build_canto_payload(data: dict, canto_num: int, cantica_full: str) -> dict:
    """Build the JSON payload injected as window.CANTO."""
    roman = int_to_roman(canto_num)
    slug = CANTICA_SLUG[cantica_full]
    return {
        "id": f"{slug}-{roman.lower()}",
        "cantica": cantica_full,
        "cantoRoman": roman,
        "cantoArabic": canto_num,
        "foliation": data.get("foliation") or f"fol. {roman.lower()}\u00b7r",
        "titleUa": data.get("title_ua", ""),
        "subtitleUa": data.get("subtitle_ua", ""),
        "summaryUa": data.get("summary_ua", ""),
        "verses": data.get("verses", ""),
        "sources": from_json(data["connections"]),
    }


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
    css_path: str = "../static/dante.css",
    js_path: str = "../static/render.js",
) -> bool:
    """Render a single canto. Returns True if changes were made/detected."""
    with open(json_path) as f:
        data = json.load(f)

    canto_num = data["canto_num"]
    canto_label = data["canto"]
    stem = json_path.stem
    prefix = stem.split("_")[0]
    cantica_full = PREFIX_TO_CANTICA[prefix]

    payload = build_canto_payload(data, canto_num, cantica_full)
    prev_link, next_link = get_nav(prefix, canto_num)

    template = env.get_template("canto.html.j2")
    html = template.render(
        cantica_slug=CANTICA_SLUG[cantica_full],
        cantica=cantica_full,
        canto_roman=int_to_roman(canto_num),
        kicker=f"Divina Commedia \u00b7 {CANTICA_LAT[cantica_full]}",
        subtitle_ua=payload["subtitleUa"],
        foliation=payload["foliation"],
        summary_ua=payload["summaryUa"],
        verses=payload["verses"],
        canto_json=json.dumps(payload, ensure_ascii=False),
        prev_link=prev_link,
        next_link=next_link,
        current_file=stem,
        title=canto_label,
        css_path=css_path,
        js_path=js_path,
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
    css_path: str = "../static/dante.css",
) -> None:
    """Generate index.html with 100-canto navigation grid + progress bar."""
    seq = build_full_sequence()
    target = out_dir if out_dir else HTML_DIR
    cantos = []
    total_conn = 0
    for prefix, abbrev, cantica, num in seq:
        stem = f"{prefix}_{num:02d}"
        json_exists = (JSON_DIR / f"{stem}.json").exists()
        html_exists = (target / f"{stem}.html").exists()
        conn_count = 0
        if json_exists:
            with open(JSON_DIR / f"{stem}.json") as f:
                data = json.load(f)
            conn_count = len(data["connections"])
            total_conn += conn_count
        cantos.append(
            {
                "stem": stem,
                "label": f"{abbrev} {int_to_roman(num)}",
                "roman": int_to_roman(num),
                "num": num,
                "cantica": cantica,
                "json_exists": json_exists,
                "html_exists": html_exists,
                "conn_count": conn_count,
            }
        )

    total = len(cantos)
    done = sum(1 for c in cantos if c["html_exists"])
    pct = round(done / total * 100) if total else 0

    template = env.get_template("index.html.j2")
    html = template.render(
        cantos=cantos,
        cantica_list=CANTICA_SEQUENCE,
        cantica_lat=CANTICA_LAT,
        css_path=css_path,
        done=done,
        total=total,
        pct=pct,
        total_conn=total_conn,
    )
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / "index.html"
    out_path.write_text(html)
    print("  rendered index.html")


def render_frontispicia(
    env: Environment,
    out_dir: Path | None = None,
    css_path: str = "../static/dante.css",
) -> None:
    """Render three per-cantica frontispicia HTML files."""
    target = out_dir if out_dir else HTML_DIR
    target.mkdir(parents=True, exist_ok=True)
    template = env.get_template("frontispicia.html.j2")
    for slug, fields in FRONTISPICIA.items():
        html = template.render(cantica=slug, css_path=css_path, **fields)
        out_path = target / f"frontispicia_{slug}.html"
        out_path.write_text(html)
        print(f"  rendered frontispicia_{slug}.html")


def build_dist(env: Environment) -> int:
    """Build flat site into dist/ for deployment."""
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()

    shutil.copy2(STATIC_DIR / "dante.css", dist_dir / "dante.css")
    shutil.copy2(STATIC_DIR / "render.js", dist_dir / "render.js")

    json_files = sorted(
        f for f in JSON_DIR.glob("*.json") if f.name != "canto.schema.json"
    )
    for path in json_files:
        render_canto(
            path,
            env,
            out_dir=dist_dir,
            css_path="dante.css",
            js_path="render.js",
        )

    render_index(env, out_dir=dist_dir, css_path="dante.css")
    render_frontispicia(env, out_dir=dist_dir, css_path="dante.css")

    print(f"\nBuilt {len(json_files) + 4} files into dist/")
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

    if "--frontispicia" in args:
        render_frontispicia(env)
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
