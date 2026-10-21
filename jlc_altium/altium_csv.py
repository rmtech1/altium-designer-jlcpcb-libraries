"""Readers for Altium's BOM and Pick & Place CSV outputs.

Altium puts a free-form preamble above the header row in Pick & Place files
and lets the user choose the columns in both outputs, so the header row is
located by content and columns are looked up by a list of accepted names.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

LCSC_RE = re.compile(r"^C\d{3,}$", re.I)
LCSC_COLUMNS = ("LCSC", "LCSC Part", "LCSC Part #", "LCSC Part Number", "JLCPCB Part Number",
                "JLCPCB Part #", "JLC", "Part Number")


def _read_text(path: Path) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def read_table(path: Path) -> list[dict]:
    """Rows of the first table in path whose header contains 'Designator'."""
    lines = _read_text(path).splitlines()
    for i, line in enumerate(lines):
        if "designator" in line.lower():
            reader = csv.DictReader(io.StringIO("\n".join(lines[i:])))
            rows = []
            for r in reader:
                r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
                if any(r.values()):
                    rows.append(r)
            return rows
    raise SystemExit(f"{path}: no header row with a 'Designator' column found")


def column(row: dict, *names: str) -> str | None:
    """The first matching column name in row (case-insensitive), or None."""
    lower = {k.lower(): k for k in row}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


def lcsc_column(rows: list[dict]) -> str | None:
    if not rows:
        return None
    for name in LCSC_COLUMNS:
        col = column(rows[0], name)
        if col and any(LCSC_RE.match(r[col]) for r in rows):
            return col
    return None


def designators(value: str) -> list[str]:
    return [d for d in re.split(r"[,\s;]+", value) if d]
