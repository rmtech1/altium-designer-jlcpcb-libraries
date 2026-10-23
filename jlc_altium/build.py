"""Builds the SQLite database that Altium reads through the DbLib.

One table per generic family (Resistors, Capacitors, Inductors, Ferrite
Beads) plus a Custom table for parts linked in the overrides file. Column
names follow Altium's DbLib conventions so the field mapping is automatic:
"Library Ref"/"Library Path" pick the symbol, "Footprint Ref"/"Footprint
Path" the footprint, and every other column becomes a component parameter.

The database is written to a temp file and swapped in at the end, so Altium
never sees a half-built library.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import sqlite3
from pathlib import Path

from . import categorize
from .config import Config

TABLES = {
    "resistor": "Resistors",
    "capacitor": "Capacitors",
    "inductor": "Inductors",
    "ferrite": "Ferrite Beads",
}
CUSTOM_TABLE = "Custom"
# Filtered views, listed by Altium as extra libraries. File-based libraries
# get no filter pane in the Components panel, so common filters are built in.
BASIC_SUFFIX = " - Basic"


def all_tables() -> list[str]:
    """Every table and view Altium will list, in display order."""
    names = []
    for table in TABLES.values():
        names += [table, table + BASIC_SUFFIX]
    return names + [CUSTOM_TABLE]

COMMON_COLUMNS = [
    "Part Number", "Library Ref", "Library Path", "Footprint Ref", "Footprint Path",
    "Comment", "Description", "Value", "Package", "Manufacturer",
    "Manufacturer Part Number", "LCSC", "JLCPCB Type", "Stock", "Price",
    "Price @100", "Datasheet", "JLCPCB URL", "Updated",
]
# Columns kept from the previous build when an override part is missing from
# the current dump (e.g. an extended part while using the basic-only source).
CARRY_OVER = ["Description", "Package", "Manufacturer", "Manufacturer Part Number",
              "JLCPCB Type", "Price", "Price @100", "Datasheet"]

OVERRIDE_COLUMNS = ["LCSC", "Library Ref", "Library Path", "Footprint Ref",
                    "Footprint Path", "Comment", "Value"]


def unit_price(tiers: list, qty: int) -> str:
    for t in tiers:
        lo, hi = t.get("qFrom") or 0, t.get("qTo")
        if lo <= qty and (hi is None or qty <= hi):
            return f"${t.get('price', 0):.4f}"
    return ""


def jlc_type(part: dict) -> str:
    if part["basic"]:
        return "Basic"
    if part["preferred"]:
        return "Preferred"
    return "Extended"


def common_row(part: dict, today: str) -> dict:
    return {
        "Part Number": part["lcsc"],
        "Description": part["description"],
        "Package": part["package"],
        "Manufacturer": part["manufacturer"],
        "Manufacturer Part Number": part["mfr"],
        "LCSC": part["lcsc"],
        "JLCPCB Type": jlc_type(part),
        "Stock": part["stock"],
        "Price": unit_price(part["price"], 1),
        "Price @100": unit_price(part["price"], 100),
        "Datasheet": part["datasheet"],
        "JLCPCB URL": f"https://jlcpcb.com/partdetail/{part['lcsc']}",
        "Updated": today,
    }


def generic_row(part: dict, fam: str, size: str, cfg: Config, today: str) -> dict:
    sym, fp = cfg.section("symbols"), cfg.section("footprints")
    values = categorize.fields(fam, part)
    value = values[categorize.VALUE_FIELD[fam]]
    row = common_row(part, today)
    row.update({
        "Library Ref": sym.get(fam, fam.title()),
        "Library Path": sym.get("library", ""),
        "Footprint Ref": f"{fp.get(fam, fam.upper())}-{size}",
        "Footprint Path": fp.get("library", ""),
        "Comment": value or part["mfr"],
        "Value": value,
        "Package": size,
    })
    row.update(values)
    return row


def read_overrides(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("LCSC") or "").strip()]
    for r in rows:
        r["LCSC"] = r["LCSC"].strip().upper()
    return rows


def _previous_rows(db: Path, table: str) -> dict[str, dict]:
    if not db.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = {r["LCSC"]: dict(r) for r in con.execute(f'SELECT * FROM "{table}"')}
        con.close()
        return rows
    except sqlite3.Error:
        return {}


def _create_table(con: sqlite3.Connection, name: str, columns: list[str]) -> None:
    defs = []
    for c in columns:
        kind = "INTEGER" if c == "Stock" else "TEXT"
        pk = " PRIMARY KEY" if c == "Part Number" else ""
        defs.append(f'"{c}" {kind}{pk}')
    con.execute(f'CREATE TABLE "{name}" ({", ".join(defs)})')


def _insert(con: sqlite3.Connection, name: str, columns: list[str], rows: list[dict]) -> None:
    sql = (f'INSERT OR REPLACE INTO "{name}" ({", ".join(f"{chr(34)}{c}{chr(34)}" for c in columns)}) '
           f'VALUES ({", ".join("?" * len(columns))})')
    con.executemany(sql, ([r.get(c, "") for c in columns] for r in rows))


def build(parts, cfg: Config, today: str | None = None) -> dict[str, int]:
    """Write the Altium database from an iterable of normalised parts."""
    today = today or dt.date.today().isoformat()
    flt = cfg.section("filter")
    min_stock = int(flt.get("min_stock_extended", 0))
    include_extended = bool(flt.get("include_extended", True))

    overrides = {r["LCSC"]: r for r in read_overrides(cfg.overrides_path)}
    generic: dict[str, list[dict]] = {f: [] for f in TABLES}
    found: dict[str, dict] = {}

    for part in parts:
        if not part["lcsc"]:
            continue
        if part["lcsc"] in overrides:
            found[part["lcsc"]] = part
        if not (part["basic"] or part["preferred"]):
            if not include_extended or part["stock"] < min_stock:
                continue
        hit = categorize.classify(part)
        if hit:
            fam, size = hit
            generic[fam].append(generic_row(part, fam, size, cfg, today))

    db = cfg.database_path
    previous = _previous_rows(db, CUSTOM_TABLE)
    custom = []
    for lcsc, o in overrides.items():
        if lcsc in found:
            row = common_row(found[lcsc], today)
        else:
            row = {c: previous.get(lcsc, {}).get(c, "") for c in CARRY_OVER}
            row.update({"Part Number": lcsc, "LCSC": lcsc, "Stock": 0,
                        "JLCPCB URL": f"https://jlcpcb.com/partdetail/{lcsc}",
                        "Updated": previous.get(lcsc, {}).get("Updated", "")})
            row["Description"] = row["Description"] or "(not in current JLCPCB data)"
        row.update({k: o.get(k, "") for k in OVERRIDE_COLUMNS[1:]})
        row["Comment"] = row["Comment"] or row.get("Value") or row.get("Manufacturer Part Number") or lcsc
        custom.append(row)

    db.parent.mkdir(parents=True, exist_ok=True)
    tmp = db.with_name(db.name + ".new")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    counts = {}
    for fam, table in TABLES.items():
        columns = COMMON_COLUMNS + [f[0] for f in categorize.FIELDS[fam]]
        _create_table(con, table, columns)
        rows = sorted(generic[fam], key=lambda r: (r["Package"], r["JLCPCB Type"] == "Extended", r["Value"]))
        _insert(con, table, columns, rows)
        counts[table] = len(rows)
    _create_table(con, CUSTOM_TABLE, COMMON_COLUMNS)
    _insert(con, CUSTOM_TABLE, COMMON_COLUMNS, custom)
    counts[CUSTOM_TABLE] = len(custom)
    for table in TABLES.values():
        con.execute(f'CREATE VIEW "{table}{BASIC_SUFFIX}" AS SELECT * FROM "{table}" '
                    f'WHERE "JLCPCB Type" != \'Extended\'')

    # The build date goes in the header rather than a table: Altium lists
    # every table in the database as a library.
    con.execute(f"PRAGMA user_version = {int(today.replace('-', ''))}")
    con.commit()
    con.execute("VACUUM")
    con.close()

    try:
        os.replace(tmp, db)
    except PermissionError:
        # Windows will not replace a file Altium's ODBC driver has open. Copy
        # the tables into the live database in one transaction instead;
        # Altium sees either the old or the new data, never a mix.
        _copy_into(tmp, db)
        tmp.unlink(missing_ok=True)
    return counts


def _copy_into(src: Path, dest: Path) -> None:
    con = sqlite3.connect(dest, timeout=120, isolation_level=None)
    con.execute("ATTACH DATABASE ? AS new", (str(src),))
    con.execute("BEGIN IMMEDIATE")
    try:
        for name, kind in con.execute(
                "SELECT name, type FROM main.sqlite_master WHERE type IN ('view', 'table') "
                "ORDER BY type = 'table'").fetchall():
            con.execute(f'DROP {kind.upper()} main."{name}"')
        objects = con.execute("SELECT name, type, sql FROM new.sqlite_master "
                              "WHERE type IN ('table', 'view') ORDER BY type = 'view'").fetchall()
        for name, kind, sql in objects:
            con.execute(sql)
            if kind == "table":
                con.execute(f'INSERT INTO main."{name}" SELECT * FROM new."{name}"')
        version = con.execute("PRAGMA new.user_version").fetchone()[0]
        con.execute(f"PRAGMA main.user_version = {int(version)}")
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    finally:
        con.execute("DETACH DATABASE new")
        con.close()
