"""Turns Altium BOM + Pick & Place outputs into JLCPCB assembly files.

    BOM: Comment, Designator, Footprint, LCSC Part #
    CPL: Designator, Mid X, Mid Y, Layer, Rotation

Rotation corrections come from a CSV of (pattern, correction) rows. A
pattern that is an LCSC code (C12345) matches that part exactly; anything
else is a regex searched in the footprint name. The first match wins, so put
exact LCSC rules first. This is the format used by matthewlai's
JLCKicadTools database, which kicad-jlcpcb-tools also uses.
"""

from __future__ import annotations

import csv
import re
from collections import OrderedDict
from pathlib import Path

from .altium_csv import LCSC_RE, column, designators, lcsc_column, read_table

MIL_TO_MM = 0.0254


def load_rotations(path: Path) -> list[tuple[str, float]]:
    if not path.exists():
        return []
    rules = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) < 2 or row[0].startswith("#"):
                continue
            try:
                rules.append((row[0].strip(), float(row[1])))
            except ValueError:
                continue  # header row
    return rules


def correction(rules: list[tuple[str, float]], footprint: str, lcsc: str) -> float:
    for pattern, delta in rules:
        if LCSC_RE.match(pattern):
            if pattern.upper() == lcsc.upper():
                return delta
        elif re.search(pattern, footprint):
            return delta
    return 0.0


def _number(value: str) -> tuple[float, str]:
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*(mm|mil)?", value)
    if not m:
        raise ValueError(f"not a coordinate: {value!r}")
    return float(m.group(1)), (m.group(2) or "")


def convert_bom(rows: list[dict]) -> tuple[list[dict], list[str], dict[str, str]]:
    """Group BOM rows by LCSC code. Returns (bom rows, unassigned designators, designator->lcsc)."""
    des_col = column(rows[0], "Designator")
    lcsc_col = lcsc_column(rows)
    comment_col = column(rows[0], "Comment", "Value")
    fp_col = column(rows[0], "Footprint", "Footprint Ref", "Package")

    groups: OrderedDict[str, dict] = OrderedDict()
    missing, by_designator = [], {}
    for r in rows:
        refs = designators(r[des_col])
        code = r[lcsc_col].upper() if lcsc_col else ""
        if not LCSC_RE.match(code):
            missing += refs
            continue
        g = groups.setdefault(code, {
            "Comment": r.get(comment_col, "") if comment_col else "",
            "Designator": [],
            "Footprint": r.get(fp_col, "") if fp_col else "",
            "LCSC Part #": code,
        })
        g["Designator"] += refs
        for d in refs:
            by_designator[d] = code
    bom = [dict(g, Designator=",".join(g["Designator"])) for g in groups.values()]
    return bom, missing, by_designator


def convert_cpl(rows: list[dict], lcsc_by_designator: dict[str, str],
                rules: list[tuple[str, float]]) -> list[dict]:
    first = rows[0]
    des_col = column(first, "Designator")
    x_col = column(first, "Center-X(mm)", "Center-X(mil)", "Center-X", "Mid X", "Ref-X(mm)", "Ref-X(mil)", "Ref-X")
    y_col = column(first, "Center-Y(mm)", "Center-Y(mil)", "Center-Y", "Mid Y", "Ref-Y(mm)", "Ref-Y(mil)", "Ref-Y")
    layer_col = column(first, "Layer")
    rot_col = column(first, "Rotation")
    fp_col = column(first, "Footprint")
    if not all((des_col, x_col, y_col, layer_col, rot_col)):
        raise SystemExit("Pick & Place file needs Designator, Center-X, Center-Y, Layer and Rotation columns")
    header_mil = "mil" in x_col.lower()

    out = []
    for r in rows:
        ref = r[des_col]
        if ref not in lcsc_by_designator:
            continue  # not assembled (no LCSC code, or DNP in the BOM)
        x, ux = _number(r[x_col])
        y, uy = _number(r[y_col])
        if ux == "mil" or (not ux and header_mil):
            x *= MIL_TO_MM
        if uy == "mil" or (not uy and header_mil):
            y *= MIL_TO_MM
        layer = "Bottom" if r[layer_col].lower().startswith("b") else "Top"
        rot = float(r[rot_col] or 0)
        rot = (rot + correction(rules, r.get(fp_col, "") if fp_col else "", lcsc_by_designator[ref])) % 360
        out.append({
            "Designator": ref,
            "Mid X": f"{x:.4f}mm",
            "Mid Y": f"{y:.4f}mm",
            "Layer": layer,
            "Rotation": f"{rot:g}",
        })
    return out


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def run(bom_path: Path, pnp_path: Path, out_dir: Path, rotations: Path) -> tuple[Path, Path, list[str]]:
    bom, missing, by_des = convert_bom(read_table(bom_path))
    cpl = convert_cpl(read_table(pnp_path), by_des, load_rotations(rotations))
    stem = Path(bom_path).stem
    bom_out = out_dir / f"{stem}_JLCPCB_BOM.csv"
    cpl_out = out_dir / f"{stem}_JLCPCB_CPL.csv"
    write_csv(bom_out, bom, ["Comment", "Designator", "Footprint", "LCSC Part #"])
    write_csv(cpl_out, cpl, ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    return bom_out, cpl_out, missing
