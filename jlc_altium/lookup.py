"""Search and BOM checks against the downloaded JLCPCB data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import categorize, source
from .altium_csv import column, designators, lcsc_column, read_table
from .build import TABLES, jlc_type, unit_price


def find(raw: Path, codes: set[str]) -> dict[str, dict]:
    """Look up specific LCSC codes in the raw source."""
    found = {}
    for part in source.read(raw, codes=codes):
        if part["lcsc"] in codes:
            found[part["lcsc"]] = part
            if len(found) == len(codes):
                break
    return found


def search(raw: Path, terms: list[str], basic_only: bool = False, limit: int = 30) -> list[dict]:
    hits = []
    # The SQL prefilter covers the same columns, so it only narrows the scan.
    rows = source.read(raw, terms=terms[:1])
    terms = [t.lower() for t in terms]
    for part in rows:
        if basic_only and not (part["basic"] or part["preferred"]):
            continue
        text = " ".join((part["lcsc"], part["mfr"], part["package"], part["description"],
                         part["manufacturer"], part["subcategory"])).lower()
        if all(t in text for t in terms):
            hits.append(part)
    # Basic first, then preferred, then by stock.
    hits.sort(key=lambda p: (not p["basic"], not p["preferred"], -p["stock"]))
    return hits[:limit]


def alternatives(db: Path, part: dict, limit: int = 3) -> list[dict]:
    """Basic/preferred parts in the Altium database with the same value and size."""
    hit = categorize.classify(part)
    if not hit or not db.exists():
        return []
    fam, size = hit
    value = categorize.fields(fam, part)[categorize.VALUE_FIELD[fam]]
    if not value:
        return []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        f'SELECT * FROM "{TABLES[fam]}" WHERE "Package" = ? AND "Value" = ? '
        f'AND "JLCPCB Type" != \'Extended\' ORDER BY "JLCPCB Type", "Stock" DESC LIMIT ?',
        (size, value, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def check_bom(bom_path: Path, raw: Path, db: Path, boards: int = 1) -> list[dict]:
    rows = read_table(bom_path)
    des_col = column(rows[0], "Designator")
    code_col = lcsc_column(rows)
    report = []
    entries = []
    for r in rows:
        refs = designators(r[des_col]) if des_col else []
        code = r[code_col].strip().upper() if code_col else ""
        entries.append((code, refs, r))

    data = find(raw, {c for c, _, _ in entries if c})
    for code, refs, r in entries:
        need = len(refs) * boards
        item = {"lcsc": code or "-", "designators": ",".join(refs), "need": need,
                "type": "", "stock": "", "status": "", "alternatives": ""}
        if not code:
            item["status"] = "NO LCSC CODE"
        elif code not in data:
            item["status"] = "NOT FOUND (out of stock, discontinued, or not in this data source)"
        else:
            p = data[code]
            item["type"] = jlc_type(p)
            item["stock"] = p["stock"]
            if p["stock"] < need:
                item["status"] = "LOW STOCK"
            else:
                item["status"] = "OK"
            if item["type"] == "Extended":
                alts = alternatives(db, p)
                item["alternatives"] = " ".join(f"{a['LCSC']}({a['JLCPCB Type']})" for a in alts)
        report.append(item)
    return report


TSV_COLUMNS = ["LCSC", "Type", "Stock", "Package", "Manufacturer Part Number",
               "Manufacturer", "Price", "Description"]


def write_tsv(path: Path, hits: list[dict], note: str = "") -> None:
    """Search results for the Altium part picker: one tab-separated row per part.

    The first line is a note shown above the results (e.g. which data was
    searched); tabs and newlines inside fields are replaced so every row
    splits cleanly in DelphiScript.
    """
    def clean(v) -> str:
        return " ".join(str(v).split())

    lines = [clean(note), "\t".join(TSV_COLUMNS)]
    for p in hits:
        lines.append("\t".join(clean(v) for v in (
            p["lcsc"], jlc_type(p), p["stock"], p["package"], p["mfr"], p["manufacturer"],
            unit_price(p["price"], 1), p["description"])))
    # BOM so Delphi's TStringList.LoadFromFile reads it as UTF-8 (Ω, µ, ±).
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
