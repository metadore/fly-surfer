"""Shared paths and helpers for the FLY-SURFER research-paper build.

Read-only with respect to the FLY-SURFER repository: every path below points at
an existing artifact or record; nothing outside ``research_paper/`` is written.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # C:/Users/Hp/fruitfly/FLY-SURFER
PAPER = ROOT / "research_paper"
FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"


def load_json(relpath: str):
    with open(ROOT / relpath, encoding="utf-8") as fh:
        return json.load(fh)


def load_jsonl(relpath: str):
    rows = []
    with open(ROOT / relpath, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(name: str, header, rows):
    """Write a UTF-8 (BOM) CSV under research_paper/tables/."""
    import csv

    path = TABLES / name
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path
