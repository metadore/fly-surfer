"""Assemble the Markdown manuscript and its generated front matter.

Concatenates ``research_paper/src/*.md`` in filename order, expands the three
placeholders in the front matter (``[[TOC]]``, ``[[LOF]]``, ``[[LOT]]``), and
writes ``research_paper/FLY_SURFER_COMPLETE_RESEARCH_PAPER.md``. Every value in
the generated lists is read from the source chapter files; nothing is written
outside ``research_paper/``.
"""

from __future__ import annotations

import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
SRC = PAPER / "src"
OUT = PAPER / "FLY_SURFER_COMPLETE_RESEARCH_PAPER.md"

FIGURE_RE = re.compile(r"^!\[(Figure (\d+)\..*?)\]\((figures/[^)]+)\)\s*$", re.S)
TABLE_RE = re.compile(r"^\*\*(Table ([0-9]+|[A-K][0-9]+)\.)\*\* (.*)$")


def short_title(text: str, limit: int = 130) -> str:
    """First sentence of a caption, trimmed to a browsable length."""
    text = " ".join(text.split())
    match = re.match(r"(.+?[.!?])(\s|$)", text)
    sentence = match.group(1) if match else text
    if len(sentence) > limit:
        cut = sentence[:limit].rsplit(" ", 1)[0]
        sentence = cut.rstrip(",;:") + " …"
    return sentence


def read_sources() -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(SRC.glob("*.md"))]


def build_toc(chapters: list[str]) -> str:
    lines = []
    for heading in chapters:
        if heading.startswith("# "):
            lines.append(f"- **{heading[2:].strip()}**")
        else:
            lines.append(f"    - {heading[3:].strip()}")
    return "\n".join(lines)


def collect_figures(sources):
    figures = []
    for _, text in sources:
        for line in text.splitlines():
            m = FIGURE_RE.match(line)
            if m:
                figures.append((int(m.group(2)), short_title(m.group(1)[len(f"Figure {m.group(2)}. "):], 110), m.group(3)))
    figures.sort(key=lambda row: row[0])
    assert [f[0] for f in figures] == list(range(1, len(figures) + 1)), "figure numbering gap"
    return figures


def collect_tables(sources):
    main, appendix = [], []
    for _, text in sources:
        for line in text.splitlines():
            m = TABLE_RE.match(line)
            if not m:
                continue
            label, number, body = m.group(1), m.group(2), m.group(3)
            entry = (number, short_title(body, 110), label)
            (main if number.isdigit() else appendix).append(entry)
    main.sort(key=lambda r: int(r[0]))
    appendix.sort(key=lambda r: (r[0][0], int(r[0][1:])))
    return main, appendix


def main() -> None:
    sources = read_sources()

    chapters = []
    for name, text in sources:
        for line in text.splitlines():
            if re.match(r"^#{1,2} (Chapter \d|[0-9]+\.[0-9]+ |[A-K]\.[0-9]+ |Abstract|Abbreviations|Table of contents|List of figures|List of tables|Appendix )", line):
                if "Table of contents" in line or "List of figures" in line or "List of tables" in line:
                    continue
                chapters.append(line)

    figures = collect_figures(sources)
    tables_main, tables_appendix = collect_tables(sources)

    lof = [f"| Figure {n} | {title} | `{path}` |" for n, title, path in figures]
    lot = [f"| {label} | {title} |" for _, title, label in tables_main]
    lot += [f"| {label} | {title} |" for _, title, label in tables_appendix]

    toc = build_toc(chapters)
    lof_md = "\n".join(["| Figure | Caption (short) | Image file |", "|---|---|---|"] + lof)
    lot_md = "\n".join(["| Table | Caption (short) |", "|---|---|"] + lot)

    body = "\n\n".join(text.rstrip() for _, text in sources)
    body = body.replace("[[TOC]]", toc)
    body = body.replace("[[LOF]]", lof_md)
    body = body.replace("[[LOT]]", lot_md)
    if "[[" in body:
        raise SystemExit("unexpanded placeholder remains")

    OUT.write_text(body + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(body.splitlines())} lines)")
    print(f"chapters/sections in TOC: {len(chapters)}; figures: {len(figures)}; tables: {len(tables_main)} main + {len(tables_appendix)} appendix")


if __name__ == "__main__":
    main()
