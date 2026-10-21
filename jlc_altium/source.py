"""Readers for the upstream JLCPCB parts dumps.

Both readers yield the same normalised dict per part:

    lcsc, mfr, manufacturer, package, description, datasheet, stock,
    basic, preferred, price (list of tiers), category, subcategory,
    attributes (dict)

The SQLite reader understands the yaqwsx/jlcparts schema (also used by the
CDFER database): components + manufacturers + categories, with `price` and
`extra` stored as JSON text. Column lookups are defensive because those
projects add columns over time.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterator


def lcsc_code(value) -> str:
    s = str(value).strip().upper()
    if not s:
        return ""
    return s if s.startswith("C") else f"C{s}"


def _json(value):
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _truthy(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def _int(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _manufacturer_from_extra(extra: dict | None) -> str:
    if not extra:
        return ""
    m = extra.get("manufacturer")
    if isinstance(m, dict):
        return m.get("en") or m.get("name") or m.get("abbr") or ""
    return m or ""


def _category_from_extra(extra: dict | None) -> tuple[str, str]:
    if not extra:
        return "", ""
    c = extra.get("category")
    if isinstance(c, dict):
        return c.get("name1", "") or "", c.get("name2", "") or ""
    return "", ""


def _attributes(extra: dict | None) -> dict:
    if not extra:
        return {}
    attrs = extra.get("attributes")
    if isinstance(attrs, dict):
        return {str(k): str(v) for k, v in attrs.items() if v not in (None, "", "-")}
    return {}


def _normalise(row: dict) -> dict:
    extra = _json(row.get("extra"))
    if not isinstance(extra, dict):
        extra = None
    category, subcategory = row.get("category") or "", row.get("subcategory") or ""
    if not category:
        category, subcategory = _category_from_extra(extra)
    description = row.get("description") or ""
    if not description and extra:
        description = extra.get("description", "") or ""
    price = _json(row.get("price"))
    lib_type = str(row.get("library_type") or row.get("type") or "").lower()
    return {
        "lcsc": lcsc_code(row.get("lcsc", "")),
        "mfr": row.get("mfr") or "",
        "manufacturer": row.get("manufacturer") or _manufacturer_from_extra(extra),
        "package": row.get("package") or "",
        "description": description,
        "datasheet": row.get("datasheet") or "",
        "stock": _int(row.get("stock")),
        "basic": _truthy(row.get("basic")) or lib_type in ("base", "basic"),
        "preferred": _truthy(row.get("preferred")) or lib_type == "preferred",
        "price": price if isinstance(price, list) else [],
        "category": category,
        "subcategory": subcategory,
        "attributes": _attributes(extra),
    }


def read_sqlite(path: Path, min_stock: int = 0, codes: set[str] | None = None,
                terms: list[str] | None = None) -> Iterator[dict]:
    """Parts from a jlcparts-schema database.

    codes limits the result to those LCSC codes; terms to rows whose text
    columns contain every term. Both are applied in SQL so lookups in the
    1 GB database stay fast.
    """
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    table = next((t for t in ("components", "jlc_components") if t in tables), None)
    if table is None:
        raise SystemExit(f"{path}: no components table found (tables: {sorted(tables)})")
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}

    select = [f"c.{c}" for c in cols]
    joins = []
    if "manufacturer_id" in cols and "manufacturers" in tables:
        select.append("m.name AS manufacturer")
        joins.append("LEFT JOIN manufacturers m ON m.id = c.manufacturer_id")
    if "category_id" in cols and "categories" in tables:
        select += ["k.category AS category", "k.subcategory AS subcategory"]
        joins.append("LEFT JOIN categories k ON k.id = c.category_id")

    where, params = [], []
    if min_stock and "stock" in cols:
        keep = ["c.stock >= ?"]
        params.append(min_stock)
        keep += [f"c.{f} = 1" for f in ("basic", "preferred") if f in cols]
        where.append("(" + " OR ".join(keep) + ")")

    if codes is not None:
        nums = [int(c[1:]) for c in codes if c[1:].isdigit()] or [-1]
        where.append(f"c.lcsc IN ({', '.join('?' * len(nums))})")
        params += nums
    text_cols = [f"c.{c}" for c in ("lcsc", "mfr", "package", "description") if c in cols]
    text_cols += [c for c, j in (("m.name", "manufacturers m"), ("k.subcategory", "categories k"))
                  if any(j in x for x in joins)]
    for term in terms or []:
        where.append("(" + " OR ".join(f"{c} LIKE ?" for c in text_cols) + ")")
        params += [f"%{term}%"] * len(text_cols)

    sql = f"SELECT {', '.join(select)} FROM {table} c {' '.join(joins)}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    for row in con.execute(sql, params):
        yield _normalise(dict(row))
    con.close()


def read_csv(path: Path) -> Iterator[dict]:
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower().replace(" ", "_"): v for k, v in row.items() if k}
            yield _normalise(row)


def read(path: Path, min_stock: int = 0, codes: set[str] | None = None,
         terms: list[str] | None = None) -> Iterator[dict]:
    if path.suffix.lower() == ".csv":
        return read_csv(path)
    return read_sqlite(path, min_stock, codes, terms)
